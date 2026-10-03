# Metodología y decisiones de análisis

## Diseño

Estudio observacional retrospectivo. Liga, operador, temporada y método definen estratos de análisis. La unidad deportiva y de remuestreo es el partido, con sus tres resultados y las dos casas juntos. No se mezclan ligas para la inferencia principal. Las temporadas aportan igual número de partidos a la estimación agregada de cada liga.

## Validación

Archivos en `data/raw/<DIV>_<AAAA-AA>.csv`. Fechas día/mes/año explícitas, aceptando años de dos o cuatro cifras. Se comprueba liga, temporada julio–junio, goles enteros no negativos y resultado coherente; nombres presentes y diferentes; duplicados de pareja dirigida por temporada. Los duplicados se ponen completos en cuarentena. No se imputan cuotas; tripletas finitas >1. Margen <=0 o >20 pp es alerta operativa y exclusión provisional. Si falla la integridad completa de temporada o la cobertura común de 90 %, el flujo se detiene para revisión. La entrega actual pasó todos los controles sin exclusiones.

El umbral de margen es una decisión del protocolo, no una ley universal. No se presupone que todo mercado posible tenga overround positivo. El tratamiento de esos casos requeriría una decisión explícita si aparecen.

## Cuotas y remoción del margen

Para cuota decimal `o_i`, `p_i=1/o_i`, `S=sum(p_i)` y `m=100*(S-1)` pp. La calibración usa probabilidades ajustadas `q`, nunca `p` brutas.

- **Proporcional:** `q_i=p_i/S`.
- **Potencia:** resolver `sum(p_i^k)=1`; `q_i=p_i^k`. La raíz se acota de forma adaptativa. No equivale al método odds-ratio.
- **Aditivo:** `q_i=p_i-(S-1)/3`. Se detiene si hay valores no positivos: no se oculta una corrección por truncamiento.
- **Shin:** resolver `sum(q_i(z))=1`, con `q_i(z)=(sqrt(z²+4(1-z)p_i²/S)-z)/(2(1-z))`. El código utiliza su forma racionalizada estable y busca la raíz en casi todo [0,1), sin fallback silencioso a cero.

Cada método expresa un supuesto; ninguno identifica el verdadero reparto del margen. Se verifican sumas unitarias, positividad y finitud.

## Calibración

Por liga, casa y método se calculan curvas por resultado H/D/A con 10 grupos de igual frecuencia. Los empates en cuantiles pueden reducir el número efectivo de grupos, que se refleja en las tablas. Se repite con 5,15,20 y con 20 grupos de igual ancho.

Cada punto muestra frecuencia, probabilidad media y brecha en pp. Los intervalos de bloques son el análisis de incertidumbre temporal, condicional a los grupos definidos en los datos originales. Wilson se exporta como referencia binomial; no se presenta como corrección de dependencia.

ECE se calcula para cada resultado como promedio ponderado de desviaciones absolutas por grupo. Se promedian los tres ECE para obtener una medida descriptiva macro. Este ECE no es directamente el error individual de cada partido ni el ECE agrupado de H/D/A del reporte antecedente. Depende de tamaño de muestra y agrupamiento; no se comparan sus valores p entre muestras ni se afirma superioridad solo por su orden.

## Sesgo favorito–longshot

Dos medidas complementarias:

1. **Pendiente del error:** regresión lineal de `100*(y-q)` sobre `10*q`, con intercepto. Unidad: pp del error por aumento de 10 pp en probabilidad. Pendiente positiva compatible con sobrevaloración de improbables e infravaloración de favoritos; se examina junto con curvas por resultado.
2. **Contraste de extremos:** media del error en probabilidades >60 % menos la media del error en probabilidades <20 %. Para contrastar métodos se define la pertenencia una sola vez con el método proporcional de cada casa, y se conserva. No es una comparación apareada entre personas ni una clasificación fija entre casas: es fija entre métodos de una misma casa.

Se compara directamente cada método con proporcional usando las mismas réplicas. El patrón puede cambiar sin que el efecto entre métodos resulte concluyente, y significancia con un método pero no otro no demuestra una diferencia entre métodos.

**Límite esencial:** con extremos fijos, la diferencia entre métodos cancela algebraicamente los resultados `y`. Por eso es un efecto mecánico sobre el ajuste de probabilidades; sus intervalos reflejan la distribución de ajustes entre partidos. No constituye una prueba independiente del sesgo verdadero ni identifica qué método representa mejor al operador. Las pendientes, brechas y curvas incorporan resultados observados y permiten evaluar calibración bajo cada supuesto.

