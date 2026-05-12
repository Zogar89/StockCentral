# StockCentral - Handoff de sesion

Fecha: 2026-05-12

## Estado actual

- Repo publico creado: `https://github.com/Zogar89/StockCentral`.
- Rama de trabajo: `codex/stockcentral-mvp-foundation`.
- Ya existe scaffold Python con modelos, configuracion de proveedores, normalizacion conservadora y conector CSV para Google Sheets.
- Tests actuales relevantes pasan para modelos, proveedores, normalizacion y Google Sheets.
- El frontend estatico, build completo, scraper Filamentos3D, enriquecimiento/cache de imagenes Grilon3 y workflows de GitHub Actions siguen pendientes.
- GitHub Pages esta activado con GitHub Actions como source. URL reservada: `https://zogar89.github.io/StockCentral/`.
- La URL todavia no sirve la app final porque falta crear el workflow de Pages y el frontend/public build.

## Decisiones tomadas

- Proveedores iniciales:
  - MundoInsumos, Zona Norte, fuente Google Sheet gid `1981641819`: `https://docs.google.com/spreadsheets/d/1r-nKy4tRRtZ-5xwgxAcia8REDVW0Dv0h/edit?gid=1981641819#gid=1981641819`.
  - Grupo Senz, Zona Oeste, fuente Google Sheet gid `614179668`: `https://docs.google.com/spreadsheets/d/14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM/edit?gid=614179668#gid=614179668`.
  - Filamentos3D, Zona Sur, fuente HTML: `https://filamentos3d.com.ar/grilon3.php`.
- Orden manual de proveedores para la vista resumen: Zona Norte, Zona Oeste, Zona Sur.
- Las planillas de Grupo Senz y MundoInsumos tienen una sola hoja relevante para el MVP y son exportables como CSV publico.
- Stock significa carretes disponibles; mostrar stock como cantidad de carretes, no como kilos.
- En la vista resumen, una celda sin stock confiable debe verse como `0` cuando el dato es cero real.
- Valores negativos, vacios, formulas con error o raros se tratan como `unknown`/dato a revisar y no suman stock.
- Sin precios en el MVP.
- Sin filtro por zona por ahora.
- Sin filtro de cantidad minima en el MVP.
- Productos sin stock siempre visibles.
- Filtros del catalogo: material, variante, color, diametro, peso/kg, marca, proveedor y estado de stock.
- PLA queda destacado porque es el caso principal de busqueda.
- Producto agrupado por `material + variant + color + diameter_mm + weight_g + brand`.
- Colores especiales se mantienen separados.
- Productos Grilon3 deben linkear a pagina oficial cuando exista y traer imagen disponible desde `https://grilon3.com.ar/productos/`.
- Imagenes: cachearlas/copiar URLs durante el build; evitar depender de hotlinks cuando sea posible.
- 3N3 queda sin sitio oficial por ahora; no inventar links.
- Si no hay link oficial de fabricante, el titulo del producto queda sin link.
- Diseno minimalista estilo Apple como inspiracion: claro, compacto, rapido, sin copiar marca ni assets.
- Footer con fuentes, contactos disponibles, ultima actualizacion y estadisticas por proveedor en carretes.
- Boton de WhatsApp por proveedor/oferta con mensaje prearmado es una buena idea para implementar.
- El repositorio puede cambiar de nombre en el futuro, pero por ahora se sigue con `StockCentral`.

## Contactos oficiales encontrados

- Filamentos3D: `https://filamentos3d.com.ar/contactenos`, WhatsApp `+54 9 11 5464-8121`, mail `info@filamentos3d.com.ar`, direccion `Gonzalez Balcarce 2121 PB, Florencio Varela, Buenos Aires`.
- Grupo Senz: `https://gruposenz.com.ar/`, telefono `+54 11 3605-9099`, mail `info@gruposenz.com.ar`, direccion `Polo Comercial K41, Moreno, Buenos Aires`.
- MundoInsumos: `https://www.mundoinsumos.com.ar/`, WhatsApp filamentos `+54 11 6586-3008`, mail `info@mundoinsumos.com.ar`, direccion `Fray Mamerto Esquiu 2273, Munro, Vicente Lopez, Buenos Aires`.

## Archivos importantes

- `docs/superpowers/specs/2026-05-12-stockcentral-design.md`: especificacion de producto.
- `docs/superpowers/plans/2026-05-12-stockcentral-mvp.md`: plan ejecutable task-by-task para implementar el MVP.
- `docs/superpowers/session-handoff-2026-05-12.md`: este handoff.
- `stockcentral/providers.py`: configuracion de fuentes, gids y contactos.
- `stockcentral/connectors/google_sheet.py`: export/parsing CSV de Google Sheets.
- `tests/test_google_sheet.py`: fixtures y cobertura de parsing defensivo de sheets.

## Preguntas abiertas

- Ver si conviene sugerir variantes cercanas cuando no hay stock exacto del color/material.
- Definir cuando aparezcan datos de Zona Norte/otros proveedores si se agrega filtro por zona o se mantiene solo como etiqueta.
- Confirmar mas adelante si el nombre publico queda `StockCentral` o se renombra el repo/producto.

## Proximo paso sugerido

Seguir con el plan desde el conector HTML de Filamentos3D, luego enriquecimiento/cache de Grilon3, `build_data.py`, frontend estatico y workflows de GitHub Actions + Pages.
