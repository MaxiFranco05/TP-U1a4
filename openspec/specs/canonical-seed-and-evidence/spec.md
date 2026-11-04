# canonical-seed-and-evidence Specification

## Purpose
TBD - created by archiving change c-17-seed-casos-prueba-y-despliegue-docker. Update Purpose after archive.

## Requirements

### Requirement: Script de Seed Canónico del Parcial
El script `seed.py` en la raíz SHALL vaciar las tablas con `RESTART IDENTITY CASCADE` y cargar el estado inicial exacto exigido por la consigna del Parcial (5 usuarios, catálogo del TP, 3 clientes, Venta 1 de $69000.00, 7 movimientos de stock y 1 evento de seguridad).

#### Scenario: Ejecución de seed.py en base vacía o existente
- **WHEN** se ejecuta `python seed.py`
- **THEN** la base queda poblada con exactamente 5 usuarios, 5 libros, 3 clientes, 1 venta, 7 movimientos de stock y 1 evento de seguridad.

#### Scenario: Invariante de stock tras el seed
- **WHEN** se consulta el stock de cada uno de los 5 libros tras correr `seed.py`
- **THEN** el campo `stock` de cada libro coincide exactamente con la suma de los valores `cantidad` de sus filas en `movimiento_stock`.

### Requirement: Suite de Pruebas de Casos C-01 a C-16
El proyecto SHALL incluir archivos `.http` comentados en `test/` demostrando la ejecución exitosa de los casos de evaluación `C-01` a `C-16` según la consigna, soportando sesiones concurrentes con `# @name` y `# @no-cookie-jar`.

#### Scenario: Demostración de casos C-01 a C-16
- **WHEN** un evaluador ejecuta las peticiones `.http` en el orden establecido
- **THEN** cada caso devuelve el código HTTP esperado (200, 201, 204, 401, 403, 404, 409, 422) y el formato JSON documentado.

### Requirement: Evidencia de Restricción de Sólo-Agregado
El proyecto SHALL incluir el script `test/solo_agregado.sql` que intente ejecutar sentencias `UPDATE` y `DELETE` sobre la tabla `movimiento_stock`, demostrando que el disparador de base de datos las rechaza con error. La salida o captura de `psql` SHALL guardarse en `evidencia/`.

#### Scenario: Intento de modificación o borrado de movimientos
- **WHEN** se ejecuta `test/solo_agregado.sql` contra la base de datos
- **THEN** PostgreSQL rechaza tanto el `UPDATE` como el `DELETE` con la excepción del trigger `trg_movimiento_stock_solo_agregado`.
