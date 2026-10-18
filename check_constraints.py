import asyncio
from sqlalchemy import text
from app.core.database import build_engine
from app.core.config import get_settings

async def check():
    settings = get_settings()
    engine = build_engine(settings.database_url, False)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT conname FROM pg_constraint WHERE conrelid = 'perfil_cliente'::regclass AND contype = 'u'"))
        for row in result:
            print('perfil_cliente unique:', row[0])
        result = await conn.execute(text("SELECT conname FROM pg_constraint WHERE conrelid = 'perfil_cliente'::regclass AND contype = 'f'"))
        for row in result:
            print('perfil_cliente fk:', row[0])
    await engine.dispose()

asyncio.run(check())