"""Code-only audit of section assembly; no paper/model/result reacquisition."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from jsonschema import Draft202012Validator
from gene_annotation_episode.literature_compiled_assay_inputs import (
    ALLOWLIST, COMMON_ROLES, _common_selection_schema,
)
from gene_annotation_episode.literature_compiled_assay_calculations import (
    COMMON_COMPONENTS, FORMULAS, _COMMON_FORMULAS, common_assessment_sheet_schema,
)

schema = _common_selection_schema()
received = schema['anyOf'][0]['anyOf']
namespaces = [row['properties']['namespace']['const'] for row in received]
kinetic = {'kind': 'received_component', 'namespace': 'literature_kinetic_cells',
           'sheet_ref': 'source_' + 'a' * 24, 'component': 'numerator_parameter'}
endpoint = {**kinetic, 'namespace': 'literature_endpoint_signal_cells', 'component': 'retained_fraction'}
assert Draft202012Validator(schema).is_valid(kinetic)
assert not Draft202012Validator(schema).is_valid(endpoint)
assert not any('summary_precision' in name for name in namespaces)
limits = common_assessment_sheet_schema()['properties']['remaining_implementation_limits']['items']['enum']
assert 'general_quality_compilation_unfinished' in limits
assert 'same_estimand_contradiction_compilation_unfinished' in limits
paths = [ROOT / 'gene_annotation_episode' / name for name in (
    'literature_compiled_assay_inputs.py', 'literature_compiled_assay_calculations.py')]
result = {
    'status': 'pass',
    'scope': 'Current code/schema inspection only, not an assay-coverage or scientific-completion claim.',
    'complete_root_reads': [{'path': str(path.relative_to(ROOT)),
                             'lines': len(path.read_text().splitlines()),
                             'sha256': sha256(path.read_bytes()).hexdigest()} for path in paths],
    'within_assay_allowed_namespaces_by_role': {role: list(choices) for role, choices in ALLOWLIST.items()},
    'common_received_namespaces': namespaces,
    'known_kinetic_selector_accepted': True,
    'endpoint_fraction_selector_accepted': False,
    'summary_precision_received_selector_available': False,
    'within_assay_formulas': FORMULAS,
    'common_assertion_formulas': _COMMON_FORMULAS,
    'common_roles': list(COMMON_ROLES),
    'common_component_names': list(COMMON_COMPONENTS),
    'declared_remaining_limits': limits,
    'numeric_components_are_not_assay_counts': True,
    'goal_changed': False, 'A105_complete': False,
}
with (HERE / 'CURRENT_ASSEMBLY_CHECK_001.json').open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps({key: result[key] for key in (
    'status', 'complete_root_reads', 'common_received_namespaces',
    'endpoint_fraction_selector_accepted', 'summary_precision_received_selector_available',
    'declared_remaining_limits')}, indent=2))
