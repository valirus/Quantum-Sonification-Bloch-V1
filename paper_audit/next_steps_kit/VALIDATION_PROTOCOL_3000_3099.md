# Protocolo propuesto para congelar antes de generar la validación

Fecha de preparación: 2026-10-04. Esta es una especificación prospectiva propuesta; no constituye por sí misma un registro público ni convierte los análisis anteriores en confirmatorios.

## Cohortes y alcance

- Desarrollo: semillas 1000–1099, ya inspeccionadas; análisis exploratorio.
- Validación propuesta: semillas 3000–3099, sin solapamiento, generadas después de congelar esta especificación.
- Misma familia de circuitos, 15 qubits, 10 capas y observación inicial 0, raíz 7, tolerancia de aristas 1e-10.
- Motor de referencia: tag `paper-pipeline-v1.0.0`, commit `bb31388202666a6ab1a365b912b4e2992429a7c6`; verificar que el checkout corresponde a esa versión. SHA256 de `src/sonification.py`: `23e747dfe61ff50cc149f7395588fca86488e77f3a18e11fdfa8f87590630ad5`.
- Conservar configuración acústica y extractor STFT. Registrar las versiones realmente instaladas. El lock del repositorio es la referencia de instalación; los metadatos de cada ejecución documentan el entorno efectivo.
- La unidad independiente es la semilla. Las 11 capas y los 2 modos son medidas repetidas.

## Resultado primario propuesto

RQ5, modo DFS, objetivo `duration_sec`. Comparar M2 con M1 mediante la diferencia de error cuadrático medio de validación: MSE(M1) − MSE(M2), positiva cuando M2 mejora.

- M0: intercepto y profundidad categórica.
- M1: M0 + `mean_bloch_radius`, `mean_linear_entropy`, `mean_theta_radius_weighted`, `phi_circular_variance_radius_weighted`.
- M2: M1 + `log1p(total_mutual_information)` y `edge_weight_entropy`.
- Ajuste OLS y escalado solo con las 100 semillas de desarrollo. No seleccionar predictores ni modelos usando la cohorte nueva.
- Evaluación única sobre las 100 semillas nuevas. Reportar MSE, R², RMSE en segundos, reducción relativa del MSE y diferencia media de errores por semilla.
- IC del 95 % por 5000 remuestreos de semillas de validación completas, manteniendo los modelos entrenados fijos; RNG 20261004. El IC expresa incertidumbre de la muestra de prueba condicionada al entrenamiento, no incertidumbre de volver a entrenar todo el procedimiento.
- Evidencia de mejora bajo esta especificación: diferencia positiva e IC inferior mayor que cero. Reportar también la magnitud absoluta; no asociarla a discriminación humana.
- Si no mejora, informar que la ganancia exploratoria no se replicó. No ampliar el lote para perseguir el cruce de un umbral estadístico.
- Aunque mejore, la duración DFS codifica directamente pesos del bosque. No interpretar el resultado como recuperación de la topología completa.

## Resultados secundarios

Aplicar las mismas definiciones corregidas de RQ1–RQ4 a las semillas nuevas con `replicate_rq1_to_rq4.py`. RQ1: cuatro asociaciones y FDR en esa familia; RQ3: veinte asociaciones capa/modo y FDR en esa familia; RQ4: seis contrastes y FDR en esa familia. RQ2: curvas descriptivas e intervalos puntuales. Las otras tres combinaciones modo/objetivo de RQ5 son secundarias; sus intervalos no reciben automáticamente una interpretación confirmatoria conjunta.

No añadir pruebas ni seleccionar capas por los resultados nuevos. Los análisis por capas 4–10 y sin capa 0 se mantienen como sensibilidad exploratoria, separada del resultado primario.

## Control del bosque, si se incorpora

Seleccionar antes de ejecutar: todas las semillas de la cohorte elegida, capas 2, 3, 6 y 10, raíz y configuración fijas; 20 réplicas por control, después de un piloto de rendimiento separado. El piloto no decide qué resultados se publican.

Condiciones: original; permutación de pesos sobre las mismas aristas; árbol aleatorio etiquetado por componente, con los mismos nodos de cada componente y el mismo multiconjunto de pesos. Bloch permanece fijo. El segundo control cambia conexiones y ubicación de pesos; el primero ayuda a distinguir los cambios de ubicación sin cambiar conexiones. No se conservan necesariamente los grados por nodo ni las distancias entre nodos.

Observación principal del control: duración BFS y número de fronteras. Control mecánico negativo: duración DFS debe mantenerse. Otros descriptores son exploratorios y se reportan juntos. Promediar réplicas por estado y capas seleccionadas por semilla antes del bootstrap. Conservar componentes degeneradas e informar la fracción de grafos realmente modificados.

Los grafos modificados son entradas sintéticas del sintetizador. No afirmar que representan nuevos estados cuánticos físicamente realizables ni que el control demuestra reconstrucción de la matriz de información mutua.

## Calidad y cierre

Guardar manifest de ejecución, metadata, WAV, matrices MI, vectores de estado, descriptores Bloch, métricas y circuitos. No sobrescribir la cohorte antigua. Excluir únicamente ejecuciones fallidas por criterios técnicos documentados y registrar cualquier sustitución antes del análisis.

Publicar desarrollo y validación identificados por separado. Una tabla conjunta descriptiva puede añadirse después, sin sustituir la evaluación independiente. Si se modifica el paneo u otra regla del motor, crear una versión y un dataset distintos.

## Adenda para la nueva validación

- Cohorte de validación: 3000–3099. El rango 2000–2099 ya fue
  examinado anteriormente en esta conversación.
- El resultado primario RQ5, sus modelos, entrenamiento, bootstrap
  y criterio de éxito permanecen como se definieron arriba.
- Las distancias se replicarán con structure_distances.py:
  Bloch/audio y MI/audio, en BFS y DFS; cuatro pruebas,
  5000 permutaciones, BH en esa familia y BY como sensibilidad.
- Las características y reglas de elegibilidad serán las del código
  congelado. El escalado acústico se fijará con el dataset de
  desarrollo 1000–1099 mediante --scale-from.
- Los controles del bosque se replicarán en las 100 semillas nuevas:
  capas 2,3,6,10; veinte réplicas por condición; raíz y configuración
  fijas. Duración BFS y fronteras serán resultados secundarios
  descriptivos; duración DFS será el control mecánico de invariancia.
- Se reportarán ambos controles y todas las características.
  Sus intervalos puntuales no constituyen una familia confirmatoria.
- El piloto de rendimiento usará 0–2 y quedará fuera de la validación.
- No se cambiarán modelos, características, capas ni tamaño del lote
  después de inspeccionar los resultados de validación.

Preparación de esta versión, UTC: 2026-10-11T07:10:02.707489+00:00
