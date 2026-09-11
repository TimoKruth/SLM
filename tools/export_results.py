"""Export selected aggregate evidence; raw tasks/checkpoints remain in private ZIPs."""
import argparse
import hashlib
import json
from pathlib import Path

CAMPAIGNS = ['code-eval-2026-09-07', 'broad-886-2026-09-08', 'broad-campaign-2026-09-07',
 'broad-monitoring-2026-09-07', 'broad-monitoring-confirmation-2026-09-07',
 'size-campaign-2026-09-08', 'size-continuation-2026-09-09', 'random-search-pilot-2026-09-08',
 'research-pilot-2026-09-09', 'research-round2-2026-09-09',
 'parameter-study-timeout-recovery-2026-09-10', 'parallel-probe-2026-09-10',
 'long-horizon-resume-2026-09-10']
FILES = ['REPORT.md', 'quality.json', 'assessment.json', 'contrasts.json', 'effects.json',
         'interactions.json', 'duration-effects.json', 'confirmation.json', 'selection.json']


def main():
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Use a new output directory')
 a.output.mkdir(parents=True);inventory=[];campaigns=[]
 for run in sorted((a.project/'runs').iterdir()):
  if not run.is_dir():continue
  f=run/'status.json';s=json.loads(f.read_text()) if f.exists() else {}
  campaigns.append({'name':run.name,**{k:s[k] for k in ['status','phase','started','finished','finished_at','deadline','elapsed_seconds','total_budget_spent_seconds','frozen_inputs_unchanged'] if k in s}})
 for name in CAMPAIGNS:
  for file in FILES:
   source=a.project/'runs'/name/file
   if not source.exists():continue
   raw=source.read_bytes();out=a.output/name/file;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
   inventory.append({'source':str(source.relative_to(a.project)),'export':str(out.relative_to(a.output)),'sha256':hashlib.sha256(raw).hexdigest()})
 (a.output/'sources.json').write_text(json.dumps(inventory,indent=2)+'\n')
 (a.output/'campaigns.json').write_text(json.dumps(campaigns,indent=2)+'\n')
 lines=['# Ergebnisarchiv vom 11. September 2026','','Unveränderte aggregierte Berichte aus den lokalen Laufartefakten. Historische Formulierungen wie „running“ oder „nächster Lauf“ spiegeln den jeweiligen Berichtstand. Aktuelle Einordnung: [ERKENNTNISSE.md](../../ERKENNTNISSE.md). Keine Trainingsfreigabe.','','Die Quellpfade und SHA-256 stehen in `sources.json`; Rohantworten, Daten und Checkpoints sind in den getrennten ZIP-Archiven. `campaigns.json` enthält den Status aller lokalen Laufverzeichnisse zum Exportzeitpunkt.','']
 lines += [f'- [{name}]({name}/REPORT.md)' for name in CAMPAIGNS if (a.output/name/'REPORT.md').exists()]
 (a.output/'INDEX.md').write_text('\n'.join(lines)+'\n')
 print(len(inventory),'aggregate files;',len(campaigns),'run directories')

if __name__=='__main__':main()
