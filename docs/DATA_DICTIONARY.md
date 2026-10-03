# Diccionario de datos

La documentación de origen suministrada está en `football_data_notes_supplied.txt`, atribuida a Football-Data. Su fecha de versión no está documentada.

| Original | Significado | Uso |
|---|---|---|
| Div | División: E0 / SP1 | Estratificación y validación |
| Date | Fecha con día primero | Temporada y orden cronológico |
| HomeTeam / AwayTeam | Equipos local / visitante | Identificador y controles de integridad |
| FTHG / FTAG | Goles a tiempo completo | Validación del resultado |
| FTR | H local; D empate; A visitante | Resultado observado |
| B365CH / CD / CA | Cuotas de cierre Bet365 para H/D/A | Pronósticos originales |
| PSCH / CD / CA | Cuotas de cierre Pinnacle para H/D/A | Pronósticos originales |

Los nombres abreviados de la tabla anterior significan B365CH, B365CD, B365CA y PSCH, PSCD, PSCA. No mezclar las columnas `PH/PD/PA` de otras épocas sin adaptación explícita. Las columnas sin C son previas al cierre: no se asumen la primera apertura. Estadísticas del partido como tiros, tarjetas y córners no se utilizan como predictores.

## Base analítica

Una fila por partido × operador. `index` alinea las matrices internas; no sustituye `match_id`. `league`, `season`, `date`, equipos, goles y `FTR` identifican el encuentro. `source_file` y `source_row` conservan trazabilidad (línea de cabecera=1).

- `odds_H/D/A`: cuota decimal original.
- `raw_H/D/A`: inverso de cuota; suma superior a uno en la muestra elegible.
- `margin_pp`: 100 × (suma de inversos − 1).
- `proportional_*`, `power_*`, `additive_*`, `shin_*`: probabilidades ajustadas; cada tripleta suma uno.
- `y_H/D/A`: indicadores de resultado; exactamente uno vale 1.
- `power_k`, `shin_z`: parámetros numéricos de remoción del margen, no modelos estimados con resultados.

## Tablas de resultados

`season=all` agrega las tres temporadas dentro de una liga. `estimate` depende de `metric` o tabla; sus unidades se especifican en metodología. `ci_low/high` son percentiles marginales bootstrap. `p_boot` es la aproximación bilateral centrada; `p_holm` corrige dentro de la familia declarada. `bootstrap_valid` informa cuántas réplicas tienen denominador utilizable.

`bias`: pendiente pp de error/10 pp de probabilidad. `extremes`: favorito menos improbable, en pp, con grupos fijos. `method_differences`: método menos proporcional. `operator_differences`: Pinnacle menos Bet365. `league_differences`: LaLiga menos Premier. `season_differences`: segunda temporada indicada menos primera. `rps_skill` es diferencia de RPSS, no de RPS bruto. `outcome_calibration`: brecha media observada−pronosticada en pp, por resultado, junto a ECE descriptivo.

Los archivos CSV están codificados UTF-8. Ningún valor ausente debe interpretarse como cero. Las referencias de puntuación se repiten por operador para facilitar lectura, pero son la misma referencia en los partidos comunes.

## Público local y pandemia (`data/processed/covid_matches.csv`)

Una fila por partido de E0/SP1 2017/18–2024/25. Usa además `HS/AS` (remates), `HF/AF` (faltas) y `HY/AY` (amarillas) de Football-Data, solo como medidas de resultado de esta pregunta, nunca como predictores.

- `period`: `pre`, `closed`, `limited`, `partial`, `post` (definiciones en METHODOLOGY.md).
- `points_diff`, `goal_diff`, `shots_diff`: local − visitante. `cards_diff`, `fouls_diff`: visitante − local.
- `qH_<método>_<casa>`: probabilidad ajustada de victoria local; `implied_<casa>` usa potencia. `gap_<casa>` = victoria local − `implied_<casa>`.
- Tablas `covid_*`: `estimate` en la unidad de la columna `unit` (% y pp ya multiplicados por 100).
- `covid_coverage.csv`: partidos con cuota de cierre válida por liga, temporada y casa. `covid_strength_adjusted.csv`: ventaja de local por periodo del modelo con fuerza equipo–temporada (`HA_*`), su cambio y la diferencia entre ligas.
- `n_a`, `n_b` en `covid_contrasts.csv`: partidos con dato válido en cada grupo del contraste.
