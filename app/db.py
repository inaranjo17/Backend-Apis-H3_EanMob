import aiomysql
from .config import settings
 
_pool: aiomysql.Pool | None = None
 
 
async def get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            db=settings.db_name,
            autocommit=True,
            minsize=1,
            maxsize=5,
            charset="utf8mb4",
        )
    return _pool
 
 
async def close_pool():
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None