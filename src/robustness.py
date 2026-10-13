"""Análisis de robustez solicitados en la revisión académica del informe.

1. Dependencia: autocorrelación, longitud de bloque óptima (Politis–White) y
   esquemas de remuestreo alternativos (bloques 1/10/20/40, semana-jornada y
   bootstrap diádico por equipos).
2. Potencia: efecto mínimo detectable (EMD) con el error estándar bootstrap.
3. Equivalencia: TOST con IC 90 % y márgenes sustantivos declarados.
4. Sesgo favorito–longshot: matriz de umbrales y curva suavizada continua.
5. Calibración: distribución nula del ECE y de REL bajo calibración perfecta.
6. Métodos de remoción: diferencias pareadas de log loss y RPS.
7. Público local: dosis (aforo), prueba placebo temporal, regla de cinco
   sustituciones, aprendizaje del mercado.
8. Inventario completo de hipótesis y familias de Holm.

Todo es retrospectivo y descriptivo; ningún resultado constituye una estrategia de apuesta.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm, chi2
from .inference import block_weights, error_slope, extreme_gap, interval, holm, weighted_mean
from .methods import scores, quantile_bins
from .covid import _strength_design, _wls, GROUPS

LEAGUES = {'E0': 'Premier League', 'SP1': 'LaLiga'}
OPS = {'B365': 'Bet365', 'PS': 'Pinnacle'}

# Márgenes de equivalencia (declarados en la revisión; ver informe, sección 4.6)
EQ_MARGINS = {'error_slope': 1.0, 'rps': 0.002, 'rps_skill': 0.02}


# ---------------------------------------------------------------------------
# Esquemas de remuestreo
# ---------------------------------------------------------------------------
def week_weights(n, strata, dates, reps, seed):
    """Bootstrap de conglomerados: semanas calendario (≈ jornadas) dentro de cada liga–temporada."""
    rng = np.random.default_rng(seed)
    W = np.zeros((reps, n))
    for ids in strata:
        d = pd.to_datetime(pd.Series(dates[ids]))
        week = ((d - d.min()).dt.days // 7).to_numpy()
        labels, inv = np.unique(week, return_inverse=True)
        k = len(labels)
        draws = rng.integers(0, k, size=(reps, k))
        counts = np.stack([np.bincount(r, minlength=k) for r in draws])
        W[:, ids] = counts[:, inv]
    return W


def schemes(n, strata, dates, home, away, reps, seed, block):
    out = {}
    for b in [1, 10, block, 40]:
        out[f'bloques de {b}' if b > 1 else 'independiente (bloque 1)'] = block_weights(n, strata, reps, b, seed)
    out['semana (≈ jornada)'] = week_weights(n, strata, dates, reps, seed + 1)
    return out


def dyadic_meat(S, teams_home, teams_away):
    """Matriz 'carne' robusta a dependencia diádica (Aronow, Samii y Assenova, 2015):
    suma s_i s_j' sobre todos los pares de partidos que comparten al menos un equipo (incluido i = j)."""
    S = np.asarray(S, float); p = S.shape[1]
    labels = pd.Index(np.unique(np.concatenate([teams_home, teams_away])))
    h = labels.get_indexer(teams_home); a = labels.get_indexer(teams_away)
    T = np.zeros((len(labels), p)); np.add.at(T, h, S); np.add.at(T, a, S)
    meat = T.T @ T - S.T @ S          # cada partido aparece en dos equipos: se resta un s_i s_i'
    # pares que comparten los dos equipos (ida y vuelta) se contaron dos veces
    key = pd.Series([frozenset(x) for x in zip(h, a)])
    for _, ix in key.groupby(key).groups.items():
        ix = np.asarray(ix)
        if len(ix) > 1:
            G = S[ix]; tot = G.sum(axis=0)
            meat -= (np.outer(tot, tot) - G.T @ G)
    return meat


