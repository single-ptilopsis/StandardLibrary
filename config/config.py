# -*- coding: utf-8 -*-
"""
StandardLibrary v1.2
配置读取，并转化为对象
TODO support network file？
"""

__all__ = ["config", "sync"]

import os
import re
import json
# 从typing导入类提示的基类，以判断类提示
from typing import _GenericAlias, Optional

try:
    import yaml
except ImportError as yaml_import_error:
    yaml = None


class ConfigError(Exception):
    """
    配置报错
    TODO 优化报错显示
    """

    def __init__(self, expect: object, k: str = None, reason: str = "", sub_expect: str = ""):
        self.expect = str(expect) + "/" + sub_expect if sub_expect else str(expect)
        self.k = k
        self.reason = reason


class Propagate:
    """
    基类，用于支持上报(文件同步)功能
    """
    _father: Optional["Propagate"]

    def __init__(self, father: Optional["Propagate"] = None):
        self._father = father

    def _propagate(self):
        if self._father is not None:
            self._father._propagate()


class PropagateCallback(Propagate):
    # 配置修改事件的回调函数
    def __init__(self, config, callback):
        """
        :param config: 配置对象
        :param callback: 回调函数，接收配置为参数
        """
        self.config = config
        self.callback = callback

    def _propagate(self):
        self.callback(self.config)


class _List(Propagate, list):
    def __init__(self, seq=(), father=None):
        Propagate.__init__(self, father)
        list.__init__(self, seq)

    def __getitem__(self, item):
        return list.__getitem__(self, item)

    def __setitem__(self, key, value):
        super(self).__setitem__(key, value)
        self._propagate()

    def pop(self, index: int = ...):
        r = super().pop(index)
        self._propagate()
        return r

    def append(self, object) -> None:
        super().append(object)
        self._propagate()

    def remove(self, object) -> None:
        super().remove(object)
        self._propagate()

    def reverse(self) -> None:
        super().reverse()
        self._propagate()

    def insert(self, index: int, object) -> None:
        super().insert(index, object)
        self._propagate()

    def extend(self, iterable) -> None:
        super().extend(iterable)
        self._propagate()

    def clear(self) -> None:
        super().clear()
        self._propagate()

    def dump(self) -> list:
        return [i.dump() if isinstance(i, _List) or isinstance(i, _Dict) else i for i in self.copy()]


class _Dict(Propagate, dict):
    def __init__(self, seq=(), father=None):
        Propagate.__init__(self, father)
        dict.__init__(self, seq)

    def __getattr__(self, key):
        if key.startswith("_"):
            return super().__getattribute__(key)
        else:
            return super().__getitem__(key)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            super().__setitem__(key, value)
        self._propagate()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._propagate()

    def pop(self, k):
        r = super().pop(k)
        self._propagate()
        return r

    def update(self, __m, **kwargs) -> None:
        super().update(__m, **kwargs)
        self._propagate()

    def clear(self) -> None:
        super().clear()
        self._propagate()

    def dump(self) -> dict:
        return {k: (v.dump() if isinstance(v, _List) or isinstance(v, _Dict) else v) for k, v in self.copy().items()}


def dict2obj(dic, father=None):
    """
    将字典转为类
    使用此方法转换的对象不能使用hasattr
    :param dic: 字典
    :param father: 父配置，用于同步文件
    :return: 对象
    """
    if not isinstance(dic, dict):
        return dic
    d = _Dict(father=father)
    for k, v in dic.items():
        if isinstance(v, list):
            v = _List((dict2obj(i, father=father) for i in v), father=father)
        d[k] = dict2obj(v, father=d)
    return d


def isbuildin(_type):
    # 判断一个类型是否是内置类
    return _type in [str, int, list, dict] or isinstance(_type, _GenericAlias)


def get_default(obj: object):
    return {k: v for k, v in obj.__dict__.items() if not k.startswith("__")}


