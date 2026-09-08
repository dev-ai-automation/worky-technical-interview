# Recursos incrustados para diagramas `journey`

## `mermaid.min.js`

- Versión: **11.4.1** (empaquetado estándar del navegador, define `globalThis.mermaid`).
- Origen del archivo: `https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js`, descargado una sola vez el 8 de septiembre de 2026 y guardado en este directorio para que `docs/diagrams/05-journeys-por-actor.html` lo cargue por ruta relativa (`assets/mermaid.min.js`), sin llamada de red al abrir el archivo.
- Licencia: **MIT**. Mermaid es de Knut Sveidqvist y colaboradores del proyecto `mermaid-js/mermaid`. El archivo trae, además, avisos de licencia MIT de dependencias empaquetadas (D3, Dagre, y una función de física tipo resorte adaptada de Framer.js).
- Motivo de esta excepción: `pretty-mermaid` no renderiza diagramas `journey`. Por eso este único tipo de diagrama del set usa Mermaid corriendo en el navegador en lugar del renderizador de la skill. Ver `docs/research/02-benchmark-skills-de-diagramas.md`.
- Nota de origen: cdnjs no publica un build UMD/navegador (`mermaid.min.js`) para la serie 11.x de Mermaid, solo módulos `.mjs`; jsdelivr sí lo publica bajo la misma versión npm. El archivo descargado es el paquete oficial de npm, sin modificar.

## Cómo regenerar

```
curl -L -o docs/diagrams/assets/mermaid.min.js https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js
```

Verificar después de descargar que el archivo no se sirvió como HTML de error (empieza con `"use strict"`, no con `<html>`), y que el archivo HTML que lo consume no hace ninguna llamada de red al abrirse sin conexión.
