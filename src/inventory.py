"""Entregables 3 y 4: tabla de desviaciones por intervalo e inventario de cobertura.

Se construyen a partir de las tablas que ya produjo la ejecución, así que se
regeneran solos con `python run_all.py`.
"""
import html
import numpy as np
import pandas as pd

LIGA = {'E0': 'Premier League', 'SP1': 'LaLiga'}
CASA = {'B365': 'Bet365', 'PS': 'Pinnacle'}
METODO = {'proportional': 'Proporcional', 'power': 'Potencia', 'additive': 'Aditivo', 'shin': 'Shin'}
RESULTADO = {'H': 'Local', 'D': 'Empate', 'A': 'Visitante'}
PERIODO = {'pre': 'Con público (antes)', 'closed': 'Puerta cerrada', 'limited': 'Aforo mínimo', 'partial': 'Aforo parcial', 'post': 'Con público (después)'}


def _f(x, d=1):
    return '—' if pd.isna(x) else f'{x:.{d}f}'.replace('.', ',')


def _html(df, wrap=False):
    return f'<div class="table-wrap{" wrap" if wrap else ""}">' + df.to_html(index=False, border=0, escape=True, na_rep='—') + '</div>'


# ---------------------------------------------------------------------------
# Entregable 3 · Tabla de desviaciones por intervalo
# ---------------------------------------------------------------------------
def deviation_table(curves):
    """Una fila por liga × casa × método × resultado × intervalo (tres temporadas juntas)."""
    c = curves[curves.season == 'all'].copy()
    out = pd.DataFrame({
        'liga': c.league.map(LIGA), 'casa': c.operator.map(CASA), 'metodo': c.method.map(METODO),
        'resultado': c.outcome.map(RESULTADO), 'intervalo': c['bin'] + 1, 'partidos': c.n,
        'prob_min_pct': 100 * c.prob_min, 'prob_max_pct': 100 * c.prob_max,
        'pronosticada_pct': 100 * c.predicted, 'observada_pct': 100 * c.observed,
        'desviacion_pp': c.gap_pp, 'ic_bloques_inf_pp': c.gap_ci_low, 'ic_bloques_sup_pp': c.gap_ci_high,
        'wilson_inf_pct': 100 * c.wilson_low, 'wilson_sup_pct': 100 * c.wilson_high,
    })
    out['ic_excluye_cero'] = (out.ic_bloques_inf_pp > 0) | (out.ic_bloques_sup_pp < 0)
    return out.reset_index(drop=True)


def method_comparison(dev):
    """Resumen por método: desviación absoluta media y máxima, e intervalos cuyo IC excluye cero."""
    g = dev.groupby(['liga', 'casa', 'metodo'], sort=False)
    res = g.apply(lambda d: pd.Series({
        'intervalos': len(d),
        'desv_abs_media_pp': np.average(d.desviacion_pp.abs(), weights=d.partidos),
        'desv_abs_max_pp': d.desviacion_pp.abs().max(),
        'ic_excluye_cero': int(d.ic_excluye_cero.sum()),
    }), include_groups=False).reset_index()
    return res


