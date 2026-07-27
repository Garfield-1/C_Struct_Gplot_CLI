import os
import shutil
import hashlib
import secrets

from debug_log import *
from configuration import *

# type_info 模板:定义类型信息的数据格式与默认值
g_type_info_template = {
        'data_type_latter': '',
        'typedef_names': [],
        'content': '',
        'data_type_first': '',
        'hash': '',
        'salt': '',
        'source_file': '',
}

class debugInfo():
        # result 为单条 type_info 字典,由 extract_C_structure 每解析出一条结构体时调用
        def debug_info(self, result, structure_type):
                log_debug(_("--- {} ---").format(structure_type))
                log_debug(_("数据类型: {}").format(result['data_type_first']))
                log_debug(_("名称: {}").format(result['data_type_latter']))
                log_debug(_("typedef别名: {}").format(', '.join(result['typedef_names'])))
                log_debug(_("完整内容:\n{}").format(result['content']))
                log_debug(_("哈希值: {}").format(result['hash']))
                log_debug(_("源文件: {}").format(result['source_file']))

debug = debugInfo()

"""
C语言结构提取
"""
class structureExtractor:
        # 从花括号位置提取结构体边界,返回起始和结束位置
        def _extract_structure_boundary(self, content, content_len, start_pos):
                depth = 0
                if start_pos < content_len and content[start_pos] == '{':
                        depth = 1
                        start_pos += 1
                else:
                        return -1

                while start_pos < content_len and depth > 0:
                        if content[start_pos] == '{':
                                depth += 1
                        elif content[start_pos] == '}':
                                depth -= 1
                        if depth > 0:
                                start_pos += 1
                        elif depth == 0:
                                break

                # 跳过 '}'
                brace_end_pos = start_pos + 1

                return brace_end_pos

        # 从 start_pos 开始查找结束位置,跳过花括号内部的内容,找到最外层的结束位置
        def _find_type_definition_end_pos(self, content, keyword_pos, keyword):
                content_len = len(content)
                pos = keyword_pos + len(keyword)

                # 先用深度计数跳过花括号内部内容
                depth = 0
                while pos < content_len:
                        if content[pos] == '{':
                                depth += 1
                        elif content[pos] == '}':
                                depth -= 1
                        if depth <= 0 and content[pos] == '}':
                                break
                        pos += 1

                # depth 归零后,从 '}' 继续向后扫描到分号 ';'
                while pos < content_len and content[pos] != ';':
                        pos += 1
                if pos < content_len:
                        # 跳过分号
                        end_pos = pos + 1
                else:
                        end_pos = content_len

                return True, end_pos

        # 从关键字位置解析完整类型定义,将结果填入 type_info,返回 end_pos
        def _parse_type_definition(self, content, keyword_pos, keyword, type_info):
                ret, end_pos = self._find_type_definition_end_pos(content, keyword_pos, keyword)
                if ret == False:
                        return end_pos

                # 检查类型关键字前面是否有 typedef
                # 由于预处理过程可以确保这里输入内容的格式,这里强制匹配前8个字符串
                is_typedef = False
                if content[keyword_pos-8:keyword_pos] == 'typedef ':
                        is_typedef = True

                # 跳过空格和关键字
                content_len = len(content)
                pos = keyword_pos + len(keyword)
                while pos < content_len and content[pos].isspace():
                        pos += 1

                # 提取类型名称
                type_name = ""
                while pos < content_len and (content[pos].isalnum() or content[pos] == '_'):
                        type_name += content[pos]
                        pos += 1

                # 找到花括号 '{'
                while pos < content_len and content[pos] != '{':
                        pos += 1

                # 找到开始和结束的{}
                brace_start_pos = pos
                brace_end_pos = self._extract_structure_boundary(content, content_len, pos)

                # 类型定义字符串:有花括号时只提取到 '}',无花括号时为空(变量声明不提取)
                if brace_end_pos != -1:
                        full_str = content[brace_start_pos:brace_end_pos]
                else:
                        full_str = ""

                # 提取 typedef 别名
                # 针对指针只会保留名称,"*"符号会删除,多个别名用逗号分隔,所有别名会全部提取
                typedef_names = []
                if is_typedef and brace_end_pos != -1:
                        alias_part = content[brace_end_pos:end_pos]
                        for name in alias_part.split(','):
                                name = name.strip().replace('*', '').rstrip(';').strip()
                                if name:
                                        typedef_names.append(name)

                # 生成随机 salt,与 full_str 拼接后计算 hash
                salt = secrets.token_hex(8)
                content_hash = hashlib.md5((full_str + salt).encode('utf-8')).hexdigest()

                # 填充类型信息
                type_info_name = type_name if type_name else ''
                type_info['data_type_latter'] = type_info_name
                type_info['typedef_names'] = typedef_names
                type_info['content'] = full_str
                type_info['data_type_first'] = keyword
                type_info['salt'] = salt
                type_info['hash'] = content_hash

                # 每一次向后移动一个关键字长度
                return keyword_pos + len(keyword)

        # 检查关键字和关键字后的第一个{中间是否有其他非法字符,如果有说明这不是结构体定义,跳过这一段
        def _check_illegal_character(self, content, keyword_pos, keyword):
                content_len = len(content)
                check_pos = keyword_pos + len(keyword)
                is_conclusion = False
                illegal_character_num = 0
                is_semicolon = False  # 标记是否遇到分号

                while check_pos < content_len:
                        # 遇到分号说明不是类型定义(是声明),立即返回分号后位置
                        # 避免继续向后搜索 { 导致游标跳跃过远
                        if content[check_pos] == ';':
                                is_semicolon = True
                                break
                        if content[check_pos] == '{':
                                is_conclusion = True
                                break
                        if content[check_pos] == '(':
                                illegal_character_num += 1
                        if content[check_pos] == ')':
                                illegal_character_num += 1
                        if content[check_pos] == '=':
                                illegal_character_num += 1
                        check_pos += 1

                if is_semicolon or (is_conclusion == True and illegal_character_num > 0):
                        end_pos = check_pos + 1
                        return False, end_pos
                else:
                        return True, keyword_pos

        # 从 start_pos 开始查找下一个关键字位置,未找到返回 -1
        def _find_next_keyword(self, content, start_pos, keyword):
                pos = start_pos
                kw_len = len(keyword)
                content_len = len(content)

                while pos < content_len:
                        if pos < 0:
                                continue
                        if pos + kw_len <= content_len and content[pos:pos + kw_len] == keyword:
                                # 确保前面不是字母/数字/下划线(避免匹配 Xxxkeyword)
                                prev_char = content[pos-1]
                                if prev_char.isalnum() or prev_char == '_' or prev_char == '(':
                                        pos += kw_len
                                        continue

                                # 避免匹配到函数参数或是函数声明
                                if content[pos-8:pos] == ' ,const' or content[pos-7:pos] == '(const':
                                        pos += kw_len
                                        continue

                                # 确保后面是空格或花括号(struct{ 也是合法语法)
                                next_char = content[pos + kw_len]
                                if next_char != ' ' and next_char != '{':
                                        pos += 1
                                        continue
                                return pos
                        pos += 1
                return -1

        # 从预处理后的C语言文件中提取所有struct定义,保留完整结构以字符串形式保存
        def extract_C_structure(self, filename, keyword):
                try:
                        f = open(filename, 'r', encoding='utf-8', errors='replace')
                except IOError:
                        log_error(_("无法打开输入文件:{}").format(filename))
                        return []

                content = f.read()
                f.close()

                pos = 0
                structure = []
                type_info = g_type_info_template.copy()

                while pos < len(content):
                        # 查找下一个关键字定义位置
                        structure_pos = self._find_next_keyword(content, pos, keyword)
                        if structure_pos == -1:
                                break

                        # 检查这个关键字是否是结构体定义
                        ret, end_pos = self._check_illegal_character(content, structure_pos, keyword)
                        if not ret:
                                pos = end_pos
                                continue

                        # 解析结构体定义,保存结构体信息
                        type_info.clear()
                        pos = self._parse_type_definition(content, structure_pos, keyword, type_info)

                        if type_info.get('content', '').strip():
                                type_info['source_file'] = filename
                                debug.debug_info(type_info, keyword)
                                structure.append(type_info.copy())

                return structure

_structure_extractor = structureExtractor()

def extract_structure(filename, keyword):
        return _structure_extractor.extract_C_structure(filename, keyword)
