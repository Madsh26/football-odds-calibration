"""Paired, stratified circular moving-block bootstrap on complete matches."""
import numpy as np


def block_weights(n, strata, reps, block, seed):
    rng=np.random.default_rng(seed)
    W=np.zeros((reps,n),dtype=float)
    for ids in strata:
        size=len(ids)
        starts=rng.integers(0,size,size=(reps,int(np.ceil(size/block))))
        draws=(starts[:,:,None]+np.arange(block))%size
        draws=draws.reshape(reps,-1)[:,:size]
        for b in range(reps): W[b,ids]=np.bincount(draws[b],minlength=size)
    return W


def weighted_mean(W, value):
    return (W @ value)/W.sum(axis=1)


def error_slope(q,y,W):
    """pp of residual change per 10 pp probability; three rows/match preserved."""
    x=10*q; e=100*(y-q)
    s0=3*W.sum(axis=1)
    sx=W@x.sum(axis=1); sy=W@e.sum(axis=1)
    sxx=W@(x*x).sum(axis=1); sxy=W@(x*e).sum(axis=1)
    return (sxy-sx*sy/s0)/(sxx-sx*sx/s0)


def extreme_gap(q,y,reference,W,low,high):
    e=100*(y-q)
    L=reference<low; H=reference>high
    nl=W@L.sum(axis=1); nh=W@H.sum(axis=1)
    return np.divide(W@(e*H).sum(axis=1),nh,out=np.full(len(W),np.nan),where=nh>0)-np.divide(W@(e*L).sum(axis=1),nl,out=np.full(len(W),np.nan),where=nl>0)


def interval(estimate, draws):
    draws=np.asarray(draws); finite=np.isfinite(draws); draws=draws[finite]
    if len(draws)<100: return dict(estimate=estimate,ci_low=np.nan,ci_high=np.nan,p_boot=np.nan,bootstrap_valid=len(draws))
    low,high=np.quantile(draws,[.025,.975])
    # Centered bootstrap two-sided tail, not a null-data bootstrap or exact test.
    p=(1+np.sum(np.abs(draws-estimate)>=abs(estimate)))/(len(draws)+1)
    return dict(estimate=float(estimate),ci_low=float(low),ci_high=float(high),p_boot=float(p),bootstrap_valid=len(draws))


def holm(p):
    p=np.asarray(p,float); result=np.full(len(p),np.nan); valid=np.flatnonzero(np.isfinite(p))
    order=valid[np.argsort(p[valid])]
    result[order]=np.minimum(1,np.maximum.accumulate(p[order]*np.arange(len(order),0,-1)))
    return result
