import os
import sys
import sqlite3

from debug_log import *
from configuration import *

class Structures:
        TABLE_NAME = "structures"

        # 表字段定义:字段名 -> SQL 类型与约束
        # 新增/删除字段时仅需修改此字典
        TABLE_COLUMNS = {
                'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'salt': 'TEXT',
                'hash': 'TEXT',
                'data_type_first': 'TEXT NOT NULL',
                'data_type_latter': 'TEXT NOT NULL',
                'typedef_names': 'TEXT',
                'content': 'TEXT',
                'ui_json': 'TEXT',
                'source_file': 'TEXT',
                'parent_num': 'INTEGER DEFAULT 0',
                'child_num': 'INTEGER DEFAULT 0',
        }

        # 可写入字段集合
        WRITABLE_FIELDS = {
                'hash', 'salt', 'data_type_first', 'data_type_latter', 'typedef_names',
                'content', 'ui_json', 'source_file',
                'parent_num', 'child_num',
        }

        # 字段值转换规则:字段名 -> 转换函数
        # 用于将业务数据类型转换为数据库存储格式
        FIELD_CONVERTERS = {
                'typedef_names': lambda value: ','.join(value) if isinstance(value, list) else value,
        }

        # 查询加速索引:索引名 -> 索引字段
        # (data_type_latter, data_type_first) 联合索引按最左前缀原则同时服务
        # by_name 与 by_data_type_latter 两类查询;hash 索引服务按 hash 的 UPDATE
        TABLE_INDEXES = {
                'idx_structures_hash': '(hash)',
                'idx_structures_latter_first': '(data_type_latter, data_type_first)',
                'idx_structures_first_content': '(data_type_first, content)',
        }

        # 将字段字典中的值按 FIELD_CONVERTERS 规则转换,返回新字典
        @staticmethod
        def _convert_fields(fields):
                converted = {}
                for field_name, value in fields.items():
                        converter = Structures.FIELD_CONVERTERS.get(field_name)
                        converted[field_name] = converter(value) if converter else value
                return converted

        # 创建 structures 表及查询索引
        def structures_init_table(self):
                self.create_table(Structures.TABLE_NAME, Structures.TABLE_COLUMNS)
                self.create_indexes(Structures.TABLE_NAME, Structures.TABLE_INDEXES)

        # 查询结果内存缓存:同一 key 的重复查询直接返回缓存结果
        # 插入新记录时整体失效,保证缓存与库内数据一致
        def _structures_lookup_cached(self, key, loader):
                cache = self._lookup_cache
                if key not in cache:
                        cache[key] = loader()
                return cache[key]

        # 插入一条结构体记录,返回插入的行 id
        def structures_insert(self, record):
                self._lookup_cache.clear()
                converted = self._convert_fields(record)
                # 只保留白名单中的可写字段
                writable = {}
                for field_name, value in converted.items():
                        if field_name in Structures.WRITABLE_FIELDS:
                                writable[field_name] = value

                if not writable:
                        return 0

                field_names = ', '.join(writable.keys())
                placeholders = ', '.join(['?'] * len(writable))
                sql = f'INSERT INTO {Structures.TABLE_NAME} ({field_names}) VALUES ({placeholders})'
                params = tuple(writable.values())

                return self.execute_insert(sql, params)

        # 更新指定记录的 ui_json 字段
        def structures_update_ui_json(self, structure_id, ui_json_str):
                sql = f'UPDATE {Structures.TABLE_NAME} SET ui_json = ? WHERE id = ?'
                return self.execute_update(sql, (ui_json_str, structure_id))

        # 按 hash 更新记录的 child_num 字段(成员引用的子结构数量)
        def structures_update_child_num(self, structure_hash, child_num):
                sql = f'UPDATE {Structures.TABLE_NAME} SET child_num = ? WHERE hash = ?'
                return self.execute_update(sql, (child_num, structure_hash))

        # 按 hash 更新记录的 parent_num 字段(被其它结构引用的次数)
        def structures_update_parent_num(self, structure_hash, parent_num):
                sql = f'UPDATE {Structures.TABLE_NAME} SET parent_num = ? WHERE hash = ?'
                return self.execute_update(sql, (parent_num, structure_hash))

        # 根据 id 查询结构体记录,返回字典或 None
        def structures_get_by_id(self, structure_id):
                sql = f'SELECT * FROM {Structures.TABLE_NAME} WHERE id = ?'
                return self.execute_query_one(sql, (structure_id,))

        # 统计结构体记录数,可按数据类型过滤
        def structures_get_count(self, data_type_first=None):
                if data_type_first:
                        sql = f'SELECT COUNT(*) AS count FROM {Structures.TABLE_NAME} WHERE data_type_first = ?'
                        row = self.execute_query_one(sql, (data_type_first,))
                else:
                        sql = f'SELECT COUNT(*) AS count FROM {Structures.TABLE_NAME}'
                        row = self.execute_query_one(sql, None)

                return row['count'] if row else 0

        # 按 data_type_latter 与 data_type_first 字段区分大小写精确匹配,返回所有匹配行的 hash 列表
        def structures_get_hashes_by_name(self, data_type_latter, data_type_first):
                def loader():
                        sql = f'SELECT hash FROM {Structures.TABLE_NAME} ' \
                                'WHERE data_type_latter = ? COLLATE BINARY AND data_type_first = ? COLLATE BINARY'
                        rows = self.execute_query(sql, (data_type_latter, data_type_first))
                        return [row['hash'] for row in rows]

                return self._structures_lookup_cached(
                        ('by_name', data_type_latter, data_type_first), loader)

        # 按 data_type_latter 字段区分大小写精确匹配,返回所有匹配行的 hash 列表
        def structures_get_hashes_by_data_type_latter(self, data_type_latter):
                def loader():
                        sql = f'SELECT hash FROM {Structures.TABLE_NAME} ' \
                                'WHERE data_type_latter = ? COLLATE BINARY'
                        rows = self.execute_query(sql, (data_type_latter,))
                        return [row['hash'] for row in rows]

                return self._structures_lookup_cached(
                        ('by_latter', data_type_latter), loader)

        # 按 typedef_name 区分大小写精确匹配,返回所有匹配行的 hash 列表
        # typedef_names 字段可能以 "," 存放多个名称:先用 SQL LIKE 模糊粗筛候选行,
        # 再取出拆分后逐个精确匹配(LIKE 不区分大小写且会子串误中,仅作粗筛)
        # LIKE 前置通配符无法走索引,依赖查询缓存避免重复全表扫描
        def structures_get_hashes_by_typedef_name(self, typedef_name):
                def loader():
                        sql = f'SELECT hash, typedef_names FROM {Structures.TABLE_NAME} ' \
                                'WHERE typedef_names LIKE ?'
                        rows = self.execute_query(sql, (f'%{typedef_name}%',))

                        result = []
                        for row in rows:
                                raw = row['typedef_names']
                                if not raw:
                                        continue
                                names = [n.strip() for n in raw.split(',')]
                                if typedef_name in names:
                                        result.append(row['hash'])
                        return result

                return self._structures_lookup_cached(
                        ('by_typedef', typedef_name), loader)

        # 按 data_type_first 与 content 字段区分大小写精确匹配,返回所有匹配行的 hash 列表
        def structures_get_hashes_by_type_and_content(self, data_type_first, content):
                def loader():
                        sql = f'SELECT hash FROM {Structures.TABLE_NAME} ' \
                                'WHERE data_type_first = ? COLLATE BINARY AND content = ? COLLATE BINARY'
                        rows = self.execute_query(sql, (data_type_first, content))
                        return [row['hash'] for row in rows]

                return self._structures_lookup_cached(
                        ('by_content', data_type_first, content), loader)

