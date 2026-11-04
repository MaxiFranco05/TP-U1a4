"""Tests bajo Strict TDD para C-17: Seed canónico, casos de prueba C-01..C-16, evidencias y despliegue Docker."""

from collections.abc import AsyncGenerator
from decimal import Decimal
from pathlib import Path
import zipfile
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.core.security import verify_password
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.ventas.models import RenglonVenta, Venta

EXPECTED_14_TABLES = {
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
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Provee la fábrica de sesiones contra PostgreSQL y limpia las tablas al finalizar."""
    settings = get_settings()
    engine = build_engine(settings.database_url, sql_echo=False)
    factory = build_session_factory(engine)
    yield factory
    async with factory() as cleanup_session:
        res = await cleanup_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
            )
        )
        existing_tables = {row[0] for row in res.fetchall()}
        if EXPECTED_14_TABLES.issubset(existing_tables):
            await cleanup_session.execute(
                text(
                    "TRUNCATE TABLE movimiento_stock, renglon_venta, venta, asignacion_rol, "
                    "intento_acceso, evento_seguridad, perfil_cliente, cliente, libro_autor, "
                    "libro, genero, autor, editorial, usuario RESTART IDENTITY CASCADE"
                )
            )
            await cleanup_session.commit()
    await engine.dispose()


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión asincrónica conectada a PostgreSQL."""
    async with session_factory() as session:
        yield session
        await session.rollback()


class TestSeedCanonico:
    """Pruebas del script canónico seed.py (Tarea 1.1)."""

    @pytest.mark.asyncio
    async def test_seed_populates_exact_canonical_state(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Scenario: Ejecución de seed() vacía y carga el estado exacto del Parcial."""
        import seed

        await seed.seed()

        # 1. Usuarios (5) y roles
        users_stmt = select(Usuario).order_by(Usuario.id)
        users = (await db_session.execute(users_stmt)).scalars().all()
        assert len(users) == 5

        email_to_user = {u.email: u for u in users}
        assert "admin@example.com" in email_to_user
        assert "admin2@example.com" in email_to_user
        assert "vendedor@example.com" in email_to_user
        assert "ana@example.com" in email_to_user
        assert "nuevo@example.com" in email_to_user

        # Verificar activo y debe_cambiar_password
        assert email_to_user["nuevo@example.com"].debe_cambiar_password is True
        assert email_to_user["admin@example.com"].debe_cambiar_password is False

        # Verificar roles vigentes
        roles_stmt = select(AsignacionRol).where(AsignacionRol.revocada_en.is_(None))
        roles = (await db_session.execute(roles_stmt)).scalars().all()
        user_roles = {r.usuario_id: r.rol for r in roles}

        assert user_roles[email_to_user["admin@example.com"].id] == "ADMIN"
        assert user_roles[email_to_user["admin2@example.com"].id] == "ADMIN"
        assert user_roles[email_to_user["vendedor@example.com"].id] == "VENDEDOR"
        assert user_roles[email_to_user["ana@example.com"].id] == "CLIENTE"
        assert user_roles[email_to_user["nuevo@example.com"].id] == "VENDEDOR"

        # Verificar passwords hasheadas con bcrypt
        assert await verify_password(seed.PASSWORDS["admin@example.com"], email_to_user["admin@example.com"].password_hash)
        assert await verify_password(seed.PASSWORDS["vendedor@example.com"], email_to_user["vendedor@example.com"].password_hash)
        assert await verify_password(seed.PASSWORDS["ana@example.com"], email_to_user["ana@example.com"].password_hash)
        assert await verify_password(seed.PASSWORDS["nuevo@example.com"], email_to_user["nuevo@example.com"].password_hash)

        # 2. Catálogo: 3 editoriales, 3 géneros, 6 autores
        ed_res = (await db_session.execute(select(Editorial))).scalars().all()
        assert len(ed_res) == 3

        gen_res = (await db_session.execute(select(Genero))).scalars().all()
        assert len(gen_res) == 3

        aut_res = (await db_session.execute(select(Autor))).scalars().all()
        assert len(aut_res) == 6

        # 3. Libros (5) con stock actual exacto
        libros_res = (await db_session.execute(select(Libro).order_by(Libro.id))).scalars().all()
        assert len(libros_res) == 5

        libros_dict = {l.titulo: l for l in libros_res}
        assert libros_dict["Rayuela"].stock == 10
        assert libros_dict["Rayuela"].precio == Decimal("25000.00")

        assert libros_dict["Antología de la literatura fantástica"].stock == 5
        assert libros_dict["Antología de la literatura fantástica"].precio == Decimal("30000.00")

        assert libros_dict["Ficciones"].stock == 8
        assert libros_dict["Ficciones"].precio == Decimal("22000.00")

        assert libros_dict["Respiración artificial"].stock == 3
        assert libros_dict["Respiración artificial"].precio == Decimal("18000.00")

        assert libros_dict["Bestiario"].stock == 1
        assert libros_dict["Bestiario"].precio == Decimal("15000.00")

        # 4. Clientes (3)
        cli_res = (await db_session.execute(select(Cliente).order_by(Cliente.id))).scalars().all()
        assert len(cli_res) == 3
        cli_dict = {c.nombre: c for c in cli_res}

        assert cli_dict["Lucía Fernández"].usuario_id is None
        # Perfil de Lucía
        perf_stmt = select(PerfilCliente).where(PerfilCliente.cliente_id == cli_dict["Lucía Fernández"].id)
        lucia_perfil = (await db_session.execute(perf_stmt)).scalar_one_or_none()
        assert lucia_perfil is not None
        assert lucia_perfil.telefono == "11-4567-8901"
        assert lucia_perfil.direccion == "Av. Corrientes 1234"

        assert cli_dict["Tomás Ríos"].usuario_id is None
        tomas_perf = (await db_session.execute(select(PerfilCliente).where(PerfilCliente.cliente_id == cli_dict["Tomás Ríos"].id))).scalar_one_or_none()
        assert tomas_perf is None

        assert cli_dict["Ana Paz"].usuario_id == email_to_user["ana@example.com"].id

        # 5. Venta 1 de Lucía Fernández registrada por vendedor@example.com
        ventas_res = (await db_session.execute(select(Venta))).scalars().all()
        assert len(ventas_res) == 1
        v1 = ventas_res[0]
        assert v1.cliente_id == cli_dict["Lucía Fernández"].id
        assert v1.total == Decimal("69000.00")

        renglones_res = (await db_session.execute(select(RenglonVenta).where(RenglonVenta.venta_id == v1.id))).scalars().all()
        assert len(renglones_res) == 2
        renglones_by_libro = {r.libro_id: r for r in renglones_res}
        assert renglones_by_libro[libros_dict["Rayuela"].id].cantidad == 1
        assert renglones_by_libro[libros_dict["Rayuela"].id].precio_unitario == Decimal("25000.00")
        assert renglones_by_libro[libros_dict["Ficciones"].id].cantidad == 2
        assert renglones_by_libro[libros_dict["Ficciones"].id].precio_unitario == Decimal("22000.00")

        # 6. Movimientos de stock (7) y cumplimiento de la invariante
        movs = (await db_session.execute(select(MovimientoStock).order_by(MovimientoStock.id))).scalars().all()
        assert len(movs) == 7

        # Invariante libro.stock == SUM(movimiento_stock.cantidad)
        for libro in libros_res:
            suma_movs = sum(m.cantidad for m in movs if m.libro_id == libro.id)
            assert libro.stock == suma_movs, f"Invariante rota para {libro.titulo}: stock {libro.stock} != sum {suma_movs}"

        # 7. Historial de seguridad (1)
        ev_res = (await db_session.execute(select(EventoSeguridad))).scalars().all()
        assert len(ev_res) == 1
        assert ev_res[0].actor == "SISTEMA"
        assert ev_res[0].accion == "Carga de los datos iniciales"


class TestSoloAgregadoYEvidencias:
    """Pruebas del script solo_agregado.sql y archivos de evidencia (Tarea 2.1 y 2.2)."""

    def test_solo_agregado_sql_file_exists(self) -> None:
        """Scenario: Existe el archivo test/solo_agregado.sql con UPDATE y DELETE."""
        sql_path = Path("test/solo_agregado.sql")
        assert sql_path.exists(), "Falta test/solo_agregado.sql"
        content = sql_path.read_text(encoding="utf-8").upper()
        assert "UPDATE MOVIMIENTO_STOCK" in content
        assert "DELETE FROM MOVIMIENTO_STOCK" in content

    @pytest.mark.asyncio
    async def test_trigger_rejects_update_and_delete_on_movimiento_stock(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Scenario: PostgreSQL rechaza UPDATE y DELETE con la excepción del trigger."""
        # Tomar un movimiento existente
        mov_res = await db_session.execute(select(MovimientoStock).limit(1))
        mov = mov_res.scalar_one_or_none()
        if mov is None:
            await db_session.rollback()
            import seed
            await seed.seed()
            mov = (await db_session.execute(select(MovimientoStock).limit(1))).scalar_one()
        mov_id = mov.id

        # Intento de UPDATE
        with pytest.raises(DBAPIError) as exc_update:
            await db_session.execute(
                text(f"UPDATE movimiento_stock SET cantidad = 99 WHERE id = {mov_id}")
            )
        await db_session.rollback()
        assert "sólo agregado" in str(exc_update.value).lower() or "append" in str(exc_update.value).lower() or "trg_movimiento_stock" in str(exc_update.value).lower()

        # Intento de DELETE
        with pytest.raises(DBAPIError) as exc_delete:
            await db_session.execute(
                text(f"DELETE FROM movimiento_stock WHERE id = {mov_id}")
            )
        await db_session.rollback()
        assert "sólo agregado" in str(exc_delete.value).lower() or "append" in str(exc_delete.value).lower() or "trg_movimiento_stock" in str(exc_delete.value).lower()

    def test_parcial_casos_http_file_exists_and_covers_c01_to_c16(self) -> None:
        """Scenario: test/parcial_casos.http cubre casos C-01 a C-16 con comentarios y @name."""
        http_path = Path("test/parcial_casos.http")
        assert http_path.exists(), "Falta test/parcial_casos.http"
        content = http_path.read_text(encoding="utf-8")
        for i in range(1, 17):
            case_tag = f"C-{i:02d}"
            assert case_tag in content, f"Falta caso {case_tag} en test/parcial_casos.http"
        assert "@name" in content
        assert "@no-cookie-jar" in content

    def test_evidencia_directory_and_files_exist(self) -> None:
        """Scenario: La carpeta evidencia/ contiene c14_solo_agregado.txt y c15_sin_nplusone.txt."""
        evidencia_dir = Path("evidencia")
        assert evidencia_dir.exists(), "Falta carpeta evidencia/"
        c14_path = evidencia_dir / "c14_solo_agregado.txt"
        assert c14_path.exists(), "Falta evidencia/c14_solo_agregado.txt"
        c15_path = evidencia_dir / "c15_sin_nplusone.txt"
        assert c15_path.exists(), "Falta evidencia/c15_sin_nplusone.txt"


class TestDespliegueDockerYEmpaquetado:
    """Pruebas para la carpeta despliegue/ y scripts/empaquetar_entrega.py (Tareas 3 y 4)."""

    def test_despliegue_directory_structure(self) -> None:
        """Scenario: La carpeta despliegue/ contiene el TP 1-4 y artefactos de despliegue."""
        despliegue_dir = Path("despliegue")
        assert despliegue_dir.exists(), "Falta carpeta despliegue/"
        assert (despliegue_dir / "app").exists(), "Falta despliegue/app/"
        assert (despliegue_dir / "migrations").exists(), "Falta despliegue/migrations/"
        assert (despliegue_dir / "seed_db.py").exists(), "Falta despliegue/seed_db.py"
        assert (despliegue_dir / "requirements.txt").exists(), "Falta despliegue/requirements.txt"
        assert (despliegue_dir / "alembic.ini").exists(), "Falta despliegue/alembic.ini"
        assert (despliegue_dir / "Dockerfile").exists(), "Falta despliegue/Dockerfile"
        assert (despliegue_dir / ".dockerignore").exists(), "Falta despliegue/.dockerignore"
        assert (despliegue_dir / "env.example").exists(), "Falta despliegue/env.example"
        assert (despliegue_dir / "DEPLOY.md").exists(), "Falta despliegue/DEPLOY.md"
        assert (despliegue_dir / "evidencia").exists(), "Falta despliegue/evidencia/"

    def test_dockerfile_specifications(self) -> None:
        """Scenario: despliegue/Dockerfile cumple D-01..D-07."""
        df_content = Path("despliegue/Dockerfile").read_text(encoding="utf-8")
        assert "python:3.12-alpine" in df_content, "Debe basarse en python:3.12-alpine (D-01)"
        assert "pip install" in df_content and "--no-cache-dir" in df_content
        assert "USER appuser" in df_content or "USER" in df_content, "Debe correr como usuario no root (D-07)"
        assert "HEALTHCHECK" in df_content, "Debe tener HEALTHCHECK (D-03)"
        assert "/health/ready" in df_content, "HEALTHCHECK debe apuntar a /health/ready"
        assert "alembic upgrade head" in df_content, "CMD debe ejecutar alembic upgrade head (D-02)"
        assert "uvicorn" in df_content and "0.0.0.0" in df_content, "Uvicorn debe escuchar en 0.0.0.0"

        # Sin secretos
        for secret in ("secret", "password", "postgres://", "postgresql+asyncpg://"):
            assert secret not in df_content.lower(), f"Dockerfile no debe contener secretos: {secret}"

    def test_dockerignore_exclusions(self) -> None:
        """Scenario: despliegue/.dockerignore excluye .env, .venv, .git, __pycache__."""
        di_content = Path("despliegue/.dockerignore").read_text(encoding="utf-8")
        assert ".env" in di_content
        assert ".venv" in di_content
        assert ".git" in di_content
        assert "__pycache__" in di_content

    def test_deploy_md_documentation(self) -> None:
        """Scenario: despliegue/DEPLOY.md documenta URL, docker commands y tabla D-01..D-08."""
        deploy_content = Path("despliegue/DEPLOY.md").read_text(encoding="utf-8")
        assert "docker build" in deploy_content
        assert "docker run" in deploy_content
        assert "D-01" in deploy_content
        assert "D-08" in deploy_content

    def test_empaquetar_entrega_generates_valid_zip(self, tmp_path: Path) -> None:
        """Scenario: scripts/empaquetar_entrega.py empaqueta parcial/ y despliegue/ sin exclusiones."""
        import scripts.empaquetar_entrega as packager

        target_zip = tmp_path / "entrega_test.zip"
        packager.crear_paquete_entrega(target_zip)

        assert target_zip.exists()
        with zipfile.ZipFile(target_zip, "r") as zf:
            namelist = zf.namelist()
            # Debe contener parcial/ y despliegue/
            has_parcial = any(name.startswith("parcial/") for name in namelist)
            has_despliegue = any(name.startswith("despliegue/") for name in namelist)
            assert has_parcial, "El zip debe contener carpeta parcial/"
            assert has_despliegue, "El zip debe contener carpeta despliegue/"

            # No debe contener .venv, .git, .env ni __pycache__
            for name in namelist:
                assert "/.venv/" not in name and not name.startswith(".venv/"), f"Zip contiene archivo excluido: {name}"
                assert "/.git/" not in name and not name.startswith(".git/"), f"Zip contiene archivo excluido: {name}"
                assert "/__pycache__/" not in name and not name.startswith("__pycache__/"), f"Zip contiene archivo excluido: {name}"
                assert not name.endswith(".env"), f"Zip contiene archivo de entorno: {name}"
