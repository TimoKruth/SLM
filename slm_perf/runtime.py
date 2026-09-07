"""Nested host-wall timing without GPU synchronization or per-event disk writes."""
from collections import defaultdict
from contextlib import contextmanager
import cProfile
import json
import math
from pathlib import Path
import pstats
import time
import sys

SCHEMA = 1


class Stats:
    """Constant-space logarithmic histogram; percentile values are bin upper bounds."""
    def __init__(self):
        self.count = self.total = self.self_ns = self.maximum = 0
        self.minimum = None
        self.bins = defaultdict(int)

    def add(self, elapsed, own):
        self.count += 1
        self.total += elapsed
        self.self_ns += own
        self.minimum = elapsed if self.minimum is None else min(self.minimum, elapsed)
        self.maximum = max(self.maximum, elapsed)
        # Approximately 5% bucket resolution, with nanosecond floor.
        self.bins[math.ceil(math.log(max(1, elapsed), 1.05))] += 1

    def percentile(self, q):
        target = math.ceil(self.count * q)
        seen = 0
        for bucket, count in sorted(self.bins.items()):
            seen += count
            if seen >= target:
                return min(self.maximum, 1.05 ** bucket) / 1e9
        return 0

    def export(self):
        return dict(count=self.count, inclusive_seconds=self.total / 1e9,
                    self_seconds=self.self_ns / 1e9, mean_seconds=self.total / max(1, self.count) / 1e9,
                    min_seconds=(self.minimum or 0) / 1e9, max_seconds=self.maximum / 1e9,
                    p50_seconds_approx=self.percentile(.5), p95_seconds_approx=self.percentile(.95))


