import numpy as np
import pandas as pd
from .inference import block_weights, error_slope, extreme_gap, interval, holm, weighted_mean
from .methods import scores, quantile_bins, wilson, murphy, calibration_logistic, goodness_of_fit


def analyze(root,cfg,matches,y,cubes,params):
    n=len(matches);B=cfg['bootstrap_reps']
    strata=[g.index.to_numpy() for _,g in matches.groupby(['league','season'],sort=True)]
    W=block_weights(n,strata,B,cfg['block_size'],cfg['seed'])
    panels={}
    for league in cfg['leagues']:
        panels[(league,'all')]=np.flatnonzero(matches.league.eq(league))
        for season in cfg['seasons']:
            panels[(league,season)]=np.flatnonzero(matches.league.eq(league)&matches.season.eq(season))
    baseline=np.empty_like(y,dtype=float)
    for league in cfg['leagues']:
        for season in cfg['seasons']:
            test=matches.league.eq(league)&matches.season.eq(season)
            train=matches.league.eq(league)&~matches.season.eq(season)
            baseline[test]=y[train].mean(axis=0)
    uniform=np.full_like(y,1/3,dtype=float)
    baselines={'historical_leave_season_out':scores(baseline,y),'uniform':scores(uniform,y)}
    collected={k:[] for k in ['margin','scores','bias','extremes','method_differences','curves','bin_sensitivity','murphy','logistic','gof',
                             'operator_differences','league_differences','season_differences','block_sensitivity','threshold_sensitivity','outcome_calibration']}
    cache={};score_cache={}
    # All main intervals use the same resampled matches and preserved strata.
    for (league,season),idx in panels.items():
        wi=W[:,idx];ones=np.ones((1,len(idx)));yy=y[idx]
        for op in cfg['operators']:
            tag=dict(league=league,season=season,operator=op,matches=len(idx))
            margin=params[op]['margin_pp'][idx]
            collected['margin'].append(dict(**tag,mean_pp=margin.mean(),median_pp=np.median(margin),sd_pp=margin.std(ddof=1),p05_pp=np.quantile(margin,.05),p95_pp=np.quantile(margin,.95),
                                            ci_low=np.quantile(weighted_mean(wi,margin),.025),ci_high=np.quantile(weighted_mean(wi,margin),.975)))
            reference=cubes[op]['proportional'][idx]
            method_bias={};method_gap={}
            for method in cfg['methods']:
                q=cubes[op][method][idx];t=dict(**tag,method=method)
                s=scores(q,yy)
                eces=[]
                for j,r in enumerate('HDA'):
                    bins=quantile_bins(q[:,j],cfg['bins']);ece=0.
                    for bb in np.unique(bins):
                        mm=bins==bb;ece+=mm.mean()*abs(yy[mm,j].mean()-q[mm,j].mean())
                    eces.append(100*ece)
                    gap_values=100*(yy[:,j]-q[:,j])
                    collected['outcome_calibration'].append(dict(**t,outcome=r,predicted_pct=100*q[:,j].mean(),observed_pct=100*yy[:,j].mean(),ece_pp=100*ece,
                        **interval(gap_values.mean(),weighted_mean(wi,gap_values))))
                rps_draws=weighted_mean(wi,s['rps']);hist=baselines['historical_leave_season_out']['rps'][idx]
                score_cache[(league,season,op,method)]=(s,rps_draws,1-rps_draws/weighted_mean(wi,hist))
                collected['scores'].append(dict(**t,brier=s['brier'].mean(),rps=s['rps'].mean(),log_loss=s['log_loss'].mean(),
                    rps_ci_low=np.quantile(rps_draws,.025),rps_ci_high=np.quantile(rps_draws,.975),
                    rpss=1-s['rps'].mean()/hist.mean(),brier_skill=1-s['brier'].mean()/baselines['historical_leave_season_out']['brier'][idx].mean(),macro_ece_pp=np.mean(eces)))
                slope=error_slope(q,yy,ones)[0];bs=error_slope(q,yy,wi)
                gap=extreme_gap(q,yy,reference,ones,cfg['low_threshold'],cfg['high_threshold'])[0]
                bg=extreme_gap(q,yy,reference,wi,cfg['low_threshold'],cfg['high_threshold'])
                method_bias[method]=(slope,bs);method_gap[method]=(gap,bg)
                collected['bias'].append(dict(**t,unit='residual pp per 10 pp probability',**interval(slope,bs)))
                collected['extremes'].append(dict(**t,definition='membership fixed by proportional probabilities',n_low=int((reference<cfg['low_threshold']).sum()),n_high=int((reference>cfg['high_threshold']).sum()),
                    low_error_pp=float(100*(yy-q)[reference<cfg['low_threshold']].mean()),high_error_pp=float(100*(yy-q)[reference>cfg['high_threshold']].mean()),
                    **interval(gap,bg)))
                if season=='all':
                    collected['murphy'].append(dict(**t,**murphy(q,yy,cfg['bins'])))
                    collected['logistic'].append(dict(**t,**calibration_logistic(q,yy)))
                    for j,r in enumerate('HDA'):
                        for g in [cfg['bins']]+cfg['bin_sensitivity']:
                            collected['gof'].append(dict(**t,outcome=r,requested_groups=g,**goodness_of_fit(q[:,j],yy[:,j],g)))
                    # Fixed curve bin membership conditional on original predictions.
                    for j,r in enumerate('HDA'):
                        b=quantile_bins(q[:,j],cfg['bins'])
                        mask_matrix=np.column_stack([b==k for k in np.unique(b)])
                        counts=wi@mask_matrix
                        bfreq=(wi@(mask_matrix*yy[:,j,None]))/counts
                        bgap=100*(wi@(mask_matrix*(yy[:,j]-q[:,j])[:,None]))/counts
                        for c,k in enumerate(np.unique(b)):
                            mask=b==k;ci=wilson(yy[mask,j].sum(),mask.sum())
                            freq=yy[mask,j].mean();pred=q[mask,j].mean();gint=interval(100*(freq-pred),bgap[:,c])
                            collected['curves'].append(dict(**t,outcome=r,bin=int(k),n=int(mask.sum()),predicted=pred,observed=freq,prob_min=q[mask,j].min(),prob_max=q[mask,j].max(),
                                wilson_low=ci[0],wilson_high=ci[1],observed_block_low=np.quantile(bfreq[:,c],.025),observed_block_high=np.quantile(bfreq[:,c],.975),
                                gap_pp=gint['estimate'],gap_ci_low=gint['ci_low'],gap_ci_high=gint['ci_high']))
                    # Separate outcomes, then macro-average absolute calibration error.
                    for bins in [cfg['bins']]+cfg['bin_sensitivity']:
                        errors=[];maximum=[]
                        for j in range(3):
                            b=quantile_bins(q[:,j],bins);e=0.;mx=0.
                            for k in np.unique(b):
                                m=b==k;d=abs(yy[m,j].mean()-q[m,j].mean());e+=m.mean()*d;mx=max(mx,d)
                            errors.append(e);maximum.append(mx)
                        collected['bin_sensitivity'].append(dict(**t,bins=bins,scheme='equal_frequency',macro_ece_pp=100*np.mean(errors),max_gap_pp=100*max(maximum)))
                    errors=[];maximum=[]
                    for j in range(3):
                        b=np.minimum((q[:,j]*20).astype(int),19);e=0.;mx=0.
                        for k in np.unique(b):
                            m=b==k;d=abs(yy[m,j].mean()-q[m,j].mean());e+=m.mean()*d;mx=max(mx,d)
                        errors.append(e);maximum.append(mx)
                    collected['bin_sensitivity'].append(dict(**t,bins=20,scheme='equal_width',macro_ece_pp=100*np.mean(errors),max_gap_pp=100*max(maximum)))
                    low,high=cfg['threshold_sensitivity']
                    # Alternative cutoffs and method-specific membership are separate checks.
                    for definition,ref,lo,hi in [('fixed_15_65',reference,low,high),('method_specific_20_60',q,cfg['low_threshold'],cfg['high_threshold'])]:
                        est=extreme_gap(q,yy,ref,ones,lo,hi)[0];draw=extreme_gap(q,yy,ref,wi,lo,hi)
                        collected['threshold_sensitivity'].append(dict(**t,definition=definition,n_low=int((ref<lo).sum()),n_high=int((ref>hi).sum()),**interval(est,draw)))
            cache[(league,season,op)]=(method_bias,method_gap)
            for method in cfg['methods'][1:]:
                for metric,m in [('error_slope',method_bias),('extreme_gap',method_gap)]:
                    est=m[method][0]-m['proportional'][0];draw=m[method][1]-m['proportional'][1]
                    collected['method_differences'].append(dict(**tag,comparison=method+' minus proportional',metric=metric,**interval(est,draw)))
            for name,s in baselines.items():
                collected['scores'].append(dict(**tag,method=name,brier=s['brier'][idx].mean(),rps=s['rps'][idx].mean(),log_loss=s['log_loss'][idx].mean(),rps_ci_low=np.nan,rps_ci_high=np.nan,
                    rpss=1-s['rps'][idx].mean()/baselines['historical_leave_season_out']['rps'][idx].mean(),brier_skill=1-s['brier'][idx].mean()/baselines['historical_leave_season_out']['brier'][idx].mean()))
        # Paired comparison, always PS minus B365 for the same matches.
        for method in cfg['methods']:
            a=score_cache[(league,season,'B365',method)];b=score_cache[(league,season,'PS',method)]
            collected['operator_differences'].append(dict(league=league,season=season,method=method,metric='rps',comparison='Pinnacle minus Bet365',
                **interval(b[0]['rps'].mean()-a[0]['rps'].mean(),b[1]-a[1])))
            ba=cache[(league,season,'B365')][0][method];bb=cache[(league,season,'PS')][0][method]
            collected['operator_differences'].append(dict(league=league,season=season,method=method,metric='error_slope',comparison='Pinnacle minus Bet365',**interval(bb[0]-ba[0],bb[1]-ba[1])))
        mm=params['PS']['margin_pp'][idx]-params['B365']['margin_pp'][idx]
        collected['operator_differences'].append(dict(league=league,season=season,method='raw',metric='margin_pp',comparison='Pinnacle minus Bet365',**interval(mm.mean(),weighted_mean(wi,mm))))
    # Independent league comparison with bootstrap preserving each league-season.
    for season in ['all']+cfg['seasons']:
        for op in cfg['operators']:
            for method in cfg['methods']:
                a=cache[('E0',season,op)][0][method];b=cache[('SP1',season,op)][0][method]
                collected['league_differences'].append(dict(season=season,operator=op,method=method,metric='error_slope',comparison='LaLiga minus Premier',**interval(b[0]-a[0],b[1]-a[1])))
                a=cache[('E0',season,op)][1][method];b=cache[('SP1',season,op)][1][method]
                collected['league_differences'].append(dict(season=season,operator=op,method=method,metric='extreme_gap',comparison='LaLiga minus Premier',**interval(b[0]-a[0],b[1]-a[1])))
                a=score_cache[('E0',season,op,method)];b=score_cache[('SP1',season,op,method)]
                rpsa=a[0]['rps'].mean();rpsb=b[0]['rps'].mean()
                ha=baselines['historical_leave_season_out']['rps'][panels[('E0',season)]].mean();hb=baselines['historical_leave_season_out']['rps'][panels[('SP1',season)]].mean()
                collected['league_differences'].append(dict(season=season,operator=op,method=method,metric='rps_skill',comparison='LaLiga minus Premier',**interval((1-rpsb/hb)-(1-rpsa/ha),b[2]-a[2])))
    for league in cfg['leagues']:
        for op in cfg['operators']:
            for method in cfg['methods']:
                for first,second in zip(cfg['seasons'][:-1],cfg['seasons'][1:]):
                    a=cache[(league,first,op)][0][method];b=cache[(league,second,op)][0][method]
                    collected['season_differences'].append(dict(league=league,operator=op,method=method,metric='error_slope',comparison=second+' minus '+first,**interval(b[0]-a[0],b[1]-a[1])))
                    a=cache[(league,first,op)][1][method];b=cache[(league,second,op)][1][method]
                    collected['season_differences'].append(dict(league=league,operator=op,method=method,metric='extreme_gap',comparison=second+' minus '+first,**interval(b[0]-a[0],b[1]-a[1])))
                    sa=score_cache[(league,first,op,method)];sb=score_cache[(league,second,op,method)]
                    collected['season_differences'].append(dict(league=league,operator=op,method=method,metric='rps_skill',comparison=second+' minus '+first,**interval((1-sb[0]['rps'].mean()/baselines['historical_leave_season_out']['rps'][panels[(league,second)]].mean())-(1-sa[0]['rps'].mean()/baselines['historical_leave_season_out']['rps'][panels[(league,first)]].mean()),sb[2]-sa[2])))
    # Block lengths reflect consecutive chronological matches, not exact jornadas.
    for block in cfg['block_sensitivity']+[cfg['block_size']]:
        wb=W if block==cfg['block_size'] else block_weights(n,strata,B,block,cfg['seed'])
        for league in cfg['leagues']:
            idx=panels[(league,'all')]
            for op in cfg['operators']:
                for method in cfg['methods']:
                    est,draw=cache[(league,'all',op)][0][method] if block==cfg['block_size'] else (error_slope(cubes[op][method][idx],y[idx],np.ones((1,len(idx))))[0],error_slope(cubes[op][method][idx],y[idx],wb[:,idx]))
                    collected['block_sensitivity'].append(dict(league=league,operator=op,method=method,block_size=block,**interval(est,draw)))
    tables={name:pd.DataFrame(rows) for name,rows in collected.items()}
    # Predefined families distinguish main pooled comparisons from seasonal exploration.
    family_defs={
        'bias':['season'],'extremes':['season'],'method_differences':['season','metric'],
        'operator_differences':['season','metric'],'league_differences':['season','metric'],
        'season_differences':['metric'],'threshold_sensitivity':['definition'],'block_sensitivity':['block_size'],'outcome_calibration':['season']}
    for name,keys in family_defs.items():
        df=tables[name];df['p_holm']=np.nan
        for _,ix in df.groupby(keys,dropna=False).groups.items(): df.loc[ix,'p_holm']=holm(df.loc[ix,'p_boot'])
    for name,df in tables.items(): df.to_csv(root/'reports/tables'/f'{name}.csv',index=False,float_format='%.12g')
    pd.DataFrame(baseline,columns=['H','D','A']).assign(match_id=matches.match_id).to_csv(root/'data/processed/baseline_predictions.csv',index=False)
    return tables
