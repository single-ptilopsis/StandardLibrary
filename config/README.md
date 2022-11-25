# config

读取配置文件(.yaml/.json)，并转化为对象  
支持默认值，类型检查与格式化

## 使用

 - 修改 config.py 中 `Config` 类
   ```python
   # 以数据库配置为例
   
   class Database:
        host: str
        port: int
        user: str
        password: str
        db: str

   class Config:
       # database配置提示
       database: Database
   ``` 
 - 填写配置文件 (config.yaml)
   ```yaml
   database:
       host: '127.0.0.1'
       port: 3306
       user: 'root'
       password: 'password'
       db: 'dbname'
   ```
 - 从 config.py 中导入 `config` (默认读取工作目录下 config.yaml)
   ```python
   from config import config
   print(config.databse.host) # 127.0.0.1
   print(config.databse.port) # 3306
   ```

 - [完整示例](./example/config.py)

## 修改配置文件路径

默认读取工作目录下名为config的配置文件
```python
# 会按照 raw_name > yaml > json 顺序检查文件
# myConfig > myConfig.yaml > myConfig.json
config: Config = read_config(raw_path="myConfig")
```
值得一提的是，config.py 支持自动识别配置类型，如 .yaml/.json，所以不加后缀的路径是可行的

## 读取其他配置文件

运行时，可以通过从config.py中导入read_config方法
```python
from config import read_config

class MyConfig:
    ...

# 原始路径导入
# 当提供expect参数时，类检查/格式化才会运行
config: MyConfig = read_config(raw_path="myConfig", expect=MyConfig)


# 但有时，配置文件不止一个，因此放在一个文件夹中会更为简洁
# 从工作目录下config文件中读取 > config/myConfig
config = read_config("myConfig")
```

## 临时配置

当一些配置并不需要储存到文件（如cmd参数，[详见](./cmd)），可使用 path=False 来表明此配置是临时的

```python
from config import read_config, Cmd

class MyConfig:
    host: Cmd('host') = '127.0.0.1'
    port: Cmd('port') = 36888

config = read_config(path=False, expect=MyConfig)
```

## Typing

目前支持 `List`, `Dict`, `Union`, `Optional`  
类型提示为`Union`时会按照最匹配选择格式化策略

详见 [typing](./typing)

## 特殊类型提示

 - [Cmd](./cmd)