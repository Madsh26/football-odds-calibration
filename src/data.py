import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .methods import remove_margin


def load_data(root,cfg):
    matches=[]; provenance=[]; coverage=[]; excluded=[]
    snapshot=root/'data/source_snapshot.csv'
    expected_hashes=pd.read_csv(snapshot).set_index('file').sha256.to_dict() if snapshot.exists() else {}
    for league in cfg['leagues']:
        for season in cfg['seasons']:
            file=root/'data/raw'/f'{league}_{season}.csv'
            if not file.exists(): raise FileNotFoundError(f'{file.name}: run python download_data.py or provide documented source CSV')
            d=pd.read_csv(file,encoding='utf-8-sig',dtype=str)
            digest=hashlib.sha256(file.read_bytes()).hexdigest()
            if file.name in expected_hashes and digest != expected_hashes[file.name]:
                raise ValueError(f'{file.name}: SHA-256 differs from the delivered snapshot; document the new version before updating source_snapshot.csv')
            provenance.append(dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),bytes=file.stat().st_size,
                source_url=f'https://www.football-data.co.uk/mmz4281/{season[2:4]}{season[-2:]}/{league}.csv',download_date='unknown',
                provenance='local copy supplied by collaborator; URL inferred from league/season, not independently authenticated'))
            d['source_row']=np.arange(len(d))+2
            required=['Div','Date','HomeTeam','AwayTeam','FTHG','FTAG','FTR']
            if not set(required).issubset(d.columns): raise ValueError(f'{file.name}: missing identifiers')
            dates=pd.to_datetime(d.Date,format='%d/%m/%Y',errors='coerce')
            dates=dates.fillna(pd.to_datetime(d.Date,format='%d/%m/%y',errors='coerce'))
            hg=pd.to_numeric(d.FTHG,errors='coerce'); ag=pd.to_numeric(d.FTAG,errors='coerce')
            expected=np.where(hg>ag,'H',np.where(hg<ag,'A','D'))
            start=pd.Timestamp(int(season[:4]),7,1); end=pd.Timestamp(int(season[:4])+1,6,30)
            valid=(d.Div.eq(league)&dates.between(start,end)&hg.notna()&ag.notna()&(hg>=0)&(ag>=0)&(hg%1==0)&(ag%1==0)&d.FTR.eq(expected)
                &d.HomeTeam.notna()&d.AwayTeam.notna()&d.HomeTeam.ne(d.AwayTeam)&d.HomeTeam.str.strip().ne('')&d.AwayTeam.str.strip().ne(''))
            duplicates=d.duplicated(['HomeTeam','AwayTeam'],keep=False)
            # Conflicting or identical duplicates are all quarantined; never select arbitrary versions.
            valid &= ~duplicates
            for i in d.index[~valid]: excluded.append(dict(file=file.name,source_row=int(d.loc[i,'source_row']),operator='all',reason='invalid match or duplicate directed pair'))
            d=d.loc[valid].copy();d['date']=dates.loc[valid];d['league']=league;d['season']=season
            d['home_goals']=hg.loc[valid].astype(int);d['away_goals']=ag.loc[valid].astype(int)
            d['match_id']=league+'_'+season+'_'+d.HomeTeam.str.replace(' ','',regex=False)+'_'+d.AwayTeam.str.replace(' ','',regex=False)
            appearances=pd.concat([d.HomeTeam,d.AwayTeam]).value_counts()
            if len(d)!=380 or len(appearances)!=20 or not appearances.eq(38).all():
                raise ValueError(f'{file.name}: failed full-season integrity; review exclusions before continuing')
            common=pd.Series(True,index=d.index)
            for op in cfg['operators']:
                columns=[op+'C'+x for x in 'HDA']
                odds=d.reindex(columns=columns).apply(pd.to_numeric,errors='coerce')
                missing=odds.isna().any(axis=1)
                invalid=(~np.isfinite(odds).all(axis=1))|(odds<=1).any(axis=1)
                margin=100*((1/odds).sum(axis=1,min_count=3)-1)
                eligible=~missing&~invalid&(margin>0)&(margin<=cfg['margin_alert_pp'])
                coverage.append(dict(league=league,season=season,operator=op,matches=len(d),missing=int(missing.sum()),
                    invalid_nonmissing=int((invalid&~missing).sum()),margin_alert=int((~missing&~invalid&~margin.between(0,cfg['margin_alert_pp'],inclusive='right')).sum()),
                    eligible=int(eligible.sum()),coverage_pct=100*eligible.mean()))
                for i in d.index[~eligible]: excluded.append(dict(file=file.name,source_row=int(d.loc[i,'source_row']),operator=op,reason='missing/invalid odds or margin alert'))
                common &= eligible
            if common.mean()<.9: raise ValueError(f'{file.name}: common coverage below 90%; scope needs review')
            d=d.loc[common].copy();d['source_file']=file.name
            matches.append(d)
    all_matches=pd.concat(matches,ignore_index=True).sort_values(['league','season','date','match_id']).reset_index(drop=True)
    all_matches['index']=np.arange(len(all_matches))
    analytic=[]; cubes={}; parameters={}
    y=np.column_stack([all_matches.FTR.eq(r).astype(int).to_numpy() for r in 'HDA'])
    for op in cfg['operators']:
        odds=all_matches[[op+'C'+r for r in 'HDA']].astype(float).to_numpy()
        qs,k,z=remove_margin(odds);cubes[op]=qs;parameters[op]=dict(odds=odds,k=k,z=z,margin_pp=100*((1/odds).sum(axis=1)-1))
        base=all_matches[['index','match_id','league','season','date','HomeTeam','AwayTeam','home_goals','away_goals','FTR','source_file','source_row']].copy()
        base['operator']=op;base['margin_pp']=parameters[op]['margin_pp'];base['power_k']=k;base['shin_z']=z
        for j,r in enumerate('HDA'):
            base['odds_'+r]=odds[:,j];base['raw_'+r]=1/odds[:,j];base['y_'+r]=y[:,j]
            for method in cfg['methods']: base[method+'_'+r]=qs[method][:,j]
        analytic.append(base)
    return all_matches,y,cubes,parameters,pd.concat(analytic,ignore_index=True),pd.DataFrame(provenance),pd.DataFrame(coverage),pd.DataFrame(excluded,columns=['file','source_row','operator','reason'])
