# Design

## UI Mockups

Decision: no (no UI)

## Context

El proyecto ya cuenta con la configuración tipada (`app/core/config.py`), el motor asincrónico y `get_session` (`app/core/database.py`), el `lifespan` en `app/main.py` (`C-09`), y los 14 modelos con las migraciones `001` a `004` aplicadas (`C-10`), incluyendo `Libro.borrado_en` (`timestamptz`, nullable).

Para cumplir los Ejercicios 3 y 6 del Parcial (y habilitar `C-12` a `C-16`), necesitamos establecer las tres piezas transversales en `app/core/`:
1. `app/core/repository.py`: `BaseRepository[T]` y `SoftDeleteRepository[T]`.
2. `app/core/unit_of_work.py`: `UnitOfWork` base como gestor de contexto asincrónico.
3. `app/core/paginacion.py`: parámetros `page`/`size`, envoltorio `{items, total, page, size, pages}` y validación de página fuera de rango (`422`).

Ver `proposal.md` para la motivación y las especificaciones `core-repositories-uow` y `pagination-envelope` para los contratos normativos.

## Goals / Non-Goals

**Goals:**
- Definir firmas tipadas, limpias y reutilizables en Python 3.12 (`Generic[T]`) para `BaseRepository[T]`, `SoftDeleteRepository[T]`, `UnitOfWork` y `PaginatedResponse[T]`.
- Asegurar por diseño que ningún repositorio ejecute `commit()` ni `rollback()` (sólo `flush()`), y que ningún `UnitOfWork` cierre la `AsyncSession`.
- Proveer helpers en `paginacion.py` que sean utilizables tanto como dependencia de FastAPI (`PaginationParams`) como en la construcción y validación del envoltorio (`paginate` / `calcular_paginas` / `validar_pagina`).

**Non-Goals:**
- Migrar los routers o servicios de los módulos de dominio (`editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`, `usuarios`) — eso pertenece a `C-13`, `C-14`, `C-15` y `C-16`.
- Implementar dependencias de autenticación/autorización (`get_usuario_actual`, `requiere_rol`) — eso pertenece a `C-12`.

## Decisions

### 1. Paso explícito de `model_cls: type[T]` en `BaseRepository[T]` (DD-07)
- **Decisión**: En Python, los parámetros de tipo genérico (`Generic[T]`) se borran en tiempo de ejecución y no están disponibles de manera directa y limpia como atributo de instancia para armar `select(self.model_cls)`. Por ello, `BaseRepository.__init__` recibe explícitamente `(self, session: AsyncSession, model_cls: type[T]) -> None`. Las subclases concretas de cada módulo (ej. `EditorialRepository(session)`) llamarán a `super().__init__(session, Editorial)`.
- **Firma de `app/core/repository.py`**:
  ```python
  from collections.abc import Sequence
  from datetime import datetime, timezone
  from typing import Any, Generic, TypeVar

  from sqlalchemy import func, select
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlmodel import SQLModel

  T = TypeVar("T", bound=SQLModel)


  class BaseRepository(Generic[T]):
      """Repositorio base asincrónico que opera sobre la sesión compartida sin hacer commit."""

      def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
          self.session = session
          self.model_cls = model_cls

      async def get_by_id(self, entity_id: int) -> T | None: ...
      async def get_all(
          self,
          *,
          offset: int = 0,
          limit: int = 20,
          filters: Sequence[Any] = (),
          order_by: Any | None = None,
          options: Sequence[Any] = (),
      ) -> list[T]: ...
      async def count(self, *, filters: Sequence[Any] = ()) -> int: ...
      async def add(self, entity: T) -> T: ...
      async def update(self, entity: T, data: dict[str, Any] | None = None) -> T: ...
      async def delete(self, entity: T) -> None: ...
  ```
- **Comportamiento de escritura en `BaseRepository`**:
  - `add(self, entity: T) -> T`: ejecuta `self.session.add(entity)`, luego `await self.session.flush()` y `await self.session.refresh(entity)` para disponer de inmediato del `id` y valores por defecto generados por la base dentro del mismo UoW, **sin llamar a `commit()`**.
  - `update(self, entity: T, data: dict[str, Any] | None = None) -> T`: si `data` se provee, aplica `setattr(entity, campo, valor)` por cada clave-valor, asegura `self.session.add(entity)`, ejecuta `await self.session.flush()` y `await self.session.refresh(entity)`, **sin llamar a `commit()`**.
  - `delete(self, entity: T) -> None`: ejecuta `await self.session.delete(entity)` y `await self.session.flush()`, **sin llamar a `commit()`**.

