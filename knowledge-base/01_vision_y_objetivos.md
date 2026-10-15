# Visión y Objetivos

## Propósito del sistema

API asincrónica para la gestión de catálogo, clientes y ventas de una librería de barrio, desarrollada como trabajo práctico integrador de Programación III (Unidades 1 a 4): demuestra dominio de FastAPI asincrónico, contratos y CRUD, ejecución sin bloqueos y persistencia relacional con SQLModel + PostgreSQL + Alembic.

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| Alumno | Entregar el TP completo cumpliendo el 100% de la consigna | Aprender async, relaciones y migraciones; portfolio con deploy opcional |
| Docente/corrector | Verificar con casos de prueba que el sistema cumple cada ejercicio | Correr `alembic upgrade head` en base vacía y los `.http` sin fricción |
| Librería (dominio ficticio) | Registrar catálogo, clientes y ventas sin papel/planilla | Consultar stock, historial de ventas y fichas de libros con autores |

## Alcance v1.0

- Módulos `health`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas` con los endpoints de referencia.
- Modelo de dominio completo (9 tablas) con UNIQUE, CHECK, FK con índices y navegación bidireccional.
- Dos migraciones Alembic autogeneradas (primera sin `genero`, segunda que la agrega).
- DTO de entrada/salida separados, códigos 201/404/409/422, paginación y búsqueda ligada.
- Altas con relaciones (libro con autores, venta con renglones), lecturas sin N+1, handlers 100% `async` + aviso con `BackgroundTasks`.
- Entrega: `requirements.txt`, `env.example`, `migrations/`, `test/*.http`, script de seed, `README.md` con pasos desde cero y evidencia C-07.

## Fuera de alcance

- Autenticación y autorización (capítulo 5).
- Repositorios y Unit of Work (capítulo 6).
- Colas de tareas con Redis (capítulos 7 y 8).
- Frontend propio, panel de administración, pagos online, reportes.

## Métricas de éxito

Los criterios de evaluación de la consigna, con sus pesos: proyecto/conexión 10%, modelos/relaciones 25%, migraciones 10%, contratos/CRUD 15%, altas con relaciones 20%, lecturas sin N+1 10%, asincronía 10%. Bloqueantes: el proyecto levanta, `alembic upgrade head` funciona en base vacía y no hay credenciales en el repo.
