# C Struct Gplot CLI

English | [简体中文](./README_zh.md)

A static code analysis tool for `C` language projects that generates `struct\union\enum` structure relationship diagrams in `svg` format

![struct mesh_leaf](./docs/README_img/struct%20mesh_leaf.png)

Supports Simplified Chinese and English, supports reading configuration files, command-line arguments, or a mix of both, using command-line arguments to override the configuration file

## Usage via CLI

```shell
# Check version
python3 ./main.py --version

# The database needs to be initialized on first run
python3 ./main.py --mode=init --input-file=./tests/test.c
# Generate the svg Topology diagram of struct node_a
python3 ./main.py --mode=svg --extract-name="struct mesh_leaf"
```

## Usage via Configuration File

```shell
# Check version
python3 ./main.py --version

# For the first run, the run_mode parameter must be set to init
python3 ./main.py
# For the second run, the run_mode parameter must be set to svg
python3 ./main.py
```

### Configuration File Description

```json
{
    // Language of the running program: zh_CN and en
    "language": "zh_CN",

	// Program run mode: init and svg
    // Must be init on first run
    "run_mode": "init",

    // init mode parameters
    "init_mode": {
        // Path of the project to parse, supports single file, folder, and archive
        "input_file":"./tests/test.c"
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
        "level": "INFO",
        // Whether to write logs to a file
        "file_log_enable": false,
        // Whether to output logs to the terminal
        "console_log_enable": true
    }
}
```

