import os
import sys
import glob
import shutil
import struct
import platform
import argparse
import subprocess

# 项目根目录:本文件位于 <root>/build_package/build_package.py,向上两级即为项目根
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 打包工作目录与产物目录,均位于 build_package/ 之下,避免污染项目根
PACKAGE_DIR = os.path.join(PROJECT_ROOT, 'build_package')
BUILD_DIR = os.path.join(PACKAGE_DIR, 'build')
DIST_DIR = os.path.join(PACKAGE_DIR, 'dist')

# src/ 下的业务模块,PyInstaller 静态分析无法感知 main.py 中的动态
# sys.path 注入,需显式声明为 hidden-import 才能全部收集进二进制
HIDDEN_IMPORTS = (
        'i18n',
        'build_svg',
        'debug_log',
        'sqlite3_db',
        'configuration',
        'parse_and_extract',
)

"""解析命令行参数

--name: 可选,产物名称,默认 struct_topology
--onedir: 可选,使用目录模式打包(默认单文件 --onefile,目录模式启动更快)
--auto-install: 可选,PyInstaller 缺失时自动 pip 安装
--no-clean: 可选,保留 build/ 与 .spec 等中间产物,便于调试
"""
def parse_args():
        parser = argparse.ArgumentParser(
                description='将 struct_topology 打包为当前平台的二进制可执行程序 '
                            '(Windows 11 / Linux / macOS 需分别在对应平台上执行本脚本)')
        parser.add_argument('--name', default='struct_topology',
                                help='产物名称,默认 struct_topology')
        parser.add_argument('--onedir', action='store_true',
                                help='使用目录模式打包(默认单文件模式,目录模式启动更快)')
        parser.add_argument('--auto-install', action='store_true',
                                help='PyInstaller 缺失时自动通过 pip 安装')
        parser.add_argument('--no-clean', action='store_true',
                                help='保留 build/ 与 .spec 等中间产物,便于调试')
        return parser.parse_args()


