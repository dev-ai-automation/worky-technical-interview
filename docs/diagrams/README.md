# Índice de diagramas

Todos los diagramas de esta carpeta son archivos HTML autocontenidos: abren en cualquier navegador sin
servidor y sin ninguna llamada de red (verificado con `grep -c "https://"` en cada archivo, ver más abajo).
Cada uno trae su fuente Mermaid legible en `docs/diagrams/src/<nombre>.mmd` y su entrada de la skill
`archify` en `docs/diagrams/src/<nombre>.<tipo>.json`, con el mismo nombre base.

Los ocho diagramas de este directorio salen ahora de la misma skill, `archify`, instalada en
`~/.agents/skills/archify` (symlink en `~/.claude/skills/archify`), para que todos compartan el mismo
contrato de entrada, el mismo validador y el mismo comando de entrega.

| # | Diagrama | Qué muestra | Documento de origen | Tipo de archify |
|---|---|---|---|---|
| 00 | [`00-as-is-systems.html`](./00-as-is-systems.html) | Arquitectura de los tres sistemas de Worky tal como existen hoy, con las siete tablas de origen agrupadas por sistema | `docs/data-model/00-as-is-schema-profile.md` | Nativo `architecture` |
| 01 | [`01-a0-engine-dataflow.html`](./01-a0-engine-dataflow.html) | Flujo de datos del motor A0: de las tres bases SQLite a `outputs/`, pasando por normalización, resolución de identidad, staging y marts de DuckDB | `openspec/changes/a0-master-dataset-engine/design.md` | Nativo `dataflow` |
| 02 | [`02-erd-as-is-tres-sistemas.html`](./02-erd-as-is-tres-sistemas.html) | Entidad relación de las siete tablas de origen (HubSpot CRM, Product DB, Vitally), con columnas, tipos, llaves implícitas y las dos uniones débiles entre sistemas | `docs/data-model/00-as-is-schema-profile.md` | Mermaid `erd` (fidelidad Mermaid, Node) |
| 03 | [`03-modelo-relacional-objetivo.html`](./03-modelo-relacional-objetivo.html) | Modelo relacional que produce el motor `worky_engine`: `master_dataset` al centro, `identity_crosswalk`, `match_audit`, las tres tablas de cuarentena y excepciones, y las tablas de origen como entrada | `openspec/changes/a0-master-dataset-engine/design.md` (sección 2) y `docs/decisions/ADR-001-identity-resolution-scorecard.md` | Mermaid `erd` (fidelidad Mermaid, Node) |
| 04 | [`04-flujo-resolucion-identidad.html`](./04-flujo-resolucion-identidad.html) | Cascada de resolución de identidad del ADR-001: normalización, deduplicación de clones, niveles T0 a T3, veto y salidas, con la cobertura medida por nivel | `docs/decisions/ADR-001-identity-resolution-scorecard.md` y `openspec/changes/a0-master-dataset-engine/specs/identity-resolution/spec.md` | Mermaid `flowchart` (fidelidad Mermaid, Node) |
| 05 | [`05-journeys-por-actor.html`](./05-journeys-por-actor.html) | Un solo journey con doce secciones (seis actores por dos escenarios: VP de Customer Success, CSM, Head of RevOps, Marketing, Sales y el especialista de Business Operations y Datos), comparando el mismo lunes de crisis antes y después del motor A0 y el Health Score | Caso de negocio (Parte B), `openspec/changes/a0-master-dataset-engine/proposal.md` y `docs/research/01-bi-revops-data-architecture.md` (carriles 4 y 5) | Mermaid `journey` (fidelidad Mermaid, navegador) |
| 06 | [`06-estados-cuenta.html`](./06-estados-cuenta.html) | Ciclo de vida de una cuenta desde la óptica del motor de tendencia: alta, historia insuficiente, tendencia calculada, en riesgo, churn y sin uso | `docs/decisions/ADR-003-usage-trend-and-leakage-guard.md` | Mermaid `state` (fidelidad Mermaid, Node) |
| 07 | [`07-modelo-estrella-warehouse.html`](./07-modelo-estrella-warehouse.html) | Esquema en estrella del comando `warehouse`: `dim_company` con SCD2 al centro, `map_source_identity` e `identity_overrides` a un lado, los cinco hechos y las tablas de A0 que envuelve como entrada | `docs/data-model/01-warehouse-model.md` | Mermaid `erd` (fidelidad Mermaid, Node) |

