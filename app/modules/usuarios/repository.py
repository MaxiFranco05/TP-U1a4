"""Repositorios de persistencia asincrónica para el módulo usuarios."""

from datetime import datetime, timedelta, timezone
from typing import Any
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

    async def get_asignacion_activa_por_rol(self, usuario_id: int, rol: str) -> AsignacionRol | None:
        """Devuelve la asignación activa (no revocada y vigente en tiempo) para usuario y rol."""
        now = datetime.now(timezone.utc)
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.rol == rol.upper(),
            AsignacionRol.revocada_en.is_(None),
            or_(
                AsignacionRol.vence_en.is_(None),
                AsignacionRol.vence_en > now,
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_asignacion_abierta_por_rol(self, usuario_id: int, rol: str) -> AsignacionRol | None:
        """Devuelve una asignación con revocada_en IS NULL independientemente de su vencimiento temporal."""
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.rol == rol.upper(),
            AsignacionRol.revocada_en.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_asignaciones_usuario(self, usuario_id: int) -> list[AsignacionRol]:
        """Devuelve el historial completo de asignaciones de un usuario ordenadas por fecha."""
        stmt = (
            select(AsignacionRol)
            .where(AsignacionRol.usuario_id == usuario_id)
            .order_by(AsignacionRol.desde.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def contar_admins_vigentes(self) -> int:
        """Cuenta usuarios distintos con rol ADMIN activo y vigente cuya cuenta de usuario esté activa (RN-05)."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(func.count(func.distinct(AsignacionRol.usuario_id)))
            .join(Usuario, Usuario.id == AsignacionRol.usuario_id)
            .where(
                AsignacionRol.rol == "ADMIN",
                AsignacionRol.revocada_en.is_(None),
                or_(
                    AsignacionRol.vence_en.is_(None),
                    AsignacionRol.vence_en > now,
                ),
                Usuario.activo.is_(True),
            )
        )
        res = await self.session.execute(stmt)
        return int(res.scalar_one() or 0)



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

    async def registrar_evento(
        self,
        actor: str,
        accion: str,
    ) -> EventoSeguridad:
        """Registra un evento de auditoría de seguridad dentro de la transacción actual (RN-16)."""
        evento = EventoSeguridad(
            actor=actor,
            accion=accion,
        )
        return await self.add(evento)


    async def listar_eventos_paginado(
        self,
        offset: int,
        limit: int,
    ) -> tuple[list[EventoSeguridad], int]:
        """Devuelve los eventos paginados ordenados determinísticamente y el total general (RN-16, C-16)."""
        count_stmt = select(func.count(EventoSeguridad.id))
        count_res = await self.session.execute(count_stmt)
        total = int(count_res.scalar_one() or 0)

        stmt = (
            select(EventoSeguridad)
            .order_by(EventoSeguridad.cuando.desc(), EventoSeguridad.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())
        return items, total

