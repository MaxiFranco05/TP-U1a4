# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|---|---|---|
| Alumno | Desarrolla y entrega el proyecto | Escribe código, migraciones, seed, tests `.http`, README |
| Docente/corrector | Evalúa con casos de prueba | Levanta el proyecto, corre `alembic upgrade head` en base vacía, ejecuta `.http` |
| Script de seed | Deja la base en estado inicial conocido | Comando documentado en el README |
| Librería (ficticia) | Dueña narrativa del dominio | No opera el sistema; sus datos (libros, clientes, ventas) son el contenido |

No hay usuarios finales reales ni roles de negocio: la consigna excluye autenticación y autorización.

## RBAC — Matriz de permisos

No aplica (sin auth). Todos los endpoints son de acceso directo, sin distinción de roles. Se registra explícitamente para que ningún change futuro asuma un modelo de permisos que no existe.

## Rutas públicas

Todas las rutas son públicas por diseño del TP:

- `/health/live`, `/health/ready`
- `/editoriales/`, `/editoriales/{id}`, `/editoriales/{id}/libros`
- `/generos/`, `/generos/{id}/libros`
- `/autores/`, `/autores/{id}`, `/autores/{id}/libros`
- `/libros/`, `/libros/{id}`
- `/clientes/`, `/clientes/{id}`, `/clientes/{id}/perfil`, `/clientes/{id}/ventas`
- `/ventas/`, `/ventas/{id}`
