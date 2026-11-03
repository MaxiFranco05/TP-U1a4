"""Repositorios de persistencia asincrónica para el módulo usuarios."""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)


class UsuarioRepository(BaseRepository[Usuario]):
    """Repositorio asincrónico para la entidad Usuario."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=Usuario)

    async def get_by_email(self, email: str) -> Usuario | None:
        """Busca un usuario por su dirección de correo electrónico única."""
        stmt = select(Usuario).where(Usuario.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    """Repositorio asincrónico para la entidad AsignacionRol."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=AsignacionRol)

    async def get_roles_vigentes_usuario(self, usuario_id: int) -> list[str]:
        """Devuelve los nombres de roles vigentes (no revocados y sin vencer) del usuario."""
        now = datetime.now(timezone.utc)
        stmt = select(AsignacionRol.rol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.revocada_en.is_(None),
            or_(
                AsignacionRol.vence_en.is_(None),
                AsignacionRol.vence_en > now,
            ),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_asignaciones_vigentes(self, usuario_id: int) -> list[AsignacionRol]:
        """Devuelve las entidades AsignacionRol vigentes del usuario."""
        now = datetime.now(timezone.utc)
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.revocada_en.is_(None),
            or_(
                AsignacionRol.vence_en.is_(None),
                AsignacionRol.vence_en > now,
            ),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    """Repositorio asincrónico para auditoría de intentos de acceso y rate limiting (RN-07)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=IntentoAcceso)

    async def contar_fallos_recientes(
        self,
        email: str,
        ip: str,
        ventana_segundos: int = 60,
    ) -> int:
        """Cuenta los intentos fallidos acumulados en la ventana temporal desde el último login exitoso."""
        now = datetime.now(timezone.utc)
        ventana_inicio = now - timedelta(seconds=ventana_segundos)

        last_success_stmt = (
            select(IntentoAcceso.cuando)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
            )
            .order_by(IntentoAcceso.cuando.desc())
            .limit(1)
        )
        last_success_res = await self.session.execute(last_success_stmt)
        last_success_time = last_success_res.scalar_one_or_none()

        if last_success_time is not None:
            # Asegurar compatibilidad de timezones para SQLite o PostgreSQL
            if last_success_time.tzinfo is None:
                last_success_time = last_success_time.replace(tzinfo=timezone.utc)
            threshold = max(ventana_inicio, last_success_time)
        else:
            threshold = ventana_inicio

        count_stmt = select(func.count(IntentoAcceso.id)).where(
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(False),
            IntentoAcceso.cuando >= threshold,
        )
        count_res = await self.session.execute(count_stmt)
        return int(count_res.scalar_one() or 0)


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    """Repositorio asincrónico para la bitácora de eventos de seguridad (RN-16)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=EventoSeguridad)

    async def registrar_evento(self, actor: str, accion: str) -> EventoSeguridad:
        """Registra un evento de auditoría de seguridad dentro de la transacción actual."""
        evento = EventoSeguridad(actor=actor, accion=accion)
        return await self.add(evento)