Sensibilidad: extremos fijos 15/65 % y pertenencia propia de cada método 20/60 %. Se exportan tamaños de grupos y réplicas válidas; con pocos extremos la incertidumbre aumenta.

## Puntuaciones y referencias

- Brier multiclase: `sum((q_i-y_i)^2)`, rango 0–2.
- RPS: promedio de errores cuadrados acumulados en los dos primeros cortes H–D–A. Orden espacial del resultado, no jerarquía de probabilidad.
- Pérdida logarítmica: `-log(q_del_resultado_observado)`.
- Referencia uniforme 1/3.
- Referencia histórica: frecuencias de H/D/A en las otras dos temporadas de la misma liga. Se dejan fuera todos los partidos de la temporada evaluada. Puede usar temporadas posteriores, por lo que es una comparación retrospectiva y no una simulación prospectiva.
- RPSS: `1-RPS/RPS_referencia`. Cada liga tiene su propia referencia. El bootstrap condiciona a esas probabilidades de referencia ya calculadas y no vuelve a estimarlas; la incertidumbre no incluye el aprendizaje de la referencia.

Menor puntuación representa mayor calidad global; no demuestra mejor calibración. Entre ligas se examina habilidad relativa para considerar tasas base diferentes. La descomposición de Murphy agrupa probabilidades; el residuo de la identidad aproximada se exporta y no se oculta.

## Remuestreo e inferencia

2.000 réplicas; semilla 20261001. Bootstrap circular de bloques móviles de 20 partidos ordenados cronológicamente, independiente dentro de cada liga–temporada. Se extraen inicios de bloques con reemplazo y se trunca la muestra al tamaño original. Todas las métricas usan las mismas ponderaciones de partidos para preservar las comparaciones entre operadores y métodos. Se repite con bloques de 1,10,40.

20 partidos representan aproximadamente dos jornadas de una liga de veinte clubes, pero no se reconstruyen jornadas oficiales y los aplazamientos afectan la interpretación. Los bloques no representan perfectamente la dependencia entre equipos a largo plazo. La sensibilidad al tamaño de bloque complementa, pero no elimina, esta limitación.

IC percentiles al 95 %. Valores p aproximados bilaterales: proporción de réplicas centradas cuya magnitud alcanza la estimación original, con corrección `(1+conteo)/(B+1)`. No son pruebas exactas ni un bootstrap generado bajo H0. La resolución Monte Carlo es 1/(B+1), y Holm puede multiplicar ese mínimo. IC son marginales; los valores p ajustados corresponden a familias y pueden no coincidir con la lectura de un IC aislado.

### Familias de Holm

Las agrupaciones se definen en el código, no según resultados:

| Tabla | Familia |
|---|---|
| bias / extremes | Cada valor de temporada por separado: 2 ligas × 2 casas × 4 métodos |
| method_differences | Temporada × métrica: 2 ligas × 2 casas × 3 métodos contra proporcional |
| operator_differences | Temporada × métrica; diferencias PS − B365 |
| league_differences | Temporada × métrica; diferencias SP1 − E0 |
| season_differences | Métrica; 2 ligas × 2 casas × 4 métodos × 2 cambios consecutivos |
| outcome_calibration | Temporada; 2 ligas × 2 casas × 4 métodos × 3 resultados |
| threshold_sensitivity | Definición de extremos; 2 ligas × 2 casas × 4 métodos |
| block_sensitivity | Tamaño de bloque; 2 ligas × 2 casas × 4 métodos |

El agregado de las tres temporadas es el análisis principal. Los estratos anuales son análisis de estabilidad. Las distintas familias no constituyen una corrección global de todos los resultados posibles; debe evitarse seleccionar hallazgos cruzando familias.

### Diagnósticos adicionales

Regresión de calibración `logit(P(y=1))=a+b*logit(q)`, con covarianza sandwich por partido al agrupar H/D/A. No incorpora dependencia entre partidos. Hosmer–Lemeshow usa número efectivo de grupos como grados de libertad para predicciones externas; Spiegelhalter evalúa una función del error. Son aproximaciones con independencia entre partidos y se exportan como diagnósticos con valores p sin ajuste: no se usan para proclamar hallazgos confirmatorios. La inferencia principal utiliza bloques.

## Análisis de público local (COVID-19)

