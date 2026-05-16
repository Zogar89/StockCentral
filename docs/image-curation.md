# Curacion de imagenes de filamentos

Este documento fija el protocolo para tocar imagenes de productos. La regla principal es que las fotos se curan de a una, con supervision humana, y nunca con un reemplazo masivo automatico.

## Regla operativa

- No correr scripts masivos que refresquen o reemplacen imagenes del catalogo completo sin aprobacion explicita.
- Comandos bloqueados para curacion puntual: `python -m centraldefilamentos.cache_grilon3_metadata`, `python -m centraldefilamentos.cache_filamentos3d_metadata`, sus variantes `--images-only`, `centraldefilamentos/update_grilon3_images.py`, `centraldefilamentos/update_filamentos3d_images.py`, y cualquier flujo que reescriba caches completas.
- Para arreglar una foto, trabajar solo sobre el `product_id` indicado por Gabriel.
- Mostrar candidatos antes de aplicar: idealmente 3 imagenes con origen, URL, dimensiones si estan disponibles, y la imagen actual.
- Aplicar solo la opcion elegida. No inferir ni propagar esa imagen a productos parecidos, colores vecinos, otros materiales o presentaciones.
- Despues de aplicar, verificar el producto tocado y productos sentinela no relacionados. ABS debe quedar como sentinela cuando se tocan fotos Grilon3, porque una carga masiva anterior lo rompio.

## Flujo manual por producto

1. Identificar el `product_id` exacto en `public/data/stock.json`.
2. Revisar la imagen actual y su `thumbnail_url`.
3. Recolectar candidatos solo desde la URL puntual del producto o desde URLs indicadas por el usuario.
4. Presentar candidatos para que Gabriel elija.
5. Descargar o referenciar solo la imagen seleccionada.
6. Actualizar unicamente los campos necesarios del producto/cache correspondiente:
   `image_url`, `image_remote_url` si aplica, `thumbnail_url`, `image_source`, `manufacturer_product_url` o `provider_product_url` si corresponde.
7. Regenerar solo la miniatura necesaria cuando la imagen es local.
8. Revisar diff antes de publicar. El diff esperado debe estar limitado al producto, su asset y su miniatura.

## Reglas actuales del codigo

Estas reglas no alcanzan para publicar sin supervision, pero explican que hace hoy el codigo cuando encuentra imagenes:

- Grilon3 no enriquece productos tipo sampler ni lapiz 3D. La funcion `_is_sampler_or_3d_pen_item` evita aplicar fotos oficiales a esos items.
- Grilon3 combina datos del catalogo con la cache local. Busca por clave exacta, por clave sin diametro y por clave historica.
- Si una metadata de Grilon3 parece de `megafill` o `maxicarrete`, el codigo borra URL, imagen, SKU y EAN para productos de menos de 2.5 kg.
- Si el nombre de archivo de la imagen detecta un color distinto al color esperado, el codigo quita la imagen de esa metadata.
- La deteccion de color sale de `COLOR_RULES` y mira `image_url` / `image_remote_url`. Es util como filtro, pero puede fallar con nombres genericos o imagenes mal nombradas.
- El parser de fichas Grilon3 solo acepta imagenes dentro de `/wp-content/uploads/`.
- En Grilon3 se descartan candidatos que parezcan `favicon`, `logo`, `auspicia`, `iso`, `tabla`, `perfil` o `icon`.
- En Grilon3 se prefiere la galeria WooCommerce del producto antes que otras imagenes de la pagina.
- En Grilon3 se puntuan mejor archivos `600x600`, `350x350` y nombres con `web`; se penalizan imagenes genericas tipo `wp-post-image`, nombres numericos, piezas, texturas o renders no claramente de bobina.
- Filamentos3D solo aplica fotos de provider a productos marca `3N3`.
- Filamentos3D descarta imagenes que parezcan logo, placeholder, default product, WhatsApp o modulos del sitio.
- Filamentos3D descarta imagenes dentro de bloques de productos relacionados, miniaturas, accesorios o cross-selling.
- Las miniaturas se generan solo para imagenes locales con ruta `assets/...`; una URL remota no genera `assets/thumbs/...`.

## Propuesta de pagina local human-in-the-loop

Pendiente de implementar con aprobacion previa. La idea es una pagina local de curacion que no publique nada automaticamente:

- Buscar producto por nombre o `product_id`.
- Mostrar imagen actual, metadata actual y productos sentinela.
- Cargar hasta 3 candidatos por URL puntual.
- Mostrar cada candidato con vista previa, fuente, URL remota, nombre de archivo y dimensiones.
- Elegir una opcion con un boton claro.
- Generar un patch local chico, revisable, sin tocar otros productos.
- Dejar registro de quien eligio la imagen y de que URL salio.

El objetivo de esa pagina es que la decision visual sea humana y que el asistente solo haga la parte mecanica: descargar, generar miniatura, aplicar el patch y publicar.