"""识别当前操作系统与 CPU 架构

返回形如 windows-x64 / linux-x64 / macos-arm64 的平台标签,
用作 dist/ 下的产物子目录名。PyInstaller 不支持交叉编译,
产物平台即为执行本脚本的平台。
"""
def detect_platform():
        system_map = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'macos'}
        system = system_map.get(platform.system())
        if system is None:
                raise RuntimeError('不支持的操作系统: {}'.format(platform.system()))

        machine = platform.machine().lower()
        arch_map = {'x86_64': 'x64', 'amd64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}
        arch = arch_map.get(machine, machine)
        return '{}-{}'.format(system, arch)


# 校验 Python 版本,低于 3.9 时 PyInstaller 新版本不再支持
def check_python_version():
        if sys.version_info < (3, 9):
                raise RuntimeError('需要 Python >= 3.9,当前版本: {}'.format(platform.python_version()))


"""检测 PyInstaller 是否可用

缺失时:auto_install 为 True 则自动 pip 安装,否则报错退出。
"""
def ensure_pyinstaller(auto_install):
        try:
                import PyInstaller  # noqa: F401
                return
        except ImportError:
                pass

        if not auto_install:
                raise RuntimeError('未安装 PyInstaller,请执行 pip install pyinstaller,'
                                   '或使用 --auto-install 让本脚本自动安装')

        print('[build_package] PyInstaller 未安装,正在自动安装 ...')
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        if result.returncode != 0:
                raise RuntimeError('PyInstaller 自动安装失败,请手动执行 pip install pyinstaller')


"""纯 Python 的 po -> mo 编译器(msgfmt 缺失时的兜底方案)

仅处理本项目所需的 msgid/msgstr 单复数之外的基本条目,
按标准 mo 二进制格式(magic 0x950412de,小端)写出。
"""
def compile_po_fallback(po_path, mo_path):
        # 解析 .po:状态机区分当前累积的是 msgid 还是 msgstr
        entries = {}
        msgid, msgstr, section = [], [], None

        # 处理 .po 字符串中的转义字符(\n \t \" \\ 等)
        def unescape(text):
                return (text.replace('\\n', '\n').replace('\\t', '\t')
                            .replace('\\r', '\r').replace('\\"', '"')
                            .replace('\\\\', '\\'))

        # 将累积完成的一条 msgid/msgstr 写入结果集
        def flush():
                if section == 'msgstr':
                        entries[unescape(''.join(msgid))] = unescape(''.join(msgstr))

        with open(po_path, 'r', encoding='utf-8') as f:
                for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                                continue
                        if line.startswith('msgid '):
                                flush()
                                msgid, msgstr, section = [line[6:].strip().strip('"')], [], 'msgid'
                        elif line.startswith('msgstr '):
                                msgstr, section = [line[7:].strip().strip('"')], 'msgstr'
                        elif line.startswith('"'):
                                # 多行字符串续行,归入当前所在小节
                                text = line.strip('"')
                                if section == 'msgid':
                                        msgid.append(text)
                                elif section == 'msgstr':
                                        msgstr.append(text)
                flush()

        # 按 mo 格式要求以 msgid 字节序排序后写出偏移表与字符串池
        keys = sorted(entries.keys())
        offsets, ids, strs = [], b'', b''
        for key in keys:
                kb, vb = key.encode('utf-8'), entries[key].encode('utf-8')
                offsets.append((len(ids), len(kb), len(strs), len(vb)))
                ids += kb + b'\x00'
                strs += vb + b'\x00'

        n = len(keys)
        # 头部 7 个 uint32 + 两张 (长度,偏移) 表,字符串池紧随其后
        keystart = 7 * 4 + 16 * n
        valuestart = keystart + len(ids)
        koffsets, voffsets = [], []
        for o1, l1, o2, l2 in offsets:
                koffsets += [l1, o1 + keystart]
                voffsets += [l2, o2 + valuestart]

        with open(mo_path, 'wb') as f:
                f.write(struct.pack('<7I', 0x950412de, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0))
                f.write(struct.pack('<{}I'.format(2 * n), *koffsets))
                f.write(struct.pack('<{}I'.format(2 * n), *voffsets))
                f.write(ids)
                f.write(strs)


"""遍历 locale/ 将全部 .po 预编译为 .mo

冻结环境中通常没有 msgfmt,i18n 的运行时编译会静默失败,
因此必须在打包前完成编译并将 .mo 打入二进制。
优先使用系统 msgfmt,缺失时回退到 compile_po_fallback。
返回本次新生成的 .mo 路径列表,供打包完成后清理。
"""
def compile_po_files():
        msgfmt = shutil.which('msgfmt')
        created = []
        pattern = os.path.join(PROJECT_ROOT, 'locale', '*', 'LC_MESSAGES', '*.po')
        for po_path in glob.glob(pattern):
                mo_path = os.path.splitext(po_path)[0] + '.mo'
                existed = os.path.exists(mo_path)
                if msgfmt:
                        result = subprocess.run([msgfmt, po_path, '-o', mo_path])
                        if result.returncode != 0:
                                raise RuntimeError('msgfmt 编译失败: {}'.format(po_path))
                else:
                        compile_po_fallback(po_path, mo_path)
                print('[build_package] 已编译翻译文件: {}'.format(os.path.relpath(mo_path, PROJECT_ROOT)))
                if not existed:
                        created.append(mo_path)
        return created


"""生成 PyInstaller runtime hook,修正冻结环境下的资源路径

configuration.py 通过 __file__ 向上三级推导项目根目录,冻结后
模块位于 sys._MEIPASS/configuration/,向上三级会越过 _MEIPASS,
导致 locale/ 定位失败。hook 在主程序启动前将路径重定向到 _MEIPASS,
从而不需要修改任何业务源码。
"""
def write_runtime_hook():
        hook_path = os.path.join(BUILD_DIR, 'runtime_hook_paths.py')
        hook_code = (
                "import os\n"
                "import sys\n"
                "\n"
                "# 冻结运行时将项目根/locale 重定向到 PyInstaller 解包目录\n"
                "if getattr(sys, 'frozen', False):\n"
                "        import configuration.configuration as _c\n"
                "        _c.g_project_root = sys._MEIPASS\n"
                "        _c.g_locale_dir = os.path.join(sys._MEIPASS, 'locale')\n"
        )
        os.makedirs(BUILD_DIR, exist_ok=True)
        with open(hook_path, 'w', encoding='utf-8') as f:
                f.write(hook_code)
        return hook_path


"""拼装 PyInstaller 命令行

- --paths src: 让静态分析能解析 src/ 下的顶层包
- --add-data: 打入 locale/ 翻译与 src/config.json 默认配置
- --runtime-hook: 注入冻结路径修正逻辑
--add-data 的源与目标分隔符跨平台使用 os.pathsep(Windows 为 ';',其余为 ':')
"""
def build_command(args, hook_path):
        sep = os.pathsep
        cmd = [
                sys.executable, '-m', 'PyInstaller',
                '--noconfirm', '--clean',
                '--onedir' if args.onedir else '--onefile',
                '--name', args.name,
                '--paths', os.path.join(PROJECT_ROOT, 'src'),
                '--distpath', os.path.join(BUILD_DIR, 'dist'),
                '--workpath', os.path.join(BUILD_DIR, 'work'),
                '--specpath', BUILD_DIR,
                '--runtime-hook', hook_path,
                '--add-data', '{}{}locale'.format(os.path.join(PROJECT_ROOT, 'locale'), sep),
                '--add-data', '{}{}.'.format(
                        os.path.join(PROJECT_ROOT, 'src', 'config.json'), sep),
        ]
        for module in HIDDEN_IMPORTS:
                cmd += ['--hidden-import', module]
        cmd.append(os.path.join(PROJECT_ROOT, 'src', 'main.py'))
        return cmd


# 以子进程执行 PyInstaller 并透传输出,失败时抛出异常
def run_build(cmd):
        print('[build_package] 执行: {}'.format(' '.join(cmd)))
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        if result.returncode != 0:
                raise RuntimeError('PyInstaller 构建失败,退出码: {}'.format(result.returncode))


"""整理产物到 build_package/dist/<平台标签>/

将 PyInstaller 输出的可执行文件(或 onedir 目录)移入按平台
命名的子目录,并附带一份 config.json 外置配置样例。
返回最终产物路径。
"""
def collect_output(args, platform_tag):
        target_dir = os.path.join(DIST_DIR, platform_tag)
        shutil.rmtree(target_dir, ignore_errors=True)
        os.makedirs(target_dir, exist_ok=True)

        raw_dist = os.path.join(BUILD_DIR, 'dist')
        exe_name = args.name + ('.exe' if platform.system() == 'Windows' else '')
        if args.onedir:
                # 目录模式:整个程序目录即为产物
                src = os.path.join(raw_dist, args.name)
                dst = os.path.join(target_dir, args.name)
        else:
                src = os.path.join(raw_dist, exe_name)
                dst = os.path.join(target_dir, exe_name)
        if not os.path.exists(src):
                raise RuntimeError('未找到构建产物: {}'.format(src))
        shutil.move(src, dst)

        # 附带外置配置样例,便于使用者按需修改后随程序分发
        config_src = os.path.join(PROJECT_ROOT, 'src', 'config.json')
        if os.path.isfile(config_src):
                shutil.copy(config_src, os.path.join(target_dir, 'config.json'))
        return dst


# 清理 build/ 目录(含 spec、work、临时 hook)与本次新生成的 .mo
def clean_artifacts(created_mo_files):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        for mo_path in created_mo_files:
                try:
                        os.remove(mo_path)
                except OSError:
                        pass

def main():
        args = parse_args()

        check_python_version()
        platform_tag = detect_platform()
        print('[build_package] 当前打包平台: {} (PyInstaller 不支持交叉编译,'
              '产物仅适用于该平台)'.format(platform_tag))

        ensure_pyinstaller(args.auto_install)

        created_mo_files = []
        try:
                created_mo_files = compile_po_files()
                hook_path = write_runtime_hook()
                cmd = build_command(args, hook_path)
                run_build(cmd)
                artifact = collect_output(args, platform_tag)
                print('[build_package] 打包完成: {}'.format(artifact))
        finally:
                if not args.no_clean:
                        clean_artifacts(created_mo_files)


if __name__ == '__main__':
        try:
                main()
        except Exception as e:
                # 捕获内部抛出的异常,打印友好错误信息后以非0退出码结束
                print('错误: {}'.format(e), file=sys.stderr)
                sys.exit(1)
