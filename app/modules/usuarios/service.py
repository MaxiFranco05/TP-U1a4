"""Servicio de dominio para autenticación, gestión de credenciales y auditoría (/auth)."""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    EntityNotFoundError,
    RateLimitExceededError,
    translate_integrity_error,
)
from app.core.paginacion import PaginatedResponse, PaginationParams, paginate
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, IntentoAcceso, Usuario
from app.modules.usuarios.schemas import (
    CambiarPasswordRequest,
    EventoSeguridadResponse,
    LoginRequest,
    LoginResponse,
    RolAsignacionResponse,
    RolAsignarRequest,
    UsuarioCreateRequest,
    UsuarioReadResponse,
    UsuarioRegistroRequest,
    UsuarioYoResponse,
)
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork


class AuthService:
    """Lógica de negocio para endpoints /auth."""

    async def _registrar_intento_independiente(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        email: str,
        ip: str,
        exito: bool,
    ) -> None:
        """Registra un intento en intento_acceso con sesión y transacción independientes.

        # SESIÓN Y TRANSACCIÓN INDEPENDIENTES PARA INTENTO_ACCESO (DD-09, Ej. 7):
        # 1. Qué hace distinto: Abre una AsyncSession separada y ejecuta una transacción
        #    aislada con commit() forzoso, sin reutilizar la sesión del request.
        # 2. Por qué no comparte la transacción de la petición: Si compartiera la sesión/transacción
        #    de la petición, cualquier fallo de autenticación (401), rate limit (429) o error
        #    inesperado provocaría un rollback que borraría el registro del intento fallido,
        #    inutilizando por completo la protección de fuerza bruta (RN-07).
        # 3. Cuál es su costo: Adquiere temporalmente una conexión adicional del pool durante
        #    la escritura y persiste filas en la base de datos aun si la petición HTTP falla.
        """
        async with session_factory() as audit_session:
            async with audit_session.begin():
                intento = IntentoAcceso(
                    email=email,
                    ip=ip,
                    exito=exito,
                    cuando=datetime.now(timezone.utc),
                )
                audit_session.add(intento)

    async def registro(
        self,
        datos: UsuarioRegistroRequest,
        uow: UsuariosUnitOfWork,
    ) -> Usuario:
        """Auto-registro atómico de un nuevo cliente (RN-02, C-02).

        1. Calcula bcrypt hash fuera del UoW (DD-10).
        2. Dentro de async with uow: persiste Usuario, AsignacionRol('CLIENTE') y Cliente.
        3. Traduce IntegrityError por email repetido a ConflictError (RN-12).
        """
        hashed_password = await hash_password(datos.password)

        try:
            async with uow:
                usuario = Usuario(
                    nombre=datos.nombre,
                    email=str(datos.email),
                    password_hash=hashed_password,
                    activo=True,
                    debe_cambiar_password=False,
                )
                await uow.usuarios.add(usuario)

                rol = AsignacionRol(
                    usuario_id=usuario.id,
                    rol="CLIENTE",
                    desde=datetime.now(timezone.utc),
                )
                await uow.asignaciones_rol.add(rol)

                cliente = Cliente(
                    nombre=datos.nombre,
                    email=str(datos.email),
                    usuario_id=usuario.id,
                )
                await uow.clientes.add(cliente)
        except IntegrityError as exc:
            translated = translate_integrity_error(exc)
            if translated.detail == "Error de integridad de la base de datos":
                raise ConflictError("Email ya registrado") from exc
            raise translated from exc

        return usuario

    async def login(
        self,
        datos: LoginRequest,
        client_ip: str,
        uow: UsuariosUnitOfWork,
        session_factory: async_sessionmaker[AsyncSession],
        dummy_password_hash: str,
    ) -> tuple[str, LoginResponse]:
        """Inicia sesión validando rate limiting, contraseña en tiempo constante y auditoría (RN-07, RN-08)."""
        settings = get_settings()

        # 1. Control de tasa de intentos fallidos (RN-07)
        fallos = await uow.intentos_acceso.contar_fallos_recientes(
            email=str(datos.email),
            ip=client_ip,
            ventana_segundos=60,
        )
        if fallos >= 5:
            await self._registrar_intento_independiente(
                session_factory,
                email=str(datos.email),
                ip=client_ip,
                exito=False,
            )
            raise RateLimitExceededError(
                detail="Demasiados intentos fallidos",
                retry_after=60,
            )

        # 2. Verificación de credenciales en tiempo constante (RN-08)
        usuario = await uow.usuarios.get_by_email(str(datos.email))

        if usuario is None or not usuario.activo:
            await verify_password(datos.password, dummy_password_hash)
            await self._registrar_intento_independiente(
                session_factory,
                email=str(datos.email),
                ip=client_ip,
                exito=False,
            )
            raise AuthenticationError("Credenciales inválidas")

        es_valido = await verify_password(datos.password, usuario.password_hash)
        if not es_valido:
            await self._registrar_intento_independiente(
                session_factory,
                email=str(datos.email),
                ip=client_ip,
                exito=False,
            )
            raise AuthenticationError("Credenciales inválidas")

        # 3. Éxito: auditar y emitir token
        await self._registrar_intento_independiente(
            session_factory,
            email=str(datos.email),
            ip=client_ip,
            exito=True,
        )

        roles_vigentes = await uow.asignaciones_rol.get_roles_vigentes_usuario(usuario.id)
        token = create_access_token(data={"sub": str(usuario.id), "roles": roles_vigentes})

        return token, LoginResponse(
            mensaje="Inicio de sesión exitoso",
            debe_cambiar_password=usuario.debe_cambiar_password,
            expira_en_segundos=settings.JWT_EXPIRATION_SECONDS,
        )

    async def obtener_yo(
        self,
        usuario: Usuario,
        token_roles: list[str],
        uow: UsuariosUnitOfWork,
    ) -> UsuarioYoResponse:
        """Devuelve la información de identidad del usuario actual, roles vigentes y del token (C-07)."""
        roles_vigentes = await uow.asignaciones_rol.get_roles_vigentes_usuario(usuario.id)
        return UsuarioYoResponse(
            id=usuario.id,
            email=usuario.email,
            nombre=usuario.nombre,
            debe_cambiar_password=usuario.debe_cambiar_password,
            roles_vigentes=roles_vigentes,
            roles_token=token_roles,
        )

    async def cambiar_password(
        self,
        usuario: Usuario,
        datos: CambiarPasswordRequest,
        uow: UsuariosUnitOfWork,
    ) -> None:
        """Cambia la contraseña del usuario verificando la actual y registrando en evento_seguridad (RN-06, RN-16, C-09)."""
        es_valida = await verify_password(datos.password_actual, usuario.password_hash)
        if not es_valida:
            raise AuthenticationError("Contraseña actual incorrecta")

        nuevo_hash = await hash_password(datos.password_nueva)

        async with uow:
            usuario.password_hash = nuevo_hash
            usuario.debe_cambiar_password = False
            await uow.usuarios.update(usuario)

            await uow.eventos_seguridad.registrar_evento(
                actor=usuario.email,
                accion="CAMBIO_PASSWORD",
            )


