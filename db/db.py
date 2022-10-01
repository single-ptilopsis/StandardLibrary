# -*- coding: utf-8 -*-
"""
StandardLibrary v1.2
异步mysql数据库
"""

import asyncio
import aiomysql

from .config import config


class DBConfig:
    host: str = '127.0.0.1'
    port: int = 3306
    user: str = 'root'
    password: str
    db: str

    minsize: int = 1
    maxsize: int = 10
    charset: str = 'utf8'

    default: bool = False
    mark: str = ''

    def __init__(self, **kwargs):
        self.host = kwargs.get('host', '127.0.0.1')
        self.port = kwargs.get('port', 3306)
        self.user = kwargs.get('user', 'root')
        self.password = kwargs['password']
        self.db = kwargs['db']

        self.minsize = kwargs.get('minsize', 1)
        self.maxsize = kwargs.get('maxsize', 10)
        self.charset = kwargs.get('charset', 'utf8')

        self.default = kwargs.get('default', False)
        self.mark = kwargs.get('mark') or self.db

    @property
    def params(self):
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'db': self.db,

            'minsize': self.minsize,
            'maxsize': self.maxsize,
            'charset': self.charset
        }


default = ''
g_conn_pool = {}


async def init_pool(config: DBConfig):
    pool = await aiomysql.create_pool(**config.params)
    g_conn_pool[config.mark] = pool


if isinstance(config.database, dict):
    config = DBConfig(**config.database)
    default = config.mark
    g_conn_pool[config.mark] = init_pool(config)

else:
    if len(config.database) == 1:
        default = DBConfig(**config.database[0]).mark

    for conf in config.database:
        conf = DBConfig(**conf)
        if conf.mark in g_conn_pool:
            raise ValueError(f'exist database {conf.mark}')
        g_conn_pool[conf.mark] = init_pool(conf)

        if conf.default:
            if default != '':
                raise ValueError('default database already exists')
            default = conf.mark

asyncio.get_event_loop().run_until_complete(asyncio.gather(*[pool for pool in g_conn_pool.values()]))


# ---- 使用 async with 的方式来优化代码, 利用 __aenter__ 和 __aexit__ 控制async with的进入和退出处理
class DBConn(object):
    def __init__(self, db: str = default, commit=True):
        """
        :param commit: 是否在最后提交事务(设置为False的时候方便单元测试)
        """
        self.db = db
        self._commit = commit

    async def __aenter__(self):

        # 从连接池获取数据库连接
        conn = await g_conn_pool[self.db].acquire()
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
        await g_conn_pool[self.db].release(self._conn)

    # ========= 一系列封装的方法
    async def insert(self, sql, params=None):
        await self.cursor.execute(sql, params)
        return self.cursor.lastrowid

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
