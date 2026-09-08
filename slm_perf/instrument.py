"""Instrument source in memory in an explicitly launched process. No file edits.

Python's original AST remains the workload; wrappers preserve arguments, returns,
exceptions and control flow. Detailed per-function coverage is provided by cProfile.
"""
import ast
import hashlib
import importlib.abc
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = {f'slm.{name}' for name in ('train','data','report','code_eval','interface_eval','prepare','prepare_v2','audit_v2','collect','rescore','overnight','sixhour','inference','broad_eval','validation','campaign')}
MODULES.add('slm_perf.workload')
MODULES.add('random_search.pilot')
MODULES.add('experiments.size_report')
MODULES.update({'future_eval.analyze','future_eval.prepare','future_eval.queue','future_eval.metrics'})
MODULES.update({'experiments.prepare_broad', 'experiments.prepare_checks'})
FUNCTIONS = {'reference_loss','token_snapshots','fresh_model','teacher_score','generate_probe','encode_rows','split_tasks','analyze','prepare','sql_result','sql_compare','error_tags','scan','main','step','dev_eval','emit','atomic_json','checkpoint','restore','evaluate','generate',
             'prepare','build','context_key','sql_query','score_general','final_answer','run_job','wait_child','validate_plan','control_ready','greedy_generate','cached_forward','report','run_python','score','load_tasks','fetch','fetch_spider_schemas','write_catalog',
             'convert','converted','reference_solutions','exclude_shared_code_groups','audit',
             'Sampler.__init__','Sampler.batch','wait_until','write_json','sha',
             'CodeOverlap.add','CodeOverlap.overlaps'}
CALLS = {
    'mx.eval': 'device.execute_and_wait',
    'mx.array': 'array.wrap_host',
    'grad_fn': 'graph.forward_backward',
    'grad': 'graph.forward_backward',
    'update': 'graph.training_update',
    'optim.clip_grad_norm': 'graph.gradient_clip',
    'optimizer.update': 'graph.optimizer_update',
    'opt.update': 'graph.optimizer_update',
    'model': 'graph.model_forward',
    'mx.savez': 'checkpoint.optimizer_save',
    'mx.load': 'checkpoint.optimizer_load',
    'pq.read_table': 'data.parquet_read',
    'shutil.copy2': 'io.copy',
    'shutil.rmtree': 'io.cleanup',
    'subprocess.Popen': 'subprocess.start',
    'subprocess.run': 'subprocess.run_and_wait',
}
METHODS = {'save_weights':'checkpoint.weights_save', 'load_weights':'checkpoint.weights_load',
           'item':'device.scalar_and_wait',
           'encode_batch':'tokenizer.encode_batch', 'encode':'tokenizer.encode', 'decode':'tokenizer.decode',
           'to_pylist':'data.arrow_to_python', 'write_text':'io.write_text', 'read_text':'io.read_text',
           'read_bytes':'io.read_bytes', 'tofile':'io.array_write', 'wait':'subprocess.wait'}


def dotted(node):
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted(node.value)
        return prefix + '.' + node.attr if prefix else ''
    return ''


class Instrument(ast.NodeTransformer):
    def __init__(self, module):
        self.module = module
        self.scope = []
        self.coverage = []

    def visit_ClassDef(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()
        return node

    def visit_FunctionDef(self, node):
        self.scope.append(node.name)
        name = '.'.join(self.scope)
        # A with-span across a generator yield would misattribute the consumer's time.
        generator = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node))
        selected = node.name in FUNCTIONS or name in FUNCTIONS
        self.generic_visit(node)
        self.scope.pop()
        if selected and not generator:
            if self.module == 'slm.train' and node.name == 'emit':
                node.body.append(ast.Expr(ast.Call(ast.Attribute(ast.Name('_slm_perf',ast.Load()), 'event',ast.Load()), [ast.Name('event',ast.Load())], [])))
            # Preserve docstrings and therefore __doc__.
            docs = node.body[:1] if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str) else []
            body = node.body[len(docs):]
            context = ast.Call(ast.Attribute(ast.Name('_slm_perf',ast.Load()),'span',ast.Load()), [ast.Constant(self.module+'.'+name)], [])
            node.body = docs + [ast.With([ast.withitem(context)],body)]
            self.coverage.append(dict(kind='function',name=name,line=node.lineno))
        return node

    def visit_Call(self, node):
        """Wrap selected calls inside functions while preserving argument evaluation order."""
        original = dotted(node.func)
        label = CALLS.get(original)
        if self.module=='slm.train' and original=='digest':
            label='data.checksum'
        if label is None and isinstance(node.func,ast.Attribute):
            label = METHODS.get(node.func.attr)
            if node.func.attr in {'encode','encode_batch','decode'} and dotted(node.func.value) not in {'tok','tokenizer'}:
                label = None
        # Only calls inside functions: do not perturb class/global initialization contracts.
        node = self.generic_visit(node)
        if not self.scope or not label:
            return node
        self.coverage.append(dict(kind='call',name=original or ast.unparse(node.func),label=label,line=node.lineno))
        return ast.copy_location(ast.Call(ast.Attribute(ast.Name('_slm_perf',ast.Load()),'call',ast.Load()),
                                         [ast.Constant(label),node.func,*node.args],node.keywords),node)


def transformed(source, filename, module):
    tree = ast.parse(source, filename)
    transform = Instrument(module)
    tree = ast.fix_missing_locations(transform.visit(tree))
    return compile(tree,filename,'exec'),transform.coverage


class Loader(importlib.abc.Loader):
    def __init__(self, name, path, monitor):
        self.name,self.path,self.monitor = name,path,monitor

    def create_module(self, spec): return None

    def get_code(self, fullname):
        source = self.path.read_text()
        code, coverage = transformed(source,str(self.path),self.name)
        self.monitor.metadata.setdefault('coverage',{})[self.name] = coverage
        self.monitor.metadata.setdefault('source_sha256',{})[str(self.path.relative_to(ROOT))] = hashlib.sha256(source.encode()).hexdigest()
        return code

    def exec_module(self, module):
        module.__dict__['_slm_perf'] = self.monitor
        exec(self.get_code(self.name),module.__dict__)

    def is_package(self, fullname): return False


class Finder(importlib.abc.MetaPathFinder):
    def __init__(self, monitor): self.monitor = monitor

    def find_spec(self, fullname, path=None, target=None):
        if fullname in MODULES:
            source = ROOT / (fullname.replace('.','/')+'.py')
            if source.exists():
                return importlib.util.spec_from_file_location(fullname,source,loader=Loader(fullname,source,self.monitor))
