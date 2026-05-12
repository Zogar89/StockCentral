# StockCentral - Diseno de MVP

Fecha: 2026-05-12

## Resumen

StockCentral sera una aplicacion web publica para usuarios de impresion 3D del AMBA. Su objetivo es centralizar el stock online de distintos proveedores de filamento para que una persona pueda encontrar rapidamente que proveedor tiene el material, color, formato o marca que necesita.

El MVP sera un sitio estatico servido con GitHub Pages. Python correra en GitHub Actions para leer fuentes externas, normalizar datos y generar un archivo JSON publico que consume el frontend.

## Objetivos

- Publicar una pagina simple y rapida para consultar stock de filamentos.
- Centralizar proveedores de Zona Sur, Zona Oeste y Zona Norte.
- Mostrar todos los productos, incluidos los que no tienen stock.
- Priorizar la experiencia de busqueda por filtros, con PLA destacado porque es el caso de uso mayoritario.
- Mantener la ingesta y normalizacion separadas del frontend para facilitar una futura migracion a backend si hace falta.

## Fuera de alcance inicial

- Precios.
- Usuarios, cuentas o favoritos sincronizados.
- Alertas de reposicion.
- Historial de stock.
- Panel de administracion.
- Filtro por zona.
- Actualizacion en tiempo real desde la web.

## Arquitectura

La solucion se divide en cinco piezas:

- `ingest`: conectores por proveedor que descargan y parsean fuentes externas.
- `normalize`: reglas para detectar material, variante, color, diametro, peso y marca.
- `build_data`: proceso que genera el JSON final para el frontend.
- `frontend`: sitio estatico con filtros y resultados agrupados.
- `.github/workflows`: ejecucion programada de GitHub Actions y publicacion en GitHub Pages.

El frontend no consulta directamente las fuentes de los proveedores. Solo consume el JSON generado por el pipeline. Esto mantiene la pagina rapida, reduce fallos visibles para el usuario y deja el modelo de datos preparado para un backend futuro.

## Fuentes iniciales

### Filamentos3D

- Zona: Zona Sur.
- Fuente de stock: `https://filamentos3d.com.ar/grilon3.php`.
- Tipo de conector: scraping HTML.
- Link visible del proveedor: sitio/fuente publica del proveedor.

### Grupo Senz

- Zona: Zona Oeste.
- Fuente de stock: Google Sheet `https://docs.google.com/spreadsheets/d/14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM`.
- Tipo de conector: exportacion CSV de Google Sheets si esta disponible publicamente.
- Link visible del proveedor: fuente o sitio publico disponible.

### MundoInsumos

- Zona: Zona Norte.
- Fuente de stock: Google Sheet `https://docs.google.com/spreadsheets/d/1r-nKy4tRRtZ-5xwgxAcia8REDVW0Dv0h/edit?gid=1981641819#gid=1981641819`.
- GID inicial: `1981641819`.
- Tipo de conector: exportacion CSV de Google Sheets si esta disponible publicamente.
- Link visible del proveedor: `https://www.mundoinsumos.com.ar/`.

## Actualizacion

GitHub Actions ejecutara la ingesta entre 2 y 4 veces por dia en horario de oficina. Una configuracion inicial razonable es correr en dias habiles a las 09:00, 12:00, 15:00 y 18:00 hora Argentina.

El pipeline debe:

- Descargar cada fuente.
- Parsear registros crudos por proveedor.
- Normalizar campos comunes.
- Agrupar productos equivalentes.
- Generar el JSON publico.
- Publicar el sitio actualizado en GitHub Pages.

Si una fuente falla, el resto de las fuentes deben seguir publicandose. El JSON debe incluir metadata de estado por proveedor para que la UI pueda mostrar ultima actualizacion y errores de manera simple.

## Modelo de datos

El JSON publico tendra dos secciones principales:

- `products`: productos agrupados para mostrar en la UI.
- `sources`: metadata por proveedor.

### Producto agrupado

Campos esperados:

