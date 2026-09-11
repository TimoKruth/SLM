#!/usr/bin/python3
"""Install only the small report job; reuse the existing PowerWatch sampler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess

LABEL='com.local.powerwatch.slm-report'
HOME=Path.home()/'Library/Application Support/PowerWatch'
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'runs/system-resources')
    a=p.parse_args();output=a.output.expanduser().resolve();output.mkdir(parents=True,exist_ok=True)
    if not (HOME/'powerwatch').is_file():raise RuntimeError('Existing PowerWatch installation required')
    domain=f'gui/{os.getuid()}'
    collector='com.local.powerwatch';agents=Path.home()/'Library/LaunchAgents'
    if subprocess.run(['launchctl','print',domain+'/'+collector],capture_output=True).returncode:
        subprocess.run(['launchctl','bootstrap',domain,str(agents/(collector+'.plist'))],check=True)
    source=Path(__file__).with_name('report.py');installed=HOME/'slm_resource_report.py'
    # Separate installed copy survives project branch switches.
    temporary=installed.with_suffix('.tmp');shutil.copy2(source,temporary);temporary.chmod(0o600);temporary.replace(installed)
    path=agents/(LABEL+'.plist')
    config={'Label':LABEL,'ProgramArguments':['/usr/bin/python3',str(installed),'--output',str(output),'--hours','6'],
        'RunAtLoad':True,'StartInterval':60,'ProcessType':'Background','Nice':10,'LowPriorityIO':True,
        'WorkingDirectory':str(HOME),'StandardOutPath':'/dev/null','StandardErrorPath':'/dev/null'}
    if subprocess.run(['launchctl','print',domain+'/'+LABEL],capture_output=True).returncode==0:
        subprocess.run(['launchctl','bootout',domain+'/'+LABEL],check=True)
    with path.open('wb') as f:plistlib.dump(config,f)
    path.chmod(0o600)
    # Verify once before enabling unattended updates.
    subprocess.run(config['ProgramArguments'],check=True)
    subprocess.run(['launchctl','bootstrap',domain,str(path)],check=True)
    record={'collector':'com.local.powerwatch','reporter':LABEL,'interval_seconds':15,'report_seconds':60,'retention_days':30,
        'source':str(source),'installed_script':str(installed),'sha256':hashlib.sha256(installed.read_bytes()).hexdigest(),
        'launch_agent':str(path),'output':str(output),'collector_changed':False}
    (output/'installation.json').write_text(json.dumps(record,indent=2)+'\n')
    print('INSTALLED',LABEL,'Dashboard:',output/'latest.html')

if __name__=='__main__':main()
