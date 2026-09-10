import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from long_study.resume import remaining_jobs, run_pending


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.jobs = ['r0-A', 'r0-B', 'r0-C', 'r0-D', 'r1-D', 'r1-C', 'r1-B', 'r1-A']
        self.previous = dict(status='paused', frozen_inputs_unchanged=True, total_budget_spent_seconds=23000,
                             stages=[dict(name=n, status='completed', elapsed_seconds=7140) for n in self.jobs[:3]] +
                             [dict(name='r0-D', status='failed', elapsed_seconds=232)])
        self.spec = dict(completed_jobs=self.jobs[:3], partial_job='r0-D', partial_spent_seconds=232, preparation_seconds=300)
        self.plan = dict(jobs=self.jobs, previous_budget_spent_seconds=23300, budget_seconds=63100,
                         evaluation_process_seconds=630, report_seconds=600)

    def test_budget_excludes_pause_and_keeps_partial_allowance(self):
        self.assertEqual(remaining_jobs(self.plan, self.spec, self.previous), self.jobs[3:])

    def test_reject_budget_reset(self):
        self.plan['budget_seconds'] = 86400
        with self.assertRaises(ValueError): remaining_jobs(self.plan, self.spec, self.previous)

    def test_reject_wrong_partial_accounting(self):
        self.spec['partial_spent_seconds'] = 0
        with self.assertRaises(ValueError): remaining_jobs(self.plan, self.spec, self.previous)

    def test_reject_reusing_unfinished_job(self):
        self.spec['completed_jobs'].append('r0-D')
        with self.assertRaises(ValueError): remaining_jobs(self.plan, self.spec, self.previous)

    def test_resume_only_partial_and_evaluate_all_remaining(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            (run / 'jobs').mkdir()
            for name in self.jobs:
                (run / 'jobs' / (name + '.json')).write_text(json.dumps({'train_seconds': 7200}))
            class FakeRunner:
                def __init__(self): self.run, self.state, self.calls, self.evals = run, {}, [], []
                def job(self, name, module, trial, args, seconds):
                    self.calls.append((name, args, seconds))
                    trial.mkdir(parents=True)
                    (trial / 'result.json').write_text('{"status":"completed"}')
                    for n in [15000000, 50000000]: (trial / f'token-{n:09d}').mkdir()
                def evaluate(self, *args): self.evals.append(args)
            runner = FakeRunner()
            with patch('long_study.resume.report'):
                run_pending(runner, self.plan, self.spec, self.jobs[3:])
            self.assertEqual([c[0] for c in runner.calls], self.jobs[3:])
            self.assertEqual(runner.calls[0][2], 6968)
            self.assertIn('--resume', runner.calls[0][1])
            self.assertTrue(all('--resume' not in c[1] and c[2] == 7200 for c in runner.calls[1:]))
            self.assertEqual(len(runner.evals), 20)


if __name__ == '__main__': unittest.main()
