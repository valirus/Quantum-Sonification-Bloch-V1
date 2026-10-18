# Quantum Sonification · v3 con ejemplos verificados

Tu pantalla muestra dos proyectos diferentes. **PowerShell / VS Code** tiene qhub-site y la interfaz en `feat/sonification-ui-final`, con Vite en el puerto 8080. **WSL / Cursor** tiene el estudio en `paper/frozen-audit-phase2`. Esta actualización se aplica a qhub-site; no modifica los resultados del estudio.

Bell, GHZ y Grover ya están simulados. Se entregan sus nueve WAV reales, registros cuánticos y código reproducible. No necesitas generar nada para escucharlos en la web.

## Paso 1 · detener la web

En la terminal **PowerShell** que está ejecutando `npm run dev`, pulsa Ctrl+C. Si pregunta si deseas terminar el trabajo, responde S o Y según el idioma. Conserva la ventana de WSL como está.

## Paso 2 · extraer la entrega

Extrae este ZIP en una carpeta nueva:

`C:\Users\valentino\Documents\Soni_Pruebas\UI_V3`

Dentro deben verse ACTUALIZAR_UI.ps1, apply-ui-update.mjs, project y examples_kit. No sustituyas a mano todo qhub-site.

## Paso 3 · aplicar la actualización

Copia sólo estas dos líneas, sin el prompt ni la salida de terminal:

```powershell
Set-Location "C:\Users\valentino\Documents\Soni_Pruebas\UI_V3"
powershell -NoProfile -ExecutionPolicy Bypass -File .\ACTUALIZAR_UI.ps1 -RepoPath "C:\Users\valentino\Documents\Soni_Pruebas\qhub-site"
```

El actualizador comprueba que estés en tu rama de interfaz y que los cinco archivos modificados coincidan con la v2 instalada. Admite los cambios esperados de esa v2 aún sin commit. Comprueba también los archivos nuevos, guarda los originales fuera del repositorio, copia los 48 destinos previstos y reconoce una v3 ya aplicada. No cambia de rama, instala paquetes, crea un commit ni hace push.

Si detecta una edición tuya distinta, se detiene antes de copiar: conserva el mensaje para revisar esa edición. No uses reset, clean, force ni borres archivos para eludir el chequeo.

## Paso 4 · volver a abrir

Después de PASS:

```powershell
Set-Location "C:\Users\valentino\Documents\Soni_Pruebas\qhub-site"
npm run dev
```

