# Actores y Roles

> **Trazabilidad TP vs Parcial**: En el TP de los capítulos 1 a 4 (`C-01` a `C-08`, y en la carpeta `despliegue/`) no existía autenticación ni autorización y todas las rutas eran públicas. En el **Parcial (Capítulos 1 a 6, `C-09` a `C-17`)** se incorpora el modelo completo de identidad, roles con vigencia en base de datos y control de acceso por grupos de rutas.

---

## Actores del sistema

| Actor | Tipo | Descripción y responsabilidades |
|---|---|---|
| **Visitante (Cualquiera)** | Humano no autenticado | Consulta estado de salud (`/health/*`), navega el catálogo público (`GET /libros`, `/editoriales`, `/generos`, `/autores/{id}/libros`), se registra (`POST /auth/registro`) o inicia sesión (`POST /auth/login`). |
| **Cliente (`CLIENTE`)** | Usuario autenticado | Se registra por la web (creando usuario + rol `CLIENTE` + ficha `Cliente` en un solo UoW) o ya existe en el seed (`ana@example.com`). Consulta sus propias compras en `GET /mis-ventas` y el detalle de sus ventas en `GET /ventas/{id}` (recibe `403` si intenta ver una venta ajena). |
| **Vendedor (`VENDEDOR`)** | Personal autenticado | Dado de alta por un administrador con contraseña provisoria (`debe_cambiar_password=True`). Una vez cambiada su clave, gestiona clientes y perfiles en el mostrador y registra y consulta todas las ventas (`POST /ventas`, `GET /ventas`, `GET /ventas/{id}`). |
| **Administrador (`ADMIN`)** | Personal autenticado | Mantiene el catálogo (altas, ediciones, bajas lógicas de libros), repone stock y consulta movimientos, da de alta al personal (`POST /usuarios`), asigna y revoca roles con vigencia (`POST/DELETE /usuarios/{id}/roles`) respetando la autoprotección (RN-05), audita eventos de seguridad (`GET /eventos`) y tiene acceso también a las operaciones de clientes y ventas. |
| **Sistema (`SISTEMA`)** | Actor interno | Actor textual (`"SISTEMA"`) que deja registro en `evento_seguridad` durante la carga de datos iniciales en `seed.py` (`"Carga de los datos iniciales"`). |
| **Docente / Corrector** | Evaluador | Ejecuta migraciones Alembic, corre `python seed.py`, ejecuta `test/*.http` (`C-01` a `C-16`) y `test/solo_agregado.sql`, e inspecciona el contenedor desplegado en el VPS (`D-01` a `D-08`). |

---

## Modelo de Roles y Vigencia en Base de Datos

- Los roles válidos están restringidos por un `CHECK` en `asignacion_rol.rol` a: `'ADMIN'`, `'VENDEDOR'`, `'CLIENTE'`.
- La tabla `usuario` **no tiene columna `rol`**: los roles de un usuario son las filas de `asignacion_rol` que están **vigentes** en el momento de la consulta:
  - `revocada_en IS NULL`
  - y `(vence_en IS NULL OR vence_en > now())`
