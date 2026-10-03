"""Público local y pandemia: ¿influía el público local en los resultados?

Experimento natural de la pandemia: partidos a puerta cerrada frente a partidos
con público, en Premier League (E0) y LaLiga (SP1), temporadas 2017/18–2024/25.
Reutiliza los métodos del proyecto: remoción del margen (src.methods), bootstrap
circular de bloques dentro de cada liga–temporada y ajuste de Holm (src.inference).
"""
import hashlib
import numpy as np
import pandas as pd
from .methods import remove_margin
from .inference import block_weights, interval, holm

MEASURES = {
    # nombre: (etiqueta, unidad, escala)
    'home_win': ('Victorias locales', '%', 100),
    'points_diff': ('Puntos local − visitante por partido', 'puntos', 1),
    'goal_diff': ('Goles local − visitante por partido', 'goles', 1),
    'shots_diff': ('Remates local − visitante por partido', 'remates', 1),
    'cards_diff': ('Amarillas visitante − local por partido', 'tarjetas', 1),
    'fouls_diff': ('Faltas visitante − local por partido', 'faltas', 1),
    'implied_B365': ('Prob. implícita de victoria local · Bet365', '%', 100),
    'implied_PS': ('Prob. implícita de victoria local · Pinnacle', '%', 100),
    'gap_B365': ('Brecha victoria local observada − implícita · Bet365', 'pp', 100),
    'gap_PS': ('Brecha victoria local observada − implícita · Pinnacle', 'pp', 100),
}
SPORT = ['home_win', 'points_diff', 'goal_diff', 'shots_diff', 'cards_diff', 'fouls_diff']
GROUPS = {'with_fans': ['pre', 'post'], 'pre': ['pre'], 'post': ['post'], 'closed': ['closed'],
          'closed_incl_limited': ['closed', 'limited']}


def _season_end(season):
    # 2019/20 se extendió hasta julio de 2020 por la suspensión.
    return pd.Timestamp(2020, 8, 31) if season == '2019-20' else pd.Timestamp(int(season[:4]) + 1, 6, 30)


def _period(league, date, c):
    if date <= pd.Timestamp(c['pre_end']): return 'pre'
    if date <= pd.Timestamp(c['closed_end']):
        for a, b in c['limited_attendance'].get(league, []):
            if pd.Timestamp(a) <= date <= pd.Timestamp(b): return 'limited'
        return 'closed'
    a, b = c['partial_attendance'].get(league, [None, None])
    if a and pd.Timestamp(a) <= date <= pd.Timestamp(b): return 'partial'
    return 'post'


