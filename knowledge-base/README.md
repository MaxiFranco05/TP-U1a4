# Librería (TP + Parcial Capítulos 1 a 6) — Base de Conocimiento

Base de conocimiento generada y actualizada desde `docs/TP_Cap1a4_Consigna.pdf` (Etapa 1: Capítulos 1 a 4, `C-01` a `C-08` completados) y `docs/Parcial_Cap1a6_Consigna.pdf` (Etapa 2: **Parcial Capítulos 1 a 6 — La librería con acceso, transacciones y despliegue en el VPS**, `C-09` a `C-17`). Alcance fijado: exacto a consigna.

## Índice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, objetivos por actor, evolución de alcance (TP v1.0 + Parcial v2.0), pesos de evaluación (Ej. 1 a Ej. 10) |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack completo (`pydantic-settings`, `bcrypt`, `PyJWT`, `Docker`), capas `Router → Service → UoW → Repository → Model`, resumen de la API |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores, roles con vigencia en BD (`ADMIN`, `VENDEDOR`, `CLIENTE`), grupos de rutas `abierto` y `protegido`, matriz RBAC completa |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | 14 tablas obligatorias, ERD, índices únicos parciales (`postgresql_where`), trigger de sólo-agregado, migraciones 001 a 004 y `seed.py` |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas de negocio vigentes del Parcial (`RN-01` a `RN-16`), paginación con envoltorio, límite 72 bytes UTF-8 y referencia al TP |
| [06_funcionalidades.md](06_funcionalidades.md) | Historias de usuario por épica (config/lifespan, catálogo/stock/baja lógica, clientes, ventas en UoW, auth, roles/eventos, seed y despliegue VPS) |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos E2E: sesión compartida + UoW, registro, login con sesión propia en `intento_acceso`, vigencia de roles, stock único, venta atómica y Docker VPS |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Responsabilidades de las 5 capas, patrones, estructura obligatoria (`parcial/` y `despliegue/`), seguridad y variables de entorno |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones de diseño `DD-01` a `DD-14` y supuestos validados `SU-01` a `SU-03` |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Estado de preguntas abiertas (`PA-01` a `PA-07`) y división equitativa del trabajo entre Maxi, Andrés y Octavio |

## Quick Start para Desarrolladores

1. Entender el dominio y los permisos → [01_vision_y_objetivos.md](01_vision_y_objetivos.md), [03_actores_y_roles.md](03_actores_y_roles.md)
2. Entender las 14 tablas, migraciones 003/004 y el seed → [04_modelo_de_datos.md](04_modelo_de_datos.md)
3. Entender las reglas `RN-01` a `RN-16` → [05_reglas_de_negocio.md](05_reglas_de_negocio.md)
4. Entender las capas (`Router → Service → UoW → Repository → Model`) → [02_descripcion_general.md](02_descripcion_general.md), [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md)
5. Implementar cada flujo → [07_flujos_principales.md](07_flujos_principales.md), [06_funcionalidades.md](06_funcionalidades.md)
6. Ver asignación de changes por integrante → [10_preguntas_abiertas.md](10_preguntas_abiertas.md) y [../CHANGES.md](../CHANGES.md)

## Resumen Ejecutivo

El proyecto parte del TP de los capítulos 1 a 4 ya completado (`C-01` a `C-08`) y se amplía para el **Parcial (Capítulos 1 a 6)** en 9 changes (`C-09` a `C-17`) divididos equitativamente entre los 3 integrantes (**Maxi**: `C-09` a `C-11`; **Andrés**: `C-12` a `C-14`; **Octavio**: `C-15` a `C-17`), incorporando autenticación con `bcrypt` y cookie `HttpOnly`, autorización por roles vigentes en base de datos, arquitectura de Repositorios + Unit of Work, control de stock de sólo-agregado con disparador en PostgreSQL, borrado lógico de libros y despliegue en contenedor Docker (`python:3.12-alpine`) del TP 1-4 en el VPS.