class Relations:
        TABLE_NAME = "relations"

        TABLE_COLUMNS = {
                'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                'parent': 'TEXT NOT NULL',
                'child': 'TEXT NOT NULL',
        }

        TABLE_INDEXES = {
                'idx_relations_child': '(child)',
        }

        # 创建 relations 表及查询索引
        def relations_init_table(self):
                self.create_table(Relations.TABLE_NAME, Relations.TABLE_COLUMNS)
                self.create_indexes(Relations.TABLE_NAME, Relations.TABLE_INDEXES)

        # 插入一条父子关系,返回插入的行 id
        def relations_insert(self, parent, child):
                sql = f'INSERT INTO {Relations.TABLE_NAME} (parent, child) VALUES (?, ?)'
                return self.execute_insert(sql, (parent, child))

        # 统计指定 child hash 在关系表中作为子结构出现的次数(即被多少个父结构引用)
        def relations_get_parent_count(self, child):
                sql = f'SELECT COUNT(*) AS count FROM {Relations.TABLE_NAME} WHERE child = ?'
                row = self.execute_query_one(sql, (child,))
                return row['count'] if row else 0

        # 查询指定 child hash 对应的所有父结构 hash,返回 parent hash 列表
        def relations_get_parent_hashes(self, child):
                sql = f'SELECT parent FROM {Relations.TABLE_NAME} WHERE child = ?'
                rows = self.execute_query(sql, (child,))
                result = []
                for row in rows:
                        result.append(row['parent'])
                return result

        def relations_clear(self):
                sql = f'DELETE FROM {Relations.TABLE_NAME}'
                return self.execute_update(sql, None)