def load_covid(root, cfg):
    """Valida temporadas completas; las cuotas de cierre ausentes quedan como NaN por casa."""
    c = cfg['covid']; rows = []; manifest = []; coverage = []
    for league in cfg['leagues']:
        for season in c['seasons']:
            folder = 'raw' if season in cfg['seasons'] else 'raw_covid'
            file = root / 'data' / folder / f'{league}_{season}.csv'
            if not file.exists():
                if season in c.get('optional_seasons', []):
                    coverage.append(dict(league=league, season=season, operator='—', matches=0, odds_available=0, note='archivo no suministrado (temporada opcional)'))
                    continue
                raise FileNotFoundError(f'{file}: falta el archivo de la temporada {season}')
            d = pd.read_csv(file, encoding='utf-8-sig', dtype=str)
            manifest.append(dict(file=f'{folder}/{file.name}', sha256=hashlib.sha256(file.read_bytes()).hexdigest(), bytes=file.stat().st_size))
            dates = pd.to_datetime(d.Date, format='%d/%m/%Y', errors='coerce').fillna(pd.to_datetime(d.Date, format='%d/%m/%y', errors='coerce'))
            num = {k: pd.to_numeric(d[k], errors='coerce') for k in ['FTHG', 'FTAG', 'HS', 'AS', 'HF', 'AF', 'HY', 'AY']}
            expected = np.where(num['FTHG'] > num['FTAG'], 'H', np.where(num['FTHG'] < num['FTAG'], 'A', 'D'))
            valid = (d.Div.eq(league) & dates.between(pd.Timestamp(int(season[:4]), 7, 1), _season_end(season))
                     & d.FTR.eq(expected) & d.HomeTeam.ne(d.AwayTeam) & ~d.duplicated(['HomeTeam', 'AwayTeam'], keep=False))
            for k in num: valid &= num[k].notna() & (num[k] >= 0)
            teams = pd.concat([d.HomeTeam, d.AwayTeam]).value_counts()
            if valid.sum() != 380 or len(teams) != 20 or not teams.eq(38).all():
                raise ValueError(f'{file.name}: falla la integridad de temporada completa')
            fr = pd.DataFrame(dict(league=league, season=season, date=dates, home=d.HomeTeam, away=d.AwayTeam, FTR=d.FTR))
            fr['period'] = [_period(league, x, c) for x in fr.date]
            fr['home_win'] = (d.FTR == 'H').astype(float); fr['draw'] = (d.FTR == 'D').astype(float); fr['away_win'] = (d.FTR == 'A').astype(float)
            pts_h = np.select([d.FTR == 'H', d.FTR == 'D'], [3, 1], 0); pts_a = np.select([d.FTR == 'A', d.FTR == 'D'], [3, 1], 0)
            fr['points_diff'] = (pts_h - pts_a).astype(float)
            fr['goal_diff'] = (num['FTHG'] - num['FTAG']).astype(float)
            fr['shots_diff'] = (num['HS'] - num['AS']).astype(float)
            fr['cards_diff'] = (num['AY'] - num['HY']).astype(float)
            fr['fouls_diff'] = (num['AF'] - num['HF']).astype(float)
            for op in cfg['operators']:
                cols = [op + 'C' + r for r in 'HDA']
                o = d.reindex(columns=cols).apply(pd.to_numeric, errors='coerce').to_numpy(dtype=float)
                with np.errstate(divide='ignore', invalid='ignore'):
                    margin = 100 * ((1 / o).sum(axis=1) - 1)
                ok = np.isfinite(o).all(axis=1) & (o > 1).all(axis=1) & (margin > 0) & (margin <= cfg['margin_alert_pp'])
                fr[f'margin_{op}'] = np.where(ok, margin, np.nan)
                qcols = {meth: np.full(len(d), np.nan) for meth in c['methods']}
                if ok.any():
                    q, k, z = remove_margin(o[ok])
                    for meth in c['methods']: qcols[meth][ok] = q[meth][:, 0]
                for meth in c['methods']: fr[f'qH_{meth}_{op}'] = qcols[meth]
                fr[f'implied_{op}'] = fr[f'qH_{c["method"]}_{op}']
                fr[f'gap_{op}'] = fr.home_win - fr[f'implied_{op}']
                note = 'completas' if ok.all() else ('sin columnas de cierre en el archivo' if not set(cols) <= set(d.columns) else f'{int((~ok).sum())} partido(s) sin cuota de cierre válida')
                coverage.append(dict(league=league, season=season, operator=op, matches=len(d), odds_available=int(ok.sum()), note=note))
            rows.append(fr)
    m = pd.concat(rows, ignore_index=True).sort_values(['league', 'season', 'date', 'home']).reset_index(drop=True)
    return m, pd.DataFrame(manifest), pd.DataFrame(coverage)


def _wmean(W, v, mask):
    """Media ponderada por réplica; ignora NaN (cuotas ausentes)."""
    keep = mask & np.isfinite(v)
    vv = np.where(keep, v, 0.)
    den = W @ keep.astype(float)
    return np.divide(W @ vv, den, out=np.full(len(W), np.nan), where=den > 0)


