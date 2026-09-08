"""Download only original train files and provenance; never activate them in a mixture."""
import json
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from next_run.prepare import ROOT, sha

OUT=ROOT/'data/candidates-next-2026-09-08'

def download(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        temp=path.with_suffix(path.suffix+'.tmp')
        with urllib.request.urlopen(url,timeout=60) as response,temp.open('wb') as f:
            while b:=response.read(1024*1024):f.write(b)
        temp.replace(path)
    return dict(url=url,path=str(path.relative_to(OUT)),sha256=sha(path),bytes=path.stat().st_size)

def main():
    OUT.mkdir(exist_ok=True)
    def get(url):
        with urllib.request.urlopen(url,timeout=30) as r:return json.load(r)
    tat_rev=get('https://api.github.com/repos/NExTplusplus/TAT-QA/commits/master')['sha']
    nli_rev=get('https://huggingface.co/api/datasets/nyu-mll/multi_nli')['sha']
    jobs=[(f'https://raw.githubusercontent.com/NExTplusplus/TAT-QA/{tat_rev}/dataset_raw/tatqa_dataset_train.json',OUT/'tatqa/train.json'),
          (f'https://raw.githubusercontent.com/NExTplusplus/TAT-QA/{tat_rev}/README.md',OUT/'tatqa/README.md'),
          (f'https://raw.githubusercontent.com/NExTplusplus/TAT-QA/{tat_rev}/LICENSE',OUT/'tatqa/LICENSE'),
          (f'https://huggingface.co/datasets/nyu-mll/multi_nli/resolve/{nli_rev}/data/train-00000-of-00001.parquet',OUT/'multinli/train.parquet'),
          (f'https://huggingface.co/datasets/nyu-mll/multi_nli/resolve/{nli_rev}/README.md',OUT/'multinli/README.md')]
    records=[]
    with ThreadPoolExecutor(max_workers=2) as ex:
        futures=[ex.submit(download,u,p) for u,p in jobs]
        for (url,path),f in zip(jobs,futures):
            try:records.append(f.result())
            except Exception as e:records.append(dict(url=url,error=str(e)))
    (OUT/'manifest.json').write_text(json.dumps(dict(status='downloaded_not_admitted',revisions=dict(tatqa=tat_rev,multinli=nli_rev),files=records,original_split='train only',external_final_tests_downloaded=False,activated=False),indent=2)+'\n')
    print(json.dumps(records,indent=2))

if __name__=='__main__':main()
