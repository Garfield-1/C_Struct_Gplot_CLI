# C Struct Gplot CLI

English | [简体中文](./README_zh.md)

A static code analysis tool for `C` language projects that generates `struct\union\enum` structure relationship diagrams in `svg` format, producing the parent node of a specified structure along with all of its child nodes

![struct mesh_leaf](./docs/README_img/struct%20mesh_leaf.png)

Supports Simplified Chinese and English, supports reading configuration files, command-line arguments, or a mix of both, using command-line arguments to override the configuration file

## Usage via CLI

### Running directly from source

At startup, the program automatically loads the `config.json` file in the current directory or the `config/config.json` file. Command-line arguments take higher priority and override the values in the configuration file.

```shell
# The database needs to be initialized on first run
python3 ./src/main.py --mode=init --input-file=<path of the project to parse>
# Generate the svg Topology diagram of struct node_a
python3 ./src/main.py --mode=svg --extract-name=<"structure to parse">

# For example
python3 ./src/main.py --mode=init --input-file=./../tests/test.c
python3 ./src/main.py --mode=svg --extract-name="struct mesh_leaf"
```

### Running from the binary

```shell
# Linux platform

# The database needs to be initialized on first run
./struct_topology --mode=init --input-file=<path of the project to parse>
# Generate the svg Topology diagram of struct node_a
./struct_topology --mode=svg --extract-name=<"structure to parse">

# On Windows, run via the command line or double-click struct_topology.exe

# The database needs to be initialized on first run
./struct_topology.exe --mode=init --input-file=<path of the project to parse>
# Generate the svg Topology diagram of struct node_a
./struct_topology.exe --mode=svg --extract-name=<"structure to parse">
```

## Usage via Configuration File

At startup, the program automatically loads the `config.json` file in the current directory or the `config/config.json` file.

```shell
# Check version
python3 ./src/main.py --version

# For the first run, the run_mode parameter must be set to init
python3 ./src/main.py
# For the second run, the run_mode parameter must be set to svg
python3 ./src/main.py
```

### Configuration File Description

```json
{
    // Language of the running program: zh_CN and en
    "language": "en",

	// Program run mode: init and svg
    // Must be init on first run
    "run_mode": "init",

    // init mode parameters
    "init_mode": {
        // Path of the project to parse, supports single file, folder, and archive
        "input_file":"./../tests/test.c"
    },

    // svg mode parameters
    "svg_mode": {
        // Name of the structure to generate
        "extract_name": "struct mesh_leaf"
    },

    // Generated database path and name
    "database": {
        "db_path": "./output",
        "db_name": "structures.db"
    },

    // Debug configuration
    "debug_log": {
        // Debug level: DEBUG,INFO,WARNING,ERROR,CRITICAL
        "level": "ERROR",
        // Whether to write logs to a file
        "file_log_enable": false,
        // Whether to output logs to the terminal
        "console_log_enable": true
    }
}
```

## Packaging

Run the following commands to generate the binary for the corresponding platform under the `build_package/dist` directory.

```shell
cd build_package/
python3 build_package.py
```