def _strength_design(s, period_levels):
    """Diseño lineal: y = HA_periodo + fuerza(local, temporada) − fuerza(visitante, temporada).

    Una referencia de fuerza por temporada (fuerza 0); HA no depende de esa elección
    porque las fuerzas solo entran como diferencias dentro de cada temporada.
    """
    P = np.column_stack([(s.period_group == p).to_numpy(float) for p in period_levels])
    keys = sorted(set(zip(s.season, s.home)) | set(zip(s.season, s.away)))
    refs = {season: min(t for ss, t in keys if ss == season) for season in s.season.unique()}
    keys = [k for k in keys if k[1] != refs[k[0]]]
    col = {k: j for j, k in enumerate(keys)}
    T = np.zeros((len(s), len(keys)))
    for i, (season, h, a) in enumerate(zip(s.season, s.home, s.away)):
        if (season, h) in col: T[i, col[(season, h)]] += 1
        if (season, a) in col: T[i, col[(season, a)]] -= 1
    return np.hstack([P, T])


def _wls(X, y, w):
    Xw = X * w[:, None]
    beta, *_ = np.linalg.lstsq(Xw.T @ X, Xw.T @ y, rcond=None)
    return beta


def strength_adjusted(m, W, league, outcome):
    """Ventaja de local por periodo ajustada por fuerza equipo–temporada; IC por bloques."""
    idx = np.flatnonzero(m.league.eq(league).to_numpy())
    s = m.iloc[idx].copy()
    s['period_group'] = s.period.where(~s.period.isin(['pre', 'post']), 'with_fans')
    levels = ['with_fans', 'closed', 'limited', 'partial']
    levels = [p for p in levels if (s.period_group == p).any()]
    X = _strength_design(s, levels); y = s[outcome].to_numpy(float)
    est = _wls(X, y, np.ones(len(s)))
    draws = np.array([_wls(X, y, W[b, idx]) for b in range(len(W))])
    out = []
    for j, p in enumerate(levels):
        if p in ('with_fans', 'closed'):
            out.append(dict(league=league, outcome=outcome, term=f'HA_{p}', **interval(est[j], draws[:, j])))
    jc, jf = levels.index('closed'), levels.index('with_fans')
    out.append(dict(league=league, outcome=outcome, term='HA_closed_minus_with_fans', **interval(est[jc] - est[jf], draws[:, jc] - draws[:, jf])))
    return out, (est[jc] - est[jf], draws[:, jc] - draws[:, jf])