Abre [la interfaz](http://localhost:8080/investigacion/sonificacion-cuantica), usando el puerto que indique Vite. Recarga con Ctrl+F5 si mantuviste una pestaña antigua.

## Paso 5 · explorar los ejemplos

El selector Muestra está encima del reproductor. Conserva seed 1060 como primera opción y agrupa Bell, GHZ y Grover como ejemplos didácticos. Cada selección reinicia en su estado inicial, sin inventar una semilla aleatoria.

- **Bell, 2 qubits:** estado inicial → H en q0 → CX de q0 a q1. El estado final es globalmente puro, pero cada qubit tiene r=0 y pureza local 1/2. La MI del par es 2 bits.
- **GHZ, 3 qubits:** preparación de Bell → CX de q1 a q2. Los estados locales finales son mixtos y la MI de cada par es 1 bit. Este valor no clasifica al GHZ como menos entrelazado que Bell: los registros tienen distinta estructura y tamaño.
- **Grover, 3 qubits:** preparación uniforme → oráculo → difusión, dos veces. El objetivo se escribe 101 en el orden q2q1q0. La probabilidad marcada pasa de 12,5 % a 78,125 % y finalmente 94,53125 %. El oráculo cambia una fase relativa antes de que la difusión transforme esa fase en probabilidades. La probabilidad mostrada se calcula del vector cuántico; no se infiere del audio.

Los WAV de Bell duran 2,24 s. GHZ dura aproximadamente 4,350 s en BFS y 4,700 s en DFS/combinado. Grover dura aproximadamente 7,452 s en BFS y 8,379 s en DFS/combinado. Puedes repetir el archivo o inspeccionar un paso pausado. Cambiar BFS/DFS/combinado conserva el paso, vuelve a su inicio y pausa la reproducción: pulsa Reproducir para escuchar la alternativa.

Los ejemplos mantienen el mapeo y la configuración acústica del motor congelado. Sólo cambia el circuito, su número de qubits y la raíz válida para ese registro (q0). Los estados se observan al terminar los bloques indicados. La aparición de compuertas sigue siendo una presentación temporal de lectura, no una simulación continua dentro de cada compuerta.

## Paso 6 · reproducción opcional en WSL

Esta parte comprueba los ejemplos ya generados; no es necesaria para abrirlos. Primero verifica el motor, en tu terminal **WSL / quantum_env**, dentro de Quantum_Sonification_Paper_Final:

```bash
sha256sum src/sonification.py
```

Debe mostrar `23e747dfe61ff50cc149f7395588fca86488e77f3a18e11fdfa8f87590630ad5`. El generador también comprueba el hash de simulations.py. Si no coinciden, no modifica tus fuentes ni genera datos.

Después:

```bash
OPENBLAS_NUM_THREADS=1 python \
  /mnt/c/Users/valentino/Documents/Soni_Pruebas/UI_V3/examples_kit/generate_examples.py \
  --repo-dir . \
  --output-dir outputs/didactic_examples_v1
```

`--repo-dir .` importa tus módulos científicos en modo lectura. `--output-dir` crea una colección nueva; si existe, el generador se detiene para preservarla. No apuntes este comando a las cohortes históricas o de validación. La salida incluye CSV/JSON, estados .npy, circuitos .qpy y WAV float32 estéreo a 22050 Hz. La configuración y las versiones efectivamente usadas quedan en generation_manifest.json.

Se entrega además frozen_reference con las fuentes exactas usadas aquí, sin modificaciones. La ejecución de referencia usó Qiskit 2.1.2 y NetworkX 3.3, y registra NumPy, SciPy y Python. La auditoría final corrigió la captura de versión: el manifiesto anterior leyó metadatos residuales de Qiskit 1.4.6, aunque el módulo importado y los 13 archivos QPY identifican 2.1.2. Se conservan los manifiestos anteriores y la explicación en verification/ENVIRONMENT_CORRECTION.json. Al repetir los ejemplos, los 65 archivos de referencia —estados, circuitos, audio, CSV y JSON de casos— coincidieron byte por byte; sólo cambió el manifiesto del entorno. No se declara que ese entorno sea idéntico al lock histórico. Las identidades matemáticas se comprobaron con tolerancia 1e-12 y los artefactos se validaron; un entorno distinto debe compararse numéricamente y registrar sus versiones, sin asumir identidad binaria de todos los archivos.

## Qué entra al paper

Sí: los tres casos pueden entrar como una subsección breve de **demostraciones del sistema**, con detalle y fuentes en material suplementario. Los fragmentos en español e inglés están en paper. Deben ir separados de las RQ y las 200 semillas: son casos deterministas, no una nueva cohorte ni un ensayo de aprendizaje.

Se incluye un control de límite del mapeo: GHZ+ y GHZ− son estados ortogonales, pero tienen los mismos descriptores locales y MI por pares, y producen PCM idéntico bajo el mismo calendario de una instantánea. Es una demostración esperada de información que el mapeo no conserva, no un descubrimiento físico. No implica que historias completas de circuitos distintos produzcan archivos continuos idénticos.

Teleportación y Shor no se incluyeron en esta entrega. Teleportación requiere describir resultados clásicos y correcciones; no se presenta una secuencia sólo unitaria como si fuera el protocolo completo.

## Evidencia y límites

verification contiene los recibos de cálculo, tipos, build, navegador, actualizador, circuito/estado y el control GHZ. Los 14 recursos originales de sonificación, App.tsx, package.json y el lock se conservan. La revisión cubre el módulo y el motor; no afirma ejecutar la suite de otras páginas con recursos ausentes en la exportación. El build mantiene sus avisos heredados sobre fuentes omitidas y chunks grandes.

El núcleo Node del actualizador se probó en Linux con casos de conversión CRLF; el wrapper PowerShell se revisó, sin afirmar una ejecución de Windows PowerShell aquí. Las comprobaciones de software no sustituyen una evaluación humana de usabilidad, aprendizaje o discriminación auditiva.
