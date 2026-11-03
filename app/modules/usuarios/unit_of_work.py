"""Unit of Work asincrónico para el módulo usuarios y sus interacciones con clientes."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuariosUnitOfWork(UnitOfWork):
    """Unit of Work que agrupa repositorios de identidad, roles, auditoría y clientes."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.usuarios = UsuarioRepository(session=self.session)
        self.asignaciones_rol = AsignacionRolRepository(session=self.session)
        self.intentos_acceso = IntentoAccesoRepository(session=self.session)
        self.eventos_seguridad = EventoSeguridadRepository(session=self.session)
        self.clientes = ClienteRepository(session=self.session)
