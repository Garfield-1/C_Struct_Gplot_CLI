# ============================================================
# 本文件所有代码均由AI生成(本段注释除外)
# ============================================================
import os
import json
from collections import deque
from configuration import CONFIG

class SvgStyle:
	# ---- 布局尺寸 ----
	ROW_HEIGHT = 26           # 单行时的行高度
	LINE_HEIGHT = 18          # 多行文字时每行的高度
	H_GAP = 100               # 层间水平间距(用于连线)
	V_GAP = 30                # 同层兄弟节点间垂直间距
	MARGIN = 25               # SVG 边距
	FONT_SIZE = 13            # 文字字号
	TEXT_PADDING = 8          # 文字左侧内边距
	CHAR_WIDTH_RATIO = 0.62   # monospace 字符宽度与字号的比例
	MIN_TABLE_WIDTH = 120     # 最小表格宽度
	MAX_TABLE_WIDTH = 1200    # 最大表格宽度
	MAX_CHARS_PER_LINE = 64   # 单行最大字符数,超过则换行

	# ---- 配色 ----
	# 表头背景色(按 data_type_first 区分)
	HEADER_COLORS = {
		'struct': '#4A90D9',
		'union': '#E8743B',
		'enum': '#50A050',
		'default': '#888888',
	}
	# 折叠引用节点(重复出现、仅显示 "......" 不展开)的专用配色
	REF_HEADER_COLOR = '#9B59B6'    # 表头背景(紫色,区别于展开节点)
	REF_BODY_COLOR = '#F1E7F7'      # 内容行背景(浅紫)
	REF_TEXT_COLOR = '#7A5299'      # "......" 文字颜色
	# 通用绘图配色
	BACKGROUND_COLOR = '#FAFAFA'    # 画布背景
	TABLE_BORDER_COLOR = '#333333'  # 表格边框
	MEMBER_TEXT_COLOR = '#333333'   # 成员行文字
	ZEBRA_ROW_COLOR = '#F5F5F5'     # 成员行隔行背景
	SEPARATOR_COLOR = '#CCCCCC'     # 行间分隔线
	EDGE_COLOR = '#999999'          # 父子连线与连接点

