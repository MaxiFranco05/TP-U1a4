# Modelo de Datos

Nombres de tablas y columnas **obligatorios** (los usan los casos de prueba y la corrección). Se pueden agregar columnas, no quitar ni renombrar.

## Dominios

- **Catálogo**: `editorial`, `genero`, `autor`, `libro`, `libro_autor` (objeto de asociación).
- **Clientes**: `cliente`, `perfil_cliente` (uno a uno).
- **Ventas**: `venta`, `renglon_venta` (composición).

## ERD (textual)

```
editorial 1───* libro *───1 genero (opcional)
libro *───* autor vía libro_autor (rol, orden)
cliente 1───0..1 perfil_cliente
cliente 1───* venta 1───* renglon_venta *───1 libro
```

Tipos: Libro–Editorial agregación · Libro–Género agregación opcional · Libro–Autor muchos a muchos con datos · Cliente–Perfil uno a uno · Venta–Cliente asociación · Venta–Renglón composición · Renglón–Libro asociación. Navegación: `libro.autorias[i].autor`.

## Entidades

### editorial
- Atributos: `id`, `nombre`, `pais`.
- Constraints: `nombre` UNIQUE.
- Relaciones: 1 a * con `libro`.

### genero
- Atributos: `id`, `nombre`.
- Constraints: `nombre` UNIQUE.
- Relaciones: 1 a * opcional con `libro`.

### autor
- Atributos: `id`, `nombre`, `nacionalidad`.
- Relaciones: * a * con `libro` vía `libro_autor`.

### libro
- Atributos: `id`, `isbn`, `titulo`, `precio` (NUMERIC 10,2), `stock`, `editorial_id`, `genero_id` (nullable).
- Constraints: `isbn` UNIQUE; CHECK `precio > 0`; CHECK `stock >= 0`.
- Relaciones: * a 1 con `editorial` y `genero`; * a * con `autor` vía `libro_autor`.

### libro_autor (objeto de asociación — entidad propia)
- Atributos: `libro_id`, `autor_id`, `rol`, `orden`.
- Constraints: PK (`libro_id`, `autor_id`); CHECK `orden >= 1`; CHECK `rol` en (autor, coautor, traductor, ilustrador).

### cliente
- Atributos: `id`, `nombre`, `email`.
- Constraints: `email` UNIQUE.
- Relaciones: 1 a 0..1 con `perfil_cliente` (`Cliente.perfil` devuelve objeto, no lista); 1 a * con `venta`.

### perfil_cliente
- Atributos: `id`, `cliente_id`, `telefono`, `direccion`.
- Constraints: `cliente_id` UNIQUE.

### venta
- Atributos: `id`, `cliente_id`, `fecha` (timestamptz), `total` (NUMERIC 12,2).
- Constraints: CHECK `total >= 0`.
- Relaciones: * a 1 con `cliente`; 1 a * con `renglon_venta` (composición).

### renglon_venta
- Atributos: `id`, `venta_id`, `libro_id`, `cantidad`, `precio_unitario` (NUMERIC 10,2).
- Constraints: CHECK `cantidad > 0`; CHECK `precio_unitario > 0`.
- Relaciones: * a 1 con `venta` y con `libro`.

Toda FK lleva índice explícito (PostgreSQL no lo crea solo) y `Relationship(back_populates=...)` en ambos extremos. Dinero siempre `Decimal`.

## Seed data inicial

Script o comando que deja la base en estado conocido: al menos editoriales, géneros, autores, libros con autorías, un cliente con perfil y una venta de ejemplo, de modo que los `.http` corran de forma reproducible.
