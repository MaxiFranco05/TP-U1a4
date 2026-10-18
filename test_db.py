import asyncio
from sqlalchemy import text

async def test():
    from app.core.config import get_settings
    from app.core.database import build_engine
    settings = get_settings()
    engine = build_engine(settings.database_url, settings.sql_echo)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Query result:", result.scalar())
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            print("Tables:", tables)
    except Exception as e:
        print("Error:", e)
    await engine.dispose()

asyncio.run(test())