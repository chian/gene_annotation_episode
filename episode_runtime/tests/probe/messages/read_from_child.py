"""What the probe takes from a child's return: of a nested plan its count and the sheet rows it returned; of an
extraction the fact, its content read through the held records, and the optional fields the commission selected."""
import json

from ...sheet_library import SHEET


def read_from_child(slot, result, summary, records):
    if slot == 'nested':
        return {'slot': slot, 'n': result['n'],
                'returned_cells': [records.table(SHEET).get(ref)['value'] for ref in result['row_refs']]}
    content = json.loads(records.get_artifact(result['fact_refs'][0]))['value'] if result['fact_refs'] else None
    return {'fact': result['fact'], 'slot': slot, 'fact_content': content,
            'selected': {name: result[name] for name in ('field', 'records_read') if name in result}}
