"""Original detached tool identifiers in root received process records."""
from collections.abc import Mapping
from copy import deepcopy
import re



RESOURCE_KINDS = ('api', 'local', 'hpc')
SELECTOR_FIELDS = {'name', 'resources'}
INFO_FIELDS = SELECTOR_FIELDS | {'description', 'instructions'}


def tool_info_selection(value):
    if not isinstance(value, list):
        raise ValueError('scientific_child_tool_info_invalid')
    result, seen = [], set()
    for item in value:
        if (not isinstance(item, Mapping) or set(item) not in (SELECTOR_FIELDS, INFO_FIELDS)
                or not isinstance(item.get('name'), str) or not item['name'].strip()
                or item.get('resources') not in RESOURCE_KINDS
                or any(not isinstance(item.get(field), str) or not item[field].strip()
                       for field in set(item) - SELECTOR_FIELDS)):
            raise ValueError('scientific_child_tool_info_invalid')
        key = item['name'], item['resources']
        if key in seen:
            raise ValueError('scientific_child_tool_info_duplicate')
        seen.add(key)
        result.append(deepcopy(dict(item)))
    return result


def selectors(value):
    if (not isinstance(value, list) or any(not isinstance(row, Mapping)
            or not SELECTOR_FIELDS <= set(row) <= INFO_FIELDS for row in value)):
        raise ValueError('scientific_child_tool_info_invalid')
    return tool_info_selection([{field: row[field] for field in ('name', 'resources')}
                                for row in value])


def parent_view(value):
    return [{field: row[field] for field in ('name', 'description', 'resources')}
            for row in value]



def tool_names(value):
    if (not isinstance(value, list) or any(not isinstance(name, str) or not name.strip()
            for name in value) or len(value) != len(set(value))):
        raise ValueError("scientific_selected_tools_invalid")
    return list(value)


