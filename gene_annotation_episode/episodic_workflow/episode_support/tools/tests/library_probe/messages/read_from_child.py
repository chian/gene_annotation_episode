"""What the probe takes from an extraction child's return."""
import json


def read_from_child(slot, result, summary, records):
    content = json.loads(records.get_artifact(result['fact_refs'][0]))['value'] if result['fact_refs'] else None
    return {'fact': result['fact'], 'slot': slot, 'fact_content': content,
            'selected': {name: result[name] for name in ('field', 'records_read') if name in result}}
