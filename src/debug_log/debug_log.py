import os
import sys
import inspect
from datetime import datetime
from enum import IntEnum

from configuration import *

# 日志等级,数值越大优先级越高
class LogLevel(IntEnum):
        DEBUG = 10
        INFO = 20
        WARNING = 30
        ERROR = 40
        CRITICAL = 50

# 日志开关
g_file_log_enable = CONFIG.get('debug_log').get('file_log_enable', False)

# 是否输出到终端
g_console_log_enable = CONFIG.get('debug_log').get('console_log_enable', False)

# 日志文件句柄(全局单例,进程生命周期内保持)
g_log_file = None

# 当前最低日志等级(低于此等级的日志不记录)
g_min_level = LogLevel.INFO

class LogConfiguration():
        def _tag_to_level(self, tag):
                tag = tag.upper()
                if tag == 'DEBUG':
                        return LogLevel.DEBUG
                elif tag == 'INFO':
                        return LogLevel.INFO
                elif tag == 'WARNING':
                        return LogLevel.WARNING
                elif tag == 'ERROR':
                        return LogLevel.ERROR
                elif tag == 'CRITICAL':
                        return LogLevel.CRITICAL
                else:
                        log_error(_("无效的日志级别配置 (debug_log.level): {},仅支持 DEBUG/INFO/WARNING/ERROR/CRITICAL,已降级为 ERROR").format(tag))
                        return LogLevel.ERROR

        # 设置最低日志等级 低于此等级的日志将被丢弃
        def _set_log_level(self, level=None):
                global g_min_level
                if level is None:
                        level = CONFIG.get('debug_log').get('level', 'INFO')
                if isinstance(level, str):
                        level = self._tag_to_level(level)
                g_min_level = level

        # 初始化控制台输出配置
        def _enable_console_init(self):
                global g_console_log_enable
                g_console_log_enable = CONFIG.get('debug_log').get('console_log_enable', True)

        def _file_path_init(self):
                global g_log_file
                log_dir = CONFIG.get('debug_log').get('log_file_path')
                log_name = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_log.txt"
                if g_log_file is None:
                        try:
                                log_file_path = os.path.join(log_dir, log_name)
                                os.makedirs(log_dir, exist_ok=True)
                                g_log_file = open(log_file_path, 'w', encoding='utf-8')
                                g_log_file.write(f"\n{'=' * 60}\n")
                                g_log_file.write(f"日志会话开始:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                g_log_file.write(f"{'=' * 60}\n")
                                g_log_file.flush()
                        except (OSError, TypeError, ValueError) as e:
                                log_error(_("初始化日志文件失败 (debug_log.log_file_path={}): {}").format(log_dir, e))

        def init_log(self):
                global g_file_log_enable, g_console_log_enable
                # 配置文件中 debug_log 被写成非对象类型时,打印 error 日志并回退默认配置
                dl_cfg = CONFIG.get('debug_log')
                if not hasattr(dl_cfg, 'get'):
                        log_error(_("无效的调试日志配置 (debug_log): {},必须为对象,已回退默认配置").format(dl_cfg))
                        set_assignment_config('debug_log', {})
                        dl_cfg = CONFIG.get('debug_log')

                g_file_log_enable = dl_cfg.get('file_log_enable', False)
                g_console_log_enable = dl_cfg.get('console_log_enable', False)
                if g_file_log_enable is False and g_console_log_enable is False:
                        return

                self._set_log_level()
                if g_file_log_enable:
                        self._file_path_init()
                self._enable_console_init()

        def close_log(self):
                global g_log_file

                if g_log_file is not None:
                        g_log_file.write(f"\n{'=' * 60}\n")
                        g_log_file.write(f"日志会话结束:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        g_log_file.write(f"{'=' * 60}\n")
                        g_log_file.flush()
                        g_log_file.close()
                        g_log_file = None

class LogSave():
        def _level_to_tag(self, level):
                if level == LogLevel.DEBUG:
                        return 'DEBUG'
                elif level == LogLevel.INFO:
                        return 'INFO '
                elif level == LogLevel.WARNING:
                        return 'WARN '
                elif level == LogLevel.ERROR:
                        return 'ERROR'
                elif level == LogLevel.CRITICAL:
                        return 'CRIT '
                else:
                        return LogLevel.ERROR

        # 获取调用方信息:模块名、函数名、行号
        def _get_caller_info(self, skip_frames=3):
                frame = inspect.currentframe()
                try:
                        for _ in range(skip_frames):
                                if frame.f_back is None:
                                        break
                                frame = frame.f_back
                        module = frame.f_globals.get('__name__', '<unknown>')
                        function = frame.f_code.co_name
                        line = frame.f_lineno
                        return module, function, line
                finally:
                        # 避免引用循环
                        del frame

        # 格式化输出日志到控制台：自行补全时间戳与调用方信息
        def console_log(self, level, message):
                if level < g_min_level:
                        return

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                module, function, line = self._get_caller_info(skip_frames=3)

                tag = self._level_to_tag(level)
                # 只保留时间部分
                short_ts = timestamp[11:]
                prefix = f"[{short_ts}] [{tag}] [{module}:{function}:{line}]"

                # WARNING 及以上输出到 stderr,其余到 stdout
                if level >= LogLevel.WARNING:
                        stream = sys.stderr
                else:
                        stream = sys.stdout
                print(f"{prefix} {message}", file=stream)

        def write_log(self, level, message):
                # 日志文件尚未初始化(如 init_log 之前就发生异常)时直接丢弃,避免二次崩溃
                if g_log_file is None:
                        return
                if level < g_min_level:
                        return

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                module, function, line = self._get_caller_info(skip_frames=3)

                tag = self._level_to_tag(level)
                log_line = f"[{timestamp}] [{tag}] [{module}:{function}:{line}] {message}\n"
                g_log_file.write(log_line)
                g_log_file.flush()

log = LogSave()

def log_debug(message):
        if g_file_log_enable:
                log.write_log(LogLevel.DEBUG, message)
        if g_console_log_enable:
                log.console_log(LogLevel.DEBUG, message)

def log_info(message):
        if g_file_log_enable:
                log.write_log(LogLevel.INFO, message)
        if g_console_log_enable:
                log.console_log(LogLevel.INFO, message)

def log_warning(message):
        if g_file_log_enable:
                log.write_log(LogLevel.WARNING, message)
        if g_console_log_enable:
                log.console_log(LogLevel.WARNING, message)

def log_error(message):
        if g_file_log_enable:
                log.write_log(LogLevel.ERROR, message)
        if g_console_log_enable:
                log.console_log(LogLevel.ERROR, message)

def log_critical(message):
        if g_file_log_enable:
                log.write_log(LogLevel.CRITICAL, message)
        if g_console_log_enable:
                log.console_log(LogLevel.CRITICAL, message)

log_config = LogConfiguration()

def init_log():
        log_config.init_log()

def close_log():
        log_config.close_log()
