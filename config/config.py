# -*- coding: utf-8 -*-
"""
StandardLibrary v1.4
配置读取，并转化为对象
TODO support network file？
"""

__all__ = ['config', 'sync']

import os
import re
import sys
import json
# 从typing导入类提示的基类，以判断类提示
from typing import _GenericAlias, Union, Optional, Any

try:
    import yaml
except ImportError as yaml_import_error:
    yaml = None


class ConfigError(Exception):
    """
    配置报错
    TODO 优化报错提示
    """

    def __init__(self, expect: object, k: str = None, reason: str = '', sub_expect: str = ''):
        self.expect = str(expect) + '/' + sub_expect if sub_expect else str(expect)
        self.k = k
        self.reason = reason


class Propagate:
    """
    基类，用于支持上报(文件同步)功能
    """
    _father: Optional['Propagate']

    def __init__(self, father: Optional['Propagate'] = None):
        self._father = father

    def _propagate(self):
        if self._father is not None:
            self._father._propagate()


class PropagateCallback(Propagate):
    """
    配置修改事件的回调函数，用于支持上报(文件同步)
    """

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
    """
    list类，添加propagate方法以支持上报
    可用dump方法序列化为一般list
    """

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
    """
    dict类，添加propagate方法以支持上报
    可用getattr方法调用dict.getitem
    e.g. d = _Dict({'a': 1}); d.a -> 1
    可用dump方法序列化为一般dict
    """

    def __init__(self, seq=(), father=None):
        Propagate.__init__(self, father)
        dict.__init__(self, seq)

    def __getattr__(self, key):
        if key.startswith('_'):
            return super().__getattribute__(key)
        else:
            return super().__getitem__(key)

    def __setattr__(self, key, value):
        if key.startswith('_'):
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


class Cmd:
    _dict = {
        'str': str,
        'int': int,
        'float': float
    }

    def __init__(self, key: str, prefix: str = '-', short: str = True, expect: Union[type, str] = str):
        """
        Cmd类配置 e.g. host
        :param key: 配置键
        :param short: 缩写，True为key首字母, False取消缩写
        :param prefix: 前缀 e.g. - / --
        :param expect: 期望类 str/int/bool 如为bool键存在即为true
                        特殊的，可以使用str类型的"str"/"int" 表示接受无参
        """
        self.key = prefix + key
        self.short = short and prefix + (key[0] if short is True else short)
        self.expect = expect

    def get_value(self):
        """
        从命令行获取值
        :return: value/False
        """
        index = self.key in sys.argv and sys.argv.index(self.key) \
                or self.short and self.short in sys.argv and sys.argv.index(self.short)
        if index:
            index += 1
            if self.expect == bool:
                return True
            elif self.expect in self._dict:
                if index < len(sys.argv):
                    return self._dict[self.expect](sys.argv[index])
                else:
                    return True
            elif index < len(sys.argv):
                return sys.argv[index]
            else:
                raise ValueError('%s must have param (type %s)' % (self.key, self.expect))
        else:
            return False

    def format(self, value):
        """
        格式化值
        :param value: 值（配置文件中）
        :return: value （格式化后）
        """
        if self.expect in self._dict:
            if isinstance(value, bool):
                return value
            else:
                return self._dict[self.expect](value)
        else:
            return self.expect(value)


def isbuildin(_type) -> bool:
    """
    判断一个类型是否是内置类
    :param _type: 类 str/int ...
    :return bool
    """
    return _type in [str, int, float, list, dict, bool]


def istyping(_type) -> bool:
    """
    判断一个类型是否是类标注
    :param _type: 类 List[str]...
    :return: bool
    """
    return isinstance(_type, _GenericAlias)


def get_default(obj: object) -> dict:
    """
    获取对象的默认值, 对于函数类默认值，会在取用时调用(要求无参)
    :param obj: 对象
    :return:
    """
    return {k: v for k, v in obj.__dict__.items() if not k.startswith('__')}


def buildin2expect(value, _type, father=None):
    """
    将值转为内置类型
    :param value: 值
    :param _type: 期望类型
    :param father: 父配置，用于支持上报
    :return: 配置
    """
    if _type == str:
        return str(value)
    elif _type == int:
        if isinstance(value, int):
            return value
        elif isinstance(value, str) or isinstance(value, float) and re.search('^[0-9 *]+$', value):
            # e.g. 3600 * 8
            return eval(value)
        else:
            int(value)
    elif _type == bool:
        return bool(value)
    elif _type == list or _type == dict:
        return config2obj(value, father=father)
    else:
        raise TypeError


def typing2expect(value, _type: _GenericAlias, father=None):
    """
    将配置转为预期typing
    :param value: 配置
    :param _type: 预期typing
    :param father: 福配置，用于同步文件
    :return: 配置对象
    """
    if _type.__origin__ == list:
        return _List((config2expect(i, _type.__args__[0], father=father) for i in value), father=father)
    elif _type.__origin__ == dict:
        return _Dict(
            ((buildin2expect(k, _type.__args__[0]), config2expect(v, _type.__args__[1], father=father)) for k, v in
             value.items()), father=father)
    elif _type.__origin__ == Union:
        default = None
        for t in _type.__args__:
            if istyping(t):
                if isinstance(value, t.__origin__):
                    return config2expect(value, t, father=father)
            elif isinstance(t, Cmd):
                if t.get_value():
                    return t.get_value()
                default = t
            elif not isbuildin(t):
                default = t
            elif isinstance(value, t):
                return config2expect(value, t, father=father)
        else:
            if default:
                return config2expect(value, default, father=father)
            else:
                raise TypeError
    else:
        # TODO else type ?
        return config2obj(value)