def ols_se(X, y, groups_match, home, away):
    """Coeficientes MCO con tres errores estándar: agrupado por partido y diádico por equipo."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    XtX_inv = np.linalg.pinv(X.T @ X); beta = XtX_inv @ X.T @ y; r = y - X @ beta
    sc = X * r[:, None]
    S = pd.DataFrame(sc).groupby(groups_match, sort=False).sum().to_numpy()
    gm = pd.Series(groups_match).drop_duplicates().index.to_numpy()
    V_match = XtX_inv @ (S.T @ S) @ XtX_inv
    V_dyad = XtX_inv @ dyadic_meat(S, home[gm], away[gm]) @ XtX_inv
    return beta, np.sqrt(np.diag(V_match)), np.sqrt(np.clip(np.diag(V_dyad), 0, None))


def team_dispersion(q, y, home, away, season):
    """¿Hay equipos sistemáticamente mal valorados? z por equipo–temporada de (victorias − prob. de victoria)."""
    rows = []
    for (s, t) in sorted(set(zip(season, home)) | set(zip(season, away))):
        mh = (season == s) & (home == t); ma = (season == s) & (away == t)
        obs = y[mh, 0].sum() + y[ma, 2].sum(); exp = q[mh, 0].sum() + q[ma, 2].sum()
        var = (q[mh, 0] * (1 - q[mh, 0])).sum() + (q[ma, 2] * (1 - q[ma, 2])).sum()
        rows.append((obs - exp) / np.sqrt(var))
    z = np.array(rows)
    return dict(team_seasons=len(z), mean_z2=float(np.mean(z ** 2)), chi2=float(np.sum(z ** 2)), p_chi2=float(chi2.sf(np.sum(z ** 2), len(z))),
                max_abs_z=float(np.max(np.abs(z))))


# ---------------------------------------------------------------------------
# Diagnóstico de dependencia
# ---------------------------------------------------------------------------
def acf(x, max_lag):
    x = np.asarray(x, float) - np.mean(x)
    v = np.dot(x, x) / len(x)
    return np.array([np.dot(x[:-k], x[k:]) / len(x) / v for k in range(1, max_lag + 1)])


def politis_white(x):
    """Longitud de bloque óptima para bootstrap circular (Politis y White, 2004; corrección de Patton et al., 2009)."""
    x = np.asarray(x, float); n = len(x); x = x - x.mean()
    kn = max(5, int(np.ceil(np.sqrt(np.log10(n)))))
    mmax = int(np.ceil(np.sqrt(n))) + kn
    rho = acf(x, mmax)
    crit = 2 * np.sqrt(np.log10(n) / n)
    m_hat = None
    for m in range(1, mmax - kn + 1):
        if np.all(np.abs(rho[m - 1:m - 1 + kn]) < crit):
            m_hat = m; break
    if m_hat is None: m_hat = mmax - kn
    M = min(2 * m_hat, mmax)
    R0 = np.dot(x, x) / n
    R = np.array([np.dot(x[:-k], x[k:]) / n for k in range(1, M + 1)])
    lam = np.array([1 if k / M <= .5 else 2 * (1 - k / M) for k in range(1, M + 1)])
    G = 2 * np.sum(lam * np.arange(1, M + 1) * R)
    g0 = R0 + 2 * np.sum(lam * R)
    D = (4 / 3) * g0 ** 2
    if G == 0 or D <= 0: return 1.0
    b = (2 * G ** 2 / D) ** (1 / 3) * n ** (1 / 3)
    return float(min(max(b, 1.0), np.ceil(min(3 * np.sqrt(n), n / 3))))


def slope_influence(q, y):
    """Contribución de cada partido al numerador de la pendiente del error (serie para la ACF)."""
    x = 10 * q; e = 100 * (y - q)
    xc = x - x.mean(); b = (xc * (e - e.mean())).sum() / (xc ** 2).sum()
    return (xc * (e - e.mean() - b * xc)).sum(axis=1)


def ljung_box(x, h):
    r = acf(x, h); n = len(x)
    q = n * (n + 2) * np.sum(r ** 2 / (n - np.arange(1, h + 1)))
    return q, chi2.sf(q, h)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def summary(est, draws, scale_ref=None):
    d = np.asarray(draws, float); d = d[np.isfinite(d)]
    se = d.std(ddof=1)
    lo90, hi90 = np.quantile(d, [.05, .95])
    base = interval(est, d)
    return dict(**base, se=se, ci90_low=lo90, ci90_high=hi90)


def equivalence(row, margin):
    """Clasificación conjunta: diferencia (IC 95 % excluye 0) y equivalencia (IC 90 % dentro de ±margen)."""
    eq = (row['ci90_low'] > -margin) and (row['ci90_high'] < margin)
    diff = (row['ci_low'] > 0) or (row['ci_high'] < 0)
    if eq and diff: return 'diferencia trivial (equivalente)'
    if eq: return 'equivalente'
    if diff: return 'diferente'
    return 'no concluyente'


def ece_matrix(q, y_sim, n_bins):
    """ECE macro (pp) para muchas realizaciones; las clases se fijan con q."""
    total = 0.
    for j in range(3):
        b = quantile_bins(q[:, j], n_bins)
        M = np.column_stack([b == k for k in np.unique(b)]).astype(float)
        cnt = M.sum(axis=0)
        obs = (y_sim[..., j] @ M) / cnt
        pred = (q[:, j] @ M) / cnt
        total = total + (np.abs(obs - pred) * (cnt / len(q))).sum(axis=-1)
    return 100 * total / 3


def rel_matrix(q, y_sim, n_bins):
    total = 0.
    for j in range(3):
        b = quantile_bins(q[:, j], n_bins)
        M = np.column_stack([b == k for k in np.unique(b)]).astype(float)
        cnt = M.sum(axis=0)
        obs = (y_sim[..., j] @ M) / cnt
        pred = (q[:, j] @ M) / cnt
        total = total + (((obs - pred) ** 2) * (cnt / len(q))).sum(axis=-1)
    return total


def simulate_outcomes(q, reps, rng):
    u = rng.random((reps, len(q)))
    c = np.cumsum(q, axis=1)
    h = (u < c[:, 0]); d = (~h) & (u < c[:, 1]); a = ~(h | d)
    return np.stack([h, d, a], axis=-1).astype(float)


def kernel_curve(q, y, W, grid, bw):
    """Error suavizado (pp) en función de la probabilidad: Nadaraya–Watson gaussiano sobre los 3 resultados."""
    qq = q.ravel(); ee = (100 * (y - q)).ravel()
    K = norm.pdf((grid[:, None] - qq[None, :]) / bw)
    W3 = np.repeat(W, 3, axis=1)
    num = W3 @ (K * ee).T; den = W3 @ K.T
    return num / den


# ---------------------------------------------------------------------------
# Parte A: calibración (2022/23–2024/25)
# ---------------------------------------------------------------------------
def calibration_robustness(cfg, matches, y, cubes, params):
    n = len(matches); B = cfg['bootstrap_reps']; seed = cfg['seed']; block = cfg['block_size']
    strata = [g.index.to_numpy() for _, g in matches.groupby(['league', 'season'], sort=True)]
    dates = matches.date.to_numpy(); home = matches.HomeTeam.to_numpy(); away = matches.AwayTeam.to_numpy()
    Ws = schemes(n, strata, dates, home, away, B, seed, block)
    W20 = Ws[f'bloques de {block}']
    lg_idx = {lg: np.flatnonzero(matches.league.eq(lg)) for lg in cfg['leagues']}
    out = {}

    # --- A1. Dependencia: ACF, Ljung–Box y bloque óptimo por liga–temporada
    dep = []; acf_rows = []
    for (lg, season), g in matches.groupby(['league', 'season'], sort=True):
        ix = g.index.to_numpy()
        for op in cfg['operators']:
            q = cubes[op]['power'][ix]; yy = y[ix]
            series = {'influencia de la pendiente': slope_influence(q, yy), 'RPS por partido': scores(q, yy)['rps']}
            for name, s in series.items():
                Q, p = ljung_box(s, 20)
                r = acf(s, 40)
                dep.append(dict(league=lg, season=season, operator=op, series=name, ljung_box_q20=Q, p_ljung_box=p,
                                acf_lag1=r[0], max_abs_acf_1_40=np.max(np.abs(r)), lags_outside_band=int(np.sum(np.abs(r) > 1.96 / np.sqrt(len(s)))),
                                politis_white_block=politis_white(s)))
                for k, v in enumerate(r, 1):
                    acf_rows.append(dict(league=lg, season=season, operator=op, series=name, lag=k, acf=v))
    out['robust_dependencia'] = pd.DataFrame(dep)
    out['robust_acf'] = pd.DataFrame(acf_rows)

    # --- A2. Estadísticos clave bajo cada esquema
    ones = lambda m: np.ones((1, m))
    rows = []; draws_store = {}
    for sname, W in Ws.items():
        for lg in cfg['leagues']:
            ix = lg_idx[lg]; yy = y[ix]; wi = W[:, ix]
            for op in cfg['operators']:
                q = cubes[op]['power'][ix]; ref = cubes[op]['proportional'][ix]
                est = error_slope(q, yy, ones(len(ix)))[0]; dr = error_slope(q, yy, wi)
                rows.append(dict(scheme=sname, statistic='Pendiente del error (pp por 10 pp)', league=lg, operator=op, **summary(est, dr)))
                draws_store[(sname, 'slope', lg, op)] = (est, dr)
                est = extreme_gap(q, yy, ref, ones(len(ix)), cfg['low_threshold'], cfg['high_threshold'])[0]
                dr = extreme_gap(q, yy, ref, wi, cfg['low_threshold'], cfg['high_threshold'])
                rows.append(dict(scheme=sname, statistic='Contraste de extremos 20/60 (pp)', league=lg, operator=op, **summary(est, dr)))
                qp = cubes[op]['proportional'][ix]
                est = est0 = error_slope(q, yy, ones(len(ix)))[0] - error_slope(qp, yy, ones(len(ix)))[0]
                dr = error_slope(q, yy, wi) - error_slope(qp, yy, wi)
                rows.append(dict(scheme=sname, statistic='Potencia − proporcional, pendiente', league=lg, operator=op, **summary(est, dr)))
            ra = scores(cubes['B365']['power'][ix], yy)['rps']; rb = scores(cubes['PS']['power'][ix], yy)['rps']
            rows.append(dict(scheme=sname, statistic='RPS Pinnacle − Bet365', league=lg, operator='—',
                             **summary(rb.mean() - ra.mean(), weighted_mean(wi, rb - ra))))
        for op in cfg['operators']:
            a = draws_store[(sname, 'slope', 'E0', op)]; b = draws_store[(sname, 'slope', 'SP1', op)]
            rows.append(dict(scheme=sname, statistic='Pendiente LaLiga − Premier', league='SP1−E0', operator=op, **summary(b[0] - a[0], b[1] - a[1])))
    sch = pd.DataFrame(rows)
    ref = sch[sch.scheme == f'bloques de {block}'].set_index(['statistic', 'league', 'operator']).se
    sch['se_ratio_vs_block20'] = [r.se / ref[(r.statistic, r.league, r.operator)] for r in sch.itertuples()]
    out['robust_esquemas'] = sch

    # --- A2b. Dependencia por equipos: EE analíticos diádicos y prueba de dispersión por equipo
    dy = []; disp = []
    for lg in cfg['leagues']:
        ix = lg_idx[lg]; yy = y[ix]; sub = matches.iloc[ix]
        ts_h = (sub.season + '|' + sub.HomeTeam).to_numpy(); ts_a = (sub.season + '|' + sub.AwayTeam).to_numpy()
        for op in cfg['operators']:
            for meth in ['proportional', 'power']:
                q = cubes[op][meth][ix]
                X = np.column_stack([np.ones(q.size), 10 * q.ravel()]); e = 100 * (yy - q).ravel()
                gid = np.repeat(np.arange(len(ix)), 3)
                beta, se_m, se_d = ols_se(X, e, gid, np.repeat(ts_h, 3), np.repeat(ts_a, 3))
                dy.append(dict(analysis='Pendiente del error (pp por 10 pp)', league=lg, operator=op, method=meth, estimate=beta[1],
                               se_match_cluster=se_m[1], se_dyadic_team_season=se_d[1], ratio=se_d[1] / se_m[1],
                               ci_low_dyadic=beta[1] - 1.96 * se_d[1], ci_high_dyadic=beta[1] + 1.96 * se_d[1],
                               p_dyadic=2 * norm.sf(abs(beta[1] / se_d[1]))))
            disp.append(dict(league=lg, operator=op, method='power', **team_dispersion(cubes[op]['power'][ix], yy, sub.HomeTeam.to_numpy(), sub.AwayTeam.to_numpy(), sub.season.to_numpy())))
    out['robust_diadico'] = pd.DataFrame(dy)
    out['robust_dispersion_equipos'] = pd.DataFrame(disp)

    # --- A3. Potencia: EMD con el SE del esquema más conservador
    pw = []
    dyt = out['robust_diadico']
    for (stat, lg, op), g in sch.groupby(['statistic', 'league', 'operator']):
        se20 = g[g.scheme == f'bloques de {block}'].se.iloc[0]; semax = g.se.max()
        if stat.startswith('Pendiente del error'):
            sd = dyt[(dyt.league == lg) & (dyt.operator == op) & (dyt.method == 'power')].se_dyadic_team_season.iloc[0]
            if sd > semax: semax = sd; g = pd.concat([g, pd.DataFrame([dict(scheme='diádico analítico', se=sd)])], ignore_index=True)
        m = {'Pendiente del error (pp por 10 pp)': 16, 'Contraste de extremos 20/60 (pp)': 16, 'Potencia − proporcional, pendiente': 12,
             'RPS Pinnacle − Bet365': 8, 'Pendiente LaLiga − Premier': 8}[stat]
        z_holm = norm.ppf(1 - .05 / (2 * m))
        pw.append(dict(statistic=stat, league=lg, operator=op, estimate=g.estimate.iloc[0], se_block20=se20, se_max=semax,
                       scheme_max=g.loc[g.se.idxmax(), 'scheme'],
                       mde80=(norm.ppf(.975) + norm.ppf(.8)) * semax, mde80_holm=(z_holm + norm.ppf(.8)) * semax, holm_family_size=m,
                       ci_low_block20=g[g.scheme == f'bloques de {block}'].ci_low.iloc[0], ci_high_block20=g[g.scheme == f'bloques de {block}'].ci_high.iloc[0]))
    out['robust_potencia'] = pd.DataFrame(pw)

    # --- A4. Equivalencia (TOST) para todas las comparaciones de las secundarias, sin selección
    eq = []
    one = lambda ix: np.ones((1, len(ix)))
    hist = np.empty_like(y, dtype=float)
    for lg in cfg['leagues']:
        for s in cfg['seasons']:
            t = (matches.league.eq(lg) & matches.season.eq(s)).to_numpy(); tr = (matches.league.eq(lg) & ~matches.season.eq(s)).to_numpy()
            hist[t] = y[tr].mean(axis=0)
    hist_rps = scores(hist, y)['rps']
    def panel(lg, season):
        m = matches.league.eq(lg) if season == 'all' else matches.league.eq(lg) & matches.season.eq(season)
        return np.flatnonzero(m)
    for lg in cfg['leagues']:
        ix = panel(lg, 'all'); yy = y[ix]; wi = W20[:, ix]
        for op in cfg['operators']:
            for meth in cfg['methods']:
                q = cubes[op][meth][ix]
                r = summary(error_slope(q, yy, one(ix))[0], error_slope(q, yy, wi))
                eq.append(dict(family='Calibración: pendiente del error = 0', comparison=f'{LEAGUES[lg]} · {OPS[op]} · {meth}', metric='error_slope', margin=EQ_MARGINS['error_slope'], **r))
        for meth in cfg['methods']:
            ra = scores(cubes['B365'][meth][ix], yy)['rps']; rb = scores(cubes['PS'][meth][ix], yy)['rps']
            r = summary(rb.mean() - ra.mean(), weighted_mean(wi, rb - ra))
            eq.append(dict(family='Casas: RPS Pinnacle − Bet365', comparison=f'{LEAGUES[lg]} · {meth}', metric='rps', margin=EQ_MARGINS['rps'], **r))
    def slope_and_skill(lg, season, op, meth):
        ix = panel(lg, season); yy = y[ix]; q = cubes[op][meth][ix]; wi = W20[:, ix]
        sl = (error_slope(q, yy, one(ix))[0], error_slope(q, yy, wi))
        r = scores(q, yy)['rps']; h = hist_rps[ix]
        sk = (1 - r.mean() / h.mean(), 1 - weighted_mean(wi, r) / weighted_mean(wi, h))
        return sl, sk
    for op in cfg['operators']:
        for meth in cfg['methods']:
            a = slope_and_skill('E0', 'all', op, meth); b = slope_and_skill('SP1', 'all', op, meth)
            eq.append(dict(family='Ligas: pendiente LaLiga − Premier', comparison=f'{OPS[op]} · {meth}', metric='error_slope', margin=EQ_MARGINS['error_slope'], **summary(b[0][0] - a[0][0], b[0][1] - a[0][1])))
            eq.append(dict(family='Ligas: RPSS LaLiga − Premier', comparison=f'{OPS[op]} · {meth}', metric='rps_skill', margin=EQ_MARGINS['rps_skill'], **summary(b[1][0] - a[1][0], b[1][1] - a[1][1])))
    for lg in cfg['leagues']:
        for op in cfg['operators']:
            for meth in cfg['methods']:
                for s1, s2 in zip(cfg['seasons'][:-1], cfg['seasons'][1:]):
                    a = slope_and_skill(lg, s1, op, meth); b = slope_and_skill(lg, s2, op, meth)
                    tag = f'{LEAGUES[lg]} · {OPS[op]} · {meth} · {s2} − {s1}'
                    eq.append(dict(family='Temporadas: pendiente', comparison=tag, metric='error_slope', margin=EQ_MARGINS['error_slope'], **summary(b[0][0] - a[0][0], b[0][1] - a[0][1])))
                    eq.append(dict(family='Temporadas: RPSS', comparison=tag, metric='rps_skill', margin=EQ_MARGINS['rps_skill'], **summary(b[1][0] - a[1][0], b[1][1] - a[1][1])))
    eq = pd.DataFrame(eq)
    eq['clasificacion'] = [equivalence(r, r['margin']) for _, r in eq.iterrows()]
    out['robust_equivalencia'] = eq

    # --- A5. Matriz de umbrales del contraste de extremos
    grid = []
    lows = [.10, .15, .20, .25, .30]; highs = [.50, .55, .60, .65, .70]
    for lg in cfg['leagues']:
        ix = lg_idx[lg]; yy = y[ix]; wi = W20[:, ix]
        for op in cfg['operators']:
            ref = cubes[op]['proportional'][ix]
            for meth in ['proportional', 'power']:
                q = cubes[op][meth][ix]
                for lo in lows:
                    for hi in highs:
                        est = extreme_gap(q, yy, ref, one(ix), lo, hi)[0]; dr = extreme_gap(q, yy, ref, wi, lo, hi)
                        grid.append(dict(league=lg, operator=op, method=meth, low=lo, high=hi, n_low=int((ref < lo).sum()), n_high=int((ref > hi).sum()), **interval(est, dr)))
    grid = pd.DataFrame(grid); grid['p_holm_grid'] = np.nan
    for _, ix in grid.groupby(['league', 'operator', 'method']).groups.items():
        grid.loc[ix, 'p_holm_grid'] = holm(grid.loc[ix, 'p_boot'])
    out['robust_umbrales'] = grid

    # --- A6. Curva continua suavizada del error con banda bootstrap
    gpts = np.round(np.arange(.04, .82, .02), 2); curve = []
    for lg in cfg['leagues']:
        ix = lg_idx[lg]; yy = y[ix]
        for op in cfg['operators']:
            for meth in ['proportional', 'power']:
                q = cubes[op][meth][ix]
                est = kernel_curve(q, yy, one(ix), gpts, .04)[0]; dr = kernel_curve(q, yy, W20[:, ix], gpts, .04)
                support = (np.abs(gpts[:, None] - q.ravel()[None, :]) < .04).sum(axis=1)
                for k, gp in enumerate(gpts):
                    curve.append(dict(league=lg, operator=op, method=meth, prob=gp, error_pp=est[k], ci_low=np.nanquantile(dr[:, k], .025),
                                      ci_high=np.nanquantile(dr[:, k], .975), local_support=int(support[k])))
    out['robust_curva_suavizada'] = pd.DataFrame(curve)

    # --- A7. ECE y REL frente a su distribución bajo calibración perfecta
    rng = np.random.default_rng(seed + 11); nul = []
    for lg in cfg['leagues']:
        ix = lg_idx[lg]; yy = y[ix]
        for op in cfg['operators']:
            for meth in cfg['methods']:
                q = cubes[op][meth][ix]
                ysim = simulate_outcomes(q, B, rng)
                for nb in [5, 10, 15, 20]:
                    e_obs = ece_matrix(q, yy[None], nb)[0]; e_null = ece_matrix(q, ysim, nb)
                    r_obs = rel_matrix(q, yy[None], nb)[0]; r_null = rel_matrix(q, ysim, nb)
                    # IC por bloques para el ECE (clases fijas)
                    wi = W20[:, ix]; tot = 0.
                    for j in range(3):
                        b = quantile_bins(q[:, j], nb); M = np.column_stack([b == k for k in np.unique(b)]).astype(float)
                        c = wi @ M; obs = (wi @ (M * yy[:, [j]])) / c; pred = (wi @ (M * q[:, [j]])) / c
                        tot = tot + (np.abs(obs - pred) * c / c.sum(axis=1, keepdims=True)).sum(axis=1)
                    e_boot = 100 * tot / 3
                    nul.append(dict(league=lg, operator=op, method=meth, bins=nb, ece_pp=e_obs, ece_ci_low=np.quantile(e_boot, .025), ece_ci_high=np.quantile(e_boot, .975),
                                    ece_null_mean=e_null.mean(), ece_null_p95=np.quantile(e_null, .95), p_ece=(1 + np.sum(e_null >= e_obs)) / (B + 1),
                                    ece_excess_pp=e_obs - e_null.mean(), rel=r_obs, rel_null_mean=r_null.mean(), rel_null_p95=np.quantile(r_null, .95),
                                    p_rel=(1 + np.sum(r_null >= r_obs)) / (B + 1)))
    nul = pd.DataFrame(nul); nul['p_holm'] = np.nan
    for _, ix in nul.groupby('bins').groups.items():
        nul.loc[ix, 'p_holm'] = holm(nul.loc[ix, 'p_ece'])
    out['robust_ece_nulo'] = nul

    # --- A8. Descomposición de Murphy con distinto número de clases
    from .methods import murphy
    mu = []
    for lg in cfg['leagues']:
        ix = lg_idx[lg]
        for op in cfg['operators']:
            for nb in [5, 10, 15, 20]:
                mu.append(dict(league=lg, operator=op, method='power', bins=nb, **murphy(cubes[op]['power'][ix], y[ix], nb)))
    out['robust_murphy_clases'] = pd.DataFrame(mu)

    # --- A9. Desempeño predictivo de los métodos (pareado)
    md = []
    for lg in cfg['leagues']:
        ix = lg_idx[lg]; yy = y[ix]; wi = W20[:, ix]
        for op in cfg['operators']:
            sp = scores(cubes[op]['power'][ix], yy)
            for other in ['proportional', 'additive', 'shin']:
                so = scores(cubes[op][other][ix], yy)
                for metric in ['log_loss', 'rps']:
                    d = sp[metric] - so[metric]
                    md.append(dict(league=lg, operator=op, comparison=f'power − {other}', metric=metric, **interval(d.mean(), weighted_mean(wi, d))))
    md = pd.DataFrame(md); md['p_holm'] = np.nan
    for _, ix in md.groupby('metric').groups.items():
        md.loc[ix, 'p_holm'] = holm(md.loc[ix, 'p_boot'])
    out['robust_metodos_puntaje'] = md
    return out


# ---------------------------------------------------------------------------
# Parte B: público local
# ---------------------------------------------------------------------------
FIVE_SUBS = {
    # Fechas en que cada liga permitió cinco sustituciones (fuentes en el informe).
    'E0': [('2020-06-17', '2020-07-26'), ('2022-07-01', '2025-06-30')],
    'SP1': [('2020-06-11', '2025-06-30')],
}


def five_subs(league, dates):
    d = pd.to_datetime(dates); out = np.zeros(len(d), bool)
    for a, b in FIVE_SUBS[league]:
        out |= (d >= pd.Timestamp(a)) & (d <= pd.Timestamp(b))
    return out


def covid_robustness(cfg, m):
    B = cfg['bootstrap_reps']; seed = cfg['seed'] + 7; block = cfg['block_size']
    strata = [g.index.to_numpy() for _, g in m.groupby(['league', 'season'], sort=True)]
    n = len(m)
    Ws = schemes(n, strata, m.date.to_numpy(), m.home.to_numpy(), m.away.to_numpy(), B, seed, block)
    W20 = Ws[f'bloques de {block}']
    out = {}

    def wmean(W, v, mask):
        keep = mask & np.isfinite(v); vv = np.where(keep, v, 0.); den = W @ keep.astype(float)
        return np.divide(W @ vv, den, out=np.full(len(W), np.nan), where=den > 0)

    one = np.ones((1, n)); pts = m.points_diff.to_numpy(float)
    # B1. Esquemas de remuestreo para el contraste principal
    rows = []
    for sname, W in Ws.items():
        for lg in cfg['leagues']:
            mc = (m.league.eq(lg) & m.period.isin(GROUPS['closed'])).to_numpy(); mf = (m.league.eq(lg) & m.period.isin(GROUPS['with_fans'])).to_numpy()
            for meas in ['points_diff', 'cards_diff', 'shots_diff']:
                v = m[meas].to_numpy(float)
                rows.append(dict(scheme=sname, league=lg, measure=meas, **summary(wmean(one, v, mc)[0] - wmean(one, v, mf)[0], wmean(W, v, mc) - wmean(W, v, mf))))
    sch = pd.DataFrame(rows)
    ref = sch[sch.scheme == f'bloques de {block}'].set_index(['league', 'measure']).se
    sch['se_ratio_vs_block20'] = [r.se / ref[(r.league, r.measure)] for r in sch.itertuples()]
    out['covid_robust_esquemas'] = sch

    # B1b. EE diádicos analíticos (equipo–temporada) para el contraste sin ajustar y el ajustado por fuerza
    dy = []
    for lg in cfg['leagues']:
        s_ = m[m.league.eq(lg) & m.period.isin(['pre', 'post', 'closed'])].copy()
        th = (s_.season + '|' + s_.home).to_numpy(); ta = (s_.season + '|' + s_.away).to_numpy(); gid = np.arange(len(s_))
        for meas in ['points_diff', 'cards_diff', 'shots_diff']:
            X = np.column_stack([np.ones(len(s_)), s_.period.eq('closed').to_numpy(float)])
            b, se_m, se_d = ols_se(X, s_[meas].to_numpy(float), gid, th, ta)
            dy.append(dict(league=lg, measure=meas, model='sin ajustar', estimate=b[1], se_match=se_m[1], se_dyadic=se_d[1], ratio=se_d[1] / se_m[1],
                           ci_low=b[1] - 1.96 * se_d[1], ci_high=b[1] + 1.96 * se_d[1], p=2 * norm.sf(abs(b[1] / se_d[1]))))
            s_['period_group'] = s_.period.where(~s_.period.isin(['pre', 'post']), 'with_fans')
            Xf = _strength_design(s_, ['with_fans', 'closed'])
            b, se_m, se_d = ols_se(Xf, s_[meas].to_numpy(float), gid, th, ta)
            L = np.zeros(Xf.shape[1]); L[1] = 1; L[0] = -1
            XtX_inv = np.linalg.pinv(Xf.T @ Xf); r = s_[meas].to_numpy(float) - Xf @ b
            S = Xf * r[:, None]
            Vm = XtX_inv @ (S.T @ S) @ XtX_inv; Vd = XtX_inv @ dyadic_meat(S, th, ta) @ XtX_inv
            est = L @ b; sm = np.sqrt(L @ Vm @ L); sd = np.sqrt(max(L @ Vd @ L, 0))
            dy.append(dict(league=lg, measure=meas, model='ajustado por fuerza equipo–temporada', estimate=est, se_match=sm, se_dyadic=sd, ratio=sd / sm,
                           ci_low=est - 1.96 * sd, ci_high=est + 1.96 * sd, p=2 * norm.sf(abs(est / sd))))
    out['covid_robust_diadico'] = pd.DataFrame(dy)

    # B2. Dosis: periodos de aforo, sin ajustar y ajustados por fuerza
    dose = []
    for lg in cfg['leagues']:
        for p in ['pre', 'post', 'closed', 'limited', 'partial']:
            mask = (m.league.eq(lg) & m.period.eq(p)).to_numpy()
            if not mask.any(): continue
            for meas in ['points_diff', 'home_win']:
                sc = 100 if meas == 'home_win' else 1; v = m[meas].to_numpy(float)
                dose.append(dict(league=lg, period=p, measure=meas, matches=int(mask.sum()), adjusted=False, **interval(sc * wmean(one, v, mask)[0], sc * wmean(W20, v, mask))))
        idx = np.flatnonzero(m.league.eq(lg).to_numpy()); s = m.iloc[idx].copy()
        s['period_group'] = s.period.where(~s.period.isin(['pre', 'post']), 'with_fans')
        levels = [p for p in ['with_fans', 'closed', 'limited', 'partial'] if (s.period_group == p).any()]
        X = _strength_design(s, levels); yv = s.points_diff.to_numpy(float)
        est = _wls(X, yv, np.ones(len(s))); dr = np.array([_wls(X, yv, W20[b, idx]) for b in range(B)])
        for j, p in enumerate(levels):
            dose.append(dict(league=lg, period=p, measure='points_diff', matches=int((s.period_group == p).sum()), adjusted=True, **interval(est[j], dr[:, j])))
            if p != 'with_fans':
                dose.append(dict(league=lg, period=f'{p} − with_fans', measure='points_diff', matches=int((s.period_group == p).sum()), adjusted=True, **interval(est[j] - est[0], dr[:, j] - dr[:, 0])))
    out['covid_robust_aforo'] = pd.DataFrame(dose)

    # B3. Prueba placebo temporal: ventanas consecutivas con público del mismo tamaño que el periodo cerrado
    plc = []; plc_dist = []
    for lg in cfg['leagues']:
        s = m[m.league.eq(lg)].sort_values('date')
        fans = s[s.period.isin(['pre', 'post'])]; L = int(s.period.eq('closed').sum())
        actual = s[s.period.eq('closed')].points_diff.mean() - fans.points_diff.mean()
        diffs = []
        for p in ['pre', 'post']:
            seg = fans[fans.period.eq(p)].points_diff.to_numpy(float)
            for start in range(0, len(seg) - L + 1, 5):
                win = seg[start:start + L]
                rest = np.delete(fans.points_diff.to_numpy(float), np.flatnonzero(fans.period.eq(p).to_numpy())[start:start + L])
                diffs.append(win.mean() - rest.mean()); plc_dist.append(dict(league=lg, segment=p, start=start, diff=diffs[-1]))
        diffs = np.array(diffs)
        plc.append(dict(league=lg, window=L, windows=len(diffs), actual=actual, placebo_min=diffs.min(), placebo_p2_5=np.quantile(diffs, .025),
                        placebo_p97_5=np.quantile(diffs, .975), placebo_max=diffs.max(), share_le_actual=float(np.mean(diffs <= actual))))
    out['covid_robust_placebo'] = pd.DataFrame(plc); out['covid_robust_placebo_dist'] = pd.DataFrame(plc_dist)

    # B4. Regla de cinco sustituciones
    subs = []
    m2 = m.copy(); m2['five'] = False
    for lg in cfg['leagues']:
        k = m2.league.eq(lg); m2.loc[k, 'five'] = five_subs(lg, m2.loc[k, 'date'])
    m2['fans'] = m2.period.isin(['pre', 'post']); m2['closed'] = m2.period.eq('closed')
    cells = {}
    for lg in cfg['leagues']:
        for fans in [True, False]:
            for five in [False, True]:
                mask = (m2.league.eq(lg) & (m2.fans if fans else m2.closed) & m2.five.eq(five)).to_numpy()
                if mask.sum() < 30: continue  # p. ej., el único partido de LaLiga a puerta cerrada antes de la suspensión
                est, dr = wmean(one, pts, mask)[0], wmean(W20, pts, mask)
                cells[(lg, fans, five)] = (est, dr)
                subs.append(dict(league=lg, crowd='con público' if fans else 'sin público', subs='5 cambios' if five else '3 cambios', matches=int(mask.sum()), **interval(est, dr)))
    for lg in cfg['leagues']:
        for name, a, b in [('sin público − con público, ambos con 3 cambios', (lg, False, False), (lg, True, False)),
                           ('sin público − con público, ambos con 5 cambios', (lg, False, True), (lg, True, True)),
                           ('5 − 3 cambios, ambos con público', (lg, True, True), (lg, True, False))]:
            if a in cells and b in cells:
                subs.append(dict(league=lg, crowd=name, subs='contraste', matches=np.nan, **interval(cells[a][0] - cells[b][0], cells[a][1] - cells[b][1])))
    out['covid_robust_sustituciones'] = pd.DataFrame(subs)

    # B5. Aprendizaje del mercado: brecha observada − implícita en la primera y la segunda mitad del periodo cerrado
    learn = []
    gap = m.gap_PS.to_numpy(float)
    for lg in cfg['leagues']:
        closed = m[m.league.eq(lg) & m.period.eq('closed')].sort_values('date')
        half = len(closed) // 2
        for name, ids in [('primera mitad', closed.index[:half]), ('segunda mitad', closed.index[half:])]:
            mask = np.zeros(n, bool); mask[ids] = True
            learn.append(dict(league=lg, part=name, date_from=closed.loc[ids].date.min().date(), date_to=closed.loc[ids].date.max().date(), matches=len(ids),
                              **interval(100 * wmean(one, gap, mask)[0], 100 * wmean(W20, gap, mask))))
        a = np.zeros(n, bool); a[closed.index[half:]] = True; b = np.zeros(n, bool); b[closed.index[:half]] = True
        learn.append(dict(league=lg, part='segunda − primera', matches=len(closed), **interval(100 * (wmean(one, gap, a)[0] - wmean(one, gap, b)[0]), 100 * (wmean(W20, gap, a) - wmean(W20, gap, b)))))
    out['covid_robust_mercado'] = pd.DataFrame(learn)
    return out


# ---------------------------------------------------------------------------
# Parte C: inventario de hipótesis y familias de Holm
# ---------------------------------------------------------------------------
def hypothesis_inventory(tables_dir):
    T = lambda name: pd.read_csv(tables_dir / f'{name}.csv')
    rows = []

    def add(df, table, family, role, desc_cols, p_col='p_boot', holm_col='p_holm'):
        for _, r in df.iterrows():
            rows.append(dict(table=table, family=family, role=role, hypothesis=' · '.join(str(r[c]) for c in desc_cols),
                             estimate=r.get('estimate'), ci_low=r.get('ci_low'), ci_high=r.get('ci_high'), p_raw=r[p_col], p_holm=r[holm_col]))
    b = T('bias'); add(b[b.season == 'all'], 'bias', 'P1 · Pendiente del error (2022/23–2024/25)', 'Principal', ['league', 'operator', 'method'])
    add(b[b.season != 'all'], 'bias', 'E · Pendiente por temporada', 'Exploratoria', ['league', 'season', 'operator', 'method'])
    e = T('extremes'); add(e[e.season == 'all'], 'extremes', 'P2 · Contraste de extremos 20/60', 'Principal (complementaria)', ['league', 'operator', 'method'])
    add(e[e.season != 'all'], 'extremes', 'E · Contraste de extremos por temporada', 'Exploratoria', ['league', 'season', 'operator', 'method'])
    md = T('method_differences'); x = md[md.season == 'all']
    for met in x.metric.unique(): add(x[x.metric == met], 'method_differences', f'P3 · Método − proporcional ({met})', 'Principal (sensibilidad al método)', ['league', 'operator', 'comparison'])
    add(md[md.season != 'all'], 'method_differences', 'E · Método − proporcional por temporada', 'Exploratoria', ['league', 'season', 'operator', 'comparison', 'metric'])
    od = T('operator_differences'); x = od[od.season == 'all']
    for met in x.metric.unique(): add(x[x.metric == met], 'operator_differences', f'S1c · Pinnacle − Bet365 ({met})', 'Secundaria (casas)', ['league', 'method'])
    add(od[od.season != 'all'], 'operator_differences', 'E · Casas por temporada', 'Exploratoria', ['league', 'season', 'method', 'metric'])
    ld = T('league_differences'); x = ld[ld.season == 'all']
    for met in x.metric.unique(): add(x[x.metric == met], 'league_differences', f'S1 · LaLiga − Premier ({met})', 'Secundaria 1 (ligas)', ['operator', 'method'])
    add(ld[ld.season != 'all'], 'league_differences', 'E · Ligas por temporada', 'Exploratoria', ['season', 'operator', 'method', 'metric'])
    sd = T('season_differences')
    for met in sd.metric.unique(): add(sd[sd.metric == met], 'season_differences', f'S2 · Temporadas consecutivas ({met})', 'Secundaria 2 (temporadas)', ['league', 'operator', 'method', 'comparison'])
    th = T('threshold_sensitivity'); x = th[th.season == 'all']
    for d in x.definition.unique(): add(x[x.definition == d], 'threshold_sensitivity', f'R · Umbrales del contraste ({d})', 'Sensibilidad', ['league', 'operator', 'method'])
    bl = T('block_sensitivity')
    for bs in bl.block_size.unique(): add(bl[bl.block_size == bs], 'block_sensitivity', f'R · Pendiente con bloque {bs}', 'Sensibilidad', ['league', 'operator', 'method'])
    cc = T('covid_contrasts')
    for (lg, c), g in cc.groupby(['league', 'contrast']):
        role = {'principal': 'Secundaria 3 (público local)', 'secundario': 'Secundaria 3 · complementaria', 'sensibilidad': 'Sensibilidad'}[g.role.iloc[0]]
        add(g, 'covid_contrasts', f'S3 · {lg} · {c}', role, ['league', 'contrast', 'measure'])
    ca = T('covid_strength_adjusted'); x = ca[ca.p_holm.notna()]
    add(x, 'covid_strength_adjusted', 'S3 · Ajustado por fuerza', 'Secundaria 3 (público local)', ['league', 'outcome', 'term'])
    cl = T('covid_league_difference'); add(cl, 'covid_league_difference', 'S3 · Premier − LaLiga', 'Secundaria 3 (público local)', ['measure'])
    import os
    if (tables_dir / 'robust_umbrales.csv').exists():
        g = T('robust_umbrales')
        for (lg, op, me), d in g.groupby(['league', 'operator', 'method']):
            add(d, 'robust_umbrales', f'R · Matriz de 25 umbrales · {lg} · {op} · {me}', 'Sensibilidad', ['league', 'operator', 'method', 'low', 'high'], holm_col='p_holm_grid')
        md = T('robust_metodos_puntaje')
        for met, d in md.groupby('metric'): add(d, 'robust_metodos_puntaje', f'R · Potencia − otros métodos ({met})', 'Sensibilidad', ['league', 'operator', 'comparison'])
        en = T('robust_ece_nulo').rename(columns={'p_ece': 'p_boot', 'ece_pp': 'estimate'})
        for nb, d in en.groupby('bins'): add(d, 'robust_ece_nulo', f'R · ECE frente a calibración perfecta ({nb} grupos)', 'Principal (diagnóstico)', ['league', 'operator', 'method'])
    inv = pd.DataFrame(rows)
    fam = inv.groupby(['family', 'role'], sort=False).agg(hypotheses=('p_raw', 'size'), p_raw_min=('p_raw', 'min'),
                                                           significant_raw=('p_raw', lambda s: int((s < .05).sum())),
                                                           significant_holm=('p_holm', lambda s: int((s < .05).sum()))).reset_index()
    return inv, fam
