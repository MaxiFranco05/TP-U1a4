import asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
# Import all models to register relationships
from app.modules.autores.models import Autor  # noqa: F401
from app.modules.clientes.models import Cliente
from app.modules.editoriales.models import Editorial  # noqa: F401
from app.modules.generos.models import Genero  # noqa: F401
from app.modules.libros.models import Libro, LibroAutor  # noqa: F401
from app.modules.ventas.models import Venta, RenglonVenta  # noqa: F401

async def test():
    settings = get_settings()
    engine = build_engine(settings.database_url, True)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:
        # Try to create duplicate email
        cliente1 = Cliente(nombre="Test 1", email="debug3@example.com")
        session.add(cliente1)
        await session.commit()

        cliente2 = Cliente(nombre="Test 2", email="debug3@example.com")
        session.add(cliente2)
        try:
            await session.commit()
        except IntegrityError as exc:
            print("IntegrityError caught")
            orig = exc.orig
            print(f"orig.args: {orig.args}")
            print(f"orig.detail: {getattr(orig, 'detail', 'NOT FOUND')}")
            print(f"orig.pgcode: {getattr(orig, 'pgcode', 'NOT FOUND')}")
            print(f"orig.sqlstate: {getattr(orig, 'sqlstate', 'NOT FOUND')}")
            print(f"orig.driver_exception: {getattr(orig, 'driver_exception', 'NOT FOUND')}")
            if hasattr(orig, 'driver_exception') and orig.driver_exception:
                de = orig.driver_exception
                print(f"driver_exception type: {type(de)}")
                print(f"driver_exception args: {de.args}")
                print(f"driver_exception constraint_name: {getattr(de, 'constraint_name', 'NOT FOUND')}")
            await session.rollback()

    await engine.dispose()

asyncio.run(test())