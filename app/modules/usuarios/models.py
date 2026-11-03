"""Modelos de persistencia de identidad, asignaciones de rol y auditoría de acceso/seguridad."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Column, DateTime, Index, func, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import MovimientoStock


class Usuario(SQLModel, table=True):
    """Identidad de acceso al sistema (RN-02, RN-03)."""

    __tablename__ = "usuario"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, nullable=False)
    nombre: str = Field(nullable=False)
    password_hash: str = Field(nullable=False)
    activo: bool = Field(default=True, nullable=False)
    debe_cambiar_password: bool = Field(default=False, nullable=False)

    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"uselist": False},
    )
    asignaciones_rol: list["AsignacionRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"foreign_keys": "[AsignacionRol.usuario_id]"},
    )
    asignaciones_otorgadas: list["AsignacionRol"] = Relationship(
        back_populates="otorgante",
        sa_relationship_kwargs={"foreign_keys": "[AsignacionRol.otorgada_por]"},
    )
    movimientos_stock: list["MovimientoStock"] = Relationship(back_populates="usuario")


class AsignacionRol(SQLModel, table=True):
    """Asignación de rol con vigencia temporal e historial de revocación (RN-03, RN-04)."""

    __tablename__ = "asignacion_rol"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')",
            name="ck_asignacion_rol_rol_valido",
        ),
        Index(
            "uq_asignacion_rol_activa",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(
        foreign_key="usuario.id",
        index=True,
        nullable=False,
    )
    rol: str = Field(nullable=False)
    desde: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    vence_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    revocada_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    otorgada_por: int | None = Field(
        default=None,
        foreign_key="usuario.id",
        index=True,
        nullable=True,
    )

    usuario: "Usuario" = Relationship(
        back_populates="asignaciones_rol",
        sa_relationship_kwargs={"foreign_keys": "[AsignacionRol.usuario_id]"},
    )
    otorgante: Optional["Usuario"] = Relationship(
        back_populates="asignaciones_otorgadas",
        sa_relationship_kwargs={"foreign_keys": "[AsignacionRol.otorgada_por]"},
    )


class IntentoAcceso(SQLModel, table=True):
    """Registro de intento de login sin clave foránea a usuario (RN-07)."""

    __tablename__ = "intento_acceso"
    __table_args__ = (
        Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    email: str = Field(nullable=False)
    ip: str = Field(nullable=False)
    exito: bool = Field(nullable=False)


class EventoSeguridad(SQLModel, table=True):
    """Bitácora de eventos administrativos y de seguridad sin clave foránea (RN-16)."""

    __tablename__ = "evento_seguridad"

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    actor: str = Field(nullable=False)
    accion: str = Field(nullable=False)
