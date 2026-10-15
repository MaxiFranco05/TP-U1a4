# Flujos Principales

## Flujo 1: Arranque y petición con sesión

**Disparador**: arranque del servidor. **Actor**: sistema.
**Pasos**:
1. `lifespan` crea motor asincrónico + fábrica de sesiones, los guarda en `app.state`.
2. Cada petición: `Depends(get_session)` crea una sesión (`expire_on_commit=False`).
3. El handler delega al service con la sesión; al responder se cierra la sesión.
4. Al apagar: se cierra el motor.
**Casos de error**: sin `DATABASE_URL` o base caída → `/health/ready` lo expone; nunca traza interna al cliente (RN-12).

## Flujo 2: Alta de libro con autores (US-012)

**Disparador**: `POST /libros/`. **Actor**: alumno/corrector.
**Pasos**:
1. Router valida `LibroCreate` (con `autores[]`) → delega al service.
2. Service construye `Libro` + objetos `LibroAutor` (rol, orden) y escribe **sin verificar existencias con `if`**.
3. Si la base rechaza una FK → 409 con mensaje propio (RN-12).
4. Responde 201 con el detalle (editorial, género, autores vía `libro.autorias[i].autor`).
**Casos de error**: ISBN repetido → 409 (C-02); editorial/autor inexistente → 409 (C-04); cuerpo inválido → 422.

## Flujo 3: Alta de venta con renglones (US-030, riesgo principal)

**Disparador**: `POST /ventas/`. **Actor**: alumno/corrector.
**Pasos**:
1. Router valida `VentaCreate` (al menos un renglón, sin libros repetidos → 422 si falla, RN-05).
2. Service lee cada `Libro` de la base, **copia** `precio_unitario`, calcula subtotales y `total` (RN-06, RN-07).
3. Agrega los renglones a `venta.renglones` (composición, RN-04) y persiste en una transacción.
4. Agenda con `BackgroundTasks` el aviso (`asyncio.sleep(0.5)` + log) y responde 201 **sin esperar** el aviso.
**Diagrama**: `Cliente → Router → Service → DB (lee libros, escribe venta+renglones) → 201 → [fondo: aviso]`.
**Casos de error**: cliente/libro inexistente → 409 (C-05); venta inválida → 422; sin PATCH posterior (RN-08).

## Flujo 4: Detalle sin N+1 (US-013, US-031)

**Disparador**: `GET /libros/{id}` o `GET /ventas/{id}`.
**Pasos**:
1. Service arma **una sola consulta** con carga anticipada declarada: `joinedload` para relaciones a uno (editorial, género, cliente), `selectinload` para colecciones (autorías, renglones).
2. Nunca se toca carga perezosa; el número de queries es fijo aunque crezcan autores/renglones (evidencia C-07 en consola con `echo` configurable).

## Flujo 5: Migración del esquema (US-040)

**Disparador**: cambio de modelos. **Actor**: alumno.
**Pasos**:
1. `alembic revision --autogenerate` → **leer** el archivo generado.
2. Si hay un problema, corregir a mano con comentario explicativo en el propio archivo.
3. `alembic upgrade head` (y verificar `downgrade -1` + `upgrade head`).
**Casos de error**: autogenerate con diff espurio → se edita antes de aplicar, nunca después.
