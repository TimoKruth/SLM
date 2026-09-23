"""Monitored launcher for the new evaluator, leaving frozen historical launchers unchanged."""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime
import uuid


def main():
    root = Path(__file__).resolve().parents[1]
    defaults = json.loads((root/'run_defaults.json').read_text())
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True)
    args, extra = p.parse_known_args()
    if '--start' not in extra:
        p.error('No inference without explicit --start; use benchmark_eval.prepare first')
    # Register only in this process. Do not alter files pinned by previous campaigns.
    from slm_perf import instrument
    from slm_perf import __main__ as monitoring
    instrument.MODULES.add('benchmark_eval.runner')
    monitoring.SUPERVISOR_MODULES.add('benchmark_eval.runner')
    session = datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    output = Path(args.run).resolve()/'performance'/session
    sys.argv = ['slm_perf','run','--mode',defaults['monitoring'],'--output',str(output),
                '--warmup-steps',str(defaults['warmup_steps']),'--flush-seconds',str(defaults['flush_seconds']),
                '--detail-seconds',str(defaults['detail_seconds']),
                '--module','benchmark_eval.runner','--','--run',args.run,*extra]
    monitoring.main()


if __name__ == '__main__':
    main()