def get_value(value, _type, father=None):
    if _type == str:
        return str(value)
    elif _type == int:
        if isinstance(value, int):
            return value
        elif isinstance(value, str) and re.search("^[0-9 *]+$", value):
            return eval(value)
        else:
            int(value)
    elif _type == list:
        return _List((dict2obj(i, father=father) for i in value), father=father)
    elif _type == dict:
        return dict2obj(value, father=father)
    elif isinstance(_type, _GenericAlias):
        if not isinstance(value, _type.__origin__):
            raise TypeError(f"need {_type.__origin__} but {type(value)} is given")
        if _type.__origin__ == list:
            if isbuildin(_type.__args__[0]):
                return _List((get_value(i, _type.__args__[0], father=father) for i in value), father=father)
            else:
                return _List((dict2expect(i, _type.__args__[0], father=father) for i in value), father=father)
        elif _type.__origin__ == dict:
            if isbuildin(_type.__args__[1]):
                return _Dict(
                    ((get_value(k, _type.__args__[0]), get_value(v, _type.__args__[1], father=father)) for k, v in
                     value.items()), father=father)
            else:
                return _Dict(
                    ((get_value(k, _type.__args__[0]), dict2expect(v, _type.__args__[1], father=father)) for k, v in
                     value.items()), father=father)
        else:
            # TODO else type ?
            return dict2obj(value)
    else:
        # shouldn't happen
        raise TypeError(f"Unknown type {_type}")


def dict2expect(dic: dict, expect: object, father=None):
    """
    将字典转为类，并根据期望对象提供默认值/类型检查
    使用此方法转换的对象不能使用hasattr
    :param dic: 字典
    :param expect: 期望对象
    :param father: 父配置，用于同步文件
    :return: 对象
    """
    d = _Dict(father=father)
    default = get_default(expect)
    k = None
    try:
        if "__annotations__" in expect.__dict__:
            for k, _type in expect.__annotations__.items():
                if k in dic:
                    if isbuildin(_type):
                        d[k] = get_value(dic[k], _type, father=d)
                    else:
                        d[k] = dict2expect(dic[k], _type, father=d)
                elif k in default:
                    d[k] = default[k]
                else:
                    raise ConfigError(expect, k, "missing config")
    except ValueError as err:
        raise ConfigError(expect, k, err.args[0])
    except TypeError as err:
        raise ConfigError(expect, k, err.args[0])
    except ConfigError as err:
        raise ConfigError(expect, err.k, err.reason, err.expect)

    for k, v in default.items():
        if k not in d:
            d[k] = v

    return d


def read_config(path: str = "config", raw_path: str = None, expect: object = None, sync: bool = False):
    """
    读取配置文件，默认在config文件夹下寻找，可用raw_path通过绝对路径读取
    可省略后缀名，会尝试自动读取，目前支持 .yaml/.json
    :param path:
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
            config = yaml.safe_load(f)
        elif path.endswith(".json"):
            config = json.load(f)
        else:
            raise TypeError(f"not support config file type {path}")
    if expect:
        try:
            config = dict2expect(config, expect)
        except ConfigError as err:
            raise ConfigError("%s config error %s: %s" % (err.expect, err.k, err.reason))
    else:
        config = dict2obj(config)

    if sync:
        _sync(config, path)

    return config


def _sync(config, path: str) -> None:
    """
    将配置与文件绑定，即配置的修改会同步到文件
    config._father = None  取消绑定
    :param config: 配置，需为read_config产物
    :param path: 绝对/相对路径
    """

    def write(config):
        with open(path, mode="wt", encoding="utf-8") as f:
            if path.endswith(".yaml"):
                if not yaml:
                    raise yaml_import_error
                yaml.dump(config.dump(), f)
            elif path.endswith(".json"):
                json.dump(config.dump(), f, ensure_ascii=False, indent=2)
            else:
                raise TypeError(f"not support config file type {path}")

    config._father(PropagateCallback(config, write))
    config._propagate()


def sync(config, path: str = "config", raw_path: str = None):
    path = raw_path or os.path.join("config", path)
    _sync(config, path)


class Config:
    """
    可在此编写提示信息，详见example.py
    """
    pass


config: Config = read_config(raw_path="config", expect=Config)
