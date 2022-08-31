# config

读取配置文件(.yaml/.json)，并转化为对象  

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

默认读取工作目录下名为config的配置文件，可修改 config.py 末尾的读取 (line:74)
```python
config: Config = read_config(raw_path="myConfig")
```
值得一提的是，config.py 支持自动识别配置类型，如 .yaml/.json，所以不加后缀的后缀名是可行的

## 读取其他配置文件

运行时，可以通过从config.py中导入read_config方法
```python
from config import read_config

# 原始路径导入
config = read_config(raw_path="myConfig")

# 但有时，配置文件不止一个，因此放在一个文件夹中会更为简洁
# 从工作目录下config文件中读取 > config/myConfig
config = read_config("myConfig")
```


