"""Failure classes and archival boundaries shared by orchestration and tests."""
from pathlib import Path


class RecoverableStop(RuntimeError):
    """Infrastructure requires attention; unstarted work must remain pending."""


def failure_kind(text):
    # MLX can abort in native code (SIGABRT, exit -6), without a Python traceback
    # or MTLCommandBufferErrorDomain. Match the driver diagnostic, not exit -6:
    # unrelated native aborts must not trigger GPU recovery.
    if any(s in text for s in ['Unable to reach MTLCompilerService','Connection init failed at lookup',
                               'Caused GPU Hang Error','kIOGPUCommandBufferCallbackErrorHang',
                               'GPU device was lost','MTLCommandBufferErrorDomain','Another GPU workload holds',
                               'An SLM GPU job is active','An SLM GPU job became active']):
        return 'gpu_service'
    if any(s in text for s in ['Available RAM below','MemoryError','out of memory','Insufficient Memory']):
        return 'memory'
    if 'Nonfinite objective or gradient' in text:return 'numerical_trial_failure'
    return 'trial_failure'


def archive_failed_output(root,module,model_run,args,label):
    """Never delete results, and never move the historical parent for an eval retry."""
    root=Path(root).resolve()
    if module=='study.trial':target=Path(model_run).resolve()
    elif module=='slm.broad_eval':target=Path(args[args.index('--output')+1]).resolve()
    elif module=='study.health':target=Path(model_run).resolve()
    else:raise RecoverableStop('Retry unsupported for module '+module)
    if not target.is_relative_to(root) or target==root:
        raise RecoverableStop('Refusing to archive output outside new campaign')
    destination=root/'attempts'/label/'output'
    if destination.exists():raise RecoverableStop('Retry archive exists; no repeated retry')
    if target.exists():
        destination.parent.mkdir(parents=True,exist_ok=True)
        target.rename(destination)
    return destination


def retry_seconds(stage_seconds,elapsed,global_remaining):
    """Recovery time counts against both the stage and campaign; no reset."""
    return max(0.,min(stage_seconds-elapsed,global_remaining-15))
