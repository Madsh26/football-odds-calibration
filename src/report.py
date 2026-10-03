import base64
import html
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LABEL={'proportional':'Proporcional','power':'Potencia','additive':'Aditivo','shin':'Shin','B365':'Bet365','PS':'Pinnacle','E0':'Premier League','SP1':'LaLiga','H':'Local','D':'Empate','A':'Visitante'}
COLOR={'proportional':'#d66b35','power':'#2366be','additive':'#15846f','shin':'#9857ab'}


def save(root,fig,name):
    fig.savefig(root/'reports/figures'/f'{name}.png',dpi=170,bbox_inches='tight',facecolor='white')
    fig.savefig(root/'reports/figures'/f'{name}.svg',bbox_inches='tight',facecolor='white')
    plt.close(fig)


def forest(ax,df,labels,title,xlabel):
    x=df.estimate.to_numpy();lo=df.ci_low.to_numpy();hi=df.ci_high.to_numpy();pos=np.arange(len(df))
    # Percentile intervals need not contain the point estimate: draw endpoints directly.
    for j in pos: ax.plot([lo[j],hi[j]],[j,j],color='#708297',lw=2)
    ax.scatter(x,pos,color='#2366be',s=24,zorder=3);ax.axvline(0,color='#8291a2',ls='--',lw=1)
    ax.set_yticks(pos,labels);ax.invert_yaxis();ax.set_title(title,loc='left',fontweight='bold');ax.set_xlabel(xlabel)
    ax.grid(axis='x',alpha=.2)