class StructTreeBuilder:
	def __init__(self, db):
		self._db = db

	def build_tree(self, hash_val):
		record = self._find_by_hash(hash_val)
		if record is None:
			return None

		expanded = set()
		root, root_slots = self._create_node(record, expanded)
		nodes = [root]
		queue = deque(root_slots)
		while queue:
			row, child_record = queue.popleft()
			child, child_slots = self._create_node(child_record, expanded)
			row['children'].append(child)
			nodes.append(child)
			queue.extend(child_slots)

		self._mark_duplicate_nodes(nodes)
		return root

	def build_parent_nodes(self, root_hash):
		parents = []
		for parent_hash in self._collect_parent_hashes(root_hash):
			record = self._find_by_hash(parent_hash)
			if record is None:
				continue
			parents.append(self._create_parent_node(record, root_hash))
		return parents


	@staticmethod
	def _mark_duplicate_nodes(nodes):
		counts = {}
		for node in nodes:
			h = node['hash']
			if h:
				counts[h] = counts.get(h, 0) + 1

		for node in nodes:
			h = node['hash']
			if h and counts[h] > 1:
				suffix = f" ({h[-6:]})"
				node['label'] += suffix
				node['rows'][0]['text'] += suffix

	def _find_by_hash(self, hash_val):
		sql = "SELECT * FROM structures WHERE hash = ? LIMIT 1"
		return self._db.execute_query_one(sql, (hash_val,))
	def _collect_parent_hashes(self, root_hash):
		parent_hashes = []
		for h in self._db.relations_get_parent_hashes(root_hash):
			if h and h != root_hash and h not in parent_hashes:
				parent_hashes.append(h)
		return parent_hashes

	def _create_node(self, record, expanded):
		hash_val = record.get('hash', '')

		if hash_val and hash_val in expanded:
			return self._create_ref_node(record), []

		if hash_val:
			expanded.add(hash_val)

		label = self._make_label(record)
		rows = [self._make_header_row(label)]
		slots = []
		for m in self._parse_members(record):
			row = self._make_member_row(m['text'])
			for child_hash in m['child_hashes']:
				child_record = self._find_by_hash(child_hash)
				if child_record:
					slots.append((row, child_record))
			rows.append(row)

		return self._make_node(record, rows, is_ref=False), slots

	def _create_ref_node(self, record):
		label = self._make_label(record)
		rows = [
			self._make_header_row(label),
			self._make_member_row('......'),
		]
		return self._make_node(record, rows, is_ref=True)

	def _create_parent_node(self, record, root_hash):
		label = self._make_label(record)
		rows = [self._make_header_row(label)]
		for m in self._parse_members(record):
			row = self._make_member_row(m['text'])
			row['links_root'] = root_hash in m['child_hashes']
			rows.append(row)
		return self._make_node(record, rows, is_ref=False)

	@staticmethod
	def _parse_members(record):
		json_str = record.get('ui_json', '')
		if not json_str:
			return []
		try:
			uj = json.loads(json_str)
		except (json.JSONDecodeError, TypeError):
			return []
		table_body = uj.get('table_body', {})
		if not isinstance(table_body, dict):
			return []
		members = []
		for key in sorted(table_body, key=StructTreeBuilder._member_sort_key):
			item = table_body[key]
			if not isinstance(item, dict):
				continue
			child_hashes = [h for h in item.get('child_hash', []) if h]
			members.append({
				'text': item.get('member_context', ''),
				'child_hashes': child_hashes,
			})
		return members

	@staticmethod
	def _member_sort_key(key):
		try:
			return int(key.rsplit('_', 1)[-1])
		except (ValueError, IndexError):
			return 0

	@staticmethod
	def _make_label(record):
		data_type_first = record.get('data_type_first', '')
		data_type_latter = record.get('data_type_latter', '')
		if not data_type_latter:
			typedef_names = record.get('typedef_names') or ''
			data_type_latter = ', '.join(
				n.strip() for n in typedef_names.split(',') if n.strip()
			)
		return f"{data_type_first} {data_type_latter}".strip()

	@staticmethod
	def _make_header_row(label):
		return {'text': label, 'is_header': True, 'children': []}

	@staticmethod
	def _make_member_row(text):
		return {'text': text, 'is_header': False, 'children': []}

	@staticmethod
	def _make_node(record, rows, is_ref):
		return {
			'label': StructTreeBuilder._make_label(record),
			'data_type_first': record.get('data_type_first', ''),
			'hash': record.get('hash', ''),
			'is_ref': is_ref,
			'rows': rows,
		}