class Monitor:
    def __init__(self, output, mode='light', warmup_steps=10, flush_seconds=60,
                 detail_seconds=30, clock=time.perf_counter_ns):
        self.output = Path(output)
        self.mode, self.warmup_steps = mode, warmup_steps
        self.flush_seconds, self.detail_seconds = flush_seconds, detail_seconds
        self.clock = clock
        self.started = self.last_flush = clock()
        self.stack, self.stats = [], defaultdict(Stats)
        self.steps = 0
        self.hook_ns = self.io_ns = 0
        self.errors = []
        self.metadata, self.events = {}, []
        self.first_event = self.last_event = None
        self.profile = None
        self.profile_seconds = 0
        self.trace = []
        self.max_trace_events = 10000
        self.trace_dropped = 0
        self.disabled = False
        self.ended = None
        self.children = []
        self.output.mkdir(parents=True, exist_ok=True)

    def start_detail(self):
        if self.mode == 'detail':
            self.profile = cProfile.Profile()
            self.profile.enable()
            self.profile_started = self.clock()

    def stop_detail(self):
        if self.profile is not None:
            self.profile.disable()
            self.profile_seconds = (self.clock() - self.profile_started) / 1e9
            self.finished_profile = self.profile
            self.profile = None

    @contextmanager
    def span(self, name):
        if self.disabled:
            yield
            return
        before = self.clock()
        if name == 'slm.train.main.step' or name == 'slm_perf.workload.step':
            name += '.warmup' if self.steps < self.warmup_steps else '.steady'
            self.steps += 1
        path = '/'.join([self.stack[-1]['path'], name]) if self.stack else name
        frame = dict(path=path, start=self.clock(), children=0)
        self.stack.append(frame)
        self.hook_ns += frame['start'] - before
        try:
            yield
        finally:
            end = self.clock()
            self.stack.pop()
            elapsed = end - frame['start']
            self.stats[path].add(elapsed, max(0, elapsed - frame['children']))
            if self.mode == 'detail' and self.profile is not None:
                if len(self.trace) < self.max_trace_events:
                    self.trace.append(dict(name=name, cat='host_wall', ph='X', pid=1, tid=1,
                                           ts=(frame['start'] - self.started)/1000, dur=elapsed/1000))
                else:
                    self.trace_dropped += 1
                if (end - self.profile_started)/1e9 >= self.detail_seconds:
                    self.stop_detail()
            done = self.clock()
            # Charge the parent's child wall interval including instrumentation bookkeeping.
            # Hook overhead is separately estimated, never subtracted from throughput.
            if self.stack:
                self.stack[-1]['children'] += done - before
            self.hook_ns += done - end

    def call(self, label, fn, *args, **kwargs):
        # Propagate explicit monitoring to supervised Python modules only.
        # External sandboxed candidate programs and caffeinate remain untouched.
        if label in ('subprocess.start', 'subprocess.run_and_wait') and args:
            command = args[0]
            if isinstance(command, (list, tuple)) and '-m' in command:
                index = command.index('-m')
                from .instrument import MODULES
                if index + 1 < len(command) and command[index+1] in MODULES:
                    module = command[index+1]
                    destination = self.output / 'children' / f'{len(self.children):03d}-{module}'
                    command = [*command[:index], '-m', 'slm_perf', 'run', '--mode', self.mode,
                               '--output', str(destination), '--warmup-steps', str(self.warmup_steps),
                               '--flush-seconds', str(self.flush_seconds), '--detail-seconds', str(self.detail_seconds),
                               '--module', module, '--', *command[index+2:]]
                    self.children.append(dict(module=module, output=str(destination)))
                    args = (command, *args[1:])
        with self.span(label):
            return fn(*args, **kwargs)

    def event(self, event):
        """Use counters already computed by the application; no extra device reads."""
        if self.disabled:
            return
        now = self.clock()
        entry = {k: event[k] for k in ('event','step','tokens','loss','lr','mlx_peak_gb','system_available_gb') if k in event}
        entry['elapsed_seconds'] = (now - self.started)/1e9
        if self.first_event is None:
            self.first_event = entry
        self.last_event = entry
        # Keep bounded history; cumulative totals and timing histograms are never truncated.
        self.events.append(entry)
        if len(self.events) > 2000:
            self.events = self.events[-2000:]
        if (now - self.last_flush)/1e9 >= self.flush_seconds:
            self.flush('running')

    def result(self, status):
        elapsed = ((self.ended if self.ended is not None else self.clock()) - self.started)/1e9
        first, last = self.first_event or {}, self.last_event or {}
        tokens = last.get('tokens', 0) - first.get('tokens', 0)
        return dict(schema=SCHEMA, status=status, mode=self.mode, metadata=self.metadata,
                    elapsed_seconds=elapsed, warmup_steps=self.warmup_steps,
                    flush_seconds=self.flush_seconds, detail_limit_seconds=self.detail_seconds,
                    observed_training_steps=self.steps, training_tokens_delta=tokens,
                    end_to_end_tokens_per_second=tokens/elapsed if elapsed else 0,
                    hook_bookkeeping_seconds_estimate=self.hook_ns/1e9,
                    monitor_io_seconds=self.io_ns/1e9, profile_capture_seconds=self.profile_seconds,
                    histogram='p50/p95: logarithmic bucket upper bounds, ~5% resolution',
                    timing_semantics='Host wall time. GPU execution is only included at existing eval/item/save boundaries; graph construction is not kernel time. Nested inclusive times must not be added.',
                    phases={k: v.export() for k,v in self.stats.items()}, children=self.children,
                    first_event=self.first_event, last_event=self.last_event,
                    recent_events=self.events, trace_dropped=self.trace_dropped, errors=self.errors)

    def flush(self, status):
        begin = self.clock()
        try:
            payload = self.result(status)
            temporary = self.output/'timings.json.tmp'
            temporary.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')
            temporary.replace(self.output/'timings.json')
        except (OSError, ValueError) as exc:
            # Monitoring failure must not fail a training step or consume unbounded memory.
            self.errors.append(type(exc).__name__ + ': ' + str(exc))
            self.disabled = True
        finally:
            self.last_flush = self.clock()
            self.io_ns += self.last_flush - begin

    def finish(self, status='completed'):
        if self.ended is None:
            self.ended = self.clock()
        self.stop_detail()
        if hasattr(self, 'finished_profile'):
            try:
                self.finished_profile.dump_stats(str(self.output/'python.prof'))
                stats = pstats.Stats(self.finished_profile)
                rows = [dict(file=k[0], line=k[1], function=k[2], primitive_calls=v[0], calls=v[1], self_seconds=v[2], cumulative_seconds=v[3]) for k,v in stats.stats.items()]
                (self.output/'python-functions.json').write_text(json.dumps(sorted(rows, key=lambda r:r['self_seconds'], reverse=True), indent=2)+'\n')
                (self.output/'trace.json').write_text(json.dumps({'traceEvents':self.trace,'displayTimeUnit':'ms'})+'\n')
            except OSError as exc:
                self.errors.append(str(exc))
        self.flush(status)
