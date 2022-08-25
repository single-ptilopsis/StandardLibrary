# -*- coding: utf-8 -*-
"""
StandardLibrary v1.0
配置读取，并转化为对象
"""

__all__ = ["config"]

import os
import yaml


class _Dict(dict):
    __setattr__ = dict.__setitem__
    __getattr__ = dict.__getitem__


def dict2obj(dic):
    """
    将字典转为类
    使用此方法转换的对象不能使用hasattr
    :param dic: 字典
    :return: 对象
    """
    if not isinstance(dic, dict):
        return dic
    d = _Dict()
    for k, v in dic.items():
        if isinstance(v, list):
            v = [dict2obj(i) for i in v]
        d[k] = dict2obj(v)
    return d


class Database:
    host: str
    port: int
    user: str
    password: str
    db: str


class Config:
    # database配置提示
    database: Database


def read_config(path="config.yaml", raw_path=None):
    """
    读取配置文件，默认在config文件夹下寻找，可用raw_path通过绝对路径读取
    """
    with open(raw_path or os.path.join("config", path), mode="rt", encoding="utf-8") as f:
        return dict2obj(yaml.safe_load(f))


config: Config = read_config(raw_path="config.yaml")

# 如果你的编辑器支持，那么很容易就能找到database的各项配置并补全
# 这破字典我是一天也看不下去了（
host = config.database.host
