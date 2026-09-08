# Benchmark de skills para diagramas en HTML (ERD, modelo relacional, flujos, journeys, C4, clases, estados y Gantt)

Fecha de consulta de todas las fuentes: 8 de septiembre de 2026.

## Para que sirve este documento

Archify ya cubre arquitectura, workflow, secuencia, flujo de datos y ciclo de vida con HTML autocontenido, validado y con temas claro y oscuro. Este documento busca la mejor skill o herramienta instalable para cubrir lo que Archify no cubre: ERD (entidad relacion), modelo relacional o de bodega de datos (hechos y dimensiones), flujos tipo flowchart, journeys por actor, y de forma ideal C4, diagrama de clases, estados y Gantt.

Se investigaron 6 skills candidatas y 6 herramientas de referencia (las librerias que las skills usan por dentro). La evaluacion uso seis criterios con peso distinto, explicados en la seccion de metodologia.

## Recomendacion en una frase

Instalar y usar **pretty-mermaid** (`imxv/pretty-mermaid-skills`) para ERD, flowchart, diagrama de clases, estados y secuencia; para journey, C4 y Gantt, escribir el diagrama en sintaxis Mermaid y renderizarlo con una copia local de la libreria Mermaid incrustada en el HTML (sin CDN), porque ninguna skill madura y sin dependencia de Chromium o Java cubre esos tres tipos todavia.

## Metodologia

Se buscó en GitHub con la API de búsqueda de repositorios (sin token, 15 resultados por consulta, ordenados por estrellas) usando las diez consultas minimas pedidas, mas variantes para completar cobertura. Se leyeron los README.md y SKILL.md de los candidatos con mas tracción usando Scrapling. Se corroboró la existencia de pretty-mermaid en el directorio skills.sh. Se instaló la skill recomendada de verdad y se generó un archivo HTML de prueba para confirmar que abre sin conexión a internet.

Criterios y peso:

| Criterio | Peso |
| --- | --- |
| Cobertura de los tipos de diagrama pedidos | 30% |
| Salida HTML autocontenida y funcional sin servidor | 20% |
| Validación o verificación automática del diagrama | 10% |
| Adopción y mantenimiento (estrellas, último commit, issues, licencia) | 20% |
| Instalación fácil en Windows sin Chromium ni Java, sin red al renderizar | 10% |
| Calidad visual para audiencia ejecutiva | 10% |

## Candidatos evaluados (skills)

