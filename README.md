# Central de Filamentos

Central de Filamentos centraliza stock online de proveedores de filamento 3D del AMBA para que usuarios de impresion 3D encuentren rapido quien tiene el material, color, marca y formato que necesitan.

## Estado actual

El proyecto esta en implementacion inicial del MVP.

Decisiones principales:

- Sitio estatico publico.
- Python para ingesta y normalizacion.
- Vite + Svelte para el frontend.
- GitHub Actions para actualizar stock 2 a 4 veces por dia en horario de oficina.
- GitHub Pages para publicar.
- Proveedores iniciales: Filamentos3D, Grupo Senz y MundoInsumos.
- UI en espanol argentino, compacta, mobile friendly y minimalista.

## Desarrollo local

```bash
python -m pip install -e ".[dev]"
npm ci
python -m pytest -v --basetemp C:\tmp\pytest-centraldefilamentos
python -m centraldefilamentos.build_data --output public/data/stock.json
python -m centraldefilamentos.generate_thumbnails --stock-json public/data/stock.json
npm run dev
```

Abrir la URL local que informa Vite.
La vista compacta de resumen queda en `/resumen.html`.
La vista interna no enlazada para vendedores queda en `/estadisticas.html`.

### Comandos

Instalar dependencias de desarrollo:

```bash
python -m pip install -e ".[dev]"
npm ci
```

Ejecutar tests en Windows local:

```bash
python -m pytest -v --basetemp C:\tmp\pytest-centraldefilamentos
```

Ejecutar tests en Linux o GitHub Actions:

```bash
python -m pytest -v
```

Generar datos para el sitio estatico:

```bash
python -m centraldefilamentos.build_data --output public/data/stock.json
python -m centraldefilamentos.generate_thumbnails --stock-json public/data/stock.json
npm run build
```

Actualizar la cache local de metadatos e imagenes oficiales de Grilon3, solo cuando Grilon3 cambie o agregue filamentos:

```bash
python -m centraldefilamentos.cache_grilon3_metadata --timeout-seconds 10 --max-workers 8
python -m centraldefilamentos.build_data --output public/data/stock.json
python -m centraldefilamentos.generate_thumbnails --stock-json public/data/stock.json
```

Si solo hace falta volver a descargar imagenes usando la cache existente, sin leer otra vez las fichas de producto:

```bash
python -m centraldefilamentos.cache_grilon3_metadata --images-only --timeout-seconds 20
python -m centraldefilamentos.build_data --output public/data/stock.json
python -m centraldefilamentos.generate_thumbnails --stock-json public/data/stock.json
```

Levantar servidor estatico local:

```bash
npm run dev
```

Previsualizar el build final como lo recibe GitHub Pages:

```bash
npm run build
npm run preview
```

## Datos

El frontend lee `public/data/stock.json` durante desarrollo. En produccion, GitHub Actions genera ese archivo, genera las miniaturas, corre `npm run build` y publica `dist/` en GitHub Pages.

`public/data/stock.json` es salida generada. Evitar editarlo a mano: los cambios persistentes van en normalizacion, fuentes o caches de metadata, y luego se regenera con los comandos anteriores.

La cache `centraldefilamentos/data/daily_provider_stock_snapshot.json` se actualiza en la corrida de las 09 hs Argentina. Guarda la captura diaria por proveedor y la captura anterior para mostrar la diferencia de carretes `vs ayer`.

La cache `centraldefilamentos/data/provider_stock_history.json` guarda hasta 30 dias por proveedor para la vista interna de vendedores. Cada dia conserva la captura base de las 09 hs y los chequeos intradia de las demas corridas. La pagina se publica como archivo no enlazado y se puede apagar con `public/data/feature_flags.json` cambiando `vendorStatsEnabled` a `false`.

Los logs de salud del build se publican en `public/data/build_business_log.json` y `public/data/build_technical_log.json`. Si una fuente falla o los conteos caen de forma sospechosa, la publicacion de stock se bloquea, se conserva el ultimo `stock.json` bueno y no se actualizan snapshots ni historiales con datos parciales.

Validaciones de resiliencia del build:

- Cada fuente se intenta hasta 2 veces, sin esperas largas entre intentos, para no estirar GitHub Actions por fallas momentaneas.
- Si una fuente falla despues de los retries, la publicacion se bloquea y el log de negocio muestra el ultimo dato bueno disponible para ese proveedor.
- Si el catalogo final queda vacio, la publicacion se bloquea.
- Si habia al menos 50 productos y la cantidad total baja mas de 40% contra el ultimo `stock.json` bueno, la publicacion se bloquea.
- Si un proveedor tenia al menos 100 carretes y su total baja mas de 60% contra el ultimo `stock.json` bueno, la publicacion se bloquea. Esta validacion mira el total del proveedor, no movimientos por color o producto.
- El JSON final debe tener `generated_at`, listas de `products`, `sources` y `manufacturers`, todas las fuentes esperadas y productos con `id` y `offers`.
- Si falla el enriquecimiento de imagenes o metadata, no se bloquea el stock: se publica con los datos disponibles y queda un warning en los logs.

La cache `centraldefilamentos/data/grilon3_metadata.json` se versiona en el repositorio. Guarda datos oficiales como Pantone, SKU, EAN y la ruta local de imagen. Las imagenes oficiales descargadas se versionan en `public/assets/grilon3/`. La actualizacion normal de stock no consulta las fichas individuales de Grilon3 ni descarga imagenes; solo lee esa cache local.

Las imagenes originales quedan en `public/assets/grilon3/` y `public/assets/filamentos3d/`. El listado usa miniaturas WebP generadas en `public/assets/thumbs/`; el popup de imagen usa la imagen original para ver mejor el color.

## GitHub Pages

El sitio publicado queda disponible en:

https://zogar89.github.io/CentraldeFilamentos/

GitHub Pages esta configurado con `build_type: workflow`. El workflow `.github/workflows/pages.yml` se puede correr manualmente con `workflow_dispatch` y tambien corre de lunes a viernes a las 12, 15, 18 y 21 UTC, que corresponden a las 09, 12, 15 y 18 hs de Argentina.

## Fuentes iniciales

- Filamentos3D
- Grupo Senz
- MundoInsumos

## Documentacion

- Spec de producto: `docs/superpowers/specs/2026-05-12-centraldefilamentos-design.md`
- Plan de implementacion: `docs/superpowers/plans/2026-05-12-centraldefilamentos-mvp.md`
- Handoff de sesion y preguntas pendientes: `docs/superpowers/session-handoff-2026-05-12.md`

## Proximo paso

Seguir mejorando la UI sobre la base Svelte y validar visualmente los flujos principales en mobile/desktop antes de cambios grandes.
