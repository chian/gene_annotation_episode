from __future__ import annotations
import hashlib
from pathlib import Path
import re
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_contracts import CALCULATOR_VERSION, parse_rna_comparison_json, validate_rna_comparison_selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_comparison_inputs import populate_rna_comparison_sheet
PLAN_VERSION = 'rna_structure_comparison_worker_plan_v1'
RESULT_VERSION = 'rna_structure_comparison_worker_result_v1'
DATA_FIELDS = {'original_sheet', 'original_bundle_software', 'received_failure'}
PLAN_FIELDS = {'version', 'selector', 'input_data', 'result_receipt_key', 'calculation_key', 'directory'}
RESULT_FIELDS = {'version', 'input_data_sha256', 'sheet_file', 'sheet_sha256', 'components_file', 'components_sha256', 'projection_rows_file', 'projection_rows_sha256', 'calculator_version', 'result_receipt_key', 'calculation_key'}

def _require(condition, code='rna_comparison_invalid_record'):
    if not condition:
        raise ValueError(code)

def _json_bytes(value):
    return (canonical(value) + '\n').encode('utf-8')

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _decode(raw):
    value = parse_rna_comparison_json(raw)
    _require(raw == _json_bytes(value), 'rna_comparison_noncanonical_bytes')
    return value

def _key(value, namespace):
    _require(type(value) is str and re.fullmatch(namespace + ':[0-9a-f]{64}', value) is not None, 'rna_comparison_identity_mismatch')

def _absolute(value):
    _require(type(value) is str and value and ('\x00' not in value) and ('\n' not in value) and ('\r' not in value), 'rna_comparison_output_path_conflict')
    path = Path(value)
    _require(path.is_absolute() and str(path) == value and (path.resolve() == path), 'rna_comparison_output_path_conflict')
    return path

def _selected_data(selector, data):
    """Closed membership only; authority and original custody belong to E."""
    selected = validate_rna_comparison_selector(selector)
    members = [m for m in selected['question']['membership'] if m['kind'] != 'alias']
    _require(type(data) is dict and set(data) == {m['member_id'] for m in members}, 'rna_comparison_operand_mismatch')
    _require(all((type(value) is dict and set(value) == DATA_FIELDS for value in data.values())), 'rna_comparison_operand_mismatch')
    populate_rna_comparison_sheet(selected, operands=data)
    for member in members:
        if member['kind'] == 'saved_sheet':
            _require(_sha(_json_bytes(data[member['member_id']]['original_sheet'])) == member['saved_input']['sheet_sha256'], 'rna_comparison_retained_input_digest_mismatch')
    return (selected, members)

def comparison_input_digests(selector: dict, data: dict) -> list[dict]:
    """Value digests, ordered by the selected non-alias membership."""
    _, members = _selected_data(selector, data)
    return [{'member_id': member['member_id'], 'kind': member['kind'], 'input_sha256': digest(data[member['member_id']])} for member in members]

def comparison_calculation_key(selector: dict, data: dict) -> str:
    """Scientific identity excludes projections and current receipt identity."""
    selected = validate_rna_comparison_selector(selector)
    return 'rna_comparison_calculation:' + digest({'selected_input_digests': comparison_input_digests(selected, data), 'question': selected['question'], 'parameters': selected['parameters'], 'calculator_version': CALCULATOR_VERSION})

def _validate_plan(plan):
    _require(type(plan) is dict and set(plan) == PLAN_FIELDS and (plan['version'] == PLAN_VERSION))
    selected = validate_rna_comparison_selector(plan['selector'])
    _key(plan['result_receipt_key'], 'rna_comparison_receipt')
    _key(plan['calculation_key'], 'rna_comparison_calculation')
    directory = _absolute(plan['directory'])
    entry = plan['input_data']
    _require(type(entry) is dict and set(entry) == {'path', 'sha256', 'size_bytes'})
    _require(type(entry['sha256']) is str and re.fullmatch('[0-9a-f]{64}', entry['sha256']) is not None)
    _require(type(entry['size_bytes']) is int and entry['size_bytes'] >= 0)
    _require(_absolute(entry['path']) == directory / 'input-data.json', 'rna_comparison_input_path_mismatch')
    return (selected, directory)