- `id`: identificador estable generado a partir de los campos normalizados.
- `material`: PLA, PETG, ABS, TPU, HIPS, Nylon u otros.
- `variant`: PLA+, silk, mate, boutique, astra, pro, flex, wood, galaxy u otras variantes cuando apliquen.
- `color`: color normalizado.
- `diameter_mm`: diametro detectado, principalmente `1.75`.
- `weight_g`: peso detectado, principalmente `1000`.
- `brand`: marca del filamento, por ejemplo `3N3` o `Grilon3`.
- `display_name`: nombre legible para la UI.
- `offers`: lista de ofertas/proveedores para ese producto.

### Oferta por proveedor

Campos esperados:

- `source_id`: identificador del proveedor.
- `provider_name`: nombre del proveedor.
- `provider_zone`: Zona Sur, Zona Oeste o Zona Norte.
- `provider_url`: URL publica para que el usuario pueda ir al proveedor.
- `original_name`: nombre original en la fuente.
- `stock_quantity`: cantidad numerica si esta disponible.
- `stock_status`: `in_stock`, `out_of_stock` o `unknown`.
- `source_url`: URL exacta de la fuente o producto cuando exista.
- `updated_at`: fecha/hora de actualizacion de ese dato si se conoce.

### Metadata de fuente

Campos esperados:

- `id`.
- `name`.
- `zone`.
- `homepage_url`.
- `source_url`.
- `last_success_at`.
- `last_attempt_at`.
- `status`: `ok` o `error`.
- `error_message`: mensaje corto si fallo la ultima actualizacion.

## Normalizacion y agrupacion

El agrupamiento principal sera por:

`material + variant + color + diameter_mm + weight_g + brand`

El MVP prioriza productos de `1.75 mm` y `1 kg`. Otros formatos, como 500 g, 750 g, 2.5 kg o 5 kg, se muestran pero no se fuerzan dentro del mismo grupo si eso puede confundir al usuario.

La normalizacion debe ser conservadora. Si un producto no se puede clasificar con confianza, se muestra como producto separado usando su nombre original o un nombre derivado simple. Es preferible duplicar visualmente un caso dudoso antes que mezclar mal colores, pesos o variantes.

## Interfaz

La UI sera un catalogo filtrable. No sera una landing page ni un buscador puro.

Comportamiento inicial:

- Mostrar todos los productos.
- Destacar el filtro PLA.
- Ordenar productos PLA primero.
- Mostrar productos sin stock con estado claro.
- No mostrar precios.
- Mostrar zona junto al proveedor, sin filtro por zona.
- Mostrar ultima actualizacion general y, cuando este disponible, por proveedor.

Filtros del MVP:

- Material.
- Variante.
- Color.
- Diametro.
- Peso / kg.
- Marca.
- Proveedor.
- Estado de stock: todos / con stock / sin stock, con `todos` por defecto.

La UI tambien tendra busqueda de texto simple para encontrar rapidamente terminos como `negro`, `pla+`, `grilon`, `3n3` o `1kg`.

Cada producto agrupado mostrara:

- Nombre normalizado.
- Atributos principales.
- Lista de proveedores/ofertas.
- Stock por proveedor.
- Nombre original de la fuente cuando ayude a verificar coincidencia.
- Link en el nombre del proveedor.

## Manejo de errores

El sistema debe tolerar fallos parciales:

- Un proveedor caido no debe romper toda la actualizacion.
- La UI debe poder mostrar que una fuente no actualizo.
- Si existe un ultimo dataset valido, se debe preferir conservarlo antes que publicar un JSON vacio por error.
- Los productos sin stock nunca deben desaparecer solo por estar en cero.

## Pruebas

Pruebas iniciales recomendadas:

- Tests de normalizacion con nombres reales de cada proveedor.
- Tests de conectores usando fixtures HTML/CSV.
- Test del build para verificar que `stock.json` respeta el esquema esperado.
- Test de que productos sin stock se conservan.
- Test de ordenamiento inicial con PLA primero.
- Test de filtros principales sobre un dataset fixture.

## Decisiones aprobadas

- Aplicacion publica.
- Sitio estatico como enfoque del MVP.
- Python para ingesta y normalizacion.
- GitHub Actions para actualizacion programada.
- GitHub Pages para publicacion.
- Solo espanol argentino.
- Enfoque local AMBA.
- Proveedores iniciales: Filamentos3D, Grupo Senz y MundoInsumos.
- Sin precios en el MVP.
- Sin filtro por zona en el MVP.
- Productos sin stock visibles.
- Agrupacion normalizada por atributos del filamento.