## Ajuste de contenido en el diagrama 05

La fuente original de `05-journeys-por-actor.mmd` traía seis bloques `journey` distintos, uno por actor,
concatenados en un solo archivo. Mermaid solo admite un bloque `journey` por diagrama: `archify validate`
no lo detecta porque su chequeo de `journey`/`c4`/`gantt` es superficial (encabezado más una línea de
estructura, no la gramática completa de Mermaid), pero un render real en Chrome sin cabeza sí lo rechazaba
con `Syntax error in text ... Expecting ... got 'journey'`. Por eso la fuente se consolidó en un solo
diagrama `journey` con doce secciones (una "Hoy" y una "Con el motor A0" por actor), siguiendo la
convención de journeys por actor que documenta la skill `archify`. El contenido de cada paso y su puntaje
no cambió, solo la estructura del archivo. El resto de las fuentes (02, 03, 04, 06) no necesitó ningún
ajuste de sintaxis: validaron sin cambios.

## Cómo regenerar cada diagrama

Todos los comandos se ejecutan desde la raíz de la skill `archify`
(`~/.claude/skills/archify` o `~/.agents/skills/archify`), usando rutas absolutas al repositorio de Worky.

Diagramas nativos de archify (00 y 01, no tocados por esta regeneración; ese flujo pertenece a otro
agente):

```
node bin/archify.mjs deliver architecture docs/diagrams/src/00-as-is-systems.architecture.json docs/diagrams/00-as-is-systems.html --json
node bin/archify.mjs deliver dataflow docs/diagrams/src/01-a0-engine-dataflow.dataflow.json docs/diagrams/01-a0-engine-dataflow.html --json
```

Diagramas de fidelidad Mermaid (02 a 06), cada uno con su propia entrada JSON en
`docs/diagrams/src/<nombre>.<tipo>.json`:

```
node bin/archify.mjs validate erd docs/diagrams/src/02-erd-as-is-tres-sistemas.erd.json --json
node bin/archify.mjs deliver erd docs/diagrams/src/02-erd-as-is-tres-sistemas.erd.json docs/diagrams/02-erd-as-is-tres-sistemas.html --json

node bin/archify.mjs validate erd docs/diagrams/src/03-modelo-relacional-objetivo.erd.json --json
node bin/archify.mjs deliver erd docs/diagrams/src/03-modelo-relacional-objetivo.erd.json docs/diagrams/03-modelo-relacional-objetivo.html --json

node bin/archify.mjs validate flowchart docs/diagrams/src/04-flujo-resolucion-identidad.flowchart.json --json
node bin/archify.mjs deliver flowchart docs/diagrams/src/04-flujo-resolucion-identidad.flowchart.json docs/diagrams/04-flujo-resolucion-identidad.html --json

node bin/archify.mjs validate journey docs/diagrams/src/05-journeys-por-actor.journey.json --json
node bin/archify.mjs deliver journey docs/diagrams/src/05-journeys-por-actor.journey.json docs/diagrams/05-journeys-por-actor.html --json

node bin/archify.mjs validate state docs/diagrams/src/06-estados-cuenta.state.json --json
node bin/archify.mjs deliver state docs/diagrams/src/06-estados-cuenta.state.json docs/diagrams/06-estados-cuenta.html --json

node bin/archify.mjs validate erd docs/diagrams/src/07-modelo-estrella-warehouse.erd.json --json
node bin/archify.mjs deliver erd docs/diagrams/src/07-modelo-estrella-warehouse.erd.json docs/diagrams/07-modelo-estrella-warehouse.html --json
```

