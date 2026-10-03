"""Respuestas breves a las cuatro preguntas, calculadas desde las tablas de la ejecución."""
import numpy as np
from .covid_report import covid_answer


def _f(x, d=2):
    return f'{x:.{d}f}'.replace('.', ',')


def answers(t, ct=None):
    bias = t['bias'].query('season=="all"')
    n_sig = int((bias.p_holm < .05).sum())
    ece = t['bin_sensitivity'].query('bins==10 and scheme=="equal_frequency" and method=="power"').macro_ece_pp
    md = t['method_differences'].query('season=="all" and metric=="extreme_gap" and comparison=="power minus proportional"')
    pw = bias.query('method=="power"'); pr = bias.query('method=="proportional"')
    pr_ci_pos = int((pr.ci_low > 0).sum())
    rpss = t['scores'].query('season=="all" and method=="power"').rpss
    out = [('Calibración y sesgo favorito–longshot',
            f'Las cuotas de cierre muestran desviaciones promedio moderadas: con potencia, el error medio por resultado (ECE) va de {_f(ece.min())} a {_f(ece.max())} pp y el mercado mejora el RPS de la '
            f'frecuencia histórica entre {_f(100*rpss.min(),1)} % y {_f(100*rpss.max(),1)} %. Ninguna de las {len(bias)} pendientes del error es significativa tras Holm ({n_sig} de {len(bias)}). '
            f'La evidencia de sesgo favorito–longshot sí depende del método: con proporcional, {pr_ci_pos} de {len(pr)} pendientes tienen IC por encima de cero (LaLiga), y pasar a potencia '
            f'reduce el contraste favorito − improbable entre {_f(-md.estimate.max())} y {_f(-md.estimate.min())} pp. Ese cambio es mecánico del ajuste: no identifica cómo reparte el margen la casa.')]
    lg = t['league_differences'].query('season=="all"'); sd = t['season_differences']
    sl = lg.query('metric=="error_slope"')
    op = t['operator_differences'].query('season=="all" and metric=="rps"'); n_op = int((op.p_holm < .05).sum())
    out.append(('Comparación entre ligas',
                (f'LaLiga muestra pendientes del error mayores que la Premier en las {len(sl)} combinaciones de casa y método, pero ' if (sl.estimate > 0).all()
                 else f'LaLiga − Premier: {int((sl.estimate > 0).sum())} de {len(sl)} pendientes son mayores en LaLiga; ') +
                (f'ninguna de las {len(lg)} diferencias entre ligas ' if (lg.p_holm >= .05).all() else f'algunas de las {len(lg)} diferencias entre ligas ') +
                f'(pendiente, extremos y habilidad RPS) es significativa tras Holm ({int((lg.p_holm < .05).sum())} de {len(lg)}). Bet365 y Pinnacle dan el mismo patrón: '
                f'{n_op} de {len(op)} diferencias de RPS entre casas son significativas.'))
    out.append(('Comparación entre temporadas',
                f'No se detectan cambios concluyentes entre las tres temporadas: {int((sd.p_holm < .05).sum())} de {len(sd)} contrastes entre temporadas consecutivas son significativos tras Holm, '
                'y la conclusión es la misma con los cuatro métodos. Tres temporadas describen estabilidad reciente, no una tendencia de largo plazo.'))
    if ct is not None:
        out.append(('Público local y pandemia', covid_answer(ct)))
    return out
