"""Explicit physical correspondence for retained A103 test oracles.

Logical saved binding IDs stay literal. This helper changes only current module
selection and original private import operands after a physical owner move.
"""
import ast
from copy import deepcopy

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a103'


def current_module_name(name):
    old = PREFIX + '.legacy_annotation'
    return PREFIX + name[len(old):] if name == old or name.startswith(old + '.') else name


def relocated_provider_roster(original):
    value = deepcopy(original)
    def visit(item):
        if isinstance(item, dict):
            for key in ('module', 'task_module') if 'definition' in item else ():
                if isinstance(item.get(key), str):
                    selected = current_module_name(item[key])
                    if selected != item[key]:
                        item['before_hierarchy_' + key] = item[key]
                        item[key] = selected
                        source_key = 'current_source' if key == 'module' else 'task_source'
                        if source_key in item:
                            item['before_hierarchy_' + source_key] = item.pop(source_key)
            for child in tuple(item.values()):
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(value)
    return value


def relocate_original_private_imports(node, row):
    before_module = row.get('before_hierarchy_module')
    if before_module is None:
        return node
    result = deepcopy(node)
    package = before_module.rsplit('.', 1)[0]
    for child in ast.walk(result):
        if isinstance(child, ast.ImportFrom):
            if child.level:
                parts = package.split('.')
                absolute = '.'.join(parts[:len(parts) - child.level + 1])
                if child.module:
                    absolute += '.' + child.module
            else:
                absolute = child.module
            selected = current_module_name(absolute)
            if child.level or selected != absolute:
                child.module, child.level = selected, 0
    return result
