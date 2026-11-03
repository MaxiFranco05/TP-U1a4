"""Servicio de dominio para autenticación, gestión de credenciales y auditoría (/auth)."""

from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.exceptions import translate_integrity_error
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, IntentoAcceso, Usuario
from app.modules.usuarios.schemas import (
    CambiarPasswordRequest,
    LoginRequest,
    LoginResponse,
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
        3. Traduce IntegrityError por email repetido a 409 Conflict.
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
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email ya registrado",
                ) from exc
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
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos fallidos",
                headers={"Retry-After": "60"},
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

        es_valido = await verify_password(datos.password, usuario.password_hash)
        if not es_valido:
            await self._registrar_intento_independiente(
                session_factory,
                email=str(datos.email),
                ip=client_ip,
                exito=False,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
            )

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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta",
            )

        nuevo_hash = await hash_password(datos.password_nueva)

        async with uow:
            usuario.password_hash = nuevo_hash
            usuario.debe_cambiar_password = False
            await uow.usuarios.update(usuario)

            await uow.eventos_seguridad.registrar_evento(
                actor=usuario.email,
                accion="CAMBIO_PASSWORD",
            )
