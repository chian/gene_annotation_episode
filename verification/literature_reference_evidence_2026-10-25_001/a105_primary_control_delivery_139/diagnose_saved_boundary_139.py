"""Inspect the already finished primary run; perform no new scientific work.

The stronger all-arithmetic-denied probe is diagnostic, not a goal requirement.
The actual goal forbids hidden reacquisition/reinterpretation, not deterministic
validation of retained operands. Native input/domain code remains unchanged.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import traceback
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.literature_rate_domains import rate_source_domain_cells_schema
from gene_annotation_episode.literature_rate_native_inputs import rate_source_population_schema
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.state import Store

case = HERE / 'run002/test_primary_selected_native_o0'
state_path = case / 'state'
store = Store.__new__(Store)
store.path = state_path.resolve(); store._savepoint = 0
store.db = sqlite3.connect((state_path / 'state.sqlite3').as_uri() + '?mode=ro', uri=True, isolation_level=None)
store.db.row_factory = sqlite3.Row
store.db.execute('PRAGMA query_only=ON')
store.db.create_function('library_scope_record', 2, store._scope_filter_record)
operation, = store.db.execute('SELECT * FROM literature_rate_operations').fetchall()
sheet_ref = json.loads(operation['outcome'])['result']['sheet_ref']
saved = json.loads((case / 'saved_numerical_sheet.json').read_text())
native = saved['native_selection']
form = json.loads((case / 'original_admitted_form.json').read_text())
rows = form['requested_primary_components']
artifacts = {store.get(native['source_ref'])[name] for name in ('artifact_ref', 'text_ref')}
get_artifact = store.get_artifact
def retained_only(ref):
    if ref in artifacts:
        raise AssertionError('Original scientific source/render bytes denied')
    return get_artifact(ref)
store.get_artifact = retained_only
calls = []
def arithmetic_denied(*args, **kwargs):
    calls.append('gene_annotation_episode.literature_rate_domains.native_domain_trace')
    raise AssertionError('Stronger diagnostic: retained-operand validation arithmetic denied')
try:
    with patch('gene_annotation_episode.literature_rate_domains.native_domain_trace', arithmetic_denied):
        try:
            LiteratureRateRepository(store, operation['run_id']).read(sheet_ref)
        except AssertionError as error:
            outcome = {'status': 'diagnostic_rejection', 'error': str(error), 'calls': calls,
                'traceback': traceback.format_exc(),
                'meaning': 'Saved native read validates retained exact operands through native_domain_trace. This is not reacquisition, statistical refitting, or scientific reinterpretation and is not by itself a goal failure.'}
        else:
            outcome = {'status': 'all_arithmetic_denied_read_succeeded', 'calls': calls}
    assert store.db.total_changes == 0
    outcome['database_changes'] = store.db.total_changes
    (HERE / 'STRICT_ARITHMETIC_DIAGNOSTIC_001.json').write_text(json.dumps(outcome, indent=2) + '\n')
    inputs = rate_source_population_schema()['properties']
    returns = rate_source_domain_cells_schema()['items']['properties']
    semantic = {
        'scope': 'Observed current native selection, saved sheet, admitted form and parent steering; no adopted replacement taxonomy',
        'already_delivered': {
            'subject': 'Exact witnessed literal complex/organism label through subject_ref',
            'endpoint': 'Exact witnessed literal coupled H2 endpoint through endpoint_ref',
            'protocol': 'Exact source footnote sentence through experiment_ref label; actual volume,temperature,reagents and complex mass visible',
            'conditions': 'Fd + Hyd and Fd + Hyd minus crotonyl-CoA literal labels through condition refs',
            'precision': 'Unavailable cells retain mean_uncertainty_unreported or censored_measurement; no SD/count invented',
            'limits': 'Original strict comparator and conditional reported-operand rational bounds retained'},
        'private_saved_only': {
            'endpoint_specific_unit_definition': native['arms']['reference']['rate']['unit']['definition'],
            'intended_change': native['comparison']['intended_change'],
            'physical_observation_owners': {role: native['arms'][role]['measurement_identity'] for role in ('reference', 'test')}},
        'return_contract_fields': list(returns),
        'missing_interfaces': [
            'Endpoint-specific unit-definition clause/amount/entity/time is not a declared return field or admitted related record; U/mg becomes generic umol/min/mg with endpoint label elsewhere.',
            'Intended-change selection is retained privately but not a declared returned field. The omission label remains visible; no constrained control meaning establishes substrate omission rather than blank subtraction.',
            'Complex/Fd/Hyd coexistence and protocol facts survive only as exact source labels, not constrained scientific interpretation fields.',
            'Physical nonnegative conditioning has no native input representation; finite conditional upper bounds 5 and1 are not returned. The existing unconstrained strict lower bounds are useful and valid.'],
        'scientifically_unavailable': [
            'Selected table SD/SEM,n,independent-preparation count and covariance',
            'Common-condition cross-endpoint productive coupling fraction',
            'Sample/blank optical slopes and measured path length',
            'Numerical isolation/sufficiency of Bcd alone from complex activity'],
        'schema_has_nonnegative_domain_input': 'nonnegative' in json.dumps(inputs),
        'numerical_values_are_not_annotation_probabilities': True,
        'same_operands_not_independent_components': ['rate_difference', 'retained_fraction', 'fractional_decrease'],
        'strict_diagnostic_does_not_change_goal_requirements': True,
    }
    (HERE / 'CURRENT_INTERFACE_LIMITS_001.json').write_text(json.dumps(semantic, indent=2) + '\n')
    print(json.dumps({'strict_arithmetic_diagnostic': outcome['status'],
        'actual_validation_callbacks': calls, 'database_changes': 0,
        'meaning_interface_gaps': len(semantic['missing_interfaces'])}, indent=2))
finally:
    store.close()
