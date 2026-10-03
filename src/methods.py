"""Margin removal and diagnostic metrics; no fitted odds selection model."""
import numpy as np
from scipy.optimize import brentq
from scipy.special import expit, logit
from scipy.stats import chi2, norm


def remove_margin(odds):
    odds = np.asarray(odds, dtype=float)
    if odds.ndim != 2 or odds.shape[1] != 3 or not np.all(np.isfinite(odds)) or np.any(odds <= 1):
        raise ValueError('Expected finite decimal odds > 1 in an n × 3 array')
    p = 1 / odds
    S = p.sum(axis=1)
    if np.any(S <= 1):
        raise ValueError('Nonpositive overround requires a documented separate treatment')
    additive = p - (S[:, None] - 1) / 3
    if np.any(additive <= 0):
        raise ValueError('Additive method gives nonpositive probabilities; do not silently truncate')
    power, shin = np.empty_like(p), np.empty_like(p)
    k, z = np.empty(len(p)), np.empty(len(p))
    for i, row in enumerate(p):
        upper = 2.
        while np.sum(row**upper) > 1:
            upper *= 2
        k[i] = brentq(lambda x: np.sum(row**x)-1, 1, upper, xtol=1e-13)
        power[i] = row**k[i]
        def q(x):
            # Stable form of Shin's quadratic root, avoiding subtractive cancellation.
            return 2*row**2/S[i] / (np.sqrt(x*x + 4*(1-x)*row**2/S[i]) + x)
        z[i] = brentq(lambda x: q(x).sum()-1, 0, 1-1e-10, xtol=1e-13)
        shin[i] = q(z[i])
    result = {'proportional': p/S[:, None], 'power': power, 'additive': additive, 'shin': shin}
    for name, q in result.items():
        if np.any(q <= 0) or np.any(q >= 1) or not np.allclose(q.sum(axis=1), 1, atol=1e-10):
            raise AssertionError(f'Invalid probabilities: {name}')
    return result, k, z


def scores(q, y):
    q, y = np.asarray(q), np.asarray(y)
    return {
        'brier': np.sum((q-y)**2, axis=1),  # Multiclass sum, range 0–2.
        'rps': np.mean((np.cumsum(q, axis=1)[:, :2]-np.cumsum(y, axis=1)[:, :2])**2, axis=1),
        'log_loss': -np.sum(y*np.log(q), axis=1)
    }


def quantile_bins(q, n):
    edges = np.unique(np.quantile(q, np.linspace(0, 1, n+1)))
    return np.searchsorted(edges[1:-1], q, side='left')


def wilson(success, n):
    z = norm.ppf(.975)
    p = success/n
    c = (p+z*z/(2*n))/(1+z*z/n)
    d = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return c-d, c+d


def murphy(q, y, n_bins):
    rel = res = unc = 0.
    for j in range(3):
        bins = quantile_bins(q[:, j], n_bins)
        mean_y = y[:, j].mean()
        unc += mean_y*(1-mean_y)
        for b in np.unique(bins):
            mask = bins == b
            w = mask.mean()
            rel += w*(q[mask,j].mean()-y[mask,j].mean())**2
            res += w*(y[mask,j].mean()-mean_y)**2
    bs = scores(q,y)['brier'].mean()
    return dict(brier=bs, reliability=rel, resolution=res, uncertainty=unc, binning_residual=bs-(rel-res+unc))


def calibration_logistic(q, y):
    """Pooled binary calibration with match-cluster sandwich; diagnostic only."""
    X = np.column_stack([np.ones(q.size), logit(q.ravel())])
    Y = y.ravel()
    beta = np.array([0.,1.])
    for _ in range(100):
        fitted = expit(X @ beta)
        hessian = X.T @ ((fitted*(1-fitted))[:,None]*X)
        step = np.linalg.solve(hessian, X.T @ (Y-fitted))
        beta += step
        if np.max(np.abs(step)) < 1e-10: break
    else: raise RuntimeError('Calibration logistic did not converge')
    residual = Y-expit(X@beta)
    cluster_scores = (X*residual[:,None]).reshape(len(q),3,2).sum(axis=1)
    bread = np.linalg.inv(hessian)
    cov = bread @ (cluster_scores.T @ cluster_scores) @ bread
    cov *= len(q)/(len(q)-1)*(q.size-1)/(q.size-2)
    se = np.sqrt(np.diag(cov))
    d = beta-np.array([0.,1.])
    return dict(intercept=beta[0], slope=beta[1], slope_ci_low=beta[1]-1.96*se[1], slope_ci_high=beta[1]+1.96*se[1],
                p_slope=2*norm.sf(abs(d[1]/se[1])), p_joint=chi2.sf(d@np.linalg.solve(cov,d),2))


def goodness_of_fit(q, y, g):
    b = quantile_bins(q,g)
    stat=0.
    for k in np.unique(b):
        m=b==k; expected=q[m].sum(); n=m.sum()
        stat += (y[m].sum()-expected)**2/(expected*(1-expected/n))
    # External predictions: zero parameters estimated for HL; diagnostic approximation.
    df=len(np.unique(b))
    numerator=((y-q)*(1-2*q)).sum()
    denominator=np.sqrt(((1-2*q)**2*q*(1-q)).sum())
    return dict(groups=df, hl=stat, p_hl=chi2.sf(stat,df), spiegelhalter_z=numerator/denominator,
                p_spiegelhalter=2*norm.sf(abs(numerator/denominator)))
