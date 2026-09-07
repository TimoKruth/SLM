"""Collect separate train-only staging data without changing the running experiment."""
from datetime import datetime
import json
import os
from pathlib import Path
from urllib.request import urlopen
from huggingface_hub import hf_hub_download
import pyarrow.parquet as pq
from slm.collect import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/candidates-wave3-2026-09-07'
# repo, original revision, data revision (HF conversion branch where necessary), train paths
SOURCES={
 'social_i_qa':('allenai/social_i_qa','8835ceb9141d7896d9d968634a9b21ae440e3ec5','537a2ec8ec565adc0b70b70752893e59e024df26',['default/train/0000.parquet']),
 'quoref':('allenai/quoref','0823a60bbacda6cb6d2d58dcd7647b0ca053ffaf','41fed5bc359f81c2f28259e6572cd1f9aab26e29',['default/train/0000.parquet']),
 'wiqa':('allenai/wiqa','8dda4b5e237452fb939b39326f68ad6607e75ab6','762ae337e9418a7d8f0de6686f5a8bc2f379d0cc',['default/train/0000.parquet']),
 'cosmos_qa':('allenai/cosmos_qa','28d9d5e2aae025e73e11177891a88dba51190013','ed50fe83db62b355759053b1cd5eef344ee371e0',['default/train/0000.parquet']),
 'wikisql':('Salesforce/wikisql','5de818eb69c5385e763201d9b9abc36df69a81dc','48cfb60afd0d5f9d2231ca90f76edf9f975181bc',['default/train/0000.parquet']),
 'dream':('dataset-org/dream','78b128b6aa3ac08913a19a3c71064bf23206bdf6','ca4c45feaf089ecfc37579eb2c594375f70dbfd5',['plain_text/train/0000.parquet']),
 'anli':('facebook/anli','8e4813d81f46d313dac7892e1c28076917cfcdf9','8e4813d81f46d313dac7892e1c28076917cfcdf9',[f'plain_text/train_r{i}-00000-of-00001.parquet' for i in (1,2,3)]),
 'scitail':('allenai/scitail','0cc4353235b289165dfde1c7c5d1be983f99ce44','0cc4353235b289165dfde1c7c5d1be983f99ce44',['tsv_format/train-00000-of-00001.parquet']),
}


def main():
    os.nice(10);OUT.mkdir(parents=True,exist_ok=True)
    found={};failures={}
    for name,(repo,original,revision,files) in SOURCES.items():
        try:
            folder=OUT/'raw'/name;folder.mkdir(parents=True,exist_ok=True)
            meta=json.load(urlopen(f'https://huggingface.co/api/datasets/{repo}/revision/{original}',timeout=60))
            converted=json.load(urlopen(f'https://huggingface.co/api/datasets/{repo}/revision/{revision}',timeout=60))
            assert meta['sha']==original and converted['sha']==revision
            (folder/'metadata.json').write_text(json.dumps(meta,indent=2));(folder/'data_revision.json').write_text(json.dumps(converted,indent=2))
            card=hf_hub_download(repo,'README.md',repo_type='dataset',revision=original,local_dir=folder)
            entries=[]
            for file in files:
                assert '/train/' in file or Path(file).name.startswith('train')
                path=Path(hf_hub_download(repo,file,repo_type='dataset',revision=revision,local_dir=folder))
                pf=pq.ParquetFile(path)
                entries.append(dict(path=file,sha256=sha(path),bytes=path.stat().st_size,rows=pf.metadata.num_rows,columns=pf.schema_arrow.names))
            item=dict(repo=repo,url='https://huggingface.co/datasets/'+repo,source_revision=original,data_revision=revision,uses_hf_converted_parquet=original!=revision,original_split='train',license_metadata=meta.get('cardData',{}).get('license'),card_sha256=sha(card),files=entries,original_train_rows=sum(f['rows'] for f in entries),status='staged_for_provenance_and_overlap_audit',used_in_training=False)
            (folder/'manifest.json').write_text(json.dumps(item,indent=2));found[name]=item;print(name,item['original_train_rows'],flush=True)
        except Exception as exc:
            failures[name]=repr(exc);print(name,repr(exc),flush=True)
    result=dict(created=datetime.now().astimezone().isoformat(),sources=found,failures=failures,new_sources=len(found),total_collected_sources=24+len(found),raw_train_rows=sum(m['original_train_rows'] for m in found.values()),bytes=sum(f['bytes'] for m in found.values() for f in m['files']),excluded_evaluation_families=['LiveCodeBench','IFBench','IFEval','IF-RLVR','BIG-Bench','BBH','BBEH'],used_in_training=False,collector_sha256=sha(__file__),note='ANLI rounds count as one benchmark. Conversion and original-card revisions are recorded separately, without claiming they are an identical source commit. No dataset loading scripts executed. No held-out split downloaded. Provenance, label quality and overlap review required before training.')
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2),flush=True)
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
