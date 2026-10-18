import asyncio
from sqlalchemy import text
from app.core.database import build_engine
from app.core.config import get_settings

async def check():
    settings = get_settings()
    engine = build_engine(settings.database_url, False)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result]
        print('Tables:', tables)
    await engine.dispose()

asyncio.run(check())