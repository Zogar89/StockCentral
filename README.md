# StockCentral

StockCentral centraliza stock online de proveedores de filamento 3D del AMBA para que usuarios de impresion 3D encuentren rapido quien tiene el material, color, marca y formato que necesitan.

## Estado actual

El proyecto esta en implementacion inicial del MVP.

Decisiones principales:

- Sitio estatico publico.
- Python para ingesta y normalizacion.
- GitHub Actions para actualizar stock 2 a 4 veces por dia en horario de oficina.
- GitHub Pages para publicar.
- Proveedores iniciales: Filamentos3D, Grupo Senz y MundoInsumos.
- UI en espanol argentino, compacta, mobile friendly y minimalista.

## Desarrollo local

```bash
python -m pip install -e ".[dev]"
python -m pytest -v --basetemp C:\tmp\pytest-stockcentral
python -m stockcentral.build_data --output public/data/stock.json
python -m stockcentral.generate_thumbnails --stock-json public/data/stock.json
python -m http.server 8000 -d public
```

Abrir `http://localhost:8000`.
La vista compacta de resumen queda en `http://localhost:8000/resumen.html`.

### Comandos

Instalar dependencias de desarrollo:

```bash
python -m pip install -e ".[dev]"
```

Ejecutar tests en Windows local:

```bash
python -m pytest -v --basetemp C:\tmp\pytest-stockcentral
```

Ejecutar tests en Linux o GitHub Actions:

```bash
python -m pytest -v
```

Generar datos para el sitio estatico:

```bash
python -m stockcentral.build_data --output public/data/stock.json
python -m stockcentral.generate_thumbnails --stock-json public/data/stock.json
```

Actualizar la cache local de metadatos e imagenes oficiales de Grilon3, solo cuando Grilon3 cambie o agregue filamentos:

```bash
python -m stockcentral.cache_grilon3_metadata --timeout-seconds 10 --max-workers 8
python -m stockcentral.build_data --output public/data/stock.json
python -m stockcentral.generate_thumbnails --stock-json public/data/stock.json
```

Si solo hace falta volver a descargar imagenes usando la cache existente, sin leer otra vez las fichas de producto:

```bash
python -m stockcentral.cache_grilon3_metadata --images-only --timeout-seconds 20
python -m stockcentral.build_data --output public/data/stock.json
python -m stockcentral.generate_thumbnails --stock-json public/data/stock.json
```

Levantar servidor estatico local:

```bash
python -m http.server 8000 -d public
```

## Datos

El frontend lee `public/data/stock.json`. En produccion, GitHub Actions genera ese archivo, genera las miniaturas y publica `public/` en GitHub Pages.

`public/data/stock.json` es salida generada. Evitar editarlo a mano: los cambios persistentes van en normalizacion, fuentes o caches de metadata, y luego se regenera con los comandos anteriores.

La cache `stockcentral/data/grilon3_metadata.json` se versiona en el repositorio. Guarda datos oficiales como Pantone, SKU, EAN y la ruta local de imagen. Las imagenes oficiales descargadas se versionan en `public/assets/grilon3/`. La actualizacion normal de stock no consulta las fichas individuales de Grilon3 ni descarga imagenes; solo lee esa cache local.

Las imagenes originales quedan en `public/assets/grilon3/` y `public/assets/filamentos3d/`. El listado usa miniaturas WebP generadas en `public/assets/thumbs/`; el popup de imagen usa la imagen original para ver mejor el color.

## GitHub Pages

El sitio publicado queda disponible en:

https://zogar89.github.io/StockCentral/

GitHub Pages esta configurado con `build_type: workflow`. El workflow `.github/workflows/pages.yml` se puede correr manualmente con `workflow_dispatch` y tambien corre de lunes a viernes a las 12, 15, 18 y 21 UTC, que corresponden a las 09, 12, 15 y 18 hs de Argentina.

## Fuentes iniciales

- Filamentos3D
- Grupo Senz
- MundoInsumos

## Documentacion

- Spec de producto: `docs/superpowers/specs/2026-05-12-stockcentral-design.md`
- Plan de implementacion: `docs/superpowers/plans/2026-05-12-stockcentral-mvp.md`
- Handoff de sesion y preguntas pendientes: `docs/superpowers/session-handoff-2026-05-12.md`

## Proximo paso

Completar el frontend estatico, validar visualmente en mobile/desktop y dejar el workflow de Pages publicando la app desde `public/`.
