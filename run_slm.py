"""Project entry point for future runs; monitoring defaults live in run_defaults.json."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parent


def command(argv, defaults=None, session=None):
    """Build the monitored argv without launching work or creating output directories."""
    defaults = json.loads((ROOT / 'run_defaults.json').read_text()) if defaults is None else defaults
    parser = argparse.ArgumentParser(description=__doc__, epilog='Additional arguments, e.g. --data or --until, are forwarded unchanged to the selected module.')
    parser.add_argument('--run', required=True)
    parser.add_argument('--module', default='slm.sixhour', choices=['slm.sixhour', 'slm.overnight', 'slm.train', 'slm.report', 'slm.code_eval', 'slm.interface_eval', 'slm.broad_eval', 'slm.validation', 'slm.campaign', 'future_eval.analyze', 'future_eval.prepare', 'future_eval.queue', 'random_search.pilot', 'next_run.performance', 'research.trial', 'research.campaign', 'study.queue', 'study.campaign', 'study.trial', 'study.health'])
    parser.add_argument('--monitoring', choices=['off', 'light', 'detail'], default=defaults['monitoring'])
    args, extra = parser.parse_known_args(argv)
    if args.monitoring not in {'off', 'light', 'detail'}:
        parser.error('Invalid monitoring default')
    if defaults['warmup_steps'] < 0 or defaults['flush_seconds'] <= 0 or defaults['detail_seconds'] <= 0:
        parser.error('Invalid monitoring timing defaults')
    result = [sys.executable, '-m', 'slm_perf', 'run', '--mode', args.monitoring]
    if args.monitoring != 'off':
        session = session or datetime.now().astimezone().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
        output = (ROOT / args.run).resolve() / 'performance' / session
        result += ['--output', str(output), '--warmup-steps', str(defaults['warmup_steps']),
                   '--flush-seconds', str(defaults['flush_seconds']), '--detail-seconds', str(defaults['detail_seconds'])]
    return result + ['--module', args.module, '--', '--run', args.run, *extra]


def main():
    """Replace this process with the project-configured launcher from the repository root."""
    arguments = command(sys.argv[1:])
    os.chdir(ROOT)
    os.execv(sys.executable, arguments)


if __name__ == '__main__':
    main()
