# Reglas de Negocio

Códigos originales de la consigna (RN-01 a RN-12) — se conservan para trazabilidad directa con el enunciado y los casos de prueba.

## Dominio: Catálogo

- **RN-01**: el ISBN de un libro es único — garante: UNIQUE en la base; violación → 409.
- **RN-03**: el precio de un libro es mayor que cero y el stock nunca es negativo — garante: CHECK en la base + validación del DTO.
- **RN-11**: el listado de libros se puede filtrar por parte del título, sin distinguir mayúsculas — garante: parámetro ligado, nunca SQL armado con texto.

## Dominio: Ventas

- **RN-04**: una venta se crea con sus renglones (los datos de cada renglón viajan dentro del cuerpo del alta; no existe alta de renglones por separado) — garante: DTO anidado; los renglones se agregan a `venta.renglones`.
- **RN-05**: una venta tiene al menos un renglón y un mismo libro no aparece en dos renglones — garante: validación del DTO; violación → 422.
- **RN-06**: el precio de cada renglón se copia del libro al registrar la venta y no cambia aunque después cambie el precio del libro — garante: el servidor lo lee de la base; nunca viaja en el DTO.
- **RN-07**: el total de la venta lo calcula el servidor como suma de cantidad × precio unitario — garante: no viaja en el DTO.
- **RN-08**: las ventas no se modifican (registran un hecho) — garante: no hay PATCH de ventas.

## Dominio: Clientes

- **RN-02**: el email de un cliente es único — garante: UNIQUE en la base; violación → 409.
- **RN-09**: un cliente tiene como máximo un perfil — garante: UNIQUE en `perfil_cliente.cliente_id`; violación → 409.

## Dominio: Excepciones globales (transversales)

- **RN-10**: todo listado se pagina con `limit` (1 a 100, defecto 20) y `offset` (desde 0) — garante: restricciones en `Query`; violación → 422.
- **RN-12**: ningún error devuelve texto interno de la base (tablas, restricciones, trazas) — garante: traducción de `IntegrityError` a mensaje propio en el service.
