# Discovery — TP Librería (PROG3, Unidades 1 a 4)

**Fecha**: 2026-10-15
**Fuentes investigadas**: `TP_Cap1a4_Consigna.pdf` (consigna oficial del TP, 12 páginas — único documento base; no hubo scraping de competidores porque no aplica al contexto)

## 1. Problema que resuelve

Una librería de barrio necesita una API para su catálogo y sus ventas: libros de
distintas editoriales, clasificados por género y escritos por uno o varios autores
(con rol: autor, coautor, traductor o ilustrador); registro de clientes (con perfil
opcional de teléfono y dirección) y registro de cada venta con sus renglones
(qué libro, cuántos ejemplares, a qué precio).

A nivel académico, el TP integra en un único proyecto los capítulos 1 a 4:
fundamentos de FastAPI, contratos y CRUD, ejecución asincrónica sin bloqueos y
persistencia relacional con SQLModel + PostgreSQL + Alembic, incluidas todas las
relaciones entre entidades.

## 2. Usuarios / roles

No hay roles de negocio: autenticación y autorización quedan explícitamente fuera
(capítulo 5). Los actores son:

- **Alumno**: desarrolla el proyecto y lo entrega en un repositorio.
- **Docente/corrector**: ejecuta `alembic upgrade head` sobre una base vacía y
  corre los casos de prueba contra los nombres de tablas/columnas obligatorios.
- **Librería (dominio ficticio)**: el "cliente" narrativo que da sentido al modelo.

## 3. Casos de uso

Los ejercicios 1 a 7 de la consigna más los casos de prueba mínimos C-01 a C-08:

1. Proyecto, conexión y ciclo de vida (lifespan, `Depends(get_session)`, healthchecks).
2. Modelos, restricciones y relaciones (UNIQUE, CHECK, FK con índices, navegación
   en ambos extremos, `libro_autor` como objeto de asociación).
3. Migraciones Alembic (mínimo dos, autogeneradas; primera sin `genero`, segunda
   que la agrega; `upgrade`/`downgrade` funcionales).
4. Contratos y CRUD (DTO separados, códigos 201/404/409/422, paginación, búsqueda
   por título con parámetros ligados).
5. Altas con relaciones (ids que viajan, datos que nacen con el alta, sin
   verificación previa con `if`: se escribe y la base rechaza con 409).
6. Lecturas sin N+1 (carga anticipada declarada en la consulta, número fijo de queries).
7. Asincronía sin bloqueos (`async def` en todos los handlers, aviso de comprobante
   con `BackgroundTasks`).

## 4. Competidores / soluciones existentes

N/A — contexto de trabajo práctico universitario, no hay competencia comercial.
"Cómo se resuelve hoy": la librería ficticia llevaría todo en papel o planilla.
Se registra el punto como no aplicable en vez de inventar datos.

## 5. Funcionalidades necesarias

Los endpoints de referencia de la consigna (módulos mínimos: `health`,
`editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`) cumpliendo
RN-01 a RN-12, más la estructura obligatoria (`app/main.py`, `app/core/`,
`app/modules/<módulo>/{models,schemas,service,router}.py`, `migrations/`,
`test/*.http`, `requirements.txt`, `env.example`, `README.md`, script de seed y
evidencia del caso C-07).

## 6. Funcionalidades opcionales

Nada fuera de la consigna (decisión explícita del usuario: alcance exacto).
La propia consigna deja afuera: autenticación/autorización (cap. 5),
repositorios y Unit of Work (cap. 6), colas con Redis (caps. 7 y 8) — van al
"no hacer", no al backlog.

## 7. Reglas de negocio

RN-01 ISBN único (409) · RN-02 email de cliente único (409) · RN-03 precio > 0 y
stock nunca negativo · RN-04 la venta se crea con sus renglones (DTO anidado, sin
alta separada) · RN-05 venta con al menos un renglón y sin libros repetidos (422) ·
RN-06 el precio del renglón lo copia el servidor del libro (nunca viaja en el DTO) ·
RN-07 el total lo calcula el servidor (no viaja en el DTO) · RN-08 las ventas no se
modifican (sin PATCH) · RN-09 máximo un perfil por cliente (409) · RN-10 paginación
`limit` 1–100 (defecto 20) y `offset` ≥ 0 (422) · RN-11 filtro de libros por parte
del título, case-insensitive, con parámetros ligados · RN-12 ningún error expone
texto interno de la base (traducción de `IntegrityError` a mensaje propio).

## 8. Integraciones

Ninguna integración externa. PostgreSQL 16 como única dependencia de
infraestructura (vía `DATABASE_URL` en `.env`) y `BackgroundTasks` con
`asyncio.sleep(0.5)` simulando el aviso de comprobante. Deploy en VPS con
Easypanel evaluado como **opcional** (no requerido para la corrección, que corre
sobre el repo con base local vacía).

## 9. Restricciones

- Stack fijo: Python 3.12, FastAPI ≥ 0.111 (todo `async def`), SQLModel ≥ 0.0.24,
  SQLAlchemy 2.0 asincrónico, asyncpg ≥ 0.30, PostgreSQL 16, Alembic ≥ 1.13
  (plantilla asincrónica), python-dotenv, uvicorn.
- Nombres de tablas y columnas obligatorios (los usan los casos de prueba; se
  puede agregar, no quitar ni renombrar).
- Estructura de proyecto obligatoria por módulo funcional.
- Entrega: repo + `requirements.txt` + `env.example` (sin secretos) +
  `migrations/` + `test/` + `README.md` con pasos desde cero. El `.env` no se sube.
- Corrección bloqueante: si no levanta, si `alembic upgrade head` falla en base
  vacía o si hay credenciales en el repo, no se corrige.
- Entorno del alumno: Windows, Docker 29.7 disponible, Python 3.14 instalado
  (hay que instalar **3.12 en paralelo**), cliente `psql` 17 (falta servidor
  PostgreSQL 16 local o expuesto).

## 10. Riesgos

- **Supuesto sin probar (principal, declarado por el usuario)**: el alta de
  ventas con renglones (RN-04 a RN-07) — DTO anidado, precios copiados, total
  calculado, validaciones 422/409. Es la parte que menos domina el alumno.
- **Riesgo de entorno**: Python 3.14 instalado vs 3.12 exigido — instalar 3.12 en
  paralelo antes de crear el venv.
- **Riesgo de entorno**: sin servidor PostgreSQL 16 disponible todavía — definir
  PG16 en Docker local (desarrollo) y dejar Easypanel/VPS solo como deploy
  opcional.
- **Riesgo de corrección**: cualquier desvío en nombres de tablas/columnas o en
  la estructura obligatoria rompe los casos de prueba.
- **Riesgo de alcance**: los agregados fuera de consigna no suman puntos
  (mitigado: alcance fijado en "exacto a consigna").

## 11. Preguntas abiertas

- ¿PostgreSQL 16 en Docker local para desarrollo, o expuesto desde el VPS con
  Easypanel? (Recomendación: Docker local para dev; VPS solo deploy opcional.)
- ¿Instalar Python 3.12 en paralelo con la 3.14 existente?
- ¿Se usa el VPS con Easypanel solo para deploy de muestra, o se incluye como
  parte documentada de la entrega?