| Repositorio | Estrellas | Último commit | Licencia | Tipos que cubre | Cómo se instala | Cómo produce HTML |
| --- | --- | --- | --- | --- | --- | --- |
| `imxv/pretty-mermaid-skills` | 1,193 | 22 ago 2026 | MIT | Flowchart, secuencia, estados, clases, ERD, XY chart (6 tipos) | `npx skills add imxv/pretty-mermaid-skills@pretty-mermaid -g -y` | Renderiza el `.mmd` a SVG con un motor propio en Node (sin navegador). El SVG se incrusta a mano en una página HTML; no genera el `.html` por sí sola |
| `Agents365-ai/drawio-skill` | 9,132 | 3 sep 2026 | MIT | ERD, UML clases, secuencia, C4 con drill down, arquitectura, y (vía conversión desde Mermaid) journey, Gantt, mindmap y más, 28 tipos en total | `npx skills add Agents365-ai/365-skills -g` | Trae `drawiohtml.py`, que exporta un `.drawio` a un visor HTML interactivo (pan, zoom, buscador, drill down) en un solo archivo. Pero ese script llama por dentro al binario `drawio` de **draw.io Desktop**, que es una app Electron, es decir trae Chromium empaquetado |
| `WH-2099/mermaid-skill` | 274 | 11 ago 2026 | MIT | 23 tipos de Mermaid, incluyendo ERD, clases, estados, Gantt, C4 y journey | Clonar el repo y copiar la carpeta a `.claude/skills/` | No renderiza nada: solo genera el texto Mermaid dentro de un bloque ` ```mermaid `. La skill asume que el visor final (GitHub, un IDE, un cliente con soporte nativo) hace el render. No produce HTML ni valida sintaxis |
| `SpillwaveSolutions/design-doc-mermaid` | 169 | 24 ago 2026 | Sin licencia declarada | Diagramas de actividad, despliegue, arquitectura y secuencia (no cubre ERD, journey, C4 ni Gantt como foco) | `git clone` a `~/.claude/skills` | Usa `mermaid-cli` (`mmdc`) para validar y exportar a PNG o SVG. `mermaid-cli` corre sobre Puppeteer, es decir necesita Chromium |
| `csthink/dashmotion` | 163 | 16 jun 2026 | MIT | Flow (flowchart, estados) y arquitectura, con animación. Sin ERD, journey, C4 ni Gantt | Instrucciones de skill en el propio repo | HTML/SVG autocontenido de verdad, sin librerías externas (usa `stroke-dashoffset` y `animateMotion`). Pero el tipo de diagrama se solapa con lo que ya cubre Archify |
| `bitsmuggler/c4-skill` | 56 | 11 feb 2026 | Sin SPDX claro | Solo C4 | Clonar repo | No confirmado que genere HTML autocontenido; alcance muy angosto para justificar una instalación aparte |

## Herramientas de referencia (lo que hay detrás de las skills)

| Herramienta | Estrellas | Último commit | Licencia | Nota relevante |
| --- | --- | --- | --- | --- |
| `mermaid-js/mermaid` | 90,158 | 8 sep 2026 | MIT | Motor detrás de casi todas las skills de la tabla anterior. Cubre de forma nativa erDiagram, journey, C4Context, classDiagram, stateDiagram, gantt y flowchart. Corre en el navegador con JavaScript puro; si se incrusta `mermaid.min.js` dentro del HTML (en vez de cargarlo desde una CDN) el archivo queda sin dependencia de red |
| `terrastruct/d2` | 25,262 | 7 sep 2026 | MPL-2.0 | Binario único en Go, sin Chromium ni Java. Genera SVG nativo. No tiene un tipo de diagrama Gantt, journey o C4 tan directo como Mermaid; su fuerza es arquitectura y flujos, que ya cubre Archify |
| `plantuml/plantuml` | 13,305 | 8 sep 2026 | LGPL-3.0 | Excelente para C4 (vía la librería C4-PlantUML) y clases, pero el motor corre en Java (JAR), lo que choca con la restricción de evitar Java |
| `yuzutech/kroki` | 4,311 | 23 ago 2026 | MIT | Unifica Mermaid, PlantUML, D2 y otros detrás de un servicio HTTP. Si se usa el servicio público hay dependencia de red; si se auto-hospeda hace falta Docker |
| `holistics/dbml` | 3,690 | 8 sep 2026 | Apache-2.0 | Lenguaje para modelar bases de datos (define tablas, relaciones). El renderizador visual público es dbdiagram.io, que es un servicio en línea, no una skill instalable ni un generador local de HTML |
| `structurizr/lite` | 383 | 1 feb 2026 | MIT | Bueno para C4, pero corre sobre Java, igual que PlantUML |

## Puntuación por criterio (sobre 100)

| Candidato | Cobertura (30) | HTML autocontenido (20) | Validación (10) | Adopción (20) | Instalación sin Chromium/Java (10) | Calidad visual (10) | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pretty-mermaid | 18 | 14 | 8 | 15 | 10 | 8 | 73 |
| drawio-skill | 28 | 18 | 8 | 20 | 2 | 9 | 85 |
| mermaid-skill (WH-2099) | 26 | 4 | 2 | 8 | 10 | 5 | 55 |
| design-doc-mermaid | 10 | 10 | 6 | 6 | 3 | 6 | 41 |
| dashmotion | 6 | 20 | 4 | 6 | 10 | 8 | 54 |

`drawio-skill` saca la puntuación más alta en la tabla porque cubre casi todos los tipos pedidos y tiene, con enorme diferencia, la mayor adopción (9,132 estrellas, commit de hace cinco días). El motivo por el que no es la recomendación final es el criterio de instalación: su script de exportación a HTML (`drawiohtml.py`) llama al binario `drawio` de draw.io Desktop, una aplicación construida sobre Electron, que trae Chromium empaquetado. Eso es justo lo que el encargo pide evitar cuando sea posible. Es una opción válida como segunda alternativa para quien ya tenga draw.io Desktop instalado o no le importe instalarlo, porque a cambio da la cobertura más completa (incluye Gantt, journey y C4 con drill down desde el mismo modelo).

## Recomendación y por qué

Se recomienda **pretty-mermaid** (`imxv/pretty-mermaid-skills`) como la skill instalada por defecto, con esta división de trabajo:

- **pretty-mermaid cubre:** ERD, flowchart, diagrama de clases, diagrama de estados y secuencia (esta última ya la cubre Archify, así que en la práctica se usa para las otras cuatro). El modelo relacional o de bodega de datos (hechos y dimensiones) se resuelve con la misma sintaxis `erDiagram`, marcando las tablas de hechos y dimensiones como entidades con sus llaves primarias y foráneas.
- **Por qué esta y no drawio-skill:** aunque drawio-skill cubre más tipos, su ruta de generación de HTML depende de un binario Electron (Chromium empaquetado), lo que la vuelve más pesada de instalar y menos alineada con el pedido explícito de evitar Chromium. pretty-mermaid es solo Node.js, corre sin navegador, tiene validación real documentada en su SKILL.md (confirma que el SVG generado empieza con `<svg`, corre `npm test` y `npm run validate`), tiene CI activo y casi 1,200 estrellas, la segunda cifra más alta entre las skills que sí renderizan (no solo documentan sintaxis).
- **El hueco que queda:** journey, C4 y Gantt. Ninguna skill encontrada cubre estos tres tipos con la misma calidad de instalación (sin Chromium, sin Java, sin red) que pretty-mermaid. La salida práctica, y la que se recomienda mientras no exista una skill madura para esto, es escribir el diagrama en sintaxis Mermaid (`journey`, `C4Context`, `gantt`) y renderizarlo con una copia local de `mermaid.min.js` incrustada dentro del propio archivo HTML, en vez de cargarla desde una CDN. Esto no requiere instalar nada adicional más que descargar una vez el archivo de la librería (MIT, sin dependencias), y el resultado sigue siendo un HTML autocontenido que abre sin conexión.

### Riesgo detectado durante la instalación

`npx skills add` corrió un análisis de seguridad automático (Socket y Snyk) sobre pretty-mermaid antes de instalar: Socket marcó "2 alertas" y Snyk lo calificó como "riesgo medio". El instalador no detalla en la terminal cuáles son esas alertas. Se puede revisar el detalle completo en `https://skills.sh/imxv/pretty-mermaid-skills`. No se encontró nada sospechoso al leer el código de `scripts/render.mjs` ni el README, pero se deja registrado para que quien lo use pueda decidir con esa información.