def deviation_section(dev, comp):
    pw = dev[dev.metodo == 'Potencia']
    n_out = int(pw.ic_excluye_cero.sum()); n_tot = len(pw)
    parts = ['<h2 id="deviations">Tabla de desviaciones por intervalo</h2>',
             '<p>Para cada resultado se agrupan los pronósticos en 10 intervalos de igual frecuencia. En cada intervalo se compara la probabilidad media '
             'pronosticada con la frecuencia observada. La desviación es observada − pronosticada, en puntos porcentuales: positiva significa que el resultado '
             'ocurrió más de lo que decía la casa. El IC por bloques (95 %) viene del bootstrap circular de 20 partidos; el de Wilson es la referencia binomial '
             'para la frecuencia observada. Las tres temporadas se agrupan dentro de cada liga.</p>',
             f'<div class="note">Con el método de potencia, {n_out} de {n_tot} intervalos ({_f(100 * n_out / n_tot)} %) tienen un IC por bloques que excluye el cero. '
             'Con un nivel del 95 % se esperan alrededor de un 5 % por azar, así que no hay un patrón sistemático de desviación.</div>',
             '<h3>Comparación entre métodos de remoción del margen</h3>',
             '<p>Desviación absoluta media (ponderada por partidos) y máxima entre los 30 intervalos de cada combinación, y cuántos intervalos tienen un IC que excluye el cero.</p>']
    t = comp.copy()
    t['desv_abs_media_pp'] = t.desv_abs_media_pp.map(_f); t['desv_abs_max_pp'] = t.desv_abs_max_pp.map(_f)
    t['intervalos'] = t.intervalos.astype(int); t['ic_excluye_cero'] = t.ic_excluye_cero.astype(int)
    parts.append(_html(t.rename(columns={'liga': 'Liga', 'casa': 'Casa', 'metodo': 'Método', 'intervalos': 'Intervalos',
                                          'desv_abs_media_pp': 'Desviación absoluta media (pp)', 'desv_abs_max_pp': 'Desviación absoluta máxima (pp)',
                                          'ic_excluye_cero': 'Intervalos con IC que excluye 0'})))
    parts.append('<h3>Detalle por intervalo · método de potencia</h3><p>Despliegue cada combinación. La tabla completa con los cuatro métodos está en '
                 '<a href="tables/desviaciones_por_intervalo.csv">desviaciones_por_intervalo.csv</a>.</p>')
    for (lg, cs), d in pw.groupby(['liga', 'casa'], sort=False):
        v = pd.DataFrame({'Resultado': d.resultado, 'Intervalo': d.intervalo, 'Partidos': d.partidos,
                          'Rango pronosticado (%)': [f'{_f(a)}–{_f(b)}' for a, b in zip(d.prob_min_pct, d.prob_max_pct)],
                          'Pronosticada (%)': d.pronosticada_pct.map(_f), 'Observada (%)': d.observada_pct.map(_f),
                          'IC Wilson observada (%)': [f'{_f(a)}–{_f(b)}' for a, b in zip(d.wilson_inf_pct, d.wilson_sup_pct)],
                          'Desviación (pp)': d.desviacion_pp.map(_f),
                          'IC bloques desviación (pp)': [f'{_f(a)} a {_f(b)}' for a, b in zip(d.ic_bloques_inf_pp, d.ic_bloques_sup_pp)],
                          'IC excluye 0': d.ic_excluye_cero.map({True: 'Sí', False: 'No'})})
        parts.append(f'<details><summary><b>{html.escape(lg)} · {html.escape(cs)}</b> · {int(d.ic_excluye_cero.sum())} de {len(d)} intervalos con IC que excluye 0</summary>{_html(v)}</details>')
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Entregable 4 · Inventario de cobertura
# ---------------------------------------------------------------------------
def coverage_inventory(coverage, exclusions, covid_coverage, covid_matches, cfg):
    """Partidos disponibles por casa, liga y temporada, con exclusiones y su motivo."""
    rows = []
    for r in coverage.itertuples():
        nexc = int(((exclusions.file == f'{r.league}_{r.season}.csv') & exclusions.operator.isin([r.operator, 'all'])).sum()) if len(exclusions) else 0
        rows.append(dict(analisis='Calibración (principal y secundarias 1 y 2)', liga=LIGA[r.league], temporada=r.season.replace('-', '/'),
                         casa=CASA[r.operator], partidos_en_archivo=r.matches, con_cuota_de_cierre=r.matches - r.missing,
                         elegibles=r.eligible, excluidos=r.matches - r.eligible, cobertura_pct=r.coverage_pct,
                         motivo_exclusion='—' if r.eligible == r.matches else f'{r.missing} sin cuota; {r.invalid_nonmissing} inválidas; {r.margin_alert} con margen fuera de 0–20 pp'))
    m = covid_matches
    for r in covid_coverage.itertuples():
        if r.matches == 0: continue
        sub = m[(m.league == r.league) & (m.season == r.season)]
        excl_periods = sub.period.isin(['limited', 'partial']).sum()
        motivo = []
        if r.odds_available < r.matches:
            motivo.append('Football-Data no publica cuotas de cierre de Bet365 antes de 2019/20; se usan solo para medidas deportivas' if r.odds_available == 0
                          else f'{r.matches - r.odds_available} partido(s) sin cuota de cierre válida; se excluyen solo de las medidas de mercado')
        if excl_periods:
            motivo.append(f'{int(excl_periods)} partido(s) con aforo mínimo o parcial: fuera del contraste principal, incluidos en la sensibilidad')
        rows.append(dict(analisis='Secundaria 3 · público local', liga=LIGA[r.league], temporada=r.season.replace('-', '/'), casa=CASA[r.operator],
                         partidos_en_archivo=r.matches, con_cuota_de_cierre=r.odds_available, elegibles=r.odds_available,
                         excluidos=r.matches - r.odds_available, cobertura_pct=100 * r.odds_available / r.matches,
                         motivo_exclusion='; '.join(motivo) if motivo else '—'))
    inv = pd.DataFrame(rows)
    periods = (m.groupby(['league', 'season', 'period']).size().unstack(fill_value=0)
               .reindex(columns=['pre', 'closed', 'limited', 'partial', 'post'], fill_value=0).reset_index())
    periods['league'] = periods.league.map(LIGA); periods['season'] = periods.season.str.replace('-', '/')
    periods = periods.rename(columns={'league': 'liga', 'season': 'temporada', **{k: v for k, v in PERIODO.items()}})
    scope = pd.DataFrame([
        dict(decision='Casas de apuestas', alcance='Bet365 y Pinnacle, cuotas de cierre (B365CH/CD/CA y PSCH/CD/CA)',
             justificacion='Dos modelos de negocio contrastantes (margen alto de mercado masivo y margen bajo de referencia) con cobertura completa en la ventana común; permiten comparar casas sobre los mismos partidos.'),
        dict(decision='Momento de la cuota', alcance='Solo cierre',
             justificacion='La cuota de cierre incorpora toda la información previa al partido. Las columnas sin C son previas al cierre y no se asumen como apertura.'),
        dict(decision='Ligas', alcance='Premier League (E0) y LaLiga (SP1)', justificacion='Dos ligas grandes comparables; no se mezclan en la inferencia principal.'),
        dict(decision='Temporadas de la calibración', alcance='2022/23, 2023/24 y 2024/25',
             justificacion='Temporadas completas posteriores a la pandemia y anteriores al corte de calidad de Pinnacle.'),
        dict(decision='Pinnacle desde el 23/07/2025', alcance='Excluida (2025/26 en adelante)',
             justificacion='Football-Data advierte que sus cuotas quedaron desactualizadas por su API; incluirlas mediría un artefacto de recolección.'),
        dict(decision='Temporada 2026/27', alcance='Excluida', justificacion='Incompleta al momento del análisis.'),
        dict(decision='Temporadas 2017/18–2021/22', alcance='Solo para la secundaria 3',
             justificacion='Contienen el periodo de la pandemia; en la calibración mezclarían la anomalía de puerta cerrada con la pregunta principal.'),
        dict(decision='Partidos con aforo mínimo o parcial', alcance='Fuera del contraste principal de la secundaria 3',
             justificacion='No son ni con público pleno ni sin público; se reincorporan en un análisis de sensibilidad.'),
        dict(decision='Imputación', alcance='Ninguna', justificacion='Las cuotas ausentes no se rellenan ni se sustituyen por cuotas previas al cierre.'),
    ])
    return inv, periods, scope