class UsuarioService:
    """Lógica de negocio para gestión de personal, roles con vigencia y auditoría (/usuarios, /eventos)."""

    async def crear_personal(
        self,
        admin_actor: Usuario,
        datos: UsuarioCreateRequest,
        uow: UsuariosUnitOfWork,
    ) -> Usuario:
        """Crea un usuario de personal con contraseña provisoria, rol inicial y auditoría (RN-06, RN-16).

        1. Calcula el hash bcrypt fuera del UoW en asyncio.to_thread bajo semáforo (DD-10).
        2. Dentro de async with uow:
           - Crea Usuario con debe_cambiar_password=True y activo=True.
           - Crea AsignacionRol inicial con otorgada_por=admin_actor.id.
           - Registra EventoSeguridad con acción 'ALTA_PERSONAL'.
        3. Traduce colisión de email duplicado a ConflictError.
        """
        hashed_password = await hash_password(datos.password)

        try:
            async with uow:
                usuario = Usuario(
                    nombre=datos.nombre,
                    email=str(datos.email),
                    password_hash=hashed_password,
                    activo=True,
                    debe_cambiar_password=True,
                )
                await uow.usuarios.add(usuario)

                rol = AsignacionRol(
                    usuario_id=usuario.id,
                    rol=datos.rol.upper(),
                    otorgada_por=admin_actor.id,
                    desde=datetime.now(timezone.utc),
                )
                await uow.asignaciones_rol.add(rol)

                await uow.eventos_seguridad.registrar_evento(
                    actor=admin_actor.email,
                    accion="ALTA_PERSONAL",
                )

        except IntegrityError as exc:
            translated = translate_integrity_error(exc)
            if translated.detail == "Error de integridad de la base de datos":
                raise ConflictError("El correo electrónico ya está registrado") from exc
            raise translated from exc

        return usuario

    async def listar_roles(
        self,
        usuario_id: int,
        uow: UsuariosUnitOfWork,
    ) -> list[AsignacionRol]:
        """Devuelve el historial completo de asignaciones de un usuario (EntityNotFoundError si no existe)."""
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise EntityNotFoundError("Usuario no encontrado")
        return await uow.asignaciones_rol.get_asignaciones_usuario(usuario_id)

    async def asignar_rol(
        self,
        admin_actor: Usuario,
        usuario_id: int,
        datos: RolAsignarRequest,
        uow: UsuariosUnitOfWork,
    ) -> AsignacionRol:
        """Asigna un rol con vigencia, reemplazando asignaciones previas vencidas (RN-03, RN-16, C-07)."""
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise EntityNotFoundError("Usuario no encontrado")

        now = datetime.now(timezone.utc)
        rol_nombre = datos.rol.upper()

        async with uow:
            asig_abierta = await uow.asignaciones_rol.get_asignacion_abierta_por_rol(
                usuario_id=usuario_id,
                rol=rol_nombre,
            )
            if asig_abierta is not None:
                vence_en = asig_abierta.vence_en
                if vence_en is not None and vence_en.tzinfo is None:
                    vence_en = vence_en.replace(tzinfo=timezone.utc)

                if vence_en is not None and vence_en <= now:
                    asig_abierta.revocada_en = now
                    await uow.asignaciones_rol.update(asig_abierta)
                    await uow.session.flush()
                else:
                    raise ConflictError("El usuario ya tiene ese rol asignado")

            nueva_asig = AsignacionRol(
                usuario_id=usuario_id,
                rol=rol_nombre,
                otorgada_por=admin_actor.id,
                desde=now,
                vence_en=datos.vence_en,
            )
            await uow.asignaciones_rol.add(nueva_asig)

            await uow.eventos_seguridad.registrar_evento(
                actor=admin_actor.email,
                accion="ASIGNACION_ROL",
            )

        return nueva_asig

    async def revocar_rol(
        self,
        admin_actor: Usuario,
        usuario_id: int,
        rol: str,
        uow: UsuariosUnitOfWork,
    ) -> AsignacionRol:
        """Revoca lógicamente un rol de un usuario con autoprotección de administrador (RN-05, RN-16, C-08).

        Directiva de comprobaciones en orden:
        1. Verificar existencia del usuario destino (EntityNotFoundError si no existe).
        2. Buscar la asignación activa (revocada_en IS NULL y sin vencer) para (usuario_id, rol) (EntityNotFoundError si no la posee).
        3. Si rol.upper() == 'ADMIN':
           - Si usuario_id == admin_actor.id: rechazar ConflictError (intento de auto-revocación).
           - Si contar_admins_vigentes() <= 1: rechazar ConflictError (último administrador restante).
        4. Proceder a la revocación lógica (revocada_en = now()) y registro en evento_seguridad.
        """
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise EntityNotFoundError("Usuario no encontrado")

        rol_nombre = rol.upper()
        asig_activa = await uow.asignaciones_rol.get_asignacion_activa_por_rol(
            usuario_id=usuario_id,
            rol=rol_nombre,
        )
        if asig_activa is None:
            raise EntityNotFoundError(f"El usuario no posee el rol '{rol_nombre}' activo")

        if rol_nombre == "ADMIN":
            if usuario_id == admin_actor.id:
                raise ConflictError("No es posible auto-revocarse el rol de administrador")

            total_admins = await uow.asignaciones_rol.contar_admins_vigentes()
            if total_admins <= 1:
                raise ConflictError("No es posible revocar al único administrador vigente del sistema")

        now = datetime.now(timezone.utc)
        async with uow:
            asig_activa.revocada_en = now
            await uow.asignaciones_rol.update(asig_activa)

            await uow.eventos_seguridad.registrar_evento(
                actor=admin_actor.email,
                accion="REVOCACION_ROL",
            )

        return asig_activa

    async def listar_eventos(
        self,
        params: PaginationParams,
        uow: UsuariosUnitOfWork,
    ) -> PaginatedResponse[EventoSeguridadResponse]:
        """Consulta paginada de eventos de seguridad con envoltorio estándar y validación (RN-16, C-16)."""
        items, total = await uow.eventos_seguridad.listar_eventos_paginado(
            offset=params.offset,
            limit=params.limit,
        )
        dtos = [EventoSeguridadResponse.model_validate(e) for e in items]
        return paginate(items=dtos, total=total, page=params.page, size=params.size)
