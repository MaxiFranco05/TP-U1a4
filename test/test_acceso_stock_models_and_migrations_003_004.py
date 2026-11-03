"""Tests de integración y metadata bajo Strict TDD para C-10: modelos de acceso, stock y migraciones 003-004."""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import class_mapper, joinedload, selectinload
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.core.exceptions import translate_integrity_error
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)
from app.modules.ventas.models import Venta

EXPECTED_ALL_14_TABLES = {
    "editorial",
    "genero",
    "autor",
    "libro",
    "libro_autor",
    "cliente",
    "perfil_cliente",
    "venta",
    "renglon_venta",
    "usuario",
    "asignacion_rol",
    "intento_acceso",
    "evento_seguridad",
    "movimiento_stock",
}


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión asincrónica conectada a PostgreSQL 16 y limpia con TRUNCATE RESTART IDENTITY CASCADE."""
    settings = get_settings()
    engine = build_engine(settings.database_url, sql_echo=False)
    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        yield session
        await session.rollback()
        res = await session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
            )
        )
        existing_tables = {row[0] for row in res.fetchall()}
        if EXPECTED_ALL_14_TABLES.issubset(existing_tables):
            await session.execute(
                text(
                    "TRUNCATE TABLE movimiento_stock, renglon_venta, venta, asignacion_rol, "
                    "intento_acceso, evento_seguridad, perfil_cliente, cliente, libro_autor, "
                    "libro, genero, autor, editorial, usuario RESTART IDENTITY CASCADE"
                )
            )
            await session.commit()
    await engine.dispose()


def test_sqlmodel_metadata_usuarios_asignacion_rol_intento_acceso_evento_seguridad() -> None:
    """Scenario: SQLModel.metadata registra usuario, asignacion_rol, intento_acceso y evento_seguridad con sus restricciones e índices."""
    tables = SQLModel.metadata.tables
    for table_name in ("usuario", "asignacion_rol", "intento_acceso", "evento_seguridad"):
        assert table_name in tables, f"Falta tabla {table_name} en SQLModel.metadata"

    # 1. Tabla usuario
    usuario_table = tables["usuario"]
    assert {
        "id",
        "email",
        "nombre",
        "password_hash",
        "activo",
        "debe_cambiar_password",
    } == set(usuario_table.columns.keys())
    assert usuario_table.columns["email"].nullable is False
    assert usuario_table.columns["activo"].nullable is False
    assert usuario_table.columns["debe_cambiar_password"].nullable is False

    # Verificar defaults de instancia en Usuario
    u_inst = Usuario(
        email="test@example.com",
        nombre="Test User",
        password_hash="$2b$04$dummyhash",
    )
    assert u_inst.activo is True
    assert u_inst.debe_cambiar_password is False

    # 2. Tabla asignacion_rol
    ar_table = tables["asignacion_rol"]
    assert {
        "id",
        "usuario_id",
        "rol",
        "desde",
        "vence_en",
        "revocada_en",
        "otorgada_por",
    } == set(ar_table.columns.keys())
    assert ar_table.columns["desde"].type.timezone is True
    assert ar_table.columns["vence_en"].type.timezone is True
    assert ar_table.columns["revocada_en"].type.timezone is True
    assert ar_table.columns["vence_en"].nullable is True
    assert ar_table.columns["revocada_en"].nullable is True
    assert ar_table.columns["otorgada_por"].nullable is True

    ar_checks = {
        c.name: str(c.sqltext)
        for c in ar_table.constraints
        if c.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_asignacion_rol_rol_valido" in ar_checks
    assert "ADMIN" in ar_checks["ck_asignacion_rol_rol_valido"]
    assert "VENDEDOR" in ar_checks["ck_asignacion_rol_rol_valido"]
    assert "CLIENTE" in ar_checks["ck_asignacion_rol_rol_valido"]

    ar_indexes = {idx.name: idx for idx in ar_table.indexes}
    assert "uq_asignacion_rol_activa" in ar_indexes
    uq_ar = ar_indexes["uq_asignacion_rol_activa"]
    assert uq_ar.unique is True
    assert [c.name for c in uq_ar.columns] == ["usuario_id", "rol"]
    assert "revocada_en IS NULL" in str(uq_ar.dialect_options["postgresql"]["where"])

    # FKs indexadas en asignacion_rol
    indexed_single_cols = {
        tuple(c.name for c in idx.columns) for idx in ar_table.indexes
    }
    assert ("usuario_id",) in indexed_single_cols
    assert ("otorgada_por",) in indexed_single_cols

    # 3. Tabla intento_acceso (sin FKs, índice compuesto)
    ia_table = tables["intento_acceso"]
    assert {"id", "cuando", "email", "ip", "exito"} == set(ia_table.columns.keys())
    assert ia_table.columns["cuando"].type.timezone is True
    assert len(ia_table.foreign_keys) == 0
    ia_indexes = {idx.name: idx for idx in ia_table.indexes}
    assert "ix_intento_acceso_email_ip_cuando" in ia_indexes
    assert [c.name for c in ia_indexes["ix_intento_acceso_email_ip_cuando"].columns] == [
        "email",
        "ip",
        "cuando",
    ]

    # 4. Tabla evento_seguridad (sin FKs)
    es_table = tables["evento_seguridad"]
    assert {"id", "cuando", "actor", "accion"} == set(es_table.columns.keys())
    assert es_table.columns["cuando"].type.timezone is True
    assert len(es_table.foreign_keys) == 0


def test_sqlmodel_metadata_movimiento_stock_libro_borrado_en_and_cliente_usuario() -> None:
    """Scenario: SQLModel.metadata registra movimiento_stock, libro.borrado_en + uq_libro_isbn_activo y cliente.usuario_id."""
    tables = SQLModel.metadata.tables
    assert "movimiento_stock" in tables

    # 1. Tabla movimiento_stock
    ms_table = tables["movimiento_stock"]
    assert {
        "id",
        "libro_id",
        "venta_id",
        "usuario_id",
        "cantidad",
        "motivo",
        "cuando",
    } == set(ms_table.columns.keys())
    assert ms_table.columns["libro_id"].nullable is False
    assert ms_table.columns["venta_id"].nullable is True
    assert ms_table.columns["usuario_id"].nullable is False
    assert ms_table.columns["cantidad"].nullable is False
    assert ms_table.columns["motivo"].nullable is False
    assert ms_table.columns["cuando"].type.timezone is True

    ms_checks = {
        c.name: str(c.sqltext)
        for c in ms_table.constraints
        if c.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_movimiento_stock_cantidad_no_cero" in ms_checks
    assert "cantidad <> 0" in ms_checks["ck_movimiento_stock_cantidad_no_cero"]

    ms_indexed_cols = {tuple(c.name for c in idx.columns) for idx in ms_table.indexes}
    assert ("libro_id",) in ms_indexed_cols
    assert ("venta_id",) in ms_indexed_cols
    assert ("usuario_id",) in ms_indexed_cols

    # 2. Libro.borrado_en e índice único parcial uq_libro_isbn_activo (sin UniqueConstraint global en isbn)
    libro_table = tables["libro"]
    assert "borrado_en" in libro_table.columns
    assert libro_table.columns["borrado_en"].nullable is True
    assert libro_table.columns["borrado_en"].type.timezone is True
    assert not libro_table.columns["isbn"].unique

    libro_unique_constraints = [
        c
        for c in libro_table.constraints
        if c.__class__.__name__ == "UniqueConstraint"
        and [col.name for col in c.columns] == ["isbn"]
    ]
    assert len(libro_unique_constraints) == 0

    libro_indexes = {idx.name: idx for idx in libro_table.indexes}
    assert "uq_libro_isbn_activo" in libro_indexes
    uq_libro = libro_indexes["uq_libro_isbn_activo"]
    assert uq_libro.unique is True
    assert [c.name for c in uq_libro.columns] == ["isbn"]
    assert "borrado_en IS NULL" in str(uq_libro.dialect_options["postgresql"]["where"])

    # 3. Cliente.usuario_id y relación Cliente.usuario con uselist=False
    cliente_table = tables["cliente"]
    assert "usuario_id" in cliente_table.columns
    assert cliente_table.columns["usuario_id"].nullable is True
    cliente_indexed_cols = {
        tuple(c.name for c in idx.columns): idx.unique for idx in cliente_table.indexes
    }
    assert cliente_indexed_cols.get(("usuario_id",)) is True

    cliente_mapper = class_mapper(Cliente)
    assert "usuario" in cliente_mapper.relationships
    assert cliente_mapper.relationships["usuario"].uselist is False

    venta_mapper = class_mapper(Venta)
    assert "movimientos_stock" in venta_mapper.relationships

    # 4. Traducción de errores para los nuevos índices/constraints en app/core/exceptions.py
    for cname, expected_msg in (
        ("uq_libro_isbn_activo", "Ya existe un libro con ese ISBN"),
        ("usuario_email_key", "Email ya registrado"),
        ("uq_asignacion_rol_activa", "El usuario ya tiene ese rol asignado"),
        ("ix_cliente_usuario_id", "El usuario ya está asociado a un cliente"),
    ):
        fake_exc = IntegrityError("stmt", {}, Exception(f'violates unique constraint "{cname}"'))
        http_exc = translate_integrity_error(fake_exc)
        assert http_exc.status_code == 409
        assert http_exc.detail == expected_msg
    _ = (Libro, MovimientoStock)


def test_migration_003_file_exists_and_is_reviewed() -> None:
    """Scenario: Existe el archivo de migración 003 en migrations/versions/ con constancia de revisión manual."""
    versions_dir = Path(__file__).resolve().parent.parent / "migrations" / "versions"
    mig_003 = sorted(f for f in versions_dir.glob("*.py") if "003" in f.name)
    assert len(mig_003) == 1, "Debe existir el archivo de la migración 003 en migrations/versions/"
    content = mig_003[0].read_text(encoding="utf-8")
    assert "Revisión manual" in content or "Revision manual" in content
    for token in (
        "usuario",
        "asignacion_rol",
        "intento_acceso",
        "evento_seguridad",
        "movimiento_stock",
        "uq_libro_isbn_activo",
        "uq_asignacion_rol_activa",
        "ix_intento_acceso_email_ip_cuando",
        "borrado_en",
        "usuario_id",
    ):
        assert token in content, f"Falta '{token}' en el contenido de la migración 003"


@pytest.mark.asyncio
async def test_database_schema_has_all_14_tables_and_partial_indexes(
    db_session: AsyncSession,
) -> None:
    """Scenario: En PostgreSQL 16 existen las 14 tablas del Parcial y los índices parciales/compuestos."""
    result = await db_session.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
        )
    )
    db_tables = {row[0] for row in result.fetchall()}
    assert db_tables == EXPECTED_ALL_14_TABLES

    idx_result = await db_session.execute(
        text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'")
    )
    indexes = {row[0]: row[1] for row in idx_result.fetchall()}
    assert "uq_libro_isbn_activo" in indexes
    assert "WHERE (borrado_en IS NULL)" in indexes["uq_libro_isbn_activo"]
    assert "uq_asignacion_rol_activa" in indexes
    assert "WHERE (revocada_en IS NULL)" in indexes["uq_asignacion_rol_activa"]
    assert "ix_intento_acceso_email_ip_cuando" in indexes


@pytest.mark.asyncio
async def test_libro_partial_unique_index_soft_delete_reuse(
    db_session: AsyncSession,
) -> None:
    """Scenarios: Duplicate active libro.isbn rejected; soft-deleted libro.isbn can be reused by a new active book."""
    suffix = uuid.uuid4().hex[:8]
    editorial = Editorial(nombre=f"Ed Parcial {suffix}", pais="Argentina")
    db_session.add(editorial)
    await db_session.commit()
    assert editorial.id is not None
    ed_id = editorial.id

    isbn_compartido = f"978-950-PU-{suffix}"
    libro_1 = Libro(
        isbn=isbn_compartido,
        titulo="Edición Original",
        precio=Decimal("10000.00"),
        stock=5,
        editorial_id=ed_id,
        borrado_en=None,
    )
    db_session.add(libro_1)
    await db_session.commit()
    assert libro_1.id is not None
    libro_1_id = libro_1.id

    # 1. Segundo libro activo con el mismo ISBN -> rechazado por uq_libro_isbn_activo
    db_session.add(
        Libro(
            isbn=isbn_compartido,
            titulo="Duplicado Activo",
            precio=Decimal("12000.00"),
            stock=3,
            editorial_id=ed_id,
            borrado_en=None,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 2. Marcar baja lógica en libro_1 (borrado_en != None) y crear nuevo libro activo con igual ISBN -> permitido
    stmt = select(Libro).where(Libro.id == libro_1_id)
    libro_db = (await db_session.execute(stmt)).scalar_one()
    libro_db.borrado_en = datetime.now(timezone.utc)
    await db_session.commit()

    libro_2_activo = Libro(
        isbn=isbn_compartido,
        titulo="Reedición Activa",
        precio=Decimal("15000.00"),
        stock=8,
        editorial_id=ed_id,
        borrado_en=None,
    )
    db_session.add(libro_2_activo)
    await db_session.commit()
    assert libro_2_activo.id is not None

    # 3. Intentar un segundo libro activo mientras libro_2_activo sigue activo -> rechazado
    db_session.add(
        Libro(
            isbn=isbn_compartido,
            titulo="Otro Activo Prohibido",
            precio=Decimal("16000.00"),
            stock=2,
            editorial_id=ed_id,
            borrado_en=None,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_usuario_asignacion_rol_partial_unique_and_cliente_usuario_relationship(
    db_session: AsyncSession,
) -> None:
    """Scenarios: Usuario/AsignacionRol partial unique index, invalid rol check, Cliente.usuario uselist=False, audit models without FK."""
    suffix = uuid.uuid4().hex[:8]
    admin = Usuario(
        email=f"admin.{suffix}@libreria.com",
        nombre="Admin",
        password_hash="$2b$04$hashadmin",
        activo=True,
        debe_cambiar_password=False,
    )
    vendedor = Usuario(
        email=f"vendedor.{suffix}@libreria.com",
        nombre="Vendedor",
        password_hash="$2b$04$hashvend",
    )
    db_session.add_all([admin, vendedor])
    await db_session.commit()
    assert admin.id is not None
    assert vendedor.id is not None
    admin_id = admin.id
    vendedor_id = vendedor.id

    # 1. Email de usuario duplicado -> rechazado
    db_session.add(
        Usuario(
            email=f"admin.{suffix}@libreria.com",
            nombre="Clon",
            password_hash="$2b$04$hashclon",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 2. Asignación abierta (revocada_en=None) persiste y rechaza duplicada abierta
    ar_1 = AsignacionRol(
        usuario_id=vendedor_id,
        rol="VENDEDOR",
        otorgada_por=admin_id,
        revocada_en=None,
    )
    db_session.add(ar_1)
    await db_session.commit()
    assert ar_1.id is not None
    assert ar_1.desde.tzinfo is not None
    ar_1_id = ar_1.id

    db_session.add(
        AsignacionRol(
            usuario_id=vendedor_id,
            rol="VENDEDOR",
            otorgada_por=admin_id,
            revocada_en=None,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 3. Al revocar ar_1 (revocada_en != None), se permite crear una nueva asignación abierta para el mismo (usuario_id, rol)
    stmt_ar = select(AsignacionRol).where(AsignacionRol.id == ar_1_id)
    ar_db = (await db_session.execute(stmt_ar)).scalar_one()
    ar_db.revocada_en = datetime.now(timezone.utc)
    await db_session.commit()

    ar_2 = AsignacionRol(
        usuario_id=vendedor_id,
        rol="VENDEDOR",
        otorgada_por=admin_id,
        revocada_en=None,
    )
    db_session.add(ar_2)
    await db_session.commit()
    assert ar_2.id is not None

    # 4. Rol inválido fuera de ('ADMIN', 'VENDEDOR', 'CLIENTE') -> rechazado por CHECK
    db_session.add(
        AsignacionRol(
            usuario_id=vendedor_id,
            rol="SUPERUSUARIO",
            otorgada_por=admin_id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 5. Cliente.usuario con uselist=False devuelve un objeto Usuario (no lista) y rechaza usuario_id duplicado
    cliente = Cliente(
        nombre="Cliente Con Usuario",
        email=f"cli.usr.{suffix}@libreria.com",
        usuario_id=vendedor_id,
    )
    db_session.add(cliente)
    await db_session.commit()

    stmt_cli = (
        select(Cliente)
        .where(Cliente.id == cliente.id)
        .options(joinedload(Cliente.usuario))
    )
    loaded_cli = (await db_session.execute(stmt_cli)).scalar_one()
    assert loaded_cli.usuario is not None
    assert not isinstance(loaded_cli.usuario, list)
    assert isinstance(loaded_cli.usuario, Usuario)
    assert loaded_cli.usuario.id == vendedor_id

    stmt_usr = (
        select(Usuario)
        .where(Usuario.id == vendedor_id)
        .options(
            joinedload(Usuario.cliente),
            selectinload(Usuario.asignaciones_rol),
        )
    )
    loaded_usr = (await db_session.execute(stmt_usr)).scalar_one()
    assert loaded_usr.cliente is not None
    assert not isinstance(loaded_usr.cliente, list)
    assert loaded_usr.cliente.id == cliente.id
    assert len(loaded_usr.asignaciones_rol) == 2

    db_session.add(
        Cliente(
            nombre="Segundo Cliente Mismo Usuario",
            email=f"cli2.usr.{suffix}@libreria.com",
            usuario_id=vendedor_id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 6. IntentoAcceso y EventoSeguridad persisten sin FK
    intento = IntentoAcceso(
        email=f"noexiste.{suffix}@anon.com",
        ip="192.0.2.55",
        exito=False,
    )
    evento = EventoSeguridad(
        actor="SISTEMA",
        accion="INICIO_APLICACION",
    )
    db_session.add_all([intento, evento])
    await db_session.commit()
    assert intento.id is not None
    assert intento.cuando.tzinfo is not None
    assert evento.id is not None
    assert evento.cuando.tzinfo is not None


def test_migration_004_file_exists_and_is_reviewed() -> None:
    """Scenario: Existe el archivo de migración 004 escrita a mano en migrations/versions/ con constancia de revisión."""
    versions_dir = Path(__file__).resolve().parent.parent / "migrations" / "versions"
    mig_004 = sorted(f for f in versions_dir.glob("*.py") if "004" in f.name)
    assert len(mig_004) == 1, "Debe existir el archivo de la migración 004 en migrations/versions/"
    content = mig_004[0].read_text(encoding="utf-8")
    assert "Revisión manual" in content or "Revision manual" in content or "Escrita a mano" in content
    for token in (
        "fn_movimiento_stock_append_only",
        "trg_movimiento_stock_append_only",
        "BEFORE UPDATE OR DELETE ON movimiento_stock",
        "DROP TRIGGER",
        "DROP FUNCTION",
    ):
        assert token in content, f"Falta '{token}' en el contenido de la migración 004"


@pytest.mark.asyncio
async def test_movimiento_stock_check_and_append_only_trigger_rejects_update_and_delete(
    db_session: AsyncSession,
) -> None:
    """Scenarios: Valid positive/negative movements persist; cantidad=0 rejected by CHECK; UPDATE and DELETE rejected by PostgreSQL trigger (RN-12, C-14)."""
    from sqlalchemy.exc import DBAPIError

    suffix = uuid.uuid4().hex[:8]
    editorial = Editorial(nombre=f"Ed Stock {suffix}", pais="Argentina")
    usuario = Usuario(
        email=f"stock.user.{suffix}@libreria.com",
        nombre="Operador Stock",
        password_hash="$2b$04$hashstock",
    )
    cliente = Cliente(nombre="Cliente Stock", email=f"cli.stock.{suffix}@libreria.com")
    db_session.add_all([editorial, usuario, cliente])
    await db_session.commit()
    assert editorial.id is not None
    assert usuario.id is not None
    assert cliente.id is not None
    ed_id = editorial.id
    usr_id = usuario.id
    cli_id = cliente.id

    libro = Libro(
        isbn=f"978-STK-{suffix}",
        titulo="El Aleph",
        precio=Decimal("18500.00"),
        stock=10,
        editorial_id=ed_id,
    )
    venta = Venta(
        cliente_id=cli_id,
        total=Decimal("37000.00"),
    )
    db_session.add_all([libro, venta])
    await db_session.commit()
    assert libro.id is not None
    assert venta.id is not None
    libro_id = libro.id
    venta_id = venta.id

    # 1. Movimiento positivo (alta/reposición sin venta) y negativo (venta) persisten y navegan bidireccionalmente
    mov_alta = MovimientoStock(
        libro_id=libro_id,
        venta_id=None,
        usuario_id=usr_id,
        cantidad=10,
        motivo="ALTA_INICIAL",
    )
    mov_venta = MovimientoStock(
        libro_id=libro_id,
        venta_id=venta_id,
        usuario_id=usr_id,
        cantidad=-2,
        motivo="VENTA",
    )
    db_session.add_all([mov_alta, mov_venta])
    await db_session.commit()
    assert mov_alta.id is not None
    assert mov_venta.id is not None
    mov_alta_id = mov_alta.id

    stmt_mov = (
        select(MovimientoStock)
        .where(MovimientoStock.id == mov_venta.id)
        .options(
            joinedload(MovimientoStock.libro),
            joinedload(MovimientoStock.usuario),
            joinedload(MovimientoStock.venta),
        )
    )
    loaded_mov = (await db_session.execute(stmt_mov)).scalar_one()
    assert loaded_mov.libro.id == libro_id
    assert loaded_mov.usuario.id == usr_id
    assert loaded_mov.venta is not None
    assert loaded_mov.venta.id == venta_id
    assert loaded_mov.cuando.tzinfo is not None

    # 2. cantidad == 0 rechazado por CHECK (ck_movimiento_stock_cantidad_no_cero)
    db_session.add(
        MovimientoStock(
            libro_id=libro_id,
            venta_id=None,
            usuario_id=usr_id,
            cantidad=0,
            motivo="INVALIDO_CERO",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 3. UPDATE sobre movimiento_stock es rechazado por el disparador trg_movimiento_stock_append_only (RN-12, C-14)
    with pytest.raises(DBAPIError):
        await db_session.execute(
            text("UPDATE movimiento_stock SET cantidad = 999 WHERE id = :id"),
            {"id": mov_alta_id},
        )
    await db_session.rollback()

    # 4. DELETE sobre movimiento_stock es rechazado por el disparador trg_movimiento_stock_append_only (RN-12, C-14)
    with pytest.raises(DBAPIError):
        await db_session.execute(
            text("DELETE FROM movimiento_stock WHERE id = :id"),
            {"id": mov_alta_id},
        )
    await db_session.rollback()

    # 5. Verificar que la fila permanece intacta tras ambos rechazos
    stmt_check = select(MovimientoStock).where(MovimientoStock.id == mov_alta_id)
    intact_mov = (await db_session.execute(stmt_check)).scalar_one()
    assert intact_mov.cantidad == 10
    assert intact_mov.motivo == "ALTA_INICIAL"

