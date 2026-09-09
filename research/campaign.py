"""One finite serial research round with hard deadlines, controls and paired selection."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from slm_perf.after_idle import stop_process
from .common import read, write, sha, quality, contrast, parent_guard

ROOT = Path(__file__).resolve().parents[1]


def variant_orders(plan):
    names = [v['name'] for v in plan['variants']]
    if len(names) != 3 or len(set(names)) != 3 or names[0] != 'baseline':
        raise ValueError('Expected baseline and two distinct interventions')
    if plan['repetitions'] != 2 or len(plan['data_order_seeds']) != 2:
        raise ValueError('Expected two data-order repetitions')
    return [names, [names[2], names[0], names[1]]]


def maximum_stage_budget(plan):
    """Sum declared process caps, including optional untouched-parent confirmation."""
    return (plan['control_seconds'] + 6 * plan['trial_seconds'] + 7 * plan['evaluation_process_seconds']
            + (5 if plan.get('require_parent_guard') else 4)
            * plan.get('confirmation_process_seconds', plan['evaluation_process_seconds']))


def matched(results):
    keys = ['additional_tokens', 'additional_steps', 'source_tokens', 'batches_sha256', 'initial_sampler', 'final_sampler']
    if any(r['status'] != 'completed' for r in results):
        raise ValueError('Incomplete fixed-work trial')
    if any(any(r[k] != results[0][k] for k in keys) for r in results[1:]):
        raise ValueError('Trial exposure differs within repetition')


def report(run, state):
    lines = ['# Begrenzte Forschungsrunde', '', 'Status: ' + state['status'], '',
             '27,3M-Modell ab letztem Sechs-Stunden-Checkpoint. FP32, 32 unveränderte Trainingsquellen. '
             'Drei Varianten × zwei Datenreihenfolgen; keine unabhängigen Initialisierungs-Seeds. '
             'Je Versuch 3M zusätzliche Tokens, keine automatische Übernahme oder Verlängerung.', '',
             'Gewichteter Trainingsloss ist zwischen Varianten nicht vergleichbar. '
             'Alle Modelle erhalten dieselbe freie Antwortauswertung und denselben Referenz-Antwortloss. '
             'Entwicklungsproxies; Code-/SQL-Ausführung und offene Textqualität bleiben unbewertet. '
             'Keine Aussage über externe Benchmark-Übertragung oder statistische Signifikanz.', '',
             '| Variante | Datenreihenfolge | Zusatz-Tokens | Sekunden | Auswahl-Genauigkeit (Familien-Makro) | Antwortloss |',
             '| --- | --- | ---: | ---: | ---: | ---: |']
    if (run / 'parent-quality.json').exists():
        parent = read(run / 'parent-quality.json')
        lines.append(f"| Ausgangsmodell ohne Zusatztraining | — | 0 | — | {parent['accuracy']:.2%} | {parent['answer_loss']:.4f} |")
    for trial in sorted((run / 'trials').glob('*')):
        if not (trial / 'result.json').exists():
            continue
        r, c = read(trial / 'result.json'), read(trial / 'config.json')
        q = None
        if (trial / 'search/summary.json').exists():
            try:
                q = quality(read(trial / 'search/summary.json'))
            except (ValueError, KeyError, TypeError):
                pass  # Preserve the failure report; partial evaluation is never scored.
        lines.append(f"| {c['intervention']['name']} | {c['repetition']} | {r['additional_tokens']:,} | {r['elapsed_seconds']:.1f} | "
                     + (f"{q['accuracy']:.2%} | {q['answer_loss']:.4f} |" if q else '— | — |'))
    if (run / 'selection.json').exists():
        s = read(run / 'selection.json')
        lines += ['', 'Für Gegenprüfung ausgewählt: ' + s['contender'] + '.',
                  'Auswahlkriterium erfüllt: ' + str(s['search_passed']) + '.']
    if (run / 'confirmation.json').exists():
        c = read(run / 'confirmation.json')
        lines += ['Gegenprüfung bestanden: ' + str(c['passes_screen']) + '.',
                  'Bestätigter Kandidat nach beiden Kriterien: ' + str(c['confirmed_candidate']) + '.',
                  'Gepaarte Änderungen der Familien-Makrogenauigkeit: ' + str(c['accuracy_deltas']) + '.',
                  'Mittlere Antwortloss-Änderung: ' + str(c['mean_answer_loss_delta']) + '.',
                  'Familienänderungen: ' + str(c['family_deltas']) + '.']
        if 'parent_guard' in c:
            lines += ['Zusätzliche Gegenprüfung gegen unverändertes Ausgangsmodell: ' + str(c['parent_guard']) + '.']
    if state.get('error'):
        lines += ['', 'Abbruchgrund: ' + state['error']]
    lines += ['', 'Die Auswahl- und Gegenprüfungsaufgaben sind gruppengetrennt. '
              'Die Gegenprüfung schließt historische 886er-Aufgabengruppen aus, kann aber früheren Inline-Dev-Loss beeinflusst haben. '
              'Abdeckung: suite-audit.json. Jede Auswertung enthält Resultate je Aufgabe und Fähigkeitsbereich.',
              '', 'Zeitbudget: maximal 60 Minuten ab Kampagnenstart einschließlich Kontrollen, Kompilierung, Speicherung und GPU-Auswertung. '
              'Die Frist wird nicht erneuert. Vollständige Prozesshistorie und Fehler: status.json.']
    (run / 'REPORT.md').write_text('\n'.join(lines) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', required=True)
    args = p.parse_args()
    run = Path(args.run).resolve()
    plan = read(run / 'plan.json')
    orders = variant_orders(plan)
    if plan.get('require_parent_guard') and maximum_stage_budget(plan) > plan['gpu_wall_budget_seconds'] - 30:
        raise ValueError('Declared stage caps exceed global budget with cleanup reserve')
    if (run / 'status.json').exists():
        raise ValueError('One-shot campaign already started; deadline and budget cannot reset')
    # Read-only verification occurs before any GPU allocation.
    frozen = read(run / 'frozen-inputs.json')
    for path, digest in frozen.items():
        if sha(path) != digest:
            raise ValueError('Frozen input changed: ' + path)
    stats = {p: (Path(p).stat().st_size, Path(p).stat().st_mtime_ns) for p in frozen}
    started = time.time()
    deadline = time.monotonic() + plan['gpu_wall_budget_seconds'] - 10
    state = dict(status='running', pid=os.getpid(), started=datetime.now().astimezone().isoformat(),
                 deadline=datetime.fromtimestamp(started + plan['gpu_wall_budget_seconds']).astimezone().isoformat(),
                 stages=[], phase='controls', budget_seconds=plan['gpu_wall_budget_seconds'])
    write(run / 'status.json', state)
    stop = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda number, frame: stop.append(number))
    caffeine = subprocess.Popen(['/usr/bin/caffeinate', '-is', '-w', str(os.getpid())])

    def run_job(name, module, model_run, arguments, seconds):
        if stop or (run / 'STOP').exists():
            raise InterruptedError('Requested stop')
        if time.monotonic() + seconds > deadline:
            raise TimeoutError('Remaining global budget insufficient for next complete stage')
        for path, stamp in stats.items():
            if (Path(path).stat().st_size, Path(path).stat().st_mtime_ns) != stamp:
                raise ValueError('Frozen input changed during campaign: ' + path)
        stage = dict(name=name, status='running', started=datetime.now().astimezone().isoformat(),
                     timeout_seconds=seconds)
        state['stages'].append(stage)
        state['phase'] = name
        write(run / 'status.json', state)
        command = [sys.executable, '-u', str(ROOT / 'run_slm.py'), '--module', module, '--run', str(model_run), *arguments]
        child = None
        begin = time.monotonic()
        try:
            with (run / (name + '.log')).open('w') as log:
                child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                stage['pid'] = child.pid
                write(run / 'status.json', state)
                while child.poll() is None:
                    if stop or (run / 'STOP').exists():
                        raise InterruptedError('Requested stop')
                    if time.monotonic() >= min(deadline, begin + seconds):
                        raise TimeoutError('Stage deadline: ' + name)
                    time.sleep(.5)
                stage['exit_code'] = child.returncode
                if child.returncode:
                    raise RuntimeError(f'{name} exited {child.returncode}; see {name}.log')
                stage['status'] = 'completed'
        except BaseException as exc:
            stage.update(status='failed', error=repr(exc))
            raise
        finally:
            stop_process(child)
            stage['elapsed_seconds'] = time.monotonic() - begin
            write(run / 'status.json', state)

    def evaluate(name, model_run, suite_name):
        destination = model_run / suite_name if model_run != Path(plan['parent']) else run / ('parent-' + suite_name)
        seconds = plan['evaluation_seconds'] if suite_name == 'search' else plan.get('confirmation_seconds', plan['evaluation_seconds'])
        process_seconds = plan['evaluation_process_seconds'] if suite_name == 'search' else plan.get('confirmation_process_seconds', plan['evaluation_process_seconds'])
        run_job(name, 'slm.broad_eval', model_run,
                ['--suite', str(run / (suite_name + '-suite.json')), '--output', str(destination),
                 '--checkpoint', 'latest', '--maximum', '256', '--max-seconds', str(seconds),
                 '--skip-code', '--answer-loss'], process_seconds)
        return quality(read(destination / 'summary.json'))

    try:
        run_job('controls', 'research.trial', run / 'controls',
                ['--plan', str(run / 'plan.json'), '--control-only'], plan['control_seconds'])
        if not read(run / 'controls/control.json')['passed']:
            raise ValueError('Control failed')
        parent_quality = evaluate('parent-search', Path(plan['parent']), 'search')
        write(run / 'parent-quality.json', parent_quality)
        qualities, trial_paths = {}, {}
        for repetition, order in enumerate(orders):
            results = []
            for name in order:
                trial = run / 'trials' / f'r{repetition}-{name}'
                trial_paths[repetition, name] = trial
                run_job(trial.name, 'research.trial', trial,
                        ['--plan', str(run / 'plan.json'), '--variant', name, '--repetition', str(repetition)], plan['trial_seconds'])
                results.append(read(trial / 'result.json'))
                matched(results)
                qualities[repetition, name] = evaluate(trial.name + '-search', trial, 'search')
        baselines = [qualities[r, 'baseline'] for r in range(2)]
        contrasts = {name: contrast(baselines, [qualities[r, name] for r in range(2)])
                     for name in orders[0][1:]}
        if plan.get('require_parent_guard'):
            for name, values in contrasts.items():
                values['parent_guard'] = parent_guard(parent_quality, [qualities[r, name] for r in range(2)])
                values['passes_screen'] = values['passes_screen'] and values['parent_guard']['passed']
        contender = max(contrasts, key=lambda name: (contrasts[name]['passes_screen'],
                        contrasts[name]['mean_accuracy_delta'], -contrasts[name]['mean_answer_loss_delta']))
        selection = dict(contender=contender, search_passed=contrasts[contender]['passes_screen'], contrasts=contrasts,
                         rule=plan['selection'], selected_before_confirmation=True)
        write(run / 'selection.json', selection)
        confirmation = {}
        if plan.get('require_parent_guard'):
            parent_confirmation = evaluate('parent-confirmation', Path(plan['parent']), 'confirmation')
            write(run / 'parent-confirmation-quality.json', parent_confirmation)
        for repetition in range(2):
            for name in ['baseline', contender]:
                trial = trial_paths[repetition, name]
                confirmation[repetition, name] = evaluate(trial.name + '-confirmation', trial, 'confirmation')
        confirmed = contrast([confirmation[r, 'baseline'] for r in range(2)],
                             [confirmation[r, contender] for r in range(2)])
        confirmed.update(contender=contender, confirmed_candidate=selection['search_passed'] and confirmed['passes_screen'])
        if plan.get('require_parent_guard'):
            confirmed['parent_guard'] = parent_guard(parent_confirmation, [confirmation[r, contender] for r in range(2)])
            confirmed['confirmed_candidate'] = confirmed['confirmed_candidate'] and confirmed['parent_guard']['passed']
        write(run / 'confirmation.json', confirmed)
        state.update(status='completed', phase='finished')
    except BaseException as exc:
        state.update(status='stopped', error=repr(exc))
    finally:
        stop_process(caffeine)
        state['elapsed_seconds'] = time.time() - started
        state['finished'] = datetime.now().astimezone().isoformat()
        # Hash again after GPU work; historical model/data inputs must remain intact.
        changes = [path for path, digest in frozen.items() if not Path(path).exists() or sha(path) != digest]
        state['frozen_input_changes'] = changes
        if changes:
            state.update(status='invalid', error='Frozen input hashes changed')
        write(run / 'status.json', state)
        report(run, state)
    if state['status'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
