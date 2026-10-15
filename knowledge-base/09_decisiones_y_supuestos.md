# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Alcance exacto a consigna
**Decisión**: implementar solo lo pedido, sin agregados. **Contexto**: los casos de prueba usan nombres fijos y los agregados no suman puntos. **Alternativas**: consigna + extras. **Justificación**: minimiza riesgo de corrección. **Trade-offs**: el proyecto no muestra capacidades extra.

### DD-02 — PostgreSQL 16 en Docker local para desarrollo
**Decisión**: PG16 en contenedor local; `DATABASE_URL` a localhost. **Contexto**: sin servidor PG16 disponible; Docker 29.7 instalado. **Alternativas**: PG instalado en Windows; PG remoto desde Easypanel. **Justificación**: reproducible, sin red, igual a lo que asume el corrector. **Trade-offs**: requiere Docker corriendo para dev y tests.

### DD-03 — `libro_autor` como entidad propia
**Decisión**: objeto de asociación con `rol` y `orden`, navegación `libro.autorias[i].autor`. **Contexto**: el M2M tiene datos propios. **Alternativas**: `link_model` simple. **Justificación**: un `link_model` escondería rol y orden; lo exige la consigna. **Trade-offs**: alta y lectura de libro manejan la tabla intermedia explícitamente.

### DD-04 — Sin verificación previa con `if`, la base decide (409)
**Decisión**: en altas con ids (libro, venta) se escribe y si la FK falla se responde 409. **Contexto**: unicidad y FK las garantiza la base (sección QUÉ evalúa, pto. 6). **Alternativas**: consultar existencia antes. **Justificación**: evita condiciones de carrera y es lo que evalúan. **Trade-offs**: obliga a traducir `IntegrityError` con precisión (RN-12).

### DD-05 — Eager loading declarado por tipo de relación
**Decisión**: `joinedload` para relaciones a uno, `selectinload` para colecciones. **Contexto**: lecturas con número fijo de consultas (C-07). **Alternativas**: una sola estrategia para todo. **Justificación**: `joined` en colecciones duplica filas; `selectin` en uno-a-uno desperdicia roundtrips. **Trade-offs**: hay que elegir bien por relación en cada lectura.

### DD-06 — `Decimal` para dinero, `expire_on_commit=False`
**Decisión**: dinero siempre `Decimal`; sesiones con `expire_on_commit=False`. **Contexto**: lo exige la consigna. **Justificación**: `float` pierde centavos; sin `expire_on_commit=False` los objetos devueltos tras commit disparan IO perezoso. **Trade-offs**: serialización de `Decimal` a cargo de los schemas.

## Supuestos inferidos

### SU-01 — Python 3.12 pendiente de resolver
**Supuesto**: se conseguirá Python 3.12 (en paralelo a la 3.14 instalada) antes de crear el venv. **Origen**: ronda kb-creator, respuesta "decidir después". **Riesgo si es falso**: incompatibilidades o incumplimiento de entrega. **Cómo validar**: instalar 3.12 y fijar el venv; ver PA-01.

### SU-02 — VPS con Easypanel solo deploy opcional
**Supuesto**: el VPS no forma parte de la corrección; como mucho, deploy de muestra post-entrega. **Origen**: análisis de la consigna (corrección sobre repo + base vacía). **Riesgo si es falso**: esfuerzo de deploy que no suma puntos. **Cómo validar**: confirmar con PA-02 antes de invertir tiempo.

### SU-03 — El corrector parte de base vacía con `upgrade head`
**Supuesto**: el flujo de corrección es repo + `alembic upgrade head` + seed + `.http`. **Origen**: consigna (formato de entrega, criterios). **Riesgo si es falso**: seed o migraciones incompletas. **Cómo validar**: probar ese flujo exacto desde cero antes de entregar (US-040).
