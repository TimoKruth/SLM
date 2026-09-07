"""Launch one reproducible six-hour wall-clock training window after data preparation."""
from datetime import datetime, timedelta
import argparse
import hashlib
import json
import sys
from pathlib import Path
from .overnight import ROOT, main as supervise, write_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--data',default='data/v2');args=p.parse_args()
    run=(ROOT/args.run).resolve();run.mkdir(parents=True,exist_ok=True)
    schedule_path=run/'schedule.json'
    if schedule_path.exists():schedule=json.loads(schedule_path.read_text())
    else:
        now=datetime.now().astimezone();until=now+timedelta(hours=6)
        schedule=dict(started_at=now.isoformat(),training_until=until.isoformat(),hard_until=(until+timedelta(minutes=15)).isoformat(),duration_seconds=21600,data=str((ROOT/args.data).resolve()),initialization='random; same architecture and frozen v1 train-only tokenizer',note='Six-hour wall-clock training window including periodic evaluation/checkpointing; report afterwards. Preparation and smoke tests excluded. Restarts do not extend the deadline.')
        write_json(schedule_path,schedule)
        snapshot=run/'source';snapshot.mkdir(exist_ok=True)
        hashes={}
        for source in (ROOT/'slm').glob('*.py'):
            (snapshot/source.name).write_bytes(source.read_bytes());hashes[source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
        write_json(run/'source_sha256.json',hashes)
    sys.argv=['slm.overnight','--run',str(run),'--data',schedule['data'],'--train-until',schedule['training_until'],'--hard-until',schedule['hard_until'],'--steps','10000000','--max-tokens','1000000000000','--code-eval']
    supervise()


if __name__=='__main__':main()