def plots(root,cfg,t):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    for league in cfg['leagues']:
        fig,axes=plt.subplots(2,3,figsize=(12,7),sharex=True,sharey=True)
        for i,op in enumerate(cfg['operators']):
            for j,r in enumerate('HDA'):
                ax=axes[i,j]
                for method in cfg['methods']:
                    d=t['curves'].query('league==@league and operator==@op and outcome==@r and method==@method')
                    ax.plot(d.predicted,d.observed,'o-',ms=3,lw=1,label=LABEL[method],color=COLOR[method])
                    if method=='power':
                        for row in d.itertuples(): ax.plot([row.predicted,row.predicted],[row.observed_block_low,row.observed_block_high],color=COLOR[method],alpha=.5,lw=1)
                ax.plot([0,1],[0,1],ls='--',color='#a1a9b2',lw=1)
                ax.set_title(f'{LABEL[op]} · {LABEL[r]}');ax.set_xlim(0,1);ax.set_ylim(0,1);ax.grid(alpha=.15)
                if i==1: ax.set_xlabel('Probabilidad ajustada')
                if j==0: ax.set_ylabel('Frecuencia observada')
        handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=4)
        fig.suptitle(f'Calibración por resultado · {LABEL[league]} · 2022/23–2024/25',fontweight='bold')
        fig.tight_layout(rect=[0,.05,1,.94]);save(root,fig,'calibration_'+league)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,league in zip(axes,cfg['leagues']):
        d=t['bias'].query('league==@league and season=="all"').copy()
        labels=[f'{LABEL[r.operator]} · {LABEL[r.method]}' for r in d.itertuples()]
        forest(ax,d,labels,LABEL[league],'Cambio del error (pp) por 10 pp de probabilidad')
    fig.suptitle('Sesgo: pendiente positiva compatible con favorito–longshot',fontweight='bold');fig.tight_layout();save(root,fig,'bias_methods')
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,league in zip(axes,cfg['leagues']):
        d=t['method_differences'].query('league==@league and season=="all" and metric=="extreme_gap"')
        labels=[f'{LABEL[r.operator]} · {r.comparison.replace(" minus proportional"," − proporcional").replace("power","potencia").replace("additive","aditivo")}' for r in d.itertuples()]
        forest(ax,d,labels,LABEL[league],'Cambio en contraste favorito − improbable (pp)')
    fig.suptitle('Efecto directo del método: mismos resultados en los extremos',fontweight='bold');fig.tight_layout();save(root,fig,'paired_method_effect')
    fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
    for ax,league in zip(axes,cfg['leagues']):
        for op,color in [('B365','#2366be'),('PS','#15846f')]:
            d=t['margin'].query('league==@league and operator==@op and season!="all"')
            x=np.arange(len(d));ax.plot(x,d.mean_pp,'o-',label=LABEL[op],color=color)
            ax.fill_between(x,d.ci_low,d.ci_high,color=color,alpha=.15)
        ax.set_xticks(x,[s.replace('-','/') for s in d.season]);ax.set_title(LABEL[league]);ax.set_ylabel('Margen medio (pp)');ax.legend();ax.grid(alpha=.15)
    fig.suptitle('Margen de cierre por casa y temporada',fontweight='bold');fig.tight_layout();save(root,fig,'margin_seasons')
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True)
    for i,league in enumerate(cfg['leagues']):
        for j,op in enumerate(cfg['operators']):
            ax=axes[i,j]
            for method in cfg['methods']:
                d=t['bias'].query('league==@league and operator==@op and method==@method and season!="all"')
                ax.plot(np.arange(len(d)),d.estimate,'o-',label=LABEL[method],color=COLOR[method])
                if method=='power': ax.fill_between(np.arange(len(d)),d.ci_low,d.ci_high,color=COLOR[method],alpha=.13)
            ax.axhline(0,ls='--',color='#a1a9b2');ax.set_title(f'{LABEL[league]} · {LABEL[op]}');ax.set_xticks(np.arange(3),[s.replace('-','/') for s in cfg['seasons']]);ax.set_ylabel('Pendiente del error (pp/10 pp)');ax.grid(alpha=.15)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',ncol=4);fig.suptitle('Variación entre temporadas · IC para potencia',fontweight='bold');fig.tight_layout(rect=[0,.05,1,.94]);save(root,fig,'bias_seasons')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,league in zip(axes,cfg['leagues']):
        d=t['operator_differences'].query('league==@league and season=="all" and metric=="rps"')
        forest(ax,d,[LABEL[m] for m in d.method],LABEL[league],'Δ RPS: Pinnacle − Bet365; negativo favorece Pinnacle')
    fig.suptitle('Comparación de precisión sobre los mismos partidos',fontweight='bold');fig.tight_layout();save(root,fig,'operator_rps')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,metric in zip(axes,['error_slope','rps_skill']):
        d=t['league_differences'].query('season=="all" and metric==@metric')
        forest(ax,d,[f'{LABEL[r.operator]} · {LABEL[r.method]}' for r in d.itertuples()],('Pendiente del error' if metric=='error_slope' else 'Habilidad RPS frente a referencia'),'LaLiga − Premier')
    fig.suptitle('Diferencias entre ligas',fontweight='bold');fig.tight_layout();save(root,fig,'league_comparison')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,league in zip(axes,cfg['leagues']):
        for op,linestyle in [('B365','-'),('PS','--')]:
            for method in ['proportional','power']:
                d=t['bin_sensitivity'].query('league==@league and operator==@op and method==@method and scheme=="equal_frequency"').sort_values('bins')
                ax.plot(d.bins,d.macro_ece_pp,'o',ls=linestyle,color=COLOR[method],label=f'{LABEL[op]} · {LABEL[method]}')
        ax.set_title(LABEL[league]);ax.set_xlabel('Grupos de igual frecuencia');ax.set_ylabel('ECE medio por resultado (pp)');ax.legend(fontsize=8);ax.grid(alpha=.15)
    fig.suptitle('Sensibilidad del error de calibración al agrupamiento',fontweight='bold');fig.tight_layout();save(root,fig,'bins_sensitivity')


def num(v): return f'{v:.3f}' if np.isfinite(v) else '—'