### 2. Segregación de `SoftDeleteRepository[T](BaseRepository[T])` (DD-07)
- **Decisión**: Separar el borrado lógico en una subclase `SoftDeleteRepository[T](BaseRepository[T])` para que las entidades sin baja lógica (`Editorial`, `Genero`, `Autor`, `Cliente`, `Venta`, `Usuario`, etc.) no tengan métodos inaplicables como `soft_delete` ni `get_by_id_including_deleted`.
- **Firma y comportamiento**:
  ```python
  class SoftDeleteRepository(BaseRepository[T]):
      """Repositorio para entidades con baja lógica mediante columna borrado_en."""

      def _active_criterion(self) -> Any:
          return getattr(self.model_cls, "borrado_en").is_(None)

      async def get_by_id(self, entity_id: int) -> T | None: ...
      async def get_all(
          self,
          *,
          offset: int = 0,
          limit: int = 20,
          filters: Sequence[Any] = (),
          order_by: Any | None = None,
          options: Sequence[Any] = (),
      ) -> list[T]: ...
      async def count(self, *, filters: Sequence[Any] = ()) -> int: ...
      async def get_by_id_including_deleted(self, entity_id: int) -> T | None: ...
      async def soft_delete(self, entity: T) -> T: ...
  ```
  - `get_by_id`, `get_all` y `count` agregan automáticamente la condición `model_cls.borrado_en.is_(None)`.
  - `get_by_id_including_deleted(self, entity_id: int) -> T | None` busca por clave primaria sin filtrar `borrado_en` (necesario para detalle histórico de ventas y para distinguir `404` vs `409` al reponer o vender un libro dado de baja en `C-15`/`C-16`).
  - `soft_delete(self, entity: T) -> T` asigna `setattr(entity, "borrado_en", datetime.now(timezone.utc))`, hace `self.session.add(entity)` y `await self.session.flush()`, **sin llamar a `commit()`**.

### 3. `UnitOfWork` como gestor de contexto asincrónico que no cierra la sesión (DD-08)
- **Decisión**: `UnitOfWork` recibe `session: AsyncSession` en `__init__`. El router lo instancia mediante una dependencia que inyecta `Depends(get_session)` (compartiendo la misma sesión con `get_usuario_actual` y `requiere_rol`) y se lo pasa sin abrir al servicio. El servicio ejecuta `async with uow:`.
- **Firma de `app/core/unit_of_work.py`**:
  ```python
  from types import TracebackType
  from typing import Self

  from sqlalchemy.ext.asyncio import AsyncSession


  class UnitOfWork:
      """Gestor de contexto transaccional asincrónico sobre la sesión de la petición."""

      def __init__(self, session: AsyncSession) -> None:
          self.session = session

      async def __aenter__(self) -> Self:
          return self

      async def __aexit__(
          self,
          exc_type: type[BaseException] | None,
          exc_val: BaseException | None,
          exc_tb: TracebackType | None,
      ) -> None:
          if exc_type is None:
              await self.session.commit()
          else:
              await self.session.rollback()

      async def commit(self) -> None:
          await self.session.commit()

      async def rollback(self) -> None:
          await self.session.rollback()
  ```
- **Por qué no cierra la sesión**: `UnitOfWork` no creó la `AsyncSession`; la creó `get_session` con `async with session_factory() as session: yield session`. Si `UnitOfWork.__aexit__` cerrara la sesión, rompería el ciclo de vida de la dependencia de FastAPI o impediría lecturas posteriores dentro de la misma petición.

### 4. Envoltorio de Paginación y Validación `422` en `app/core/paginacion.py`
- **Decisión**: Proveer en `app/core/paginacion.py`:
  1. `PaginationParams`: clase inyectable con `Depends()` que declara `page: int = Query(default=1, ge=1, description="Número de página (empieza en 1)")` y `size: int = Query(default=20, ge=1, le=100, description="Tamaño de página (1 a 100)")`, más la propiedad `offset: int` (`(self.page - 1) * self.size`) y `limit: int` (`self.size`).
  2. `PaginatedResponse[T](SQLModel, Generic[T])` (con alias `Page = PaginatedResponse` para comodidad): modelo genérico con campos exactos `items: list[T]`, `total: int`, `page: int`, `size: int`, `pages: int`.
  3. `calcular_paginas(total: int, size: int) -> int`: devuelve `1` cuando `total == 0`, y `math.ceil(total / size)` cuando `total > 0`.
  4. `validar_pagina(page: int, pages: int) -> None` y `paginate(items: Sequence[T], total: int, page: int, size: int) -> PaginatedResponse[T]`:
     - Calcula `pages = calcular_paginas(total, size)`.
     - Si `page < 1` o `size < 1` o `size > 100`, lanza `HTTPException(status_code=422, detail=...)`.
     - Si `page > pages`, lanza `HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"La página {page} no existe: hay {pages}")`.
     - Devuelve `PaginatedResponse(items=list(items), total=total, page=page, size=size, pages=pages)`.

## Risks / Trade-offs

- **[Risk] Expiración de atributos al hacer `commit()` al salir del `UnitOfWork`** → **Mitigation**: La fábrica de sesiones construida en `app/core/database.py` (`build_session_factory`) ya configura `expire_on_commit=False`, y `BaseRepository.add`/`update` ejecutan `flush()` + `refresh()` dentro de la transacción activa.
- **[Risk] Solicitar `page=1` cuando `total=0` con filtro vacío** → **Mitigation**: `calcular_paginas(0, size)` devuelve explícitamente `1` (no `0`), por lo que `page=1` es válido y devuelve `{items: [], total: 0, page: 1, size: 20, pages: 1}`, mientras que `page=2` con `total=0` dispara `422` con `"La página 2 no existe: hay 1"`.
