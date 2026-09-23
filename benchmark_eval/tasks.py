"""Explicit answer contracts. References are never used to build prompts/extract answers."""
import ast
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

MARKER = 'Final answer:'


def load_tasks(path):
    path = Path(path)
    if path.suffix == '.jsonl':
        raw = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        value = json.loads(path.read_text())
        raw = value['general'] if isinstance(value, dict) else value
    tasks = []
    for row in raw:
        if 'original_id' in row:
            kind = 'legacy_proxy'
            if row['source'] in {'apps', 'code_contests', 'mbpp', 'spider', 'wikisql', 'samsum', 'hellaswag', 'piqa'}:
                kind = 'external'
            task = dict(id=str(row['original_id']), source=row['source'], prompt=row['prompt'],
                        kind=kind, reference=row['answer'], legacy=row)
        else:
            task = dict(row)
        validate_task(task)
        tasks.append(task)
    identities = [(t['source'], t['id']) for t in tasks]
    if not tasks or len(set(identities)) != len(identities):
        raise ValueError('Empty suite or duplicate task identities')
    return tasks


def validate_task(task):
    for key in ('id', 'source', 'prompt', 'kind'):
        if not isinstance(task.get(key), str) or not task[key].strip():
            raise ValueError(f'Missing task {key}')
    if task['kind'] not in {'choice', 'text', 'number', 'external', 'legacy_proxy'}:
        raise ValueError('Unsupported grader/task kind')
    if not isinstance(task.get('system', ''), str):
        raise ValueError('System instructions must be text')
    if task.get('requires_tools') or task.get('requires_images'):
        raise ValueError('This runner is text-only; use the official tool/image harness')
    if task['kind'] == 'choice':
        choices = task.get('choices')
        if not isinstance(choices, list) or not 2 <= len(choices) <= 26 or not all(isinstance(x, str) and x.strip() for x in choices):
            raise ValueError('Choice tasks require 2–26 text choices')
        if task.get('reference') not in [chr(65+i) for i in range(len(choices))]:
            raise ValueError('Choice reference must be a valid letter')
    elif task['kind'] != 'external' and not isinstance(task.get('reference'), str):
        raise ValueError('Scored task requires a string reference')
    if task['kind'] == 'number' and number(task['reference']) is None:
        raise ValueError('Invalid numeric reference')


def prompt_for(task):
    # Never read reference/answer here, including for legacy tasks.
    prompt = task['prompt']
    if task['kind'] == 'external':
        return prompt  # Official instruction/code/agent graders have their own contracts.
    if task['kind'] == 'choice':
        prompt += '\n\n' + '\n'.join(f'{chr(65+i)}. {v}' for i,v in enumerate(task['choices']))
        contract = 'the single option letter'
    elif task['kind'] == 'number':
        contract = 'the numeric result, without units'
    elif task['kind'] == 'legacy_proxy':
        source = task['source']
        contract = 'the answer only, without explanation'
        if source in {'gsm8k', 'tabmwp'}:
            contract = 'the numeric result only, without units'
        elif source == 'math':
            contract = 'the final mathematical expression, without a box wrapper'
        elif source in {'aqua_rat', 'qasc'}:
            contract = 'the option letter followed by its exact option text, as shown in the question'
        elif task['legacy'].get('choices'):
            contract = 'the exact text of the selected option (not its letter)'
        elif source == 'go_emotions':
            contract = 'the emotion labels separated by commas'
    else:
        contract = 'the short answer only'
    return prompt + f'\n\nYou may explain your reasoning. End with exactly one line in this format:\n{MARKER} <{contract}>\nDo not put Markdown formatting around that final line.'


def input_text(task):
    """Flatten system instructions for the SLM; Qwen receives native message roles."""
    prompt = prompt_for(task)
    return ('System instructions:\n'+task['system']+'\n\n'+prompt) if task.get('system') else prompt



def extract(text):
    """Unambiguous final line or a bare answer; no reference-dependent search."""
    text = text.strip()
    found = re.findall(r'^[ \t]*Final answer:[ \t]*(.*?)[ \t]*$', text, re.M | re.I)
    if found:
        values = [x.strip() for x in found]
        if len(values) != 1 or not values[0] or text.splitlines()[-1].strip().casefold() != ('Final answer: '+values[0]).casefold():
            return None
        return values[0]
    # Bare single-line responses accepted; prose won't match by substring.
    return text if text and '\n' not in text else None


def normalized(text):
    return ' '.join(text.strip().casefold().split())


def number(text):
    # No eval/sympy, units, arbitrary comma stripping or answer search.
    text = text.strip()
    if not re.fullmatch(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', text):
        return None
    try:
        value = Decimal(text)
        return value if value.is_finite() else None
    except InvalidOperation:
        return None


def legacy_scorer():
    path = Path(__file__).resolve().parents[1]/'slm/broad_eval.py'
    tree = ast.parse(path.read_text())
    tree.body = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module == 'train')]
    scope = {'__name__':'slm.contract_scoring', '__package__':'slm'}
    exec(compile(tree, str(path), 'exec'), scope)
    return scope['score_general']


def grade(task, text, legacy=None):
    if task['kind'] == 'external':
        return dict(status='unscored_external_grader_required', correct=None)
    value = extract(text)
    if value is None:
        return dict(status='format_error', correct=False)
    if task['kind'] == 'choice':
        if value not in [chr(65+i) for i in range(len(task['choices']))]:
            return dict(status='format_error', correct=False)
        correct = value == task['reference']
    elif task['kind'] == 'number':
        parsed = number(value)
        if parsed is None:
            return dict(status='format_error', correct=False)
        correct = parsed == number(task['reference'])
    elif task['kind'] == 'legacy_proxy':
        if legacy is None:
            legacy = legacy_scorer()
        if task['source'] == 'gsm8k':
            value = '#### '+value
        elif task['source'] == 'math':
            value = '\\boxed{'+value+'}'
        elif task['source'] in {'aqua_rat', 'qasc'}:
            value = 'Answer: '+value
        metric = legacy(task['legacy'], value)
        if not metric.get('reference_parseable', True):
            return dict(status='unscored_invalid_reference', correct=None)
        if 'correct' not in metric:
            return dict(status='unscored_external_grader_required', correct=None)
        correct = bool(metric['correct'])
    else:
        correct = normalized(value) == normalized(task['reference'])
    return dict(status='correct' if correct else 'incorrect', correct=correct)
