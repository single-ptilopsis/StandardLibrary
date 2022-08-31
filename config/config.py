# -*- coding: utf-8 -*-
"""
StandardLibrary v1.1
配置读取，并转化为对象
TODO support network file？
TODO 读取类提示，默认值
"""

__all__ = ["config"]

import os
import json

try:
    import yaml
except ImportError as yaml_import_error:
    yaml = None


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


class Config:
    """
    可在此编写提示信息，详见example.py
    """
    pass


def read_config(path: str = "config", raw_path: str = None):
    """
    读取配置文件，默认在config文件夹下寻找，可用raw_path通过绝对路径读取
    可省略后缀名，会尝试自动读取，目前支持 .yaml/.json
    """
    path = raw_path or os.path.join("config", path)
    if not os.path.exists(path):
        for i in [".yaml", ".json"]:
            if os.path.exists(path + i):
                path = path + i
                break
        else:
            raise FileNotFoundError(path)

    with open(path, mode="rt", encoding="utf-8") as f:
        if path.endswith(".yaml"):
            if not yaml:
                raise yaml_import_error
            return dict2obj(yaml.safe_load(f))
        elif path.endswith(".json"):
            return dict2obj(json.load(f))
        else:
            raise TypeError(f"not support config file type {path}")


config: Config = read_config(raw_path="config")