### Cómo conviven pretty-mermaid y Archify

| Necesitas | Usa |
| --- | --- |
| Arquitectura, infraestructura, topología de red o seguridad | Archify (`architecture`) |
| Procesos, aprobaciones, runbooks, CI/CD | Archify (`workflow`) |
| Llamadas API, trazas de request, mensajería | Archify (`sequence`) o pretty-mermaid si ya se tiene el `.mmd` |
| Pipelines ETL/ELT, linaje de datos | Archify (`dataflow`) |
| Máquinas de estado, reintentos, estados terminales | Archify (`lifecycle`) o pretty-mermaid (`stateDiagram-v2`) |
| Entidad relación de una base de datos | pretty-mermaid (`erDiagram`) |
| Modelo relacional o de bodega (hechos y dimensiones) | pretty-mermaid (`erDiagram`), marcando hechos y dimensiones como entidades |
| Diagrama de flujo simple sin arquitectura de por medio | pretty-mermaid (`flowchart`) |
| Diagrama de clases | pretty-mermaid (`classDiagram`) |
| Journey de un actor o usuario | Mermaid `journey` con `mermaid.min.js` incrustado localmente (sin skill dedicada todavía) |
| C4 (contexto, contenedores, componentes) | Mermaid `C4Context` con `mermaid.min.js` incrustado, o drawio-skill si se acepta instalar draw.io Desktop |
| Gantt | Mermaid `gantt` con `mermaid.min.js` incrustado localmente |

