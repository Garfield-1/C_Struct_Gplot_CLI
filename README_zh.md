# C Struct Gplot CLI

[English](./README.md) | 简体中文

`C`语言项目静态代码分析工具,可生成`svg`格式的`struct\union\enum`结构关系图,生成指定结构的父节点和其所有的子节点

![struct mesh_leaf](./docs/README_img/struct%20mesh_leaf.png)

支持简体中文和英文,支持读取配置文件,命令行参数,也可以二者混合使用使用命令行参数覆盖配置文件

## 通过cli使用

### 直接通过源代码执行

程序运行时会自动导入当前目录下的`config.json`文件或`config/config.json`文件,命令行输入的参数优先级更高,会覆盖配置文件中的值

```shell
# 第一次需要初始化数据库
python3 ./src/main.py --mode=init --input-file=<要解析的项目路径>
# 生成struct node_a的svg Topology 图
python3 ./src/main.py --mode=svg --extract-name=<"要解析的结构体">

# 例如
python3 ./src/main.py --mode=init --input-file=./../tests/test.c
python3 ./src/main.py --mode=svg --extract-name="struct mesh_leaf"
```

### 通过二进制执行

```shell
# linux平台

# 第一次需要初始化数据库
./struct_topology --mode=init --input-file=<要解析的项目路径>
# 生成struct node_a的svg Topology 图
./struct_topology --mode=svg --extract-name=<"要解析的结构体">

# windows平台通过命令行工具或者双击struct_topology.exe

# 第一次需要初始化数据库
./struct_topology.exe --mode=init --input-file=<要解析的项目路径>
# 生成struct node_a的svg Topology 图
./struct_topology.exe --mode=svg --extract-name=<"要解析的结构体">
```

## 通过配置文件使用

程序运行时会自动导入当前目录下的`config.json`文件或`config/config.json`文件

```shell
# 查看版本
python3 ./src/main.py --version

# 第一次需要配置run_mode参数为init
python3 ./src/main.py
# 第二次需要配置run_mode参数为svg
python3 ./src/main.py
```

### 配置文件说明

```json
{
    // 当前程序运行语言:zh_CN和en
    "language": "en",

	// 程序运行模式:init和svg
    // 首次运行必须是init
    "run_mode": "init",

    // init模式参数
    "init_mode": {
        // 要解析的项目路径,支持单文件,文件夹,压缩包
        "input_file":"./../tests/test.c"
    },

    // svg模式参数
    "svg_mode": {
        // 要生成的结构名称
        "extract_name": "struct mesh_leaf"
    },

    // 生成数据库路径和名称
    "database": {
        "db_path": "./output",
        "db_name": "structures.db"
    },

    // 调试配置
    "debug_log": {
        // 调试等级:DEBUG,INFO,WARNING,ERROR,CRITICAL
        "level": "ERROR",
        // 是否记录日志文件
        "file_log_enable": false,
        // 日志是否输出终端
        "console_log_enable": true
    }
}
```

## 打包方法

执行命令,会在`build_package/dist`目录下生成对应平台的二进制文件

```shell
cd build_package/
python3 build_package.py
```