Si se edita el contenido de un diagrama, hay que editar primero su fuente legible en
`docs/diagrams/src/<nombre>.mmd` y copiar el texto actualizado dentro del campo `source` del JSON
correspondiente (o regenerar el JSON con un script corto, como se hizo en esta regeneración), antes de
volver a correr `validate` y `deliver`.

## Diagramas 02, 03, 04 y 06: renderizado en Node, sin navegador

Estos cuatro usan el motor `beautiful-mermaid` de archify, que corre en Node y entrega un `<svg>` ya
terminado dentro del HTML. Abren sin JavaScript y sin conexión.

## Diagrama 05: renderizado en el navegador

`journey` no tiene motor de render en Node dentro de archify. El HTML entregado trae el runtime de Mermaid
vendorizado por la propia skill (sin CDN) y renderiza el diagrama en el navegador del lector, al abrir el
archivo, sin llamada de red. Por eso este archivo pesa más (unos 2.5 MB) que los demás: incluye el runtime
completo de Mermaid, no solo el SVG final. El directorio `docs/diagrams/assets/` (que traía una copia
manual de `mermaid.min.js` para una versión anterior de este diagrama, hecha con `pretty-mermaid`) se
eliminó en esta regeneración porque ya ningún HTML de esta carpeta lo referencia.

## Límite documentado: los tipos Mermaid no pasan por las compuertas de composición nativas de archify

Los tipos `erd`, `flowchart`, `class`, `state`, `journey`, `c4` y `gantt` leen y renderizan la sintaxis de
Mermaid tal cual, con el motor de layout propio de Mermaid (o de `beautiful-mermaid`), no con el compilador
de geometría nativo de archify. Las compuertas de composición de archify (separación de etiquetas, cruces
de relaciones, corredores ambiguos, ritmo de rutas) leen atributos (`data-edge-*`, clases
`a-default`/`a-emphasis`/...) que solo emite el compilador de layout de los tipos nativos
(`architecture`, `workflow`, `sequence`, `dataflow`, `lifecycle`). Un SVG renderizado por Mermaid nunca
trae esos atributos, así que esas compuertas pasan trivialmente en vez de validar algo real para esta
familia de tipos. Lo que sí valida `validate`/`deliver` para los tipos Mermaid: presencia y buena formación
del SVG o del código fuente incrustado, cero referencias a `https://`, un chequeo superficial de encabezado
y estructura (no la gramática completa de Mermaid, ver la nota del diagrama 05 arriba), y los conteos de
`mermaidMeta` (entidades, relaciones, nodos, aristas, actores, secciones, pasos, según el tipo) como ayuda
de diagnóstico, no como hecho certificado: en el diagrama 02, por ejemplo, el conteo de `relationships` da
4 por un método basado en expresiones regulares, aunque la fuente trae 6 líneas de relación reales. Esta
limitación está documentada en la propia skill, en `references/mermaid-render-types.md`, bajo
"Honest limitations".

## Verificación de que un HTML no llama a la red

```
grep -c "https://" docs/diagrams/<archivo>.html
```

El resultado da `0` en los cinco diagramas regenerados en esta pasada (02, 03, 04, 05 y 06): en 02 a 04 y
06 el SVG está incrustado en línea, y en 05 el runtime de Mermaid está vendorizado dentro del propio HTML,
sin CDN. Los diagramas 00 y 01 no se tocaron en esta regeneración y sí traen referencias a
`https://fonts.gstatic.com` y `https://fonts.googleapis.com` (Google Fonts) en su plantilla nativa de
archify; eso pertenece al otro flujo que generó esos dos archivos y no se corrigió aquí.