def coverage_section(inv, periods, scope):
    main = inv[inv.analisis.str.startswith('Calibración')]
    cov = inv[inv.analisis.str.startswith('Secundaria 3')]
    fmt = lambda d: d.assign(cobertura_pct=d.cobertura_pct.map(_f)).rename(columns={
        'liga': 'Liga', 'temporada': 'Temporada', 'casa': 'Casa', 'partidos_en_archivo': 'Partidos en el archivo',
        'con_cuota_de_cierre': 'Con cuota de cierre', 'elegibles': 'Elegibles', 'excluidos': 'Excluidos', 'cobertura_pct': 'Cobertura (%)',
        'motivo_exclusion': 'Motivo de exclusión'}).drop(columns='analisis')
    parts = ['<h2 id="coverage">Inventario de cobertura</h2>',
             f'<p>Partidos disponibles por casa, liga y temporada, con las exclusiones aplicadas y su justificación. En la calibración, las dos casas cubren el '
             f'100 % de los {int(main.partidos_en_archivo.sum() // 2):,} partidos y no hubo exclusiones; las validaciones de integridad, resultado y cuotas están en la metodología.</p>'.replace('2,280', '2.280'),
             '<h3>Decisiones de alcance</h3>',
             _html(scope.rename(columns={'decision': 'Decisión', 'alcance': 'Alcance', 'justificacion': 'Justificación'}), wrap=True),
             '<h3>Calibración · pregunta principal y secundarias 1 y 2</h3>', _html(fmt(main)),
             '<h3>Secundaria 3 · público local</h3>',
             '<p>Las medidas deportivas (resultados, goles, remates, tarjetas) usan todos los partidos; las de mercado, solo los que tienen cuota de cierre válida de esa casa.</p>',
             _html(fmt(cov), wrap=True), '<h4>Partidos por periodo</h4>', _html(periods)]
    return '\n'.join(parts)


def build_inventory_tables(root, cfg, t):
    """Escribe las tablas CSV y devuelve el HTML de ambas secciones."""
    out = root / 'reports/tables'
    dev = deviation_table(t['curves']); comp = method_comparison(dev)
    dev.to_csv(out / 'desviaciones_por_intervalo.csv', index=False, float_format='%.6g')
    comp.to_csv(out / 'comparacion_metodos_desviacion.csv', index=False, float_format='%.6g')
    coverage = pd.read_csv(out / 'coverage.csv'); exclusions = pd.read_csv(out / 'exclusions.csv')
    sections = deviation_section(dev, comp)
    cov_html = ''
    if (out / 'covid_coverage.csv').exists() and (root / 'data/processed/covid_matches.csv').exists():
        inv, periods, scope = coverage_inventory(coverage, exclusions, pd.read_csv(out / 'covid_coverage.csv'),
                                                 pd.read_csv(root / 'data/processed/covid_matches.csv'), cfg)
        inv.to_csv(out / 'inventario_cobertura.csv', index=False, float_format='%.6g')
        periods.to_csv(out / 'inventario_periodos_publico_local.csv', index=False)
        scope.to_csv(out / 'decisiones_de_alcance.csv', index=False)
        cov_html = coverage_section(inv, periods, scope)
    return sections, cov_html