**Pregunta.** ¿Se redujo la ventaja de local cuando se jugó sin público, por qué canales y lo incorporó el mercado?

**Muestra.** Temporadas completas 2017/18–2024/25 de E0 y SP1 (16 archivos, 6.080 partidos, 380 por liga–temporada). 2022/23–2024/25 son los mismos archivos del análisis principal; 2017/18–2021/22 están en `data/raw_covid/`. La temporada 2019/20 se valida hasta el 31/08/2020 porque terminó en julio. Todas las temporadas son anteriores al corte de calidad de Pinnacle de julio de 2025.

**Cobertura de cuotas.** Football-Data no publica cuotas de cierre de Bet365 antes de 2019/20; Pinnacle de cierre está completa salvo un partido de LaLiga 2017/18. Las medidas deportivas usan todas las temporadas; cada medida de mercado usa los partidos con cuota de cierre válida de esa casa (no se imputan cuotas ni se sustituyen por cuotas previas al cierre). `covid_coverage.csv` documenta la cobertura y los tamaños efectivos aparecen en `n_a`/`n_b`. Una sensibilidad repite las medidas deportivas solo desde 2019/20.

**Periodos** (fechas en `config.json`):

| Periodo | Premier League | LaLiga |
|---|---|---|
| Con público (antes) | hasta 09/03/2020 | hasta 09/03/2020 |
| Puerta cerrada | reanudación (17/06/2020) a fin de 2020/21 | desde 10/03/2020 (Eibar–Real Sociedad sin público) a fin de 2020/21 |
| Aforo mínimo (excluido del contraste principal) | 02–26/12/2020 y 18–23/05/2021 | 16–23/05/2021 |
| Aforo parcial (excluido) | — | 01/08–30/09/2021 |
| Con público (después) | desde 2021/22 | desde 01/10/2021 |

Las ventanas de aforo mínimo son aproximaciones de las reaperturas parciales regionales; su inclusión se evalúa como sensibilidad.

**Medidas por partido.** Victoria local (0/1); puntos del local − puntos del visitante (3/1/0), que vale cero sin ventaja de local; goles local − visitante; remates local − visitante (canal de rendimiento); amarillas y faltas del visitante − del local (canal arbitral); probabilidad implícita de victoria local con el método de potencia (B365 y PS); brecha victoria local observada − implícita.

**Contrastes.** Principal: puerta cerrada − con público (antes y después agrupados). Secundarios: cerrada − antes, cerrada − después, después − antes, y cerrada incluyendo aforo mínimo. Diferencia entre ligas del efecto principal (Premier − LaLiga). Fracción de la ventaja en puntos que desapareció: 1 − cerrada/con público.

**Ajuste por fuerza de equipos.** Robustez para que la ventaja de cada periodo no dependa de qué equipos jugaron en casa en cada tramo (2019/20 se parte en dos). Por liga, mínimos cuadrados con `resultado = HA_periodo + fuerza(local, temporada) − fuerza(visitante, temporada)`, para puntos y goles. Las fuerzas se identifican con una referencia por temporada; HA no depende de esa elección. Se reestima en cada réplica con los mismos pesos de bloques. Holm sobre los cuatro cambios y las dos diferencias entre ligas.

**Inferencia.** Igual que el análisis principal: bootstrap circular de bloques de 20 partidos cronológicos dentro de cada liga–temporada, 2.000 réplicas, IC percentil y p bootstrap centrado. Holm dentro de cada familia liga × contraste (10 medidas) y en la familia de diferencias entre ligas. Sensibilidad con bloques de 1, 10 y 40 y con el método proporcional.

**Límites.** Experimento natural, no ensayo aleatorio: la pandemia también alteró calendario, descansos y viajes. Los ascensos cambian la composición de equipos entre temporadas. El periodo "antes" cubre 2017/18 a marzo de 2020; para Bet365, solo 2019/20 hasta marzo. Tarjetas y remates indican canales compatibles, no los separan causalmente.

## Reproducibilidad y alcance

Las fuentes locales se identifican por SHA-256. El reporte se genera a partir de las tablas de la misma ejecución. Las pruebas verifican ecuaciones mediante cálculos independientes, escalas de puntuación, identidad de Murphy, conservación de estratos, pendiente con filas explícitamente repetidas y muestra común.

No se interpretan diferencias como efectos causales de liga, margen o método. Ausencia de evidencia no es evidencia de equivalencia. Calibración histórica no identifica oportunidades rentables.
