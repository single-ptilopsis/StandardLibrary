# -*- coding: utf-8 -*-
"""
StandardLibrary v1.0
异步mysql数据库
"""

import asyncio
import aiomysql

from .config import config


class DBConfig:
    def __init__(self, host, db, user, password, port=3306):
        """
        :param host:数据库ip地址
        :param port:数据库端口
        :param db:库名
        :param user:用户名
        :param password:密码
        """
        self.host = host
        self.port = port
        self.db = db
        self.user = user
        self.password = password

        self.minsize = 1
        self.maxsize = 10

        self.charset = "utf8mb4"


class DBPoolConn:
    def __init__(self, config: DBConfig):
        self.config = config
        self.__pool: aiomysql.Pool = None

    async def init_pool(self):
        self.__pool: aiomysql = await aiomysql.create_pool(
            minsize=self.config.minsize,
            maxsize=self.config.maxsize,
            charset=self.config.charset,
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            user=self.config.user,
            password=self.config.password,
        )

    async def get_conn(self) -> aiomysql.Connection:
        return await self.__pool.acquire()

    async def release(self, conn):
        return await self.__pool.release(conn)

    def __await__(self):
        return self.init_pool().__await__()


# 初始化DB配置和链接池
db_config = DBConfig(
    config.database.host,
    config.database.db,
    config.database.user,
    config.database.password,
    config.database.port,
)

g_conn_pool = DBPoolConn(db_config)
asyncio.get_event_loop().run_until_complete(g_conn_pool)


# ---- 使用 async with 的方式来优化代码, 利用 __aenter__ 和 __aexit__ 控制async with的进入和退出处理
class DBConn(object):
    def __init__(self, commit=True):
        """
        :param commit: 是否在最后提交事务(设置为False的时候方便单元测试)
        """
        self._commit = commit

    async def __aenter__(self):

        # 从连接池获取数据库连接
        conn = await g_conn_pool.get_conn()
        await conn.ping(reconnect=True)
        cursor: aiomysql.Cursor = await conn.cursor(aiomysql.cursors.DictCursor)
        conn.autocommit = False

        self._conn = conn
        self._cursor = cursor
        return self

    async def __aexit__(self, *exc_info):
        # 提交事务
        if self._commit:
            await self._conn.commit()
        # 在退出的时候自动关闭连接和cursor
        await self._cursor.close()
        await g_conn_pool.release(self._conn)

    # ========= 一系列封装的方法
    async def insert(self, sql, params=None):
        await self.cursor.execute(sql, params)
        return self.cursor.lastrowid

    # 返回 count
    async def get_count(self, sql, params=None, count_key="count(id)"):
        await self.cursor.execute(sql, params)
        data = await self.cursor.fetchone()
        if not data:
            return 0
        return data[count_key]

    async def fetch_one(self, sql, params=None):
        await self.cursor.execute(sql, params)
        return await self.cursor.fetchone()

    async def fetch_all(self, sql, params=None):
        await self.cursor.execute(sql, params)
        return await self.cursor.fetchall()

    async def fetch_by_pk(self, sql, pk):
        await self.cursor.execute(sql, (pk,))
        return await self.cursor.fetchall()

    async def update_by_pk(self, sql, params=None):
        await self.cursor.execute(sql, params)

    async def delete(self, sql, params=None):
        await self.cursor.execute(sql, params)

    @property
    def cursor(self):
        return self._cursor