def dict2obj(value: dict, expect: type, father=None):
    """
    将字典配置转为预期对象
    使用此方法转换的对象不能使用hasattr
    :param value: 配置
    :param expect: 预期类
    :param father: 福配置，用于同步文件
    :return: 配置对象
    """
    d = _Dict(father=father)
    default = get_default(expect)
    k = None
    try:
        if '__annotations__' in expect.__dict__:
            # 类标注处理
            for k, _type in expect.__annotations__.items():
                if isinstance(_type, Cmd):
                    v = _type.get_value() \
                        or k in value and _type.format(value[k]) \
                        or k in default and _type.format(default[k])
                    if v:
                        d[k] = v
                    else:
                        raise ConfigError(expect, k, 'missing config')
                elif k in value:
                    d[k] = config2expect(value[k], _type)
                elif k in default:
                    d[k] = get_value(default[k], father=father)
                elif not isbuildin(_type) and not istyping(_type):
                    d[k] = config2expect({}, _type)
                else:
                    raise ConfigError(expect, k, 'missing config')

    except ValueError as err:
        raise ConfigError(expect, k, err.args[0])
    except TypeError as err:
        raise ConfigError(expect, k, err.args[0])
    except ConfigError as err:
        raise ConfigError(expect, err.k, err.reason, err.expect)

    for k, v in default.items():
        # 无标注默认值
        if k not in d:
            d[k] = get_value(v, father=d)
    for k, v in value.items():
        if k not in d:
            d[k] = config2obj(v, father=d)

    return d


def get_value(value, father=None):
    """
    识别值类型，调用函数或抽取对象默认值
    :param value: 值
    :param father: 父配置，用于同步文件
    :return:
    """
    if isinstance(value, type):
        return config2obj(get_default(value), father=father)
    elif callable(value):
        return config2obj(value(), father=father)
    else:
        return config2obj(value, father=father)


def config2obj(config, father=None):
    """
    将配置转为类
    使用此方法转换的对象不能使用hasattr
    :param config: 可为str/int/list/dict
    :param father: 父配置，用于同步文件
    :return: 对象
    """
    if isinstance(config, list):
        l = _List(father=father)
        l.extend(config2obj(c, father=l) for c in config)
        return l
    elif isinstance(config, dict):
        d = _Dict(father=father)
        for k, v in config.items():
            d[k] = config2obj(v, father=d)
        return d
    else:
        return config


def config2expect(config: Any, expect: type, father=None):
    """
    将配置转为预期类，并根据期望对象提供默认值/类型检查
    使用此方法转换的对象不能使用hasattr
    :param config: 配置
    :param expect: 期望对象
    :param father: 父配置，用于同步文件
    :return: 配置对象
    """
    if isbuildin(expect):
        return buildin2expect(config, expect, father=father)
    if istyping(expect):
        return typing2expect(config, expect, father=father)
    else:
        return dict2obj(config, expect, father=father)


def read_config(path: str = 'config', raw_path: str = None, expect: type = None, sync: bool = False):
    """
    读取配置文件，默认在config文件夹下寻找，可用raw_path通过绝对路径读取
    可省略后缀名，会尝试自动读取，目前支持 .yaml/.json
    """
    path = raw_path or os.path.join('config', path)
    if not os.path.exists(path):
        for i in ['.yaml', '.json']:
            if os.path.exists(path + i):
                path = path + i
                break
        else:
            raise FileNotFoundError(path)

    with open(path, mode='rt', encoding='utf-8') as f:
        if path.endswith('.yaml'):
            if not yaml:
                raise yaml_import_error
            config = yaml.safe_load(f)
        elif path.endswith('.json'):
            config = json.load(f)
        else:
            raise TypeError(f'not support config file type {path}')

    if config is None:
        config = {}

    if expect:
        try:
            config = config2expect(config, expect)
        except ConfigError as err:
            raise ConfigError('%s config error %s: %s' % (err.expect, err.k, err.reason))
    else:
        config = config2obj(config)

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
        with open(path, mode='wt', encoding='utf-8') as f:
            if path.endswith('.yaml'):
                if not yaml:
                    raise yaml_import_error
                yaml.dump(config.dump(), f)
            elif path.endswith('.json'):
                json.dump(config.dump(), f, ensure_ascii=False, indent=2)
            else:
                raise TypeError(f'not support config file type {path}')

    config._father(PropagateCallback(config, write))
    config._propagate()


def sync(config, path: str = 'config', raw_path: str = None):
    path = raw_path or os.path.join('config', path)
    _sync(config, path)


class Config:
    """
    可在此编写提示信息，详见example.py
    """
    pass


config: Config = read_config(raw_path='config', expect=Config)
