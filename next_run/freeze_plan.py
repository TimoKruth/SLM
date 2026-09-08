"""Write an inert experiment proposal and version pins; never launch training."""
import json
import urllib.request
from datetime import datetime
from next_run.prepare import ROOT,OUT,sha

def main():
    src=ROOT/'runs/size-27m-2026-09-08-3h'
    verification=json.loads((OUT/'bf16-launcher-verification.json').read_text())
    assert verification['resumed_steps']==16 and verification['precision_mismatch_rejected']
    assert json.loads((OUT/'precision-validation/validation.json').read_text())['status']=='passed'
    assert json.loads((OUT/'performance-screen/summary.json').read_text())['precision_gate']
    assert json.loads((OUT/'final-verification.json').read_text())['original_campaign_inputs_unchanged']
    plan=dict(status='prepared_not_started',training_authorized=False,suggested_training_seconds=21600,
      purpose='Best useful broad learning progress within a proposed six-hour budget; not a pure duration-only causal comparison.',
      run='runs/next-27m-long-NOT-STARTED',module='slm.train',
      arguments=['--data','runs/size-campaign-2026-09-08/data-families','--execution','compiled','--forward-precision','bf16',
        '--seed','20260906','--steps','1000000','--max-tokens','1000000000000','--dim','512','--layers','6','--heads','8','--hidden','1368','--context','1024','--batch-size','2',
        '--checkpoint-seconds','600','--eval-seconds','1800','--schedule-tokens','300000000','--snapshot-tokens','30000000','100000000','119011223','200000000','240000000','300000000'],
      deadline_rule='Set --until exactly once at stage admission to now + authorized duration; no automatic restart granting extra time. Only final checkpoint cleanup has up to 120 seconds extra.',
      initialization='New random weights, same seed and original train-only tokenizer; no model/optimizer continuation.',
      rationale='BF16 screening improved throughput by 20.3% versus same-session FP32, with FP32 master weights. A 300M-token cosine horizon covers roughly 6h at projected improved historical throughput; it is a schedule, not guaranteed work or a token stopping target.',
      fp32_control_option='Use --forward-precision fp32 and 240000000 schedule tokens for six hours. This removes precision change but still changes the learning-rate horizon versus the old 3h run.',
      confounders=['Forward precision and LR horizon differ from original 3h run','One seed, fixed historical order','Reduced power and temperature/background load affect fixed-time comparisons'],
      conditions='Keep user power/noise mode unchanged; record pmset, PowerWatch interval and system competition before/after. light monitoring mandatory.',
      primary_endpoint='Last complete checkpoint at the authorized wall deadline; never choose best checkpoint post hoc.',
      evaluation=dict(suite='runs/size-campaign-2026-09-08/suite.json',general_tasks=886,maximum=256,skip_code=False,answer_loss=True,max_seconds=900,
        metrics=['Each of seven ability families separately','Macro of scored-source accuracy within each scored family; average across six scored families secondary','Reference answer loss across 31 sources','Code execution and WikiSQL execution proxy separately','Repetition, output limits, contextual coverage','Frozen seen-train/matched-dev diagnostic subset','Posthoc reference-sensitivity exclusions held fixed before new training'],
        precision='Standalone evaluation in FP32 for all models; inline training dev follows forward precision. Do not compare their loss values as identical protocols.',
        snapshots='Evaluate every reached listed token snapshot after training, serially, same suite, skip code; each <=900s. Repeated reading of these dev results is model selection, not external transfer.',
        baseline='27m three-hour final plus available original matched-token snapshots',
        practical_success='At least +3 percentage points in the average of the six scored-family accuracies, improvement in at least three scored families, and no family regression greater than 5 points. An exploratory predeclared utility threshold, not a statistical proof.',
        continuation_rule='No automatic extra training. If loss improves without better free answers, prioritize objective/format diagnostics over adding more hours.'),
      ready_checks=['Corrected 32-source audit passed','Observed training sample replay matches first 10M snapshot','Performance and FP32-master checkpoint checks passed','Regular monitored BF16 start/resume smoke passed','Source/data hashes rechecked immediately before eventual launch'],
      blocked_actions=['No long training starts from preparation scripts','No transfer test data loaded','Staged new sources not included'])
    pins={}
    for repo in ['LiveCodeBench/LiveCodeBench','allenai/IFBench','google-deepmind/bbeh']:
        with urllib.request.urlopen(f'https://api.github.com/repos/{repo}/commits?per_page=1',timeout=30) as r:
            pins[repo]=json.load(r)[0]['sha']
    transfer=dict(status='protocol_prepared_tests_unopened',code_revisions=pins,
      benchmarks=dict(LiveCodeBench='Python code-generation pass@1 using official harness in resource-limited sandbox',IFBench='Official strict instruction and prompt compliance metrics; no LLM judge',BBEH='Official per-task answer scoring and macro across task types'),
      freeze_before_open=['Candidate checkpoint hash','Untrained random 27m baseline seed and current 3h baseline checkpoint','Dataset revision and official evaluator revision','Prompt adapter using dataset-independent fixtures only','Greedy one attempt, 1024-token total context, maximum 512 new tokens subject to available context','Stratified task selection by stable ID hash if a subset budget is required, never by outputs'],
      context_policy='Report all selected tasks and number unsupported by context. Do not silently truncate instructions or present a length-filtered subset as an official full score. Report attempted subset quality and full-selection coverage separately.',
      contamination='All three benchmark families, training variants and derivatives remain excluded from training/tokenizer/model selection. Opening them is a separate explicit final-evaluation stage.',
      inference_scope='Tests probe different capabilities but failure on hard/long tasks does not prove the model learned nothing. No current transfer-success claim.',
      data_downloaded=False,tests_executed=False)
    (ROOT/'next_run/long_plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'next_run/transfer_protocol.json').write_text(json.dumps(transfer,indent=2)+'\n')
    files=[ROOT/'run_slm.py',ROOT/'run_defaults.json',ROOT/'slm/train.py',ROOT/'slm/precision.py',ROOT/'slm/model.py',ROOT/'slm/data.py',
      ROOT/'runs/size-campaign-2026-09-08/data-families/manifest.json',ROOT/'data/v4-broad-corrected-2026-09-08/audit.json',ROOT/'runs/size-campaign-2026-09-08/suite.json',
      OUT/'seen-train-suite.json',OUT/'matched-dev-suite.json',ROOT/'next_run/manual_findings.json',ROOT/'next_run/long_plan.json',ROOT/'next_run/transfer_protocol.json']
    files += [p for folder in ['slm','slm_perf','next_run'] for p in (ROOT/folder).glob('*.py')]
    (OUT/'preparation-manifest.json').write_text(json.dumps(dict(created_at=datetime.now().astimezone().isoformat(),long_training_started=False,sha256={str(p.relative_to(ROOT)):sha(p) for p in files}),indent=2)+'\n')
    print('PREPARED ONLY; no long training launched')

if __name__=='__main__':main()
