"""CPU-only budget and comparison helpers."""
import hashlib
import json
import math


def signature(plan,job):
    inputs=dict(job=job,data=plan['data_manifest_sha256'],parent=plan['parent_checkpoint'],
                parent_weights=plan['parent_weights_sha256'])
    return hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()


def validate_plan(plan):
    if len(plan['jobs'])!=8 or len(set(plan['jobs']))!=8:raise ValueError('Eight unique jobs required')
    if not 0<plan['budget_seconds']<=86400:raise ValueError('Invalid remaining budget')
    if plan['previous_budget_spent_seconds']+plan['budget_seconds']!=86400:
        raise ValueError('Budget reset or extension')
    required=8*7200+33*630+plan['control_seconds']+plan['report_seconds']
    if required+60>plan['budget_seconds']:raise ValueError('Stage caps exceed remaining budget')
    return required


def phase_for_elapsed(elapsed,limit,reserve):
    if not all(math.isfinite(x) for x in [elapsed,limit,reserve]) or limit<=reserve or reserve<0:
        raise ValueError('Invalid wall budget')
    return 'checkpoint' if elapsed>=limit-reserve else 'train'


def differences(a,b):
    return dict(accuracy=b['accuracy']-a['accuracy'],answer_loss=b['answer_loss']-a['answer_loss'],
                families={k:b['families'][k]-a['families'][k] for k in a['families']})