- **Autorización en cada petición (RN-04)**: el JWT firmado incluye `sub`, `exp` y los `roles` vigentes al momento de emitirlo, pero los roles del token son **sólo informativos** (expuestos en `GET /auth/yo`). La dependencia `requiere_rol` consulta `asignacion_rol` en la base de datos en cada petición usando la misma sesión que el Unit of Work. Así, revocar un rol quita el permiso de inmediato a una sesión ya abierta sin esperar a que venza el token (`C-07`).
- **Historial de roles**: revocar un rol (`DELETE /usuarios/{id}/roles/{rol}`) escribe `revocada_en = now()` y **nunca borra la fila**. Reasignar un rol cuyo vencimiento ya pasó cierra la fila anterior (`revocada_en`) y abre una fila nueva, preservando el índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL` (RN-03).
- **Autoprotección (RN-05)**: un administrador no puede revocarse su propio rol `ADMIN`, y el sistema nunca puede quedar sin al menos un administrador vigente (ambos casos responden `409`, `C-08`).

---

## Dos Grupos de Rutas y Cambio Obligatorio de Contraseña (RN-06)

En `app/main.py` las rutas se organizan en **dos grupos**:

1. **Grupo Abierto**:
   - No exige el control de cambio obligatorio de contraseña.
   - Incluye rutas sin sesión (`/health/*`, `/auth/registro`, `/auth/login`, `/auth/logout`, lecturas públicas de `/libros`, `/editoriales`, `/generos`, `/autores/{id}/libros`) y rutas de `/auth` que sí piden usuario autenticado pero deben ser accesibles cuando `debe_cambiar_password=True` (`GET /auth/yo`, `POST /auth/cambiar-password`).
2. **Grupo Protegido**:
   - Lleva montada **una sola vez** a nivel de grupo/router la dependencia que verifica `usuario_actual.debe_cambiar_password`: si es `True`, rechaza con `403 Forbidden` antes de ejecutar cualquier ruta protegida (`C-09`).
   - Cuando el usuario ejecuta `POST /auth/cambiar-password`, `debe_cambiar_password` pasa a `False` y **la misma cookie de sesión ya abierta sirve inmediatamente** para usar las rutas protegidas sin volver a iniciar sesión (`C-09`).

---

## Matriz RBAC Completa de Endpoints

| Grupo | Método | Ruta | Quién puede acceder | Códigos de respuesta |
|---|---|---|---|---|
| Abierto | `GET` | `/health/live` | Cualquiera | `200` |
| Abierto | `GET` | `/health/ready` | Cualquiera | `200, 503` |
| Abierto | `POST` | `/auth/registro` | Cualquiera | `201, 409, 422` |
| Abierto | `POST` | `/auth/login` | Cualquiera | `200, 401, 422, 429` |
| Abierto | `POST` | `/auth/logout` | Cualquiera | `200` |
| Abierto | `GET` | `/auth/yo` | Autenticado (incluso con cambio de clave pendiente) | `200, 401` |
| Abierto | `POST` | `/auth/cambiar-password` | Autenticado (incluso con cambio de clave pendiente) | `200, 401, 422` |
| Abierto | `GET` | `/libros` (`page, size, titulo, genero_id`) | Cualquiera | `200, 422` |
| Abierto | `GET` | `/libros/{id}` | Cualquiera | `200, 404, 422` |
| Abierto | `GET` | `/editoriales`, `/generos` (`page, size`) | Cualquiera | `200, 422` |
| Abierto | `GET` | `/editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` | Cualquiera | `200, 404` |
| Protegido | `POST` | `/usuarios` | `ADMIN` | `201, 401, 403, 409, 422` |
| Protegido | `GET` | `/usuarios/{id}/roles` | `ADMIN` | `200, 401, 403, 404` |
| Protegido | `POST` | `/usuarios/{id}/roles` | `ADMIN` | `201, 401, 403, 404, 409, 422` |
| Protegido | `DELETE` | `/usuarios/{id}/roles/{rol}` | `ADMIN` | `200, 401, 403, 404, 409` |
| Protegido | `GET` | `/eventos` (`page, size`) | `ADMIN` | `200, 401, 403, 422` |
| Protegido | `POST` | `/editoriales`, `/generos`, `/autores` | `ADMIN` | `201, 401, 403, 409, 422` |
| Protegido | `PATCH` | `/editoriales/{id}`, `/autores/{id}` | `ADMIN` | `200, 401, 403, 404, 409, 422` |
| Protegido | `POST` | `/libros` (con `autores` y `stock_inicial`) | `ADMIN` | `201, 401, 403, 409, 422` |
| Protegido | `PATCH` | `/libros/{id}` (título y precio; sin `stock`) | `ADMIN` | `200, 401, 403, 404, 409, 422` |
| Protegido | `DELETE` | `/libros/{id}` (baja lógica) | `ADMIN` | `204, 401, 403, 404` |
| Protegido | `POST` | `/libros/{id}/reponer` | `ADMIN` | `200, 401, 403, 404, 409, 422` |
| Protegido | `GET` | `/libros/{id}/movimientos` | `ADMIN` | `200, 401, 403, 404` |
| Protegido | `POST` | `/clientes` | `VENDEDOR`, `ADMIN` | `201, 401, 403, 409, 422` |
| Protegido | `GET`, `PATCH` | `/clientes/{id}` (con su perfil) | `VENDEDOR`, `ADMIN` | `200, 401, 403, 404, 409, 422` |
| Protegido | `POST` | `/clientes/{id}/perfil` | `VENDEDOR`, `ADMIN` | `201, 401, 403, 404, 409` |
| Protegido | `GET` | `/clientes/{id}/ventas` | `VENDEDOR`, `ADMIN` | `200, 401, 403, 404` |
| Protegido | `POST` | `/ventas` (con `renglones`) | `VENDEDOR`, `ADMIN` | `201, 401, 403, 409, 422` |
| Protegido | `GET` | `/ventas` (`page, size`) | `VENDEDOR`, `ADMIN` | `200, 401, 403, 422` |
| Protegido | `GET` | `/ventas/{id}` | Personal (`ADMIN`/`VENDEDOR`) o `CLIENTE` dueño (validado en servicio) | `200, 401, 403, 404` |
| Protegido | `GET` | `/mis-ventas` (`page, size`) | Autenticado (`CLIENTE` u otro usuario con ficha) | `200, 401, 403, 422` |

> **Nota sobre endpoints del TP**: En el TP 1-4 existían además `GET /editoriales/{id}`, `PATCH /generos/{id}`, `GET /autores/`, `GET /autores/{id}` y `GET /clientes/`. Se pueden conservar para compatibilidad de pruebas internas siempre que respeten la estructura de repositorios/UoW y los permisos de su módulo.