# 提供原始 SQL 执行接口,并通过多重继承直接暴露 Structures/Relations 业务接口供子类使用
class BaseDatabase(Structures, Relations):
        def __init__(self, db_path):
                self.db_path = db_path
                self._db_conn = None
                self._lookup_cache = {}

        def execute_insert(self, sql, params=None):
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(sql, params or ())
                conn.commit()
                return cursor.lastrowid

        def execute_update(self, sql, params=None):
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(sql, params or ())
                conn.commit()
                return cursor.rowcount

        def execute_query(self, sql, params=None):
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(sql, params or ())
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        def execute_query_one(self, sql, params=None):      
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(sql, params or ())
                row = cursor.fetchone()
                return dict(row) if row else None

        def create_table(self, table_name, columns_def):
                fields_sql = ', '.join(
                        f'{data_type_latter} {definition}' for data_type_latter, definition in columns_def.items()
                )
                sql = f'CREATE TABLE IF NOT EXISTS {table_name} ({fields_sql})'
                self.execute_update(sql, None)

        def create_indexes(self, table_name, indexes_def):
                for index_name, columns in indexes_def.items():
                        sql = f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {columns}'
                        self.execute_update(sql, None)

        def init_db(self):
                self.structures_init_table()
                self.relations_init_table()
                if isinstance(self, DiskDatabase):
                        log_info(_("磁盘模式:已连接磁盘数据库 {}").format(self.db_path))
                else:
                        log_info(_("内存模式:数据库初始化完成(SQLite :memory: 模式)"))

        def close(self):
                if self._db_conn is not None:
                        self._db_conn.close()
                        self._db_conn = None
                        log_info(_("数据库连接已关闭"))

# 磁盘数据库:直接连接磁盘数据库文件
class DiskDatabase(BaseDatabase):
        def __init__(self, db_path):
                super().__init__(db_path)

        def _get_connection(self):
                if self._db_conn is None:
                        self._db_conn = sqlite3.connect(self.db_path)
                        log_info(_("磁盘数据库模式:已连接 {}").format(self.db_path))
                        self._db_conn.row_factory = sqlite3.Row
                return self._db_conn

# 内存数据库:使用 :memory: 连接,需调用 flush_to_disk 持久化
class MemoryDatabase(BaseDatabase):
        def __init__(self, db_path):
                super().__init__(db_path)

        # 获取内存数据库连接
        def _get_connection(self):
                if self._db_conn is None:
                        self._db_conn = sqlite3.connect(':memory:')
                        log_info(_("内存数据库模式:使用 :memory:(需调用 flush_to_disk 持久化)"))
                        self._db_conn.row_factory = sqlite3.Row
                return self._db_conn

        # 将内存数据库写入磁盘文件
        def flush_to_disk(self, db_path=None):
                if self._db_conn is None:
                        log_warning(_("数据库未初始化,无需写入磁盘"))
                        return
                if db_path is None:
                        db_path = self.db_path
                out_dir = os.path.dirname(db_path)
                if out_dir and not os.path.exists(out_dir):
                        os.makedirs(out_dir)
                if os.path.exists(db_path):
                        os.remove(db_path)
                disk_conn = sqlite3.connect(db_path)
                self._db_conn.backup(disk_conn)
                disk_conn.close()
                log_info(_("内存数据库已写入磁盘:{}").format(db_path))

def get_db_file_path():
        database = CONFIG.get('database')
        # 配置文件中 database 被写成非对象类型时,CONFIG.get 会原样返回该值
        if not hasattr(database, 'get'):
                msg = _("无效的数据库配置 (database): {},必须为对象").format(database)
                log_error(msg)
                raise ValueError(msg)
        db_path = database.get('db_path')
        db_name = database.get('db_name')
        if not isinstance(db_path, str) or not db_path.strip():
                msg = _("无效的数据库路径配置 (database.db_path): {}").format(db_path)
                log_error(msg)
                raise ValueError(msg)
        if not isinstance(db_name, str) or not db_name.strip():
                msg = _("无效的数据库文件名配置 (database.db_name): {}").format(db_name)
                log_error(msg)
                raise ValueError(msg)
        return os.path.join(db_path, db_name)

def create_disk_db():
        db_file = get_db_file_path()
        if not os.path.isfile(db_file):
                msg = _("数据库文件不存在: {},请先以 init 模式生成数据库").format(db_file)
                log_error(msg)
                raise FileNotFoundError(msg)
        return DiskDatabase(db_file)

def create_memory_db():
        return MemoryDatabase(get_db_file_path())
