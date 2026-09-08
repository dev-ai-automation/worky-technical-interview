# Índice de diagramas

Todos los diagramas de esta carpeta son archivos HTML autocontenidos: abren en cualquier navegador sin
servidor y, salvo el de journeys, sin ninguna llamada de red. Cada uno trae su fuente en
`docs/diagrams/src/` con el mismo nombre base.

| # | Diagrama | Qué muestra | Documento de origen | Herramienta |
|---|---|---|---|---|
| 00 | [`00-as-is-systems.html`](./00-as-is-systems.html) | Arquitectura de los tres sistemas de Worky tal como existen hoy, con las siete tablas de origen agrupadas por sistema | `docs/data-model/00-as-is-schema-profile.md` | Archify (`architecture`) |
| 01 | [`01-a0-engine-dataflow.html`](./01-a0-engine-dataflow.html) | Flujo de datos del motor A0: de las tres bases SQLite a `outputs/`, pasando por normalización, resolución de identidad, staging y marts de DuckDB | `openspec/changes/a0-master-dataset-engine/design.md` | Archify (`dataflow`) |
| 02 | [`02-erd-as-is-tres-sistemas.html`](./02-erd-as-is-tres-sistemas.html) | Entidad relación de las siete tablas de origen (HubSpot CRM, Product DB, Vitally), con columnas, tipos, llaves implícitas y las dos uniones débiles entre sistemas | `docs/data-model/00-as-is-schema-profile.md` | pretty-mermaid (`erDiagram`) |
| 03 | [`03-modelo-relacional-objetivo.html`](./03-modelo-relacional-objetivo.html) | Modelo relacional que produce el motor `worky_engine`: `master_dataset` al centro, `identity_crosswalk`, `match_audit`, las tres tablas de cuarentena y excepciones, y las tablas de origen como entrada | `openspec/changes/a0-master-dataset-engine/design.md` (sección 2) y `docs/decisions/ADR-001-identity-resolution-scorecard.md` | pretty-mermaid (`erDiagram`) |
| 04 | [`04-flujo-resolucion-identidad.html`](./04-flujo-resolucion-identidad.html) | Cascada de resolución de identidad del ADR-001: normalización, deduplicación de clones, niveles T0 a T3, veto y salidas, con la cobertura medida por nivel | `docs/decisions/ADR-001-identity-resolution-scorecard.md` y `openspec/changes/a0-master-dataset-engine/specs/identity-resolution/spec.md` | pretty-mermaid (`flowchart`) |
| 05 | [`05-journeys-por-actor.html`](./05-journeys-por-actor.html) | Seis journeys (VP de Customer Success, CSM, Head of RevOps, Marketing, Sales y el especialista de Business Operations y Datos), cada uno comparando el mismo lunes de crisis antes y después del motor A0 y el Health Score | Caso de negocio (Parte B), `openspec/changes/a0-master-dataset-engine/proposal.md` y `docs/research/01-bi-revops-data-architecture.md` (carriles 4 y 5) | Mermaid 11.4.1 en el navegador (`journey`), cargado localmente |
| 06 | [`06-estados-cuenta.html`](./06-estados-cuenta.html) | Ciclo de vida de una cuenta desde la óptica del motor de tendencia: alta, historia insuficiente, tendencia calculada, en riesgo, churn y sin uso | `docs/decisions/ADR-003-usage-trend-and-leakage-guard.md` | pretty-mermaid (`stateDiagram-v2`) |

## Cómo regenerar cada diagrama

Los diagramas 02, 03, 04 y 06 se generan con la skill `pretty-mermaid`, instalada en
`~/.agents/skills/pretty-mermaid` (symlink en `~/.claude/skills/pretty-mermaid`). Desde la raíz de esa
skill:

```
node scripts/render.mjs --input docs/diagrams/src/02-erd-as-is-tres-sistemas.mmd --output docs/diagrams/02-erd-as-is-tres-sistemas.svg --theme zinc-light
node scripts/render.mjs --input docs/diagrams/src/03-modelo-relacional-objetivo.mmd --output docs/diagrams/03-modelo-relacional-objetivo.svg --theme zinc-light --node-spacing 60 --layer-spacing 80
node scripts/render.mjs --input docs/diagrams/src/04-flujo-resolucion-identidad.mmd --output docs/diagrams/04-flujo-resolucion-identidad.svg --theme zinc-light --node-spacing 40 --layer-spacing 60
node scripts/render.mjs --input docs/diagrams/src/06-estados-cuenta.mmd --output docs/diagrams/06-estados-cuenta.svg --theme zinc-light --node-spacing 40 --layer-spacing 60
```

Después de renderizar cada SVG hace falta, a mano: quitar las dos líneas `@import url('https://fonts.googleapis.com/...')` que trae por omisión (dejan de ser necesarias porque el CSS ya define una fuente de respaldo del sistema), incrustar el SVG resultante dentro de la página HTML de este directorio, y confirmar con `grep -c "https://" archivo.html` que el resultado da 0.

El diagrama 05 no usa `pretty-mermaid`, porque esa skill no soporta el tipo `journey`. Usa Mermaid 11.4.1
corriendo en el navegador, cargado desde `docs/diagrams/assets/mermaid.min.js` (ver
`docs/diagrams/assets/README.md` para la versión, la licencia MIT y el comando de descarga). El HTML no
necesita regenerarse para cambiar contenido: basta con editar el texto dentro de cada bloque
`<pre class="mermaid">`, o su fuente de referencia en `docs/diagrams/src/05-journeys-por-actor.mmd`.

Los diagramas 00 y 01 se generaron con la skill `archify` y se regeneran desde sus fuentes JSON
(`docs/diagrams/src/00-as-is-systems.architecture.json` y
`docs/diagrams/src/01-a0-engine-dataflow.dataflow.json`); ese flujo pertenece a otro agente y no se modificó
para este documento.

## Verificación de que un HTML no llama a la red

```
grep -c "https://" docs/diagrams/<archivo>.html
```

El resultado debe ser `0` en los diagramas 00, 01, 02, 03, 04 y 06 (el SVG está incrustado en línea). El
diagrama 05 tampoco contiene `https://` en su propio HTML: carga `assets/mermaid.min.js` por ruta relativa,
sin CDN.
