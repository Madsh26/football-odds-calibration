"""Figuras, hallazgos y sección HTML de la análisis de público local (público local)."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LEAGUE = {'E0': 'Premier League', 'SP1': 'LaLiga'}
PERIOD = {'pre': 'Con público\n(antes)', 'closed': 'Puerta\ncerrada', 'post': 'Con público\n(después)'}
PERIOD_TXT = {'pre': 'Con público (antes)', 'closed': 'Puerta cerrada', 'limited': 'Aforo mínimo (excluido)',
              'partial': 'Aforo parcial (excluido)', 'post': 'Con público (después)'}
COLOR = {'E0': '#2366be', 'SP1': '#d66b35'}
PCOLOR = {'pre': '#2366be', 'closed': '#c0392b', 'post': '#15846f'}


def _fmt(x, d=2):
    return f'{x:.{d}f}'.replace('.', ',') if np.isfinite(x) else '—'


def _p(x):
    return '&lt;0,001' if x < .001 else _fmt(x, 3)


def _save(root, fig, name):
    fig.savefig(root / 'reports/figures' / f'{name}.png', dpi=170, bbox_inches='tight', facecolor='white')
    fig.savefig(root / 'reports/figures' / f'{name}.svg', bbox_inches='tight', facecolor='white')
    plt.close(fig)


def _periods(ax, per, measure, title, ylabel, zero=True):
    x = np.arange(3)
    for k, league in enumerate(['E0', 'SP1']):
        d = per.query('league==@league and measure==@measure').set_index('period').loc[['pre', 'closed', 'post']]
        off = (k - .5) * .18
        ax.errorbar(x + off, d.estimate, yerr=[d.estimate - d.ci_low, d.ci_high - d.estimate], fmt='o', ms=7, capsize=0,
                    lw=2, color=COLOR[league], label=LEAGUE[league])
    if zero: ax.axhline(0, color='#8291a2', ls='--', lw=1)
    ax.set_xticks(x, [PERIOD[p] for p in ['pre', 'closed', 'post']]); ax.set_title(title, loc='left', fontweight='bold')
    ax.set_ylabel(ylabel); ax.grid(axis='y', alpha=.2)


def covid_plots(root, ct):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    per = ct['covid_period_means']
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    _periods(axes[0], per, 'points_diff', 'Ventaja de local en puntos', 'Puntos local − visitante por partido')
    _periods(axes[1], per, 'home_win', 'Victorias locales', '% de partidos', zero=False)
    axes[0].legend(loc='upper right')
    fig.suptitle('Ventaja de local por periodo · IC 95 % por bloques', fontweight='bold')
    fig.tight_layout(); _save(root, fig, 'covid_home_advantage')

    # Serie por temporada: 2019/20 se parte en antes / cerrada; 2020/21 cerrada; resto con público
    sp = ct['covid_season_period']
    seasons = sorted(sp.season.unique())
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, league in zip(axes, ['E0', 'SP1']):
        d = sp[(sp.league == league) & sp.period.isin(['pre', 'closed', 'post'])]
        shown = set()
        for r in d.itertuples():
            x = seasons.index(r.season) + {'pre': -.14, 'closed': .14, 'post': 0}[r.period] * (r.season == '2019-20')
            lab = PERIOD_TXT[r.period] if r.period not in shown else None; shown.add(r.period)
            ax.errorbar(x, r.points_diff, yerr=[[r.points_diff - r.ci_low], [r.ci_high - r.points_diff]], fmt='o', ms=7, lw=2,
                        color=PCOLOR[r.period], label=lab)
        ax.axhline(0, color='#8291a2', ls='--', lw=1); ax.axvspan(seasons.index('2019-20'), seasons.index('2020-21') + .5, color='#c0392b', alpha=.06)
        ax.set_xticks(range(len(seasons)), [s.replace('-', '/') for s in seasons], rotation=35)
        ax.set_title(LEAGUE[league], loc='left', fontweight='bold'); ax.grid(axis='y', alpha=.2)
        ax.set_ylabel('Puntos local − visitante por partido')
    axes[0].legend(loc='lower left', fontsize=8.5)
    fig.suptitle('Ventaja de local por temporada · la franja marca la etapa sin público', fontweight='bold')
    fig.tight_layout(); _save(root, fig, 'covid_seasons')

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    _periods(axes[0], per, 'cards_diff', 'Árbitro: amarillas al visitante − al local', 'Tarjetas por partido')
    _periods(axes[1], per, 'shots_diff', 'Juego: remates del local − del visitante', 'Remates por partido')
    axes[0].legend(loc='upper right')
    fig.suptitle('Canales: tarjetas (arbitraje) y remates (rendimiento) · IC 95 % por bloques', fontweight='bold')
    fig.tight_layout(); _save(root, fig, 'covid_mechanisms')

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    x = np.arange(3)
    for ax, league in zip(axes, ['E0', 'SP1']):
        obs = per.query('league==@league and measure=="home_win"').set_index('period').loc[['pre', 'closed', 'post']]
        for op, mk, col in [('B365', 'D', '#2366be'), ('PS', 's', '#15846f')]:
            imp = per[(per.league == league) & (per.measure == f'implied_{op}')].set_index('period').loc[['pre', 'closed', 'post']]
            lab = 'Implícita Bet365 (potencia; antes = solo 2019/20)' if op == 'B365' else 'Implícita Pinnacle (potencia)'
            ax.plot(x + (.12 if op == 'PS' else -.12), imp.estimate, mk, ms=7, color=col, label=lab)
        ax.errorbar(x, obs.estimate, yerr=[obs.estimate - obs.ci_low, obs.ci_high - obs.estimate], fmt='o', ms=8, color='#203049', lw=2, label='Observada (IC por bloques)')
        ax.set_xticks(x, [PERIOD[p] for p in ['pre', 'closed', 'post']]); ax.set_title(LEAGUE[league], loc='left', fontweight='bold')
        ax.set_ylabel('Victoria local (%)'); ax.grid(axis='y', alpha=.2)
    axes[0].legend(loc='lower left', fontsize=8)
    fig.suptitle('El mercado bajó la probabilidad del local sin público', fontweight='bold')
    fig.tight_layout(); _save(root, fig, 'covid_market')


def _row(ct, league, measure, contrast='closed_minus_with_fans'):
    c = ct['covid_contrasts']
    return c[(c.league == league) & (c.measure == measure) & (c.contrast == contrast)].iloc[0]


def _adj(ct, league, outcome, term='HA_closed_minus_with_fans'):
    a = ct['covid_strength_adjusted']
    return a[(a.league == league) & (a.outcome == outcome) & (a.term == term)].iloc[0]


def covid_answer(ct):
    """Texto breve de la respuesta (para el resumen y findings)."""
    sh = ct['covid_share_lost'].set_index('league'); e, s = sh.loc['E0'], sh.loc['SP1']
    pe, ps = _row(ct, 'E0', 'points_diff'), _row(ct, 'SP1', 'points_diff')
    ge = _adj(ct, 'SP1', 'goal_diff')
    return (f"Durante el periodo sin público, la ventaja de local en la Premier pasó de {_fmt(e.home_adv_with_fans)} a {_fmt(e.home_adv_closed)} puntos por partido "
            f"(p ajustado {_p(pe.p_holm)}): quedó prácticamente en cero. En LaLiga bajó de {_fmt(s.home_adv_with_fans)} a {_fmt(s.home_adv_closed)} (cerca del {s.estimate:.0f} %); "
            f"la caída es consistente en todas las medidas, pero solo en goles ajustados por fuerza y en remates supera el control de comparaciones múltiples "
            f"(goles: p ajustado {_p(ge.p_holm)}). El mercado bajó la probabilidad del local unos 3 pp y no se detectó un cambio concluyente en la brecha de victoria local observada frente a la prevista.")


def covid_findings(ct):
    lines = []
    sh = ct['covid_share_lost'].set_index('league')
    for lg in ['E0', 'SP1']:
        p = _row(ct, lg, 'points_diff'); w = _row(ct, lg, 'home_win'); cd = _row(ct, lg, 'cards_diff'); s = sh.loc[lg]
        a = _adj(ct, lg, 'points_diff'); ag = _adj(ct, lg, 'goal_diff')
        lines.append(f"{LEAGUE[lg]}: con público, el local sumaba {s.home_adv_with_fans:.2f} puntos más que el visitante por partido; a puerta cerrada, {s.home_adv_closed:.2f}. "
                     f"Cambio {p.estimate:.2f} puntos (IC {p.ci_low:.2f} a {p.ci_high:.2f}; p ajustado {p.p_holm:.3f}); victorias locales {w.estimate:+.1f} pp "
                     f"(IC {w.ci_low:.1f} a {w.ci_high:.1f}; p ajustado {w.p_holm:.3f}). Desapareció el {s.estimate:.0f} % de la ventaja en puntos (IC {s.ci_low:.0f} a {s.ci_high:.0f} %; más de 100 % indica que el local quedó levemente por debajo del visitante).")
        lines.append(f"{LEAGUE[lg]}, ajustado por fuerza de equipo–temporada: {a.estimate:.2f} puntos (IC {a.ci_low:.2f} a {a.ci_high:.2f}; p ajustado {a.p_holm:.3f}) y {ag.estimate:.2f} goles por partido (IC {ag.ci_low:.2f} a {ag.ci_high:.2f}; p ajustado {ag.p_holm:.3f}).")
        lines.append(f"{LEAGUE[lg]}: la diferencia de amarillas en contra del visitante cambió {cd.estimate:+.2f} por partido (IC {cd.ci_low:.2f} a {cd.ci_high:.2f}; p ajustado {cd.p_holm:.3f}).")
        i = _row(ct, lg, 'implied_PS'); g = _row(ct, lg, 'gap_PS')
        lines.append(f"{LEAGUE[lg]}: Pinnacle redujo la probabilidad implícita del local en {abs(i.estimate):.1f} pp (p ajustado {i.p_holm:.3f}); "
                     f"la brecha observada − implícita cambió {g.estimate:+.1f} pp (IC {g.ci_low:.1f} a {g.ci_high:.1f}; p ajustado {g.p_holm:.3f}).")
    b = ct['covid_league_difference']; k = int((b.p_holm < .05).sum())
    lines.append(f"Entre ligas, {k} de {len(b)} diferencias del efecto (Premier − LaLiga) alcanzan p ajustado <0,05: el efecto estimado es mayor en la Premier, pero la diferencia no es concluyente.")
    return lines


def _restart_note(ct):
    sp = ct['covid_season_period']
    g = lambda lg, ss: sp[(sp.league == lg) & (sp.season == ss) & (sp.period == 'closed')].iloc[0]
    e1, e2, s1, s2 = g('E0', '2019-20'), g('E0', '2020-21'), g('SP1', '2019-20'), g('SP1', '2020-21')
    return (f'<p><b>Por temporada.</b> En la Premier, la reanudación de 2019/20 sin público (junio–julio de 2020, {e1.matches} partidos) todavía mostró ventaja de local '
            f'({_fmt(e1.points_diff)} puntos; IC {_fmt(e1.ci_low)} a {_fmt(e1.ci_high)}); la caída se concentró en 2020/21 ({_fmt(e2.points_diff)}; IC {_fmt(e2.ci_low)} a {_fmt(e2.ci_high)}). '
            f'En LaLiga el descenso ya aparece en la reanudación ({_fmt(s1.points_diff)}) y se mantiene en 2020/21 ({_fmt(s2.points_diff)}). '
            'Los tramos son cortos, así que esta lectura es descriptiva; los contrastes formales agrupan todo el periodo sin público.</p>')


def covid_section(ct, img, table):
    sh = ct['covid_share_lost'].set_index('league')
    c = ct['covid_contrasts']; dd = ct['covid_descriptives']
    main = c[c.contrast == 'closed_minus_with_fans'][['league', 'label', 'unit', 'n_a', 'n_b', 'estimate', 'ci_low', 'ci_high', 'p_boot', 'p_holm']].copy()
    main['league'] = main.league.map(LEAGUE)
    main = main.rename(columns={'league': 'Liga', 'label': 'Medida', 'unit': 'Unidad', 'n_a': 'Partidos cerrada', 'n_b': 'Partidos con público',
                                'estimate': 'Puerta cerrada − con público', 'ci_low': 'IC inferior', 'ci_high': 'IC superior', 'p_boot': 'p bootstrap', 'p_holm': 'p ajustado (Holm)'})
    desc = dd[['league', 'period', 'matches', 'date_min', 'date_max', 'home_win_pct', 'draw_pct', 'away_win_pct', 'points_diff', 'goal_diff', 'shots_diff', 'cards_diff', 'implied_PS', 'gap_PS']].copy()
    desc['league'] = desc.league.map(LEAGUE); desc['period'] = desc.period.map(PERIOD_TXT)
    desc = desc.rename(columns={'league': 'Liga', 'period': 'Periodo', 'matches': 'Partidos', 'date_min': 'Desde', 'date_max': 'Hasta', 'home_win_pct': '% local',
                                'draw_pct': '% empate', 'away_win_pct': '% visitante', 'points_diff': 'Puntos L−V', 'goal_diff': 'Goles L−V', 'shots_diff': 'Remates L−V',
                                'cards_diff': 'Amarillas V−L', 'implied_PS': 'Implícita local PS (%)', 'gap_PS': 'Brecha PS (pp)'})
    adj = ct['covid_strength_adjusted'].copy()
    adj['league'] = adj.league.replace({**LEAGUE, 'E0−SP1': 'Premier − LaLiga'})
    adj['outcome'] = adj.outcome.map({'points_diff': 'Puntos L−V', 'goal_diff': 'Goles L−V'})
    adj['term'] = adj.term.map({'HA_with_fans': 'Ventaja con público', 'HA_closed': 'Ventaja a puerta cerrada',
                                'HA_closed_minus_with_fans': 'Cambio (cerrada − con público)', 'difference_between_leagues': 'Diferencia del cambio entre ligas'})
    adj = adj[['league', 'outcome', 'term', 'estimate', 'ci_low', 'ci_high', 'p_boot', 'p_holm']].rename(columns={
        'league': 'Liga', 'outcome': 'Medida', 'term': 'Término', 'estimate': 'Estimación', 'ci_low': 'IC inferior', 'ci_high': 'IC superior', 'p_boot': 'p bootstrap', 'p_holm': 'p ajustado'})
    sec = c[(c.role != 'principal') & c.measure.isin(['points_diff', 'home_win', 'goal_diff', 'cards_diff', 'implied_PS', 'gap_PS'])][['league', 'contrast', 'label', 'estimate', 'ci_low', 'ci_high', 'p_holm']].copy()
    sec['league'] = sec.league.map(LEAGUE)
    sec['contrast'] = sec.contrast.map({'closed_minus_pre': 'Cerrada − antes', 'closed_minus_post': 'Cerrada − después', 'post_minus_pre': 'Después − antes',
                                        'closed_incl_limited_minus_with_fans': 'Cerrada (+ aforo mínimo) − con público'})
    sec = sec.rename(columns={'league': 'Liga', 'contrast': 'Contraste', 'label': 'Medida', 'estimate': 'Estimación', 'ci_low': 'IC inferior', 'ci_high': 'IC superior', 'p_holm': 'p ajustado'})
    btw = ct['covid_league_difference'][['label', 'unit', 'estimate', 'ci_low', 'ci_high', 'p_holm']].rename(columns={'label': 'Medida', 'unit': 'Unidad', 'estimate': 'Premier − LaLiga', 'ci_low': 'IC inferior', 'ci_high': 'IC superior', 'p_holm': 'p ajustado'})
    sens = ct['covid_sensitivity'][['check', 'league', 'measure', 'estimate', 'ci_low', 'ci_high', 'p_boot']].copy()
    sens['league'] = sens.league.map(LEAGUE)
    sens = sens.rename(columns={'check': 'Comprobación', 'league': 'Liga', 'measure': 'Medida', 'estimate': 'Cerrada − con público', 'ci_low': 'IC inferior', 'ci_high': 'IC superior', 'p_boot': 'p bootstrap'})
    e, s = sh.loc['E0'], sh.loc['SP1']
    n_pre_e = int(dd[(dd.league == 'E0') & (dd.period == 'pre')].matches.iloc[0]); n_pre_s = int(dd[(dd.league == 'SP1') & (dd.period == 'pre')].matches.iloc[0])
    n_total = f'{int(dd.matches.sum()):,}'.replace(',', '.')
    first = min(ct['covid_season_period'].season).replace('-', '/')
    pe, ps = _row(ct, 'E0', 'points_diff'), _row(ct, 'SP1', 'points_diff')
    we, ws = _row(ct, 'E0', 'home_win'), _row(ct, 'SP1', 'home_win')
    ae, as_ = _adj(ct, 'E0', 'points_diff'), _adj(ct, 'SP1', 'points_diff')
    age, ags = _adj(ct, 'E0', 'goal_diff'), _adj(ct, 'SP1', 'goal_diff')
    ce, cs = _row(ct, 'E0', 'cards_diff'), _row(ct, 'SP1', 'cards_diff')
    re_, rs = _row(ct, 'E0', 'shots_diff'), _row(ct, 'SP1', 'shots_diff')
    ie, is_ = _row(ct, 'E0', 'implied_PS'), _row(ct, 'SP1', 'implied_PS')
    ge, gs = _row(ct, 'E0', 'gap_PS'), _row(ct, 'SP1', 'gap_PS')
    pp_e, pp_s = _row(ct, 'E0', 'points_diff', 'post_minus_pre'), _row(ct, 'SP1', 'points_diff', 'post_minus_pre')
    parts = [
        '<h2 id="covid">Público local y pandemia · ¿Influía el público local en los resultados?</h2>',
        '<section><p><b>Pregunta.</b> ¿Se redujo la ventaja de local en Premier League y LaLiga cuando los partidos se jugaron sin público durante la pandemia, '
        'por qué canales (arbitraje y rendimiento) y lo incorporó el mercado de cuotas de cierre?</p>'
        f'<p><b>Diseño.</b> Experimento natural con las temporadas completas {first}–2024/25 de ambas ligas ({n_total} partidos). Periodos: <i>con público antes</i> (hasta el 9/03/2020; {n_pre_e} partidos en la Premier y {n_pre_s} en LaLiga), '
        '<i>puerta cerrada</i> (desde la reanudación hasta el final de 2020/21) y <i>con público después</i> (Premier desde agosto de 2021; LaLiga desde el 1/10/2021, al volver el aforo pleno). '
        'Los partidos con aforo mínimo (Premier: diciembre de 2020 y últimas jornadas de mayo de 2021; LaLiga: últimas jornadas de mayo de 2021) y con aforo parcial (LaLiga, agosto–septiembre de 2021) '
        'se excluyen del contraste principal; la sensibilidad reincorpora los de aforo mínimo. El contraste principal agrupa los periodos con público anterior y posterior frente a puerta cerrada.</p>'
        '<p><b>Medidas.</b> La ventaja de local es puntos del local − puntos del visitante por partido (vale cero si jugar en casa no da ventaja); también victorias locales, goles, remates (rendimiento) '
        'y amarillas y faltas del visitante − del local (arbitraje). El mercado se mide con la probabilidad implícita de victoria local (método de potencia, cuotas de cierre) y su brecha frente a lo observado. '
        'Football-Data no publica cuotas de cierre de Bet365 antes de 2019/20, así que las medidas de Bet365 usan 2019/20 en adelante y Pinnacle cubre todo el periodo.</p>'
        '<p><b>Inferencia.</b> La del proyecto: bootstrap circular de bloques de 20 partidos dentro de cada liga–temporada (2.000 réplicas) y Holm por liga y contraste sobre las diez medidas. '
        'Como robustez, un modelo lineal estima la ventaja de local por periodo controlando la fuerza de cada equipo en cada temporada '
        '(resultado = ventaja del periodo + fuerza del local − fuerza del visitante), con los mismos remuestreos.</p></section>',
        img('covid_home_advantage', 'Ventaja de local en puntos y porcentaje de victorias locales por periodo, con IC 95 % por bloques.'),
        img('covid_seasons', 'Ventaja de local por temporada; 2019/20 se divide en el tramo con público y el tramo a puerta cerrada.'),
        _restart_note(ct),
        f'<div class="note"><b>Respuesta.</b> La ventaja de local se redujo durante el periodo sin público; el diseño no aísla su efecto causal. '
        f'<b>Premier League:</b> la ventaja pasó de {_fmt(e.home_adv_with_fans)} a {_fmt(e.home_adv_closed)} puntos por partido (cambio {_fmt(pe.estimate)}; IC {_fmt(pe.ci_low)} a {_fmt(pe.ci_high)}; p ajustado {_p(pe.p_holm)}) '
        f'y las victorias locales cayeron {_fmt(-we.estimate,1)} pp: la ventaja media en puntos quedó prácticamente en cero. Ajustando por la fuerza de los equipos se mantiene la caída ({_fmt(ae.estimate)}; p ajustado {_p(ae.p_holm)}). '
        f'<b>LaLiga:</b> la ventaja bajó de {_fmt(s.home_adv_with_fans)} a {_fmt(s.home_adv_closed)} (cerca del {s.estimate:.0f} %; cambio {_fmt(ps.estimate)}, IC {_fmt(ps.ci_low)} a {_fmt(ps.ci_high)}). '
        f'La caída aparece en todas las medidas, pero solo supera el control de comparaciones múltiples en remates (p ajustado {_p(rs.p_holm)}) y en goles ajustados por fuerza '
        f'({_fmt(ags.estimate)} goles por partido; p ajustado {_p(ags.p_holm)}); en puntos no lo alcanza (p ajustado {_p(ps.p_holm)} sin ajustar por fuerza y {_p(as_.p_holm)} ajustado). '
        f'En el periodo posterior la ventaja media volvió a ser positiva en ambas ligas ("después − antes": {_fmt(pp_e.estimate)} y {_fmt(pp_s.estimate)} puntos, sin diferencia significativa). '
        'El efecto estimado es mayor en la Premier, pero la diferencia entre ligas no es concluyente.</div>',
        '<h3>Ventaja de local ajustada por fuerza de los equipos</h3><p>Cada temporada completa equilibra partidos de local y visitante, pero 2019/20 se divide en dos tramos con calendarios distintos. '
        'El modelo asigna a cada equipo una fuerza por temporada, de modo que la ventaja de cada periodo no dependa de qué equipos jugaron en casa en cada tramo.</p>', table(adj),
        img('covid_mechanisms', 'Diferencia de tarjetas amarillas y de remates entre visitante y local por periodo.'),
        f'<p><b>Canal arbitral.</b> Con público, el visitante recibía más amarillas que el local. Sin público esa diferencia desapareció en la Premier ({_fmt(ce.estimate)} por partido; p ajustado {_p(ce.p_holm)}) '
        f'y se redujo en LaLiga sin superar el ajuste ({_fmt(cs.estimate)}; p ajustado {_p(cs.p_holm)}). <b>Canal de rendimiento.</b> La ventaja de remates del local cayó en ambas ligas '
        f'(Premier {_fmt(re_.estimate)}, p ajustado {_p(re_.p_holm)}; LaLiga {_fmt(rs.estimate)}, p ajustado {_p(rs.p_holm)}). '
        'Las diferencias son compatibles con cambios en decisiones arbitrales y rendimiento; las tarjetas también dependen del juego. El diseño no identifica un efecto causal de cada mecanismo.</p>',
        img('covid_market', 'Victoria local observada frente a probabilidad implícita de Bet365 y Pinnacle por periodo.'),
        f'<p><b>Mercado.</b> Pinnacle bajó la probabilidad implícita del local {_fmt(-ie.estimate,1)} pp en la Premier y {_fmt(-is_.estimate,1)} pp en LaLiga (ambos p ajustado {_p(max(ie.p_holm, is_.p_holm))}); Bet365, desde 2019/20, se movió en la misma dirección y con magnitud similar. '
        f'La brecha observada − implícita se volvió negativa durante el cierre (cambio: Premier {_fmt(ge.estimate,1)} pp, IC {_fmt(ge.ci_low,1)} a {_fmt(ge.ci_high,1)}; LaLiga {_fmt(gs.estimate,1)} pp, IC {_fmt(gs.ci_low,1)} a {_fmt(gs.ci_high,1)}). '
        'Eso sugiere que el precio se ajustó algo menos de lo que cayó la ventaja real, pero el cambio no es concluyente: esta medida no demuestra un deterioro de la brecha de victoria local y tampoco prueba calibración perfecta.</p>',
        '<h3>Contraste principal: puerta cerrada − con público</h3>', table(main),
        '<h3>Descriptivos por periodo</h3>', table(desc),
        '<h3>Contrastes secundarios</h3><p>"Cerrada − antes" y "cerrada − después" evalúan la consistencia del cambio frente a cada referencia. "Después − antes" explora diferencias entre periodos con público; estos contrastes no descartan por sí solos otras alteraciones de la pandemia.</p>', table(sec),
        '<h3>¿Difiere el efecto entre ligas?</h3>', table(btw),
        '<h3>Sensibilidad</h3><p>Tamaño de bloque (1, 10 y 40 partidos), método de remoción del margen (proporcional frente a potencia) y restricción a las temporadas con cuotas de Bet365 (desde 2019/20). Ninguna cambia la dirección ni el orden de magnitud de los efectos.</p>', table(sens),
        '<section><h3>Límites</h3><ul><li>Es un experimento natural, no un ensayo: la pandemia también cambió calendarios, descansos y viajes. La ausencia de público es la explicación más directa, no la única posible.</li>'
        '<li>El modelo ajustado controla la fuerza de cada equipo por temporada, no cambios de forma dentro de una temporada.</li>'
        '<li>Las ventanas de aforo mínimo son aproximaciones documentadas en config.json; incluirlas no cambia las conclusiones.</li>'
        '<li>Antes de 2019/20 no hay cuotas de cierre de Bet365 en la fuente; las conclusiones de mercado se apoyan en Pinnacle para ese tramo.</li></ul></section>',
    ]
    return '\n'.join(parts)
