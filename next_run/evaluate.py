"""Run bounded diagnostics through the monitored project entry point."""
import json
import subprocess
from datetime import datetime
from next_run.prepare import ROOT, OUT, RUN, sha

def main():
    conditions=json.loads((RUN/'RUN_CONDITIONS.json').read_text())
    conditions.update(recorded_at=datetime.now().astimezone().isoformat(),power_settings=subprocess.check_output(['pmset','-g','custom'],text=True),execution='Serial diagnostics; no long training started')
    (OUT/'RUN_CONDITIONS.json').write_text(json.dumps(conditions,indent=2)+'\n')
    for label,maximum in [('seen-train',256),('matched-dev',256),('length-probe',512)]:
        output=OUT/label
        if (output/'summary.json').exists():
            summary=json.loads((output/'summary.json').read_text())
            protocol=json.loads((output/'protocol.json').read_text())
            assert protocol['suite_sha256']==sha(OUT/f'{label}-suite.json')
            checkpoint=RUN/json.loads((RUN/'latest.json').read_text())['checkpoint']/'model.safetensors'
            assert protocol['checkpoint_sha256']==sha(checkpoint)
            assert summary['selected_general']==summary['evaluated_general'] and not summary['deadline_reached']
            continue
        command=[str(ROOT/'.venv/bin/python'),'run_slm.py','--module','slm.broad_eval','--run',str(RUN),
            '--suite',str(OUT/f'{label}-suite.json'),'--output',str(output),'--checkpoint','latest','--maximum',str(maximum),'--max-seconds','480','--skip-code','--answer-loss']
        with (OUT/f'{label}.log').open('w') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=540,check=True)
        summary=json.loads((output/'summary.json').read_text())
        assert summary['selected_general']==summary['evaluated_general'] and not summary['deadline_reached']
        print(label,'completed',summary['evaluated_general'],flush=True)

if __name__=='__main__':main()
