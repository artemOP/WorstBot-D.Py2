from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Any, Iterable, Sequence


class Record(asyncpg.Record):
    def __getattr__(self, name: str) -> Any:
        return self[name]


class Pool:
    _pool: asyncpg.Pool

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        record_class = self.kwargs.pop("record_class", Record)
        self._pool = await asyncpg.create_pool(*self.args, record_class=record_class, setup=self._setup, **self.kwargs)  # type: ignore
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        await self._pool.close()

    def __str__(self) -> str:
        return "Custom asyncpg connection pool"

    async def _setup(self, conn: asyncpg.Connection) -> asyncpg.Connection:
        await conn.set_type_codec("numeric", encoder=str, decoder=float, schema="pg_catalog", format="text")
        return conn

    async def fetch(self, sql: str, *args) -> list[Record] | None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    async def fetchrow(self, sql: str, *args) -> Record | None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchrow(sql, *args)

    async def fetchval(self, sql: str, *args) -> Any:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def execute(self, sql: str, *args) -> Any:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def executemany(self, sql: str, args: Iterable[Sequence]) -> Any:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                return await conn.executemany(sql, args)
