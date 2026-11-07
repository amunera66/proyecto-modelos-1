# Correcciones de la Fase 1

Este documento responde a la retroalimentación del profesor sobre la Fase 1. Cada apartado indica qué se pidió, qué se hizo, el resultado y dónde está la evidencia.

- **Notebook:** `fase-2/notebooks/analisis_correcciones.ipynb`.
- **Decisiones:** `fase-2/docs/decisiones.md`.

Las métricas de este documento son del análisis del Paso 2, con `early_stopping="auto"`. Las métricas finales del modelo están en la sección "Paso 3 – Entrenamiento" de `decisiones.md`.

| Corrección | Resultado | Estado |
|---|---|---|
| C1. EDA | Predictoras sin redundancia; mayor correlación de 0,323 | Resuelta |
| C2. Sagas compartidas | De 469 colecciones compartidas a 0 | Resuelta |
| C3. `es_franquicia` | Reemplazada por `es_secuela` | Resuelta |
| C4. Estabilidad entre CV y prueba | Redacción moderada, con evidencia de 10 semillas | Resuelta |
| C5. Filtros y horizonte | Filtros explícitos; fecha de corte no verificada | Resuelta con una limitación |
| C6. Revisión de PR | Sin revisiones registradas en los PR #1 a #5 | Pendiente |
| C7. Contrato y metadatos | Contrato y esquema definidos; faltan las pruebas formales | En curso |

## C1. EDA

**Qué pidió el profesor.** Completar el EDA: correlaciones entre las predictoras numéricas finales, su relación con `vote_average`, el análisis por género e idioma y las posibles redundancias.

**Qué se hizo.** Con el conjunto de entrenamiento se calcularon correlaciones de Pearson y Spearman, gráficos hexbin contra el objetivo, boxplots y tablas por género e idioma, y comparaciones según `es_franquicia` y según si falta `budget`. Las categorías raras se agruparon con la lista que aprendió el `OneHotEncoder`.

**Resultado.**

- **Redundancia:** no hay. La mayor correlación es 0,323 (Spearman, `budget` y `runtime`).
- **Relación con `vote_average` (Spearman):** `runtime` 0,229, `release_year` −0,163 y `budget` −0,046.
- **Categorías:** `Documentary` tiene la mayor mediana por género (7,1) y `Horror` la menor (5,5). `en` tiene la mediana más baja por idioma (6,1); los demás grupos tienen 6,5 o más.
- **`budget` nulo:** faltar casi no cambia la calificación promedio (d de Cohen de −0,025), pero la diferencia varía con la época. Hasta 1999, las películas con presupuesto reportado están mejor calificadas (+0,17 y +0,13); desde 2000 casi no hay diferencia.

Estas cifras son asociaciones, no efectos causales. La importancia por permutación de la Fase 1 no reemplaza este análisis, porque mide de qué depende el modelo ya ajustado.

**Evidencia.** Sección 1 del notebook y apartado "C1" de `decisiones.md`.

## C2. Sagas compartidas

**Qué pidió el profesor.** Hay 469 colecciones que aparecen a la vez en entrenamiento y en prueba. Pidió justificar si el modelo generaliza a sagas conocidas o nuevas, y evaluar por grupos.

**Qué se hizo.** Se creó `src/splitting.py`. El grupo es la colección, o la propia película si no tiene colección. La partición usa `GroupShuffleSplit` y la CV, `GroupKFold(5)`. El equipo adoptó esta estrategia porque una película nueva suele ser de una saga no vista por el modelo.

**Resultado.** Se confirmaron las 469 colecciones, con 604 películas de prueba en una colección vista. Por grupos quedan 0.

Con `es_franquicia`, para comparar solo el efecto de la partición:

| Partición | Filas train / prueba | RMSE en CV | RMSE en prueba | R² en prueba |
|---|---|---|---|---|
| Aleatoria | 17.324 / 4.332 | 0,7989 | 0,7813 | 0,3745 |
| Por grupos | 17.335 / 4.321 | 0,7981 | 0,8028 | 0,3457 |

En 10 semillas, partir por grupos cuesta 0,0071 de RMSE en promedio (desviación de 0,0068).

**Evidencia.** Secciones 2 y 5 del notebook, `src/splitting.py` y la decisión (a) de `decisiones.md`.

## C3. `es_franquicia` → `es_secuela`

**Qué pidió el profesor.** Verificar que `es_franquicia` era información disponible al estreno, porque la pertenencia a una colección pudo definirse después.

**Qué se hizo.** Se contó cuántas películas son la primera de su colección y se creó `es_secuela`: vale 1 si en su colección existe otra película con `release_date` estrictamente anterior. Se calcula sobre el dataset limpio, antes de los filtros. El equipo reemplazó `es_franquicia` por `es_secuela`, y el contrato sigue teniendo 6 predictoras.

**Resultado.**

- 1.704 de las 4.487 películas con colección (38,0 %) son la primera de su saga. Para ellas, `es_franquicia` podría no conocerse al estreno.
- 390 de las 1.695 colecciones (23,0 %) tienen una sola película en el dataset.
- `es_franquicia` mezcla dos grupos opuestos: las primeras películas tienen media 6,318, las secuelas 5,830 y las películas sin colección 6,212.

Con partición por grupos:

| Sexta predictora | RMSE en CV | RMSE en prueba | R² en prueba |
|---|---|---|---|
| `es_franquicia` | 0,7981 | 0,8028 | 0,3457 |
| `es_secuela` | 0,7949 | 0,8007 | 0,3491 |

`es_secuela` gana en las 10 semillas probadas, por 0,0029 en promedio (desviación de 0,0015). La mejora es pequeña y no fue el motivo principal del cambio: lo fue que la variable se conoce al estreno.

**Limitación.** `es_secuela` vale 0 si la película anterior no está en el dataset. Puede afectar a parte de las 207 películas de la población que son las únicas de su colección.

**Evidencia.** Secciones 3 y 5 del notebook, `add_sequel_feature` en `src/features.py` y la decisión (b) de `decisiones.md`.

## C4. Estabilidad entre CV y prueba

**Qué pidió el profesor.** Moderar la afirmación de que la cercanía entre CV y prueba descarta el efecto de la partición.

**Qué se hizo.** Se repitió la evaluación con 10 semillas, cambiando la partición y la semilla del modelo. Esta comparación no se usó para ajustar nada.

**Resultado.** La estabilidad entre CV y prueba es evidencia favorable, no una garantía.

- La prueba de la Fase 1 (RMSE 0,7813) quedó por debajo de la media de la partición aleatoria en 10 semillas (0,7921, desviación de 0,0079). Es decir, esa partición resultó favorable.
- La dirección de la diferencia cambia con la partición: con la aleatoria, prueba quedó mejor que CV (0,7813 frente a 0,7989); por grupos, peor (0,8028 frente a 0,7981).

Por eso, las métricas se deben leer con su variación y no como un valor exacto.

**Evidencia.** Secciones 2 y 5 del notebook.

## C5. Filtros explícitos y horizonte del objetivo

**Qué pidió el profesor.** Mantener explícito el filtro de más de 10 votos y definir el horizonte de la calificación que se predice.

**Qué se hizo.** Los filtros quedaron como reglas fijas en `src/config.py` y se registran en `metadata.json`. Además, se buscó la fecha de corte en la documentación del dataset y en `release_date`.

**Resultado.**

| Paso | Quita | Quedan |
|---|---|---|
| CSV crudo | — | 45.466 |
| Limpieza | 36 | 45.430 |
| `status == "Released"` | 445 | 44.985 |
| `vote_count > 10` | 23.329 | 21.656 |

- **Definición del objetivo:** el modelo predice `vote_average` acumulado hasta la fecha de corte del dataset, solo para películas estrenadas con más de 10 votos.
- **Fecha de corte: no verificada.** La descripción del dataset habla de películas estrenadas hasta julio de 2017, pero se consultó en réplicas ([hyper.ai](https://hyper.ai/en/datasets/34654) y [Baselight](https://baselight.app/u/kaggle/dataset/rounakbanik_the_movies_dataset)), no en Kaggle, y no dice cuándo se descargaron los votos.
- **Fechas en los datos:** el máximo de `release_date` en la población es 2017-10-27, y 12 películas son posteriores a julio de 2017. Las 6 fechas posteriores a 2017 corresponden a películas no estrenadas, que quita el filtro de `status`.
- **Implicación:** el horizonte no es igual para todas las películas. Una de 1995 acumuló votos durante más de 20 años y una de 2017, semanas o meses.

**Evidencia.** Sección 4 del notebook, `src/config.py` y `src/data.py`.

## Notas sobre C6 y C7

**C6. Revisión de PR.** El profesor pidió que otro integrante revise formalmente cada PR antes del merge. Los PR #1 a #5 no tienen ninguna revisión registrada en GitHub, así que esta corrección sigue pendiente. El PR de este paso indica a Juan Esteban González Duque como revisor; la aprobación debe quedar registrada en GitHub antes del merge.

**C7. Contrato y metadatos.** El profesor pidió conservar los metadatos, el contrato de 6 predictoras y las pruebas de carga con datos nuevos.

- **Contrato:** sigue teniendo 6 predictoras, con `es_secuela` en lugar de `es_franquicia`. Está en `src/config.py`.
- **Metadatos:** `metadata.json` guarda el contrato, los datos, la partición, los filtros y el entorno. El esquema está en `decisiones.md`.
- **Pruebas de carga:** se comprobó de forma manual que los modelos guardados con `es_franquicia` se cargan y predicen igual con los nuevos defaults. Las pruebas formales con pytest corresponden al Paso 5.