class TreeLayout:
	def layout(self, root, parents):
		self._preprocess_rows(root)
		for parent in parents:
			self._preprocess_rows(parent)
		self._calc_subtree_height(root)

		parent_col_w, parents_h = self._measure_parent_column(parents)

		content_h = max(root['subtree_height'], parents_h)
		center_y = SvgStyle.MARGIN + content_h / 2

		tree_x = SvgStyle.MARGIN
		if parents:
			tree_x += parent_col_w + SvgStyle.H_GAP
		self._assign_coords(root, tree_x, center_y)

		self._stack_parents(
			parents, center_y - parents_h / 2, SvgStyle.MARGIN + parent_col_w
		)

		svg_width = self._find_max_right_edge(root) + SvgStyle.MARGIN
		svg_height = SvgStyle.MARGIN * 2 + content_h
		return svg_width, svg_height

	def _preprocess_rows(self, node):
		for row in node['rows']:
			row['lines'] = self._wrap_text(row['text'], SvgStyle.MAX_CHARS_PER_LINE)
			row['height'] = max(
				SvgStyle.ROW_HEIGHT, len(row['lines']) * SvgStyle.LINE_HEIGHT
			)
		for child in self._get_children(node):
			self._preprocess_rows(child)

	@staticmethod
	def _wrap_text(text, max_chars):
		if len(text) <= max_chars:
			return [text]
		lines = []
		remaining = text
		while len(remaining) > max_chars:
			break_pos = remaining.rfind(' ', 0, max_chars)
			if break_pos <= 0:
				break_pos = max_chars
			lines.append(remaining[:break_pos].rstrip())
			remaining = remaining[break_pos:].lstrip()
		if remaining:
			lines.append(remaining)
		return lines

	@staticmethod
	def _node_height(node):
		return sum(row.get('height', SvgStyle.ROW_HEIGHT) for row in node['rows'])


	@staticmethod
	def _calc_table_width(node):
		max_len = 0
		for row in node['rows']:
			lines = row.get('lines', [row['text']])
			for line in lines:
				max_len = max(max_len, len(line))
		text_width = max_len * SvgStyle.FONT_SIZE * SvgStyle.CHAR_WIDTH_RATIO
		width = int(text_width + SvgStyle.TEXT_PADDING * 2)
		return max(SvgStyle.MIN_TABLE_WIDTH, min(width, SvgStyle.MAX_TABLE_WIDTH))

	def _calc_subtree_height(self, node):
		own_h = self._node_height(node)
		children = self._get_children(node)
		if not children:
			node['subtree_height'] = own_h
		else:
			children_h = sum(self._calc_subtree_height(c) for c in children)
			children_h += SvgStyle.V_GAP * (len(children) - 1)
			node['subtree_height'] = max(own_h, children_h)
		return node['subtree_height']

	def _measure_parent_column(self, parents):
		if not parents:
			return 0, 0
		col_w = max(self._calc_table_width(p) for p in parents)
		total_h = sum(self._node_height(p) for p in parents)
		total_h += SvgStyle.V_GAP * (len(parents) - 1)
		return col_w, total_h

	def _assign_coords(self, node, x, y_center):
		self._place_node(node, x, y_center - self._node_height(node) / 2)

		children = self._get_children(node)
		if not children:
			return

		total_children_h = sum(c['subtree_height'] for c in children)
		total_children_h += SvgStyle.V_GAP * (len(children) - 1)
		child_y_top = y_center - total_children_h / 2

		child_x = x + node['table_width'] + SvgStyle.H_GAP
		for child in children:
			child_center = child_y_top + child['subtree_height'] / 2
			self._assign_coords(child, child_x, child_center)
			child_y_top += child['subtree_height'] + SvgStyle.V_GAP

	def _stack_parents(self, parents, y_top, right_x):
		for parent in parents:
			self._place_node(parent, right_x - self._calc_table_width(parent), y_top)
			y_top += parent['height'] + SvgStyle.V_GAP

	def _place_node(self, node, x, y_top):
		node['x'] = x
		node['y'] = y_top
		node['table_width'] = self._calc_table_width(node)
		node['height'] = self._node_height(node)
		y_offset = 0
		for row in node['rows']:
			row['y_offset'] = y_offset
			y_offset += row['height']

	@staticmethod
	def _get_children(node):
		children = []
		for row in node['rows']:
			children.extend(row['children'])
		return children

	def _find_max_right_edge(self, node):
		right = node['x'] + node['table_width']
		for child in self._get_children(node):
			right = max(right, self._find_max_right_edge(child))
		return right

