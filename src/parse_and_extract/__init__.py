from .preprocess_file import preprocess_input_file
from .build_ui_json import fill_ui_json_and_relations_table
"""
C数据结构解析模块
此模块完全采用静态代码分析,仅用于解析C语言数据结构
后续可能使用独立的词法+语法解析器代替,不要与其他模块耦合
"""
from .extract_structure import extract_structure


__all__ = ['extract_structure', 'fill_ui_json_and_relations_table', 'preprocess_input_file']
