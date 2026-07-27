import os
import json

# 程序名
g_prog = 'C Struct Gplot CLI'
# 版本号
g_version = '1.0'

# 项目根目录
g_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# locale目录
g_locale_dir = os.path.join(g_project_root, 'locale')

# 当前程序运行目录,导入时固定
g_run_dir = os.getcwd()

# 默认配置文件路径
g_config_file = None

# 用户手动下发配置
g_user_config = {}

# 默认配置
g_defaults = {
        "run_mode": "init",
        "language": "en",
        "temp_file_path": os.path.join(g_run_dir,".temp_file"),
        "init_mode": {
                "input_file": None,
        },
        "svg_mode": {
                "extract_name": None,
        },
        "database": {
                "db_path": os.path.join(g_run_dir, "output"),
                "db_name": "structures.db"
        },
        "debug_log": {
                "file_log_enable": False,
                "level": "INFO",
                "console_log_enable": True,
                "log_file_path": os.path.join(g_run_dir, "log")
        },
}

class configuration:
        # 配置访问器,包装原始 dict,提供属性式访问与默认值回退
        def __init__(self, data=None, defaults=None):
                self._data = data if data is not None else g_user_config
                self._defaults = defaults if defaults is not None else g_defaults

        # 从磁盘读取config.json,文件不存在时回退到默认值
        def _load_raw(self):
                if g_config_file is None:
                        return dict(g_defaults)

                try:
                        with open(g_config_file, 'r', encoding='utf-8') as f:
                                return json.load(f)
                except FileNotFoundError:
                        return dict(g_defaults)
                except json.JSONDecodeError as e:
                        return dict(g_defaults)

        # 获取配置项,优先从 g_user_config 取值,找不到则回退到 g_defaults;值为 dict 时返回子 configuration 对象
        def get(self, key, default=None):
                value = self._data.get(key)
                if value is None:
                        value = self._defaults.get(key, default)
                if isinstance(value, dict):
                        sub_defaults = self._defaults.get(key, {})
                        if not isinstance(sub_defaults, dict):
                                sub_defaults = {}
                        return configuration(value, sub_defaults)
                return value

# 配置指定的配置项,覆盖默认值
def set_assignment_config(configuration, value):
        global g_user_config
        g_user_config[configuration] = value
        return g_user_config

# 配置指定的配置文件,覆盖默认值
def set_config_file(config_file):
        global g_config_file
        g_config_file = config_file

# 供外部模块读取 locale 目录路径的接口
def get_locale_dir():
        return g_locale_dir

# 进程内全局单例,其他模块导入此对象
CONFIG = configuration(g_user_config, g_defaults)