def findings(t):
    count=int((t['bias'].query('season=="all"').p_holm<.05).sum())
    lines=[f'En el análisis principal agregado por liga, {count} de 16 pendientes del error alcanzan p ajustado <0,05. Esto limita la evidencia de sesgo sistemático después de controlar las comparaciones; no demuestra ausencia de sesgo ni equivalencia a calibración perfecta.']
    for league in ['E0','SP1']:
        for op in ['B365','PS']:
            d=t['bin_sensitivity'].query('league==@league and operator==@op and bins==10 and scheme=="equal_frequency"')
            a=d.query('method=="proportional"').iloc[0];b=d.query('method=="power"').iloc[0]
            bias=t['bias'].query('league==@league and operator==@op and season=="all"')
            prop=bias.query('method=="proportional"').iloc[0];power=bias.query('method=="power"').iloc[0]
            lines.append(f"{LABEL[league]} / {LABEL[op]}: ECE medio por resultado de {a.macro_ece_pp:.2f} pp con proporcional y {b.macro_ece_pp:.2f} pp con potencia. La pendiente del error pasa de {prop.estimate:.2f} (IC {prop.ci_low:.2f} a {prop.ci_high:.2f}) a {power.estimate:.2f} (IC {power.ci_low:.2f} a {power.ci_high:.2f}) pp por cada 10 pp de probabilidad. Estos errores dependen del agrupamiento.")
    d=t['method_differences'].query('season=="all" and metric=="extreme_gap" and comparison=="power minus proportional"')
    for r in d.itertuples(): lines.append(f"Cambio directo potencia − proporcional, {LABEL[r.league]} / {LABEL[r.operator]}: {r.estimate:.2f} pp en el contraste favorito − improbable (IC {r.ci_low:.2f} a {r.ci_high:.2f}; p ajustado {r.p_holm:.4f}). Los grupos se mantienen fijos con las probabilidades proporcionales.")
    for league in ['E0','SP1']:
        sc=t['scores'].query('league==@league and season=="all" and method=="power"')
        lines.append(f"{LABEL[league]}: con potencia, el RPS mejora entre {100*sc.rpss.min():.1f} % y {100*sc.rpss.max():.1f} % frente a la referencia histórica dejando una temporada fuera. Esto mide calidad global, no calibración por sí sola.")
    d=t['operator_differences'].query('season=="all" and metric=="rps"')
    lines.append(f"Entre casas, {int((d.p_holm<.05).sum())} de {len(d)} diferencias apareadas de RPS alcanzan p ajustado <0,05. No se establece superioridad concluyente de un operador.")
    for metric,name in [('error_slope','pendiente del error'),('extreme_gap','contraste favorito − improbable'),('rps_skill','habilidad relativa de RPS')]:
        d=t['league_differences'].query('season=="all" and metric==@metric')
        count=int((d.p_holm<.05).sum())
        lines.append(f"Comparación entre ligas: {count} de {len(d)} contrastes de {name} alcanzan p ajustado <0,05. No se interpreta ausencia de significancia como equivalencia.")
        d=t['season_differences'].query('metric==@metric');count=int((d.p_holm<.05).sum())
        lines.append(f"Comparaciones entre temporadas consecutivas: {count} de {len(d)} contrastes de {name} alcanzan p ajustado <0,05. Tres temporadas describen estabilidad reciente, no una tendencia de largo plazo.")
    lines.append('El reparto real del margen no está observado: estos resultados cuantifican sensibilidad a supuestos y no identifican el mecanismo interno de los operadores. Una diferencia de puntuación no equivale a una diferencia de calibración ni permite concluir rentabilidad.')
    lines.append('En el efecto directo de método con grupos fijos, el resultado observado se cancela algebraicamente. Su intervalo estrecho mide variación en el ajuste de probabilidades entre partidos; no demuestra por sí solo que exista sesgo real ni que potencia sea el método verdadero.')
    return lines


