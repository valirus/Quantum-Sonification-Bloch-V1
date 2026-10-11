# Quantum sonification: manuscrito de cierre / closeout manuscript

Este paquete completa el contenido científico del manuscrito usando el motor V1 intacto y la validación 3000–3099. No cambia el código de sonificación. La versión española es para revisión del equipo; la inglesa es la base editorial. Ambas contienen la misma evidencia.

## Overleaf

1. Importe el ZIP como proyecto nuevo.
2. En **Main document**, elija `manuscript_en.tex` o `manuscript_es.tex`.
3. Use **pdfLaTeX**. Los archivos oficiales `sn-jnl.cls` y `sn-basic.bst` están incluidos sin modificación.
4. Para el suplemento elija `supplement_en.tex` o `supplement_es.tex`.

Los PDF compilados están incluidos. Las seis figuras son vectoriales y tienen versiones lingüísticas separadas. No se requieren datos, Python, una conexión al repositorio ni el motor para compilar los textos. `reproducibility/input_evidence.zip` es evidencia de análisis y no se descomprime para compilar en Overleaf.

Localmente, con TeX Live y latexmk:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript_en.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript_es.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error supplement_en.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error supplement_es.tex
```

## Qué queda cerrado

- Dos cohortes principales separadas: 1000–1099 desarrollo y 3000–3099 validación. Son 200 semillas, 2.200 instantáneas y 4.400 salidas primarias. Las 32.800 síntesis de controles no son estados cuánticos independientes adicionales.
- RQ1–RQ5, con resultado primario único DFS/duración, observaciones repetidas y familias de corrección explícitas.
- Mejora primaria: 82,01 % de reducción de MSE; RMSE 46,65 → 19,78 ms. Es error de predicción, no cambio de duración ni discriminación humana.
- Controles: DFS mantiene exactamente duración en 16.000 comparaciones. BFS depende de organización de fronteras y ubicación de pesos.
- Distancias: Bloch replica asociaciones débiles; información mutua/DFS no replica el resultado exploratorio.
- Certificado físico: una familia continua de estados tiene audio final idéntico por modo y entropía central entre 0 y 7 bits. La prueba está completa y el código/certificados la acompañan. No se reclama primera demostración general del fenómeno de marginales.
- Limitación de V1: el paneo tiene una discontinuidad azimutal. Se documenta; no se modifica silenciosamente.

La evidencia computacional permite cerrar este alcance sin generar otro lote ni mejorar el prototipo para perseguir significación.

## Lo que debe completar el equipo antes de enviar

1. **Interfaz real:** aportar captura(s) y versión del código de interfaz; documentar controles disponibles, correspondencia visual/audio, sincronización si existe y una tarea de uso. El artículo actualmente describe el motor y sus implicaciones de diseño. No afirma haber evaluado una interfaz no suministrada. No sustituya Fig. 1 por una interfaz ficticia.
2. **Autoría:** nombres, afiliaciones, orden, correspondencia y contribuciones. No se inventaron datos personales.
3. **Declaraciones:** financiación, conflictos, aprobación final y texto de asistencia de IA. Se dejaron explícitamente pendientes las declaraciones que sólo los autores pueden conocer.
4. **Disponibilidad:** publicar un depósito permanente y versionado del dataset y del código de análisis congelado; sustituir el texto provisional de disponibilidad por enlaces verificables. Los CSV del paquete no sustituyen los WAV, vectores de estado y QPY originales retenidos en WSL.
5. **Revisión humana:** revisar fórmulas, fuentes, afirmaciones y traducción; aprobar el manuscrito completo. Esta entrega no equivale a aceptación editorial ni a revisión por pares.

El formato es Springer Nature para **Journal on Multimodal User Interfaces**. El nombre no es “Journal on Multimodal User Experience”. La interfaz documentada será relevante para ese encaje. Para **IEEE Transactions on Quantum Engineering**, el argumento de ingeniería y límites de representación puede conservarse, pero se debe migrar a su plantilla oficial. No se necesita hacer ambos cambios editoriales a la vez ni ampliar la investigación física.

## Reproducción del análisis

Desde la carpeta descomprimida del paquete, usando el entorno del proyecto con NumPy, pandas y SciPy:

```bash
bash reproducibility/reproduce.sh
```

El script extrae la evidencia en un destino nuevo; reconstruye todos los modelos primarios, asociaciones y bootstrap de RQ1, 264 bandas de RQ2, las 20 permutaciones de RQ3 (100.000 cada una), contrastes RQ4, distancias y controles; verifica hashes, identidades temporales y la familia física. Escribe sólo carpetas nuevas `reproduction_results/` y `reproducibility/reproduction_inputs/`. No llama a la generación del dataset ni modifica el motor. Si ya existen entradas de reproducción, detiene la ejecución para conservar resultados; use otra copia del paquete para repetir.

Para repetir además las comprobaciones de audio de la familia física con el código congelado y las dependencias Qiskit/NetworkX del proyecto:

```bash
OPENBLAS_NUM_THREADS=1 python reproducibility/verify_physical_family.py \
  --render --output-dir reproduction_results/physical_family_render
```

La comprobación numérica sin `--render` fue ejecutada en esta auditoría. La igualdad de audio con el motor original procede también del certificado archivado, con hash del mismo motor; no se presenta la ejecución sin `--render` como una síntesis de audio.

`reproducibility/frozen_analysis/external_validation.py` es la copia de referencia archivada de la especificación OLS. Los scripts efectivamente suministrados en el cierre WSL están además dentro de `input_evidence.zip`. Las reconstrucciones independientes y sus recibos se distinguen del código original.

## Organización

- `manuscript_*.tex`, `.pdf`, `.bbl`: artículo completo.
- `supplement_*.tex`, `.pdf`: métodos adicionales, resultados secundarios y demostraciones.
- `figures/`: seis figuras por idioma; los PNG son copias de revisión.
- `data/`: las dos cohortes, predicciones y tablas completas.
- `reproducibility/`: protocolo, fuentes sin modificar, evidencia compacta original, certificados y verificaciones.
- `GUIA_LECTURA_ES.md`: lectura didáctica del aporte y de las diferencias entre cantidades.
- `CLAIMS_AND_EVIDENCE.csv`: afirmaciones, fuentes, alcance y límites.
- `EDITORIAL_CLOSEOUT.md`: cambios respecto del borrador y decisiones de cierre.
- `TEMPLATE_PROVENANCE.md`: procedencia de la plantilla.

## English handoff

Import this archive into Overleaf and select `manuscript_en.tex` with pdfLaTeX. The computational study is complete within the stated frozen scope. Before submission, document the actual visual interface, finalize author metadata and declarations, deposit the complete underlying runs with permanent links, and obtain human author approval. No additional seed cohort or engine modification is required by the demonstrated claims. This archive is a Springer-format manuscript package, not an IEEE-format submission.
