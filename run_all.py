"""Run from any directory: python run_all.py [--bootstrap-reps N]."""
import os
# Fix nested BLAS thread overhead and reproducible parallel reduction behavior.
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('MPLCONFIGDIR',str(__import__('pathlib').Path(__file__).resolve().parent/'.cache/matplotlib'))
from pathlib import Path
import argparse
import json
import platform
import time
import numpy as np
import pandas as pd
import scipy
from src.data import load_data
from src.analysis import analyze
from src.report import build_report
from src.covid import load_covid, analyze_covid

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bootstrap-reps',type=int,default=None)
    args=parser.parse_args();root=Path(__file__).resolve().parent
    cfg=json.loads((root/'config.json').read_text(encoding='utf-8'))
    if args.bootstrap_reps is not None: cfg['bootstrap_reps']=args.bootstrap_reps
    if cfg['bootstrap_reps']<100: raise ValueError('At least 100 replicates required; use 2000 for results')
    (root/'data/processed').mkdir(parents=True,exist_ok=True)
    for directory in ['tables','figures']: (root/'reports'/directory).mkdir(parents=True,exist_ok=True)
    start=time.perf_counter();print('Validating six complete seasons...',flush=True)
    matches,y,cubes,params,base,manifest,coverage,excluded=load_data(root,cfg)
    base.to_csv(root/'data/processed/analytic.csv',index=False)
    matches[['match_id','league','season','date','HomeTeam','AwayTeam','FTR','home_goals','away_goals']].to_csv(root/'data/processed/matches.csv',index=False)
    manifest.to_csv(root/'data/source_manifest.csv',index=False)
    coverage.to_csv(root/'reports/tables/coverage.csv',index=False);excluded.to_csv(root/'reports/tables/exclusions.csv',index=False)
    print(f'{len(matches)} matches; {len(base)} operator records. Running block bootstrap...',flush=True)
    tables=analyze(root,cfg,matches,y,cubes,params)
    print('Home advantage: home crowd and COVID-19 (2017/18-2024/25)...',flush=True)
    covid_matches,covid_manifest,covid_coverage=load_covid(root,cfg)
    covid_manifest.to_csv(root/'data/covid_source_manifest.csv',index=False)
    covid_coverage.to_csv(root/'reports/tables/covid_coverage.csv',index=False)
    covid_tables=analyze_covid(root,cfg,covid_matches)
    print('Generating charts and results report...',flush=True)
    build_report(root,cfg,matches,y,cubes,params,tables,covid_tables)
    metadata=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,config=cfg,
                  matches=len(matches),records=len(base),covid_matches=len(covid_matches),elapsed_seconds=round(time.perf_counter()-start,2))
    (root/'reports/run_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(f"Complete in {metadata['elapsed_seconds']} seconds: reports/index.html",flush=True)

if __name__=='__main__': main()