def analyze_covid(root, cfg, m):
    c = cfg['covid']; B = cfg['bootstrap_reps']
    strata = [g.index.to_numpy() for _, g in m.groupby(['league', 'season'], sort=True)]
    W = block_weights(len(m), strata, B, cfg['block_size'], cfg['seed'] + 7)
    ones = np.ones((1, len(m)))

    def stat(league, measure, period_set, weights):
        mask = (m.league.eq(league) & m.period.isin(period_set)).to_numpy()
        return _wmean(weights, m[measure].to_numpy(dtype=float), mask)

    def n_valid(league, measure, period_set):
        return int((m.league.eq(league) & m.period.isin(period_set) & m[measure].notna()).sum())

    # Descriptivos por liga y periodo
    desc = []
    for league in cfg['leagues']:
        for p in ['pre', 'closed', 'limited', 'partial', 'post']:
            s = m[m.league.eq(league) & m.period.eq(p)]
            if len(s) == 0: continue
            row = dict(league=league, period=p, matches=len(s), date_min=s.date.min().date(), date_max=s.date.max().date(),
                       home_win_pct=100 * s.home_win.mean(), draw_pct=100 * s.draw.mean(), away_win_pct=100 * s.away_win.mean())
            for meas, (lab, unit, scale) in MEASURES.items():
                if meas == 'home_win': continue
                row[meas] = scale * s[meas].mean()
            row['matches_B365'] = int(s.implied_B365.notna().sum()); row['matches_PS'] = int(s.implied_PS.notna().sum())
            desc.append(row)
    desc = pd.DataFrame(desc)

    # Contrastes: estimación con pesos unitarios; IC y p con bloques
    contrasts = []
    plan = [('closed_minus_with_fans', 'closed', 'with_fans', 'principal'),
            ('closed_minus_pre', 'closed', 'pre', 'secundario'),
            ('closed_minus_post', 'closed', 'post', 'secundario'),
            ('post_minus_pre', 'post', 'pre', 'secundario'),
            ('closed_incl_limited_minus_with_fans', 'closed_incl_limited', 'with_fans', 'sensibilidad')]
    cache = {}
    for league in cfg['leagues']:
        for name, a, b, role in plan:
            for meas, (lab, unit, scale) in MEASURES.items():
                est = scale * (stat(league, meas, GROUPS[a], ones)[0] - stat(league, meas, GROUPS[b], ones)[0])
                draws = scale * (stat(league, meas, GROUPS[a], W) - stat(league, meas, GROUPS[b], W))
                cache[(league, name, meas)] = (est, draws)
                contrasts.append(dict(league=league, contrast=name, role=role, measure=meas, label=lab, unit=unit,
                                      n_a=n_valid(league, meas, GROUPS[a]), n_b=n_valid(league, meas, GROUPS[b]), **interval(est, draws)))
    contrasts = pd.DataFrame(contrasts)
    contrasts['p_holm'] = np.nan
    for _, ix in contrasts.groupby(['league', 'contrast']).groups.items():
        contrasts.loc[ix, 'p_holm'] = holm(contrasts.loc[ix, 'p_boot'])

    # Diferencia entre ligas del efecto principal (Premier − LaLiga), estratos independientes
    between = []
    for meas, (lab, unit, scale) in MEASURES.items():
        a = cache[('E0', 'closed_minus_with_fans', meas)]; b = cache[('SP1', 'closed_minus_with_fans', meas)]
        between.append(dict(contrast='Premier − LaLiga (efecto puerta cerrada)', measure=meas, label=lab, unit=unit, **interval(a[0] - b[0], a[1] - b[1])))
    between = pd.DataFrame(between); between['p_holm'] = holm(between.p_boot)

    # Fracción de la ventaja de local (puntos) que desapareció sin público
    share = []
    for league in cfg['leagues']:
        base = stat(league, 'points_diff', GROUPS['with_fans'], ones)[0]; closed = stat(league, 'points_diff', GROUPS['closed'], ones)[0]
        bw = stat(league, 'points_diff', GROUPS['with_fans'], W); cw = stat(league, 'points_diff', GROUPS['closed'], W)
        share.append(dict(league=league, home_adv_with_fans=base, home_adv_closed=closed,
                          **interval(100 * (1 - closed / base), 100 * (1 - cw / bw))))
    share = pd.DataFrame(share)

    # Robustez: ventaja de local ajustada por fuerza de equipo–temporada
    adjusted = []; adj_cache = {}
    for league in cfg['leagues']:
        for outcome in ['points_diff', 'goal_diff']:
            rows, eff = strength_adjusted(m, W, league, outcome)
            adjusted += rows; adj_cache[(league, outcome)] = eff
    adjusted = pd.DataFrame(adjusted)
    for outcome in ['points_diff', 'goal_diff']:
        a = adj_cache[('E0', outcome)]; b = adj_cache[('SP1', outcome)]
        adjusted = pd.concat([adjusted, pd.DataFrame([dict(league='E0−SP1', outcome=outcome, term='difference_between_leagues', **interval(a[0] - b[0], a[1] - b[1]))])], ignore_index=True)
    adjusted['p_holm'] = np.nan
    ix = adjusted.term.isin(['HA_closed_minus_with_fans', 'difference_between_leagues'])
    adjusted.loc[ix, 'p_holm'] = holm(adjusted.loc[ix, 'p_boot'])

    # Sensibilidad: tamaño de bloque y método de remoción
    sens = []
    for block in cfg['block_sensitivity']:
        Wb = block_weights(len(m), strata, B, block, cfg['seed'] + 7)
        for league in cfg['leagues']:
            for meas in ['points_diff', 'cards_diff', 'gap_B365', 'gap_PS']:
                scale = MEASURES[meas][2]
                est = scale * (stat(league, meas, GROUPS['closed'], ones)[0] - stat(league, meas, GROUPS['with_fans'], ones)[0])
                draws = scale * (stat(league, meas, GROUPS['closed'], Wb) - stat(league, meas, GROUPS['with_fans'], Wb))
                sens.append(dict(check=f'bloque {block}', league=league, measure=meas, **interval(est, draws)))
    for league in cfg['leagues']:
        for op in cfg['operators']:
            for meth in c['methods']:
                v = (m.home_win - m[f'qH_{meth}_{op}']).to_numpy()
                mc = (m.league.eq(league) & m.period.isin(GROUPS['closed'])).to_numpy()
                mf = (m.league.eq(league) & m.period.isin(GROUPS['with_fans'])).to_numpy()
                est = 100 * (_wmean(ones, v, mc)[0] - _wmean(ones, v, mf)[0]); draws = 100 * (_wmean(W, v, mc) - _wmean(W, v, mf))
                sens.append(dict(check=f'método {meth}', league=league, measure=f'gap_{op}', **interval(est, draws)))
    # Ventana común con Bet365 (solo desde 2019/20) para las medidas deportivas
    common = m.implied_B365.notna().to_numpy()
    for league in cfg['leagues']:
        for meas in ['points_diff', 'home_win', 'cards_diff']:
            scale = MEASURES[meas][2]; v = m[meas].to_numpy(float)
            mc = (m.league.eq(league) & m.period.isin(GROUPS['closed'])).to_numpy() & common
            mf = (m.league.eq(league) & m.period.isin(GROUPS['with_fans'])).to_numpy() & common
            est = scale * (_wmean(ones, v, mc)[0] - _wmean(ones, v, mf)[0]); draws = scale * (_wmean(W, v, mc) - _wmean(W, v, mf))
            sens.append(dict(check='solo temporadas desde 2019/20', league=league, measure=meas, **interval(est, draws)))
    sens = pd.DataFrame(sens)

    # Medias por periodo con IC por bloques (figuras)
    per = []
    for league in cfg['leagues']:
        for p in ['pre', 'closed', 'post', 'with_fans']:
            for meas, (lab, unit, scale) in MEASURES.items():
                est = scale * stat(league, meas, GROUPS[p], ones)[0]; draws = scale * stat(league, meas, GROUPS[p], W)
                fin = draws[np.isfinite(draws)]
                lo, hi = np.quantile(fin, [.025, .975]) if len(fin) >= 100 else (np.nan, np.nan)
                per.append(dict(league=league, period=p, measure=meas, label=lab, unit=unit, estimate=est, ci_low=lo, ci_high=hi,
                                matches=n_valid(league, meas, GROUPS[p])))
    per = pd.DataFrame(per)

    # Serie por temporada y tramo (figura): 2019/20 se divide en antes/cerrada
    sp = []
    for (league, season, period), g in m.groupby(['league', 'season', 'period'], sort=True):
        ix = g.index.to_numpy(); v = m.points_diff.to_numpy(float); mask = np.zeros(len(m), bool); mask[ix] = True
        draws = _wmean(W, v, mask)
        sp.append(dict(league=league, season=season, period=period, matches=len(g), points_diff=g.points_diff.mean(),
                       ci_low=np.nanquantile(draws, .025), ci_high=np.nanquantile(draws, .975), bootstrap_valid=int(np.isfinite(draws).sum()),
                       home_win_pct=100 * g.home_win.mean(), cards_diff=g.cards_diff.mean(),
                       implied_PS_pct=100 * g.implied_PS.mean(), implied_B365_pct=100 * g.implied_B365.mean()))
    season_period = pd.DataFrame(sp)

    tables = dict(covid_descriptives=desc, covid_contrasts=contrasts, covid_league_difference=between,
                  covid_share_lost=share, covid_strength_adjusted=adjusted, covid_sensitivity=sens,
                  covid_season_period=season_period, covid_period_means=per)
    for name, df in tables.items():
        df.to_csv(root / 'reports/tables' / f'{name}.csv', index=False, float_format='%.12g')
    m.to_csv(root / 'data/processed/covid_matches.csv', index=False)
    return tables