class SvgRenderer:

	def render_to_file(self, root, parents, svg_width, svg_height, output_path):
		parts = [
			f'<svg xmlns="http://www.w3.org/2000/svg" '
			f'width="{svg_width:.0f}" height="{svg_height:.0f}">'
		]

		parts.append(
			f'<rect width="100%" height="100%" fill="{SvgStyle.BACKGROUND_COLOR}"/>'
		)

		self._draw_tree_edges(parts, root)
		self._draw_parent_edges(parts, parents, root)
		self._draw_tree_tables(parts, root)
		for parent in parents:
			self._draw_table(parts, parent)

		parts.append('</svg>')

		with open(output_path, 'w', encoding='utf-8') as f:
			f.write('\n'.join(parts))
		print(f"SVG 已生成：{output_path}")

	def _draw_tree_edges(self, parts, node):
		for row in node['rows']:
			for child in row['children']:
				x1 = node['x'] + node['table_width']
				y1 = node['y'] + row['y_offset'] + row['height'] / 2
				x2 = child['x']
				y2 = child['y'] + child['rows'][0]['height'] / 2
				self._draw_edge(parts, x1, y1, x2, y2)
				self._draw_tree_edges(parts, child)

	def _draw_parent_edges(self, parts, parents, root):
		x2 = root['x']
		y2 = root['y'] + root['rows'][0]['height'] / 2
		for parent in parents:
			link_rows = [r for r in parent['rows'] if r.get('links_root')]
			if not link_rows:
				link_rows = [parent['rows'][0]]
			for row in link_rows:
				x1 = parent['x'] + parent['table_width']
				y1 = parent['y'] + row['y_offset'] + row['height'] / 2
				self._draw_edge(parts, x1, y1, x2, y2)

	@staticmethod
	def _draw_edge(parts, x1, y1, x2, y2):
		cp_dx = (x2 - x1) * 0.5
		parts.append(
			f'<path d="M {x1:.1f} {y1:.1f} C {x1 + cp_dx:.1f} {y1:.1f} '
			f'{x2 - cp_dx:.1f} {y2:.1f} {x2:.1f} {y2:.1f}" '
			f'stroke="{SvgStyle.EDGE_COLOR}" stroke-width="1.5" fill="none"/>'
		)
		parts.append(
			f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="3" '
			f'fill="{SvgStyle.EDGE_COLOR}"/>'
		)


	def _draw_tree_tables(self, parts, node):
		self._draw_table(parts, node)
		for row in node['rows']:
			for child in row['children']:
				self._draw_tree_tables(parts, child)

	def _draw_table(self, parts, node):
		x = node['x']
		y = node['y']
		tw = node['table_width']
		rows = node['rows']
		is_ref = node.get('is_ref', False)
		header_color = self._header_color(node)
		max_chars = int(
			(tw - SvgStyle.TEXT_PADDING * 2)
			/ (SvgStyle.FONT_SIZE * SvgStyle.CHAR_WIDTH_RATIO)
		) + 1

		parts.append(
			f'<rect x="{x:.1f}" y="{y:.1f}" width="{tw}" height="{node["height"]}" '
			f'fill="white" stroke="{SvgStyle.TABLE_BORDER_COLOR}" stroke-width="1.5"/>'
		)

		for i, row in enumerate(rows):
			row_y = y + row['y_offset']
			if row['is_header']:
				self._draw_header_row(parts, row, x, row_y, tw, header_color, max_chars)
			elif is_ref:
				self._draw_ref_body_row(parts, row, x, row_y, tw)
			else:
				zebra = i % 2 == 1
				self._draw_member_row(parts, row, x, row_y, tw, zebra, max_chars)

			if i < len(rows) - 1:
				self._draw_row_separator(parts, x, row_y + row['height'], tw)

	def _draw_header_row(self, parts, row, x, row_y, tw, color, max_chars):
		parts.append(
			f'<rect x="{x:.1f}" y="{row_y:.1f}" width="{tw}" '
			f'height="{row["height"]}" fill="{color}" stroke="none"/>'
		)
		text_y = self._row_text_top(row, row_y)
		for j, line in enumerate(row['lines']):
			line_text = self._escape_xml(self._truncate(line, max_chars))
			parts.append(
				f'<text x="{x + tw / 2:.1f}" y="{text_y + j * SvgStyle.LINE_HEIGHT:.1f}" '
				f'font-size="{SvgStyle.FONT_SIZE}" font-family="monospace" '
				f'fill="white" font-weight="bold" text-anchor="middle">{line_text}</text>'
			)

	def _draw_ref_body_row(self, parts, row, x, row_y, tw):
		parts.append(
			f'<rect x="{x:.1f}" y="{row_y:.1f}" width="{tw}" '
			f'height="{row["height"]}" fill="{SvgStyle.REF_BODY_COLOR}" stroke="none"/>'
		)
		text_y = self._row_text_top(row, row_y)
		parts.append(
			f'<text x="{x + tw / 2:.1f}" y="{text_y:.1f}" '
			f'font-size="{SvgStyle.FONT_SIZE}" font-family="monospace" '
			f'fill="{SvgStyle.REF_TEXT_COLOR}" text-anchor="middle">......</text>'
		)

	def _draw_member_row(self, parts, row, x, row_y, tw, zebra, max_chars):
		if zebra:
			parts.append(
				f'<rect x="{x:.1f}" y="{row_y:.1f}" width="{tw}" '
				f'height="{row["height"]}" fill="{SvgStyle.ZEBRA_ROW_COLOR}" stroke="none"/>'
			)
		text_y = self._row_text_top(row, row_y)
		for j, line in enumerate(row['lines']):
			line_text = self._escape_xml(self._truncate(line, max_chars))
			parts.append(
				f'<text x="{x + SvgStyle.TEXT_PADDING:.1f}" '
				f'y="{text_y + j * SvgStyle.LINE_HEIGHT:.1f}" '
				f'font-size="{SvgStyle.FONT_SIZE}" font-family="monospace" '
				f'fill="{SvgStyle.MEMBER_TEXT_COLOR}">{line_text}</text>'
			)

	@staticmethod
	def _draw_row_separator(parts, x, line_y, tw):
		parts.append(
			f'<line x1="{x:.1f}" y1="{line_y:.1f}" '
			f'x2="{x + tw:.1f}" y2="{line_y:.1f}" '
			f'stroke="{SvgStyle.SEPARATOR_COLOR}" stroke-width="0.5"/>'
		)

	@staticmethod
	def _header_color(node):
		if node.get('is_ref', False):
			return SvgStyle.REF_HEADER_COLOR
		return SvgStyle.HEADER_COLORS.get(
			node.get('data_type_first', ''), SvgStyle.HEADER_COLORS['default']
		)

	@staticmethod
	def _row_text_top(row, row_y):
		num_lines = len(row['lines'])
		return (
			row_y + row['height'] / 2
			- (num_lines - 1) * SvgStyle.LINE_HEIGHT / 2
			+ SvgStyle.FONT_SIZE / 3
		)

	@staticmethod
	def _truncate(text, max_len):
		return text if len(text) <= max_len else text[:max_len] + '...'

	@staticmethod
	def _escape_xml(text):
		text = text.replace('&', '&amp;')
		text = text.replace('<', '&lt;')
		text = text.replace('>', '&gt;')
		text = text.replace('"', '&quot;')
		text = text.replace("'", '&apos;')
		return text

def build_svg(hash_val, db):
	if not hash_val:
		raise ValueError("hash 不能为空")

	builder = StructTreeBuilder(db)
	root = builder.build_tree(hash_val)
	if root is None:
		raise ValueError(f"未在数据库中找到 hash 为 '{hash_val}' 的结构体")

	parents = builder.build_parent_nodes(hash_val)
	svg_width, svg_height = TreeLayout().layout(root, parents)
	output_dir = CONFIG.get('database').get('db_path')
	os.makedirs(output_dir, exist_ok=True)
	extract_name = CONFIG.get('svg_mode').get('extract_name') or ''
	base_name = '_'.join(extract_name.split()) or 'struct'
	output_path = os.path.join(output_dir, f'{base_name}_{hash_val[-4:]}.svg')

	SvgRenderer().render_to_file(root, parents, svg_width, svg_height, output_path)
	return output_path
