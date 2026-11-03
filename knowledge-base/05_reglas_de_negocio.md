# Reglas de Negocio

> **Numeración del Parcial vs TP**: En la consigna del **Parcial (Capítulos 1 a 6)** las reglas de negocio se numeran de nuevo de **RN-01 a RN-16** y reemplazan a las del TP en lo que se superponen. Siguen vigentes, además, las restricciones heredadas del TP (`CHECK precio > 0`, `CHECK stock >= 0`, `CHECK orden >= 1`, `CHECK cantidad > 0`, `PerfilCliente` único por cliente y búsqueda de libros por título case-insensitive con parámetros ligados).

---

## Reglas de Negocio Vigentes — Parcial (RN-01 a RN-16)

| Código | Enunciado oficial | Garante esperado | Caso de prueba |
|---|---|---|---|
| **RN-01** | El correo de un usuario, el de un cliente, el nombre de una editorial y el de un género son únicos. El ISBN de un libro es único entre los que no están dados de baja. | `UNIQUE` e índice único parcial `(isbn) WHERE borrado_en IS NULL` en la base; `409` con mensaje propio. | `C-02`, `C-13` |
| **RN-02** | El auto-registro (`POST /auth/registro`) crea el usuario, su rol `CLIENTE` y su ficha de cliente: o quedan las tres filas, o ninguna. Si ya existe un cliente con ese correo, el registro da `409` y no se apropia de esa ficha. | Un solo Unit of Work (`UsuariosUnitOfWork`). | `C-02` |
| **RN-03** | Un usuario tiene a lo sumo una asignación abierta por rol. | Índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`; `409`. | `C-07` |
| **RN-04** | Los permisos se deciden con los roles vigentes en la base (`revocada_en IS NULL` y sin vencer), en cada petición. Los roles que trae el token son informativos. | Dependencia `requiere_rol` que consulta `asignacion_rol` en cada request. | `C-06`, `C-07` |
| **RN-05** | Un administrador no puede revocarse su propio rol `ADMIN`, y el sistema nunca queda sin administradores vigentes. | Comprobación en el servicio antes de revocar; `409`. | `C-08` |
| **RN-06** | Mientras un usuario tenga el cambio de contraseña pendiente (`debe_cambiar_password=True`), sólo puede usar las rutas de `/auth` y las que no piden sesión. | Dos grupos de rutas en `app/main.py` (`abierto` y `protegido`); `403`. | `C-09` |
| **RN-07** | Después de 5 intentos fallidos con el mismo correo desde la misma dirección IP en 60 segundos, el login responde `429` sin verificar la contraseña. Un login correcto reinicia la cuenta: los fallos anteriores siguen en la tabla, pero dejan de contar. | Conteo sobre `intento_acceso` (desde el último éxito en los últimos 60 s); encabezado `Retry-After`. | `C-05` |
| **RN-08** | El login responde lo mismo (`401` con idéntico mensaje), y tarda lo mismo, exista o no el correo. | Verificación `bcrypt` contra el hash del usuario o contra el hash ficticio calculado en `lifespan` (`app.state`). | `C-04` |
| **RN-09** | Una venta nace con sus renglones (al menos uno, sin libros repetidos), con el precio de cada renglón copiado del libro y el total calculado por el servidor. Las ventas no se modifican. | Validación en DTO (`422`); el precio, fecha y total nunca viajan en el cuerpo de entrada (`extra="forbid"`); no hay `PATCH` de ventas. | `C-10` |
| **RN-10** | Registrar una venta descuenta el stock de cada libro y deja un movimiento por renglón. Si un libro no alcanza, **no queda ninguna de esas escrituras**: ni la venta, ni los renglones, ni los descuentos, ni los movimientos. | Un solo Unit of Work (`VentasUnitOfWork`); `409`. | `C-10`, `C-11`, `C-12` |
| **RN-11** | El stock de un libro sólo cambia a través de movimientos: el alta con `stock_inicial`, la reposición (`POST /libros/{id}/reponer`) y la venta (`POST /ventas`). No se edita por `PATCH`. | Punto único de escritura de stock + `extra="forbid"` en `LibroUpdate` (`422`). Siempre se cumple `libro.stock == SUM(movimiento_stock.cantidad)`. | `C-10`, `C-11`, `C-13`, `C-16` |
| **RN-12** | `movimiento_stock` es de sólo agregado: nadie puede modificar ni borrar sus filas. | Disparador (`TRIGGER`) en PostgreSQL, instalado por la **Migración 004** escrita a mano. | `C-14` |
| **RN-13** | Un libro dado de baja (`borrado_en IS NOT NULL`) deja de aparecer en el catálogo y no se puede vender ni reponer (`409`), pero sus datos se conservan y las ventas anteriores lo siguen mostrando. | `SoftDeleteRepository[Libro]` + `get_by_id_including_deleted` / relación en detalle de ventas; `409` al vender o reponer. | `C-12`, `C-13` |
| **RN-14** | Lo propio sólo pide estar autenticado: un cliente ve sus ventas y ninguna otra. | `GET /mis-ventas` y comprobación de personal o cliente dueño en el servicio de `GET /ventas/{id}`; `403` si es ajena. | `C-06` |
| **RN-15** | Ningún error devuelve al cliente texto interno de la base (nombres de tablas, constraints, trazas SQL). Ninguna entrada inválida termina en un `500` (incluyendo contraseñas de más de 72 bytes UTF-8). | Traducción de `IntegrityError` a `409` con mensaje propio; validación en contratos (`extra="forbid"`, límite 72 bytes UTF-8 → `422`). | `C-01`, `C-02`, `C-16` |
| **RN-16** | Cada alta de personal (`POST /usuarios`), cambio de rol (`POST/DELETE /usuarios/{id}/roles`) y cambio de contraseña (`POST /auth/cambiar-password`) deja una línea en `evento_seguridad`, en la **misma transacción** que el cambio. | Un solo Unit of Work (`UsuariosUnitOfWork`). | `C-07`, `C-09` |

---

## Reglas Transversales Adicionales (Consigna Ej. 3, Ej. 4, Ej. 5)

- **Paginación con envoltorio (`app/core/paginacion.py`)**:
  - Todo listado paginado recibe `page >= 1` (defecto `1`) y `size` entre `1` y `100` (defecto `20`) → `422` si no cumple.
  - Devuelve `{items, total, page, size, pages}`.
  - Si `total == 0`, hay `1` página vacía (`pages: 1`, `items: []`).
  - Si `page > pages`, responde **`422`** con el mensaje exacto: `«La página {page} no existe: hay {pages}»` (`C-16`).
  - `total` cuenta con los mismos filtros que la página (`C-16`).
- **Validación de vencimiento de rol (`POST /usuarios/{id}/roles`)**:
  - `vence_en` es opcional, pero si se envía debe incluir zona horaria (`tzinfo` no nulo) y ser una fecha en el futuro → si no tiene zona horaria o ya pasó, responde **`422`** (no `409`, `C-07`).
- **Límite de 72 bytes en contraseñas**:
  - Todo campo contraseña que termina en `bcrypt` (registro, login, alta de personal, contraseña actual y nueva en cambio de clave) valida `len(v.encode("utf-8")) <= 72` en el contrato de entrada → `422` si supera (evita `ValueError` / `500` en `bcrypt>=5`).

---

## Referencia Histórica: Numeración Original del TP (Capítulos 1 a 4 — Carpeta `despliegue/`)

En la entrega de `despliegue/` (que contiene el TP de los capítulos 1 a 4 intacto) rigen las reglas originales del TP:
- **TP RN-01**: ISBN único (`UNIQUE` simple en `libro.isbn` → `409`).
- **TP RN-02**: Email de cliente único (`409`).
- **TP RN-03**: `precio > 0` y `stock >= 0` (`CHECK` + DTO).
- **TP RN-04 a RN-08**: Venta con renglones anidados, `>= 1` renglón sin repetidos (`422`), precio copiado del libro, total calculado por el servidor, sin `PATCH` de ventas.
- **TP RN-09**: Máximo un perfil por cliente (`409`).
- **TP RN-10**: Paginación `limit` (1–100, def. 20) y `offset` (`>= 0`).
- **TP RN-11**: Filtro de libros por título case-insensitive con parámetros ligados.
- **TP RN-12**: Ningún error devuelve texto interno de la base.
