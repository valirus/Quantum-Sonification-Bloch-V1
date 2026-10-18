# Quantum Sonification — demo pública

Aplicación React/Vite independiente basada en la interfaz V3 de QuantumHub. Incluye la muestra RQC 1060 y tres casos ilustrativos, Bell, GHZ y Grover. Los audios BFS, DFS y combinado y los datos se entregan como archivos estáticos.

## Desarrollo y compilación

Requiere Node compatible con `package.json`. La publicación fija Node 24.19.0 en `.node-version`; la preparación se comprobó con esa versión.

```bash
npm ci
npm run dev
```

Compilación de producción:

```bash
npm run build
```

El build verifica integridad de los archivos V3, ejecuta las 49 pruebas originales, comprueba TypeScript y produce `dist/`. Cada archivo científico público conserva los bytes del ZIP suministrado; si se cambia deliberadamente una implementación de interfaz, deberá documentarse una nueva referencia de auditoría.

## Cloudflare Pages

En el repositorio científico, configurar raíz `web`, rama `feat/public-sonification-demo`, comando `npm run build` y salida `dist`. La aplicación se sirve en `/` de su hostname. Las direcciones históricas `/investigacion/sonificacion-cuantica` redirigen a `/`.

Este es un despliegue de recursos estáticos; no ejecuta Python, Qiskit ni nuevos circuitos del visitante. No necesita credenciales en el código. Cloudflare vuelve a compilar; `dist` y `node_modules` no se versionan.

## Procedencia

- Repositorio científico: https://github.com/valirus/Quantum-Sonification-Bloch-V1
- Motor de referencia: `bb31388202666a6ab1a365b912b4e2992429a7c6`.
- Renderer SHA256: `23e747dfe61ff50cc149f7395588fca86488e77f3a18e11fdfa8f87590630ad5`.
- Cierre de interfaz asociado a `fdd3722b6b50f8a003d94f4b5432d39306f409f6` en `QuantumHub-Peru/qhub-site`.
- `docs/UPSTREAM_INTEGRITY.json`: hashes de la interfaz, las pruebas y los recursos originales, y de los ZIP utilizados.
- `docs/PROVENANCE.json` y `docs/USO_INTERFAZ.md`: documentación conservada del cierre V3.
- `verification/build_checks.json` y `verification/audio_checks.json`: comprobaciones de esta preparación.

El entorno del paper se mantiene separado de las herramientas de compilación web. Los ejemplos didácticos no se incorporan a las cohortes estadísticas. La visualización de Lissajous representa el audio estéreo, no un espacio de Hilbert reconstruido. Los WAV originales siguen siendo la referencia científica; los MP3 existentes de la muestra 1060 son copias para reproducción web.