def build_report(root,cfg,matches,y,cubes,params,t,ct=None):
    plots(root,cfg,t)
    conclusions=findings(t)
    covid_lines=[]
    if ct is not None:
        from .covid_report import covid_plots, covid_findings, covid_section
        covid_plots(root,ct);covid_lines=covid_findings(ct)
    from .summary import answers
    brief=answers(t,ct)
    (root/'reports/findings.md').write_text('# Resultados del análisis ejecutado\n\n## Respuestas en breve\n\n'+'\n\n'.join(f'**{q}.** '+html.unescape(a) for q,a in brief)+'\n\n## Detalle\n\n'+'\n\n'.join(conclusions)+('\n\n## Público local y pandemia\n\n'+'\n\n'.join(covid_lines) if covid_lines else '')+'\n\nVéase index.html y las tablas CSV para intervalos, ajustes y sensibilidad.\n',encoding='utf-8')
    def table(df,columns=None):
        if columns is not None: df=df[columns]
        df=df.copy()
        for col in ['league','operator','method']:
            if col in df:
                df[col]=df[col].replace({**LABEL,'historical_leave_season_out':'Frecuencia histórica (otra temporada)','uniform':'Uniforme'})
        if 'season' in df: df['season']=df.season.replace({'all':'Tres temporadas'})
        if 'comparison' in df:
            df['comparison']=df.comparison.str.replace('power','potencia').str.replace('additive','aditivo').str.replace('proportional','proporcional').str.replace(' minus ',' − ')
        if 'metric' in df: df['metric']=df.metric.replace({'error_slope':'Pendiente del error','extreme_gap':'Contraste de extremos (pp)','rps_skill':'Habilidad relativa RPS'})
        df=df.rename(columns={'league':'Liga','operator':'Casa','method':'Método / referencia','season':'Temporada','matches':'Partidos','mean_pp':'Margen medio (pp)',
            'median_pp':'Mediana (pp)','ci_low':'IC inferior','ci_high':'IC superior','macro_ece_pp':'ECE por resultado (pp)','max_gap_pp':'Mayor brecha (pp)',
            'rpss':'Habilidad RPS','brier':'Brier','rps':'RPS','log_loss':'Pérdida logarítmica','comparison':'Comparación','estimate':'Estimación','p_holm':'p ajustado','metric':'Medida'})
        return '<div class="table-wrap">'+df.to_html(index=False,border=0,float_format=lambda x:f'{x:.4f}',na_rep='—',escape=True)+'</div>'
    def img(name,caption):
        content=base64.b64encode((root/'reports/figures'/f'{name}.png').read_bytes()).decode()
        return f'<figure><img src="data:image/png;base64,{content}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>'
    css='''body{margin:0;color:#203049;background:#f4f6fa;font:16px/1.6 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:30px}header{background:#152a47;color:white;padding:40px;border-radius:16px}h1{font-size:36px;line-height:1.2}h2{margin-top:45px;color:#183452}h3{margin-top:25px}nav{display:flex;gap:15px;flex-wrap:wrap;margin:25px 0}a{color:#2366be}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin:25px 0}.card,section{background:white;border-radius:12px;padding:24px}.card strong{display:block;font-size:30px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;white-space:nowrap;width:100%;font-size:13px}th,td{text-align:right;padding:9px;border-bottom:1px solid #e3e9ef}th{background:#edf2f8}th:first-child,td:first-child{text-align:left}figure{margin:25px 0}img{width:100%;height:auto;background:white;border-radius:10px}figcaption{font-size:13px;color:#53657a}li{margin-bottom:12px}.note{border-left:4px solid #2366be;padding:15px;background:#edf3fb}@media(max-width:700px){main{padding:12px}header{padding:22px}h1{font-size:27px}.cards{grid-template-columns:1fr}}'''
    parts=[f'<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Auditoría de cuotas · Premier y LaLiga</title><style>{css}</style><main>',
        '<header><p>FOOTBALL ODDS CALIBRATION · ANÁLISIS RETROSPECTIVO</p><h1>Calibración de cuotas y ventaja de local</h1><p>Cuotas de cierre 2022/23–2024/25 y público local 2017/18–2024/25. Comparaciones entre ligas, operadores, temporadas y métodos de retirada del margen.</p><p>Contribución conjunta: Mauricio Serrano · Andrés Beleño · Carlos Cadena</p></header>',
        '<nav><a href="#brief">Respuestas</a><a href="#questions">Preguntas</a><a href="#results">Hallazgos</a><a href="#calibration">Calibración</a><a href="#methods">Métodos</a><a href="#comparisons">Comparaciones</a><a href="#covid">Público local (COVID)</a><a href="#limits">Método y límites</a><a href="#files">Datos y tablas</a></nav>',
        f'<div class="cards"><div class="card"><strong>{len(matches):,}</strong>partidos únicos</div><div class="card"><strong>{2*len(matches):,}</strong>registros de operador</div><div class="card"><strong>{cfg["bootstrap_reps"]:,}</strong>réplicas de remuestreo</div></div>',
        '<section id="brief"><h2>Respuestas en breve</h2>'+''.join(f'<p><b>{html.escape(q)}.</b> {a}</p>' for q,a in brief)+'</section>',
        '<section id="questions"><h2>Preguntas de investigación</h2><p><b>Principal.</b> ¿Qué tan bien calibradas están las probabilidades de victoria local, empate y victoria visitante obtenidas de las cuotas de cierre de Bet365 y Pinnacle en Premier League y LaLiga durante 2022/23–2024/25, y en qué medida la evidencia del sesgo favorito–longshot depende del método empleado para remover el margen?</p><p><b>Entre ligas.</b> ¿Difieren las ligas en magnitud y dirección de las desviaciones, especialmente en resultados de baja y alta probabilidad, y son consistentes estas diferencias entre casas?</p><p><b>Entre temporadas.</b> ¿Cómo varían la calibración y el sesgo dentro de cada liga y operador, y se mantienen las conclusiones al cambiar de método?</p><p><b>Público local (COVID-19).</b> ¿Se redujo la ventaja de local en ambas ligas cuando se jugó sin público, por qué canales, y lo incorporó el mercado? Usa las temporadas 2017/18–2024/25.</p></section>',
        '<h2 id="results">Hallazgos calculados</h2><section><ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in conclusions)+'</ul>'+('<h3>Público local (COVID-19)</h3><ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in covid_lines)+'</ul>' if covid_lines else '')+'</section>',
        '<h2>Margen y cobertura</h2><p>Ambas casas tienen cobertura común completa en los seis archivos. La selección evita la temporada parcial y queda antes del corte de Pinnacle señalado en la documentación de la fuente. Las medias de margen no son probabilidades de pérdida ni demuestran superioridad predictiva.</p>',
        table(t['margin'].query('season=="all"'),['league','operator','matches','mean_pp','median_pp','ci_low','ci_high']),img('margin_seasons','Margen: intervalos por bloques temporales; cada partido conserva ambas casas.'),
        '<h2 id="calibration">Calibración por resultado</h2><p>La diagonal representa concordancia. Se muestran 10 grupos de igual frecuencia por resultado; las barras de potencia usan el remuestreo por bloques. La comparación no se realiza sobre probabilidades brutas.</p>',
        img('calibration_E0','Premier League: local, empate y visitante; curvas de cuatro métodos.'),img('calibration_SP1','LaLiga: mismo procedimiento y periodo que Premier.'),
        table(t['bin_sensitivity'].query('bins==10 and scheme=="equal_frequency"'),['league','operator','method','macro_ece_pp','max_gap_pp']),
        '<h3>Precisión frente a referencias</h3><p>Brier usa la suma multiclase (rango 0–2); RPS usa H–D–A y división por dos. La referencia histórica se calcula con las otras dos temporadas de la misma liga. Es una comparación retrospectiva dejando una temporada fuera, no una simulación de pronóstico futuro. Sus probabilidades permanecen fijas en los intervalos bootstrap.</p>',
        table(t['scores'].query('season=="all"'),['league','operator','method','brier','rps','log_loss','rpss']),
        '<h2 id="methods">Sesgo y efecto directo del método</h2><p>Una pendiente positiva indica que el error observado − pronosticado crece con la probabilidad. Se reportan unidades de puntos porcentuales de error por cada 10 puntos de probabilidad.</p>',img('bias_methods','Pendientes e intervalos por bloques, por liga y operador.'),
        '<p>Para comparar métodos, los resultados de baja (&lt;20 %) y alta (&gt;60 %) probabilidad se identifican una sola vez con el método proporcional de cada casa. Se conserva esa pertenencia al aplicar los cuatro ajustes. Así no se confunde cambio de probabilidades con cambio de integrantes del grupo. En esta diferencia directa el resultado observado se cancela: mide el efecto del ajuste, no constituye una prueba independiente de sesgo real.</p>',
        img('paired_method_effect','Contraste directo entre métodos sobre los mismos resultados; no basta comparar valores p separados.'),
        table(t['method_differences'].query('season=="all" and metric=="extreme_gap"'),['league','operator','comparison','estimate','ci_low','ci_high','p_holm']),
        '<h2 id="comparisons">Ligas, casas y temporadas</h2>',img('operator_rps','Pinnacle − Bet365: diferencias de RPS apareadas, con intervalos por bloques.'),img('league_comparison','Comparación de pendiente y habilidad relativa a la referencia de cada liga.'),img('bias_seasons','Cada temporada se mantiene como estrato; los tamaños pequeños en extremos limitan precisión.'),
        '<h3>Calibración y precisión por temporada</h3><p>El ECE anual es descriptivo y sensible al ruido de muestras menores. Una subida aislada no demuestra empeoramiento del pronóstico.</p>',
        table(t['scores'].query('season!="all" and method=="power"'),['league','season','operator','macro_ece_pp','rps','rpss']),
        '<h3>Contrastes temporales</h3>',table(t['season_differences'].query('method=="power"'),['league','operator','metric','comparison','estimate','ci_low','ci_high','p_holm']),
        (covid_section(ct,img,table) if ct is not None else ''),
        '<h2>Sensibilidad y diagnósticos</h2>',img('bins_sensitivity','La estimación ECE cambia con el número de grupos; esto no implica necesariamente cambios del mercado.'),
        '<p>También se repite el remuestreo con bloques de 1, 10 y 40 partidos, y el contraste de extremos con límites 15/65 y pertenencia específica de cada método. Las tablas incluyen regresión logística con covarianza por partido, Hosmer–Lemeshow y Spiegelhalter como diagnósticos, y descomposición de Murphy con residuo explícito por agrupamiento.</p>',
        '<h2 id="limits">Método y límites de interpretación</h2><section><ul>',
        f'<li>Remuestreo circular de bloques de {cfg["block_size"]} partidos consecutivos, independiente dentro de cada liga–temporada. Se preservan resultado, métodos y casas de cada partido. No equivale a jornadas exactas y no captura toda la dependencia de equipos que reaparecen a largo plazo.</li>',
        '<li>Los IC son percentiles del bootstrap. Los valores p son aproximaciones de colas de la distribución bootstrap centrada, con corrección de Monte Carlo; no son pruebas exactas ni datos generados bajo una hipótesis nula. Se aplica Holm por familias declaradas en la metodología. Los IC mostrados son marginales, no simultáneos.</li>',
        '<li>Las curvas mantienen fijos sus grupos originales en el remuestreo: incertidumbre condicional al esquema de agrupamiento. Wilson se exporta como referencia binomial; no corrige dependencia temporal.</li>',
        '<li>Las diferencias de ECE entre muestras también dependen de su tamaño y agrupamiento. El análisis compara pendientes y habilidad relativa formalmente; ECE se usa descriptivamente.</li>',
        '<li>Hosmer–Lemeshow, Spiegelhalter y la regresión logística son diagnósticos con supuestos más restrictivos. La regresión respeta el partido, pero no corrige dependencia temporal. No rechazar no demuestra calibración perfecta.</li>',
        '<li>Los grupos de favoritos pueden ser pequeños por temporada; intervalos amplios impiden descartar desviaciones relevantes. Tres temporadas no identifican tendencias históricas de largo plazo.</li>',
        '<li>Los archivos proceden de copias locales suministradas: fechas de descarga desconocidas. Hay huellas y URLs de origen esperado, pero no cotejo remoto. Ningún método identifica el reparto verdadero del margen.</li>',
        '<li>Evaluación retrospectiva de probabilidades. No se seleccionan apuestas ni se estima rentabilidad.</li></ul></section>',
        '<h2 id="files">Archivos de resultados</h2><p>El HTML contiene las figuras incorporadas y puede abrirse sin conexión. Las tablas y figuras independientes se conservan en el proyecto.</p><ul>',
        '<li><a href="../data/processed/analytic.csv">Base analítica</a> · <a href="../data/processed/matches.csv">Partidos</a> · <a href="../data/processed/covid_matches.csv">Base de público local y pandemia</a> · <a href="findings.md">Hallazgos en texto</a> · <a href="executive_summary.md">Resumen ejecutivo</a></li>']
    for name in ['coverage','exclusions']+list(t): parts.append(f'<li><a href="tables/{name}.csv">{html.escape(name)}.csv</a></li>')
    parts.append('</ul><p>Fuente: <a href="https://www.football-data.co.uk/">Football-Data</a>. Métodos: <a href="https://doi.org/10.11648/j.ajss.20170506.12">Clarke, Kovalchik e Ingram (2017)</a>. Detalles de fórmulas, familias de contrastes y procedencia en la documentación del repositorio.</p></main></html>')
    (root/'reports/index.html').write_text('\n'.join(parts),encoding='utf-8')