## Estado de la instalación

Se instaló pretty-mermaid de forma global con:

```
npx -y skills add imxv/pretty-mermaid-skills@pretty-mermaid -g -y
```

Quedó en `~/.agents/skills/pretty-mermaid`, con symlink en `~/.claude/skills/pretty-mermaid`. Se confirmó que `SKILL.md` es legible y describe el flujo de trabajo completo (elegir tipo de diagrama, elegir formato de salida, renderizar, validar). Después de instalar hizo falta correr `npm install` dentro de la carpeta de la skill, porque el paquete `@resvg/resvg-js` (necesario solo para exportar a PNG) no se instala automáticamente; para SVG, que es el formato que se usa para HTML, no hace falta ese paso pero se dejó instalado por si se necesita exportar a PNG más adelante.

## Prueba de humo

Se generó un ERD mínimo de dos tablas (CLIENTE y PEDIDO, con la relación "realiza") en:

```
C:\Users\Lenovo\AppData\Local\Temp\claude\C--Users-Lenovo-Documents-cartera-clientes-21-worky\97e1cd25-198a-4335-8bad-d11032601f00\scratchpad\diagram-smoke\erd-smoke.html
```

Pasos: se escribió `erd.mmd` con sintaxis `erDiagram`, se renderizó a SVG con `node scripts/render.mjs`, y se incrustó el SVG resultante dentro de una página HTML mínima.

Riesgo encontrado y corregido: la salida por defecto de pretty-mermaid agrega dos líneas `@import url('https://fonts.googleapis.com/...')` dentro del propio SVG, para cargar las fuentes Inter y JetBrains Mono desde Google Fonts. Eso es una dependencia de red al momento de abrir el archivo. Como el CSS ya trae una fuente de respaldo del sistema (`system-ui`, `ui-monospace`), el diagrama se ve bien aunque ese `@import` falle, pero para dejar el archivo verdaderamente libre de llamadas de red se quitaron esas dos líneas a mano antes de incrustar el SVG en el HTML final. Se confirmó con una búsqueda de texto que el archivo final no contiene ningún `https://` fuera del identificador de espacio de nombres XML (`http://www.w3.org/2000/svg`, que no es una llamada de red), y que el SVG incrustado es XML válido.

## Fuentes consultadas

- GitHub Search API, consultas: `claude skill mermaid`, `agent skill mermaid diagrams`, `skill erd diagram`, `SKILL.md diagram`, `mermaid erDiagram html`, `dbml erd html`, `d2 diagram skill`, `plantuml skill`, `c4 model skill`, `user journey diagram generator`. Consultado el 8 de septiembre de 2026.
- `https://raw.githubusercontent.com/imxv/Pretty-mermaid-skills/HEAD/README.md` y `.../SKILL.md`, 8 de septiembre de 2026.
- `https://raw.githubusercontent.com/WH-2099/mermaid-skill/HEAD/README.md` y `.../.claude/skills/mermaid/SKILL.md`, 8 de septiembre de 2026.
- `https://raw.githubusercontent.com/Agents365-ai/drawio-skill/HEAD/README.md`, `.../skills/drawio-skill/SKILL.md` y `.../skills/drawio-skill/scripts/drawiohtml.py`, 8 de septiembre de 2026.
- `https://raw.githubusercontent.com/SpillwaveSolutions/design-doc-mermaid/HEAD/README.md`, 8 de septiembre de 2026.
- `https://raw.githubusercontent.com/csthink/dashmotion/HEAD/README.md`, 8 de septiembre de 2026.
- `https://www.skills.sh/imxv/pretty-mermaid-skills/pretty-mermaid`, 8 de septiembre de 2026.
- GitHub API, endpoint de repositorio individual, para `mermaid-js/mermaid`, `terrastruct/d2`, `plantuml/plantuml`, `yuzutech/kroki`, `holistics/dbml` y `structurizr/lite`, 8 de septiembre de 2026.
- `~/.agents/skills/archify/SKILL.md` (skill ya instalada, usada como referencia de cobertura y formato de salida), leída el 8 de septiembre de 2026.
