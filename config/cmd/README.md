
# Cmd

这是一个特殊的类型提示，为支持命令行参数而存在

```python
from typing import Union

# init 参数
class Cmd:
    def __init__(self, key: str, prefix: str = '-', short: str = True, expect: Union[type, str] = str):
        """
        Cmd类配置 e.g. host
        :param key: 配置键
        :param short: 缩写，True为key首字母, False取消缩写
        :param prefix: 前缀 e.g. - / --
        :param expect: 期望类 str/int/float/bool 如为bool键存在即为true
                    特殊的，可以使用str类型的"str"/"int"/"float" 表示接受无参
        """
        ...
```

 ## 示例

```python
from config import Cmd

class MyConfig:
    host: Cmd('host') = '127.0.0.1'
    port: Cmd('port') = 36888
```

此例中，读取配置是会优先查询命令行中是否有 `-host` `-port` 参数，并读取跟随在它们后面的值。如不存在，将查询 `-h` `-p`，然后才是默认值

原参数 > 缩写 > 默认值

## 类型检查

支持 `str` `int` `float` `bool`，默认为`str`  

上面的例子中，`port`显然是int类型的配置，可用 expect 参数指定的类型

```python
from config import Cmd

class MyConfig:
    port: Cmd('port', expect=int) = 36888
```

特殊的，当expect为`bool`时，只要存在配置的键，即为True，不存在则返回False

### 复合类型

一些参数可以为True，也可以为具体的值，可传入`'str'` `'int'` `'float'` (str类型)来表示

```python
from config import Cmd

class MyConfig:
    # 默认无cd，存在键则使用默认值，有参数则使用参数
    # 当键不存在时，同bool，返回False
    cd: Cmd('cmd', expect='int')
```

## 示例

[数据库配置](./example)