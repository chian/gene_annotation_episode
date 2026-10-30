"""Hand-constructed shape fixture, not an executed new owner calculation."""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
root = json.loads((BASE / 'controlled_adapter_parent_review_065/shared_representation_probe_002/RESULT_001.json').read_text())
inputs = deepcopy(root['mixed_unknown_owner']['inputs'])
inputs['version'] = 'controlled_response_owner_inputs_v2'
inputs['relationships']['control_reference_reuse'] = 'unknown'
inputs['covariance'] = {'physical_observation_ids': ['main1', 'controlB', 'main0'],
    'units': ['nmol/min'] * 3, 'matrix': [[.25, 0, .1], [0, .04, 0], [.1, 0, .25]]}
inputs['variance_status'] = 'known'
schema = json.loads((HERE / 'OWNER_INPUT_SCHEMA_004.json').read_text())
Draft202012Validator(schema).validate(inputs)
value = {'scope': 'HAND-CONSTRUCTED input/expectations, shape validation only; new owner calculator unimplemented',
    'inputs': inputs,
    'expected_semantics': {'known_required_owner_ids': ['main1', 'controlB', 'main0'],
        'provided_owner_ids': ['main1', 'controlB', 'main0'], 'unknown_active_role': 'empty_condition0',
        'effect_umol_per_min': .00205, 'conditional_effect_bounds': [.00195, .00215],
        'covariance_state': 'incomplete_active_coverage', 'contrast_variance': None,
        'contrast_standard_uncertainty': None, 'contrast_precision': None,
        'source_profile_log_ratio': None, 'source_signed_index': None,
        'owner_identity_inferred_from_equal_sets': False},
    'new_semantic_validator_or_calculator_executed': False}
with (HERE / 'ACTIVE_UNKNOWN_OWNER_CASE_006.json').open('x') as stream:
    json.dump(value, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps({'shape_valid': True, 'new_owner_calculator_executed': False}))
