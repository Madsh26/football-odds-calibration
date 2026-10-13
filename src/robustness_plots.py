"""Figuras de la revisión: diagrama causal, dependencia, umbrales, curva suavizada y robustez del público local."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

LEAGUE = {'E0': 'Premier League', 'SP1': 'LaLiga'}
OP = {'B365': 'Bet365', 'PS': 'Pinnacle'}
OPCOLOR = {'B365': '#2366be', 'PS': '#15846f'}
LCOLOR = {'E0': '#2366be', 'SP1': '#d9692f'}


def _save(fig, root, name):
    fig.savefig(root / 'reports/figures' / f'{name}.png', dpi=170, bbox_inches='tight', facecolor='white')
    fig.savefig(root / 'reports/figures' / f'{name}.svg', bbox_inches='tight', facecolor='white')
    plt.close(fig)


def dag(root):
    fig, ax = plt.subplots(figsize=(11.5, 4.3)); ax.set_xlim(0, 12.6); ax.set_ylim(-.05, 4.95); ax.axis('off')
    def box(x, y, t, c, w=2.3, h=.9, ls='-'):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle='round,pad=0.04', fc=c, ec='#33475b', lw=1.1, ls=ls))
        ax.text(x, y, t, ha='center', va='center', fontsize=9)
    def arrow(a, b, c='#33475b', ls='-', rad=0.0):
        ax.annotate('', xy=b, xytext=a, arrowprops=dict(arrowstyle='-|>', color=c, lw=1.3, ls=ls, connectionstyle=f'arc3,rad={rad}', shrinkA=0, shrinkB=0))
    box(1.3, 4.4, 'Periodo de pandemia', '#f6f0d0')
    box(1.3, 2.1, 'Presencia de\npúblico local', '#fde6d6')
    box(5.0, 4.4, 'Otros cambios del periodo:\ncalendario, 5 sustituciones,\nCOVID en plantillas', '#fff4f4', w=2.9, h=1.0, ls='--')
    box(5.0, 3.0, 'Canal arbitral\n(amarillas, faltas)', '#e4eefb')
    box(5.0, 0.9, 'Canal deportivo\n(remates)', '#e4eefb')
    box(8.6, 2.1, 'Resultado\n(puntos L − V)', '#e2f3ee')
    box(8.6, 0.4, 'Fuerza equipo–temporada\n(ajustada en el modelo)', '#e9f6e6', w=2.7, h=.75)
    box(11.4, 3.8, 'Cuota de cierre\n(prob. implícita)', '#f1f1f1', w=2.2)
    arrow((1.3, 3.95), (1.3, 2.55))
    arrow((2.45, 4.4), (3.55, 4.4), c='#b03a2e', ls='--')
    arrow((6.45, 4.15), (8.3, 2.55), c='#b03a2e', ls='--')
    arrow((2.45, 2.35), (3.85, 2.85)); arrow((2.45, 1.85), (3.85, 1.05)); arrow((2.45, 2.1), (7.45, 2.1))
    ax.text(5.0, 2.17, 'otras rutas directas', fontsize=7.5, color='#5d6d7e', ha='center', va='bottom')
    arrow((6.15, 2.85), (7.45, 2.3)); arrow((6.15, 1.05), (7.45, 1.9))
    arrow((8.6, 0.78), (8.6, 1.65))
    arrow((6.45, 4.65), (10.3, 4.0), c='#7f8c8d', rad=-.1); arrow((9.95, 0.6), (11.2, 3.35), c='#7f8c8d', rad=.15)
    ax.text(11.4, 4.35, 'brecha = resultado − cuota', fontsize=7.5, color='#5d6d7e', ha='center', va='bottom')
    _save(fig, root, 'rev_dag')


def dependence(root, out):
    a = out['robust_acf']; s = out['robust_esquemas']
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    ax = axes[0]
    for series, ls in [('influencia de la pendiente', '-'), ('RPS por partido', ':')]:
        d = a[(a.series == series) & (a.operator == 'B365')].groupby('lag').acf.mean()
        ax.plot(d.index, d.values, ls=ls, color='#2366be', label=f'{series} (Bet365)')
    k = a[(a.operator == 'B365')].groupby(['league', 'season']).ngroups
    ax.axhspan(-1.96 / np.sqrt(380 * k), 1.96 / np.sqrt(380 * k), color='#a1a9b2', alpha=.25, label=f'banda 95 % de la media de {k} series independientes')
    ax.axhline(0, color='#8291a2', lw=.8); ax.set_xlabel('Rezago (partidos consecutivos)'); ax.set_ylabel('Autocorrelación media')
    ax.set_title('Autocorrelación dentro de cada liga–temporada', loc='left', fontweight='bold', fontsize=10); ax.legend(fontsize=7.5, frameon=False, loc='upper center', bbox_to_anchor=(.5, -.2), ncol=2)
    ax = axes[1]
    keep = ['Pendiente del error (pp por 10 pp)', 'Contraste de extremos 20/60 (pp)', 'RPS Pinnacle − Bet365', 'Pendiente LaLiga − Premier']
    order = ['independiente (bloque 1)', 'bloques de 10', 'bloques de 20', 'bloques de 40', 'semana (≈ jornada)']
    for k, st in enumerate(keep):
        d = s[s.statistic == st].groupby('scheme').se_ratio_vs_block20.mean().reindex(order)
        ax.plot(d.values, np.arange(len(order)) + (k - 1.5) * .12, 'o', ms=5, label=st)
    ax.axvline(1, color='#8291a2', ls='--', lw=1); ax.set_yticks(np.arange(len(order)), order)
    ax.set_xlabel('Error estándar relativo al de bloques de 20'); ax.set_title('Sensibilidad del error estándar al remuestreo', loc='left', fontweight='bold', fontsize=10)
    ax.legend(fontsize=7.5, frameon=False, loc='upper center', bbox_to_anchor=(.35, -.2), ncol=2); ax.invert_yaxis()
    fig.tight_layout(); _save(fig, root, 'rev_dependencia')


def thresholds(root, out):
    g = out['robust_umbrales']; g = g[g.method == 'power']
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.3), sharey=True)
    for ax, (lg, op) in zip(axes, [('E0', 'B365'), ('E0', 'PS'), ('SP1', 'B365'), ('SP1', 'PS')]):
        d = g[(g.league == lg) & (g.operator == op)]
        M = d.pivot(index='low', columns='high', values='estimate'); P = d.pivot(index='low', columns='high', values='p_boot')
        im = ax.imshow(M.values, cmap='RdBu_r', vmin=-12, vmax=12, origin='lower')
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                star = '*' if P.values[i, j] < .05 else ''
                ax.text(j, i, f'{M.values[i, j]:.1f}{star}'.replace('.', ','), ha='center', va='center', fontsize=7.5)
        ax.set_xticks(range(M.shape[1]), [f'>{int(100 * c)}' for c in M.columns]); ax.set_yticks(range(M.shape[0]), [f'<{int(100 * r)}' for r in M.index])
        ax.set_title(f'{LEAGUE[lg]} · {OP[op]}', fontsize=9.5); ax.set_xlabel('Umbral favoritos (%)')
    axes[0].set_ylabel('Umbral longshots (%)')
    cb = fig.colorbar(im, ax=axes, fraction=.015, pad=.01); cb.set_label('Contraste (pp)')
    fig.suptitle('Contraste de extremos (favoritos − longshots) con 25 pares de umbrales · método de potencia · * IC 95 % excluye 0 (sin ajustar)', fontsize=10, fontweight='bold', y=1.02)
    _save(fig, root, 'rev_umbrales')


def smooth_curve(root, out):
    c = out['robust_curva_suavizada']
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.7), sharey=True)
    for ax, lg in zip(axes, ['E0', 'SP1']):
        for op in ['B365', 'PS']:
            d = c[(c.league == lg) & (c.operator == op) & (c.method == 'power') & (c.local_support >= 50)]
            ax.plot(d.prob * 100, d.error_pp, color=OPCOLOR[op], label=f'{OP[op]} · potencia')
            ax.fill_between(d.prob * 100, d.ci_low, d.ci_high, color=OPCOLOR[op], alpha=.12)
            p = c[(c.league == lg) & (c.operator == op) & (c.method == 'proportional') & (c.local_support >= 50)]
            ax.plot(p.prob * 100, p.error_pp, color=OPCOLOR[op], ls=':', lw=1.2, label=f'{OP[op]} · proporcional')
        ax.axhline(0, color='#8291a2', ls='--', lw=1); ax.set_title(LEAGUE[lg], loc='left', fontweight='bold', fontsize=10)
        ax.set_xlabel('Probabilidad ajustada (%)'); ax.grid(alpha=.15)
    axes[0].set_ylabel('Error observado − pronosticado (pp)'); axes[1].legend(fontsize=8, frameon=False, loc='upper left')
    fig.suptitle('Curva continua del error de calibración (núcleo gaussiano, ancho 4 pp) · banda IC 95 % por bloques', fontsize=10, fontweight='bold')
    fig.tight_layout(); _save(fig, root, 'rev_curva_suavizada')


def covid(root, out):
    pl = out['covid_robust_placebo_dist']; ps = out['covid_robust_placebo']; sb = out['covid_robust_sustituciones']; af = out['covid_robust_aforo']
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.9), gridspec_kw=dict(width_ratios=[1, 1.25]))
    ax = axes[0]
    for lg in ['E0', 'SP1']:
        d = pl[pl.league == lg]['diff']
        ax.hist(d, bins=25, color=LCOLOR[lg], alpha=.45, label=f'{LEAGUE[lg]}: ventanas placebo con público')
        act = ps[ps.league == lg].actual.iloc[0]
        ax.axvline(act, color=LCOLOR[lg], lw=2.2); ax.text(act, ax.get_ylim()[1] * (.9 if lg == 'E0' else .75), f' real\n {act:.2f}'.replace('.', ','), color=LCOLOR[lg], fontsize=8, va='top')
    ax.axvline(0, color='#8291a2', ls='--', lw=1); ax.set_xlabel('Diferencia de ventaja local (puntos)'); ax.set_ylabel('Ventanas')
    ax.set_title('Prueba placebo temporal', loc='left', fontweight='bold', fontsize=10); ax.legend(fontsize=7.5, frameon=False, loc='upper right')
    ax = axes[1]
    rows = []
    for lg in ['E0', 'SP1']:
        for r in sb[(sb.league == lg) & (sb.subs != 'contraste')].itertuples():
            rows.append((f'{LEAGUE[lg]} · {r.crowd} · {r.subs} (n={int(r.matches)})', r.estimate, r.ci_low, r.ci_high, lg))
        for p, lab in [('limited', 'aforo mínimo'), ('partial', 'aforo parcial')]:
            d = af[(af.league == lg) & (af.period == p) & (af.measure == 'points_diff') & (~af.adjusted)]
            if len(d): r = d.iloc[0]; rows.append((f'{LEAGUE[lg]} · {lab} (n={int(r.matches)})', r.estimate, r.ci_low, r.ci_high, lg))
    for i, (lab, e, lo, hi, lg) in enumerate(rows):
        ax.plot([lo, hi], [i, i], color=LCOLOR[lg], lw=2); ax.plot(e, i, 'o', color=LCOLOR[lg])
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=7.8); ax.invert_yaxis(); ax.axvline(0, color='#8291a2', ls='--', lw=1)
    ax.set_xlabel('Puntos local − visitante por partido (IC 95 % por bloques)'); ax.set_title('Público, regla de sustituciones y aforo', loc='left', fontweight='bold', fontsize=10)
    fig.tight_layout(); _save(fig, root, 'rev_publico_robustez')


def robustness_plots(root, cfg, out):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    dag(root); dependence(root, out); thresholds(root, out); smooth_curve(root, out); covid(root, out)
