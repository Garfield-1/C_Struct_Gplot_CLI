import os
import glob
import shutil
import subprocess
import gettext

from debug_log import *
from configuration import *

# 翻译域名,对应 locale/<lang>/LC_MESSAGES/<DOMAIN>.mo
DOMAIN = 'user_prompt'

# 支持的语言,以及未指定时的默认语言
SUPPORTED_LANGUAGES = ('zh_CN', 'en')

# 借助系统的 msgfmt 将过时/缺失的 .mo 从 .po 编译出来,使使用者只需维护 .po
# 环境未安装 msgfmt 时静默跳过,程序回退到已有 .mo 或原文,不影响运行
def _compile_po_files():
        msgfmt = shutil.which('msgfmt')
        if not msgfmt:
                return
        pattern = os.path.join(get_locale_dir(), '*', 'LC_MESSAGES', '*.po')
        for po_path in glob.glob(pattern):
                mo_path = os.path.splitext(po_path)[0] + '.mo'
                # 仅当 .mo 缺失或 .po 更新时才重新编译
                if (not os.path.exists(mo_path)
                                or os.path.getmtime(po_path) > os.path.getmtime(mo_path)):
                        try:
                                subprocess.run(
                                        [msgfmt, po_path, '-o', mo_path], check=False)
                        except OSError:
                                # 调用失败(如只读目录)时不阻断程序运行
                                pass


# 初始化 gettext,并将 _ 安装到内建命名空间,供全局直接使用
def setup_i18n(lang=None):
        _compile_po_files()
        if lang is None:
                lang = CONFIG.get('language')
        if lang not in SUPPORTED_LANGUAGES:
                log_error(_("无效的语言配置 (language): {},仅支持 {},将回退到原文").format(
                        lang, '/'.join(SUPPORTED_LANGUAGES)))
        translation = gettext.translation(
                DOMAIN, get_locale_dir(), languages=[str(lang)], fallback=True)
        translation.install()
        return translation


# 导入即安装一个恒等翻译,保证任何位置的 _() 调用都不会因未初始化而报错
gettext.install(DOMAIN)
