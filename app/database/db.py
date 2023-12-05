import os

from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()

user = os.environ.get('USER')
password = os.environ.get('PASSWORD')
host = os.environ.get('HOST')
port = os.environ.get('PORT')
name = os.environ.get('NAME')

class Base(DeclarativeBase):
    pass

class DatabaseSessionManager:
    def __init__(self, url: str):
        self._engine = create_async_engine(url, echo=True)
        self._session_maker = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)

    async def session(self):
        async with self._session_maker() as session:
            yield session

url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
sessionmanager = DatabaseSessionManager(url)
engine = create_async_engine(url)

async def get_db() -> AsyncSession:
    async for session in sessionmanager.session():
        yield session