"""Bounded synthetic diagnostic, not a regression contract accepting the gap.

Run from this artifact directory with the project venv Python. Imports are
restricted to the copied 209 baseline plus its synthetic engineering fixtures.
"""
from pathlib import Path
import asyncio
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
PIN = ROOT / 'pin_001'
sys.path[:0] = [str(PIN), str(PIN / 'tests')]
from test_literature_compiled_assay_185 import setup, extraction, add_source
from test_literature_compiled_assay_binding_185 import binding_for, FORM
from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.literature_compiled_assay_storage import REQUESTED, LiteratureCompiledAssayRepository
import gene_annotation_episode.literature_compiled_assay_inputs as inputs

manifest = json.loads((ROOT / 'PIN_MANIFEST_001.json').read_text())['selected_hashes']
assert all(hashlib.sha256((PIN / name).read_bytes()).hexdigest() == digest
           for name, digest in manifest.items())
work = ROOT / 'diagnostic_store_002'
work.mkdir(exist_ok=False)
store, context, arguments, outputs = setup(work)
with store:
    # Unknown corrections remain unknown. They are not needed to define q/E.
    for role in ('g', 'k', 'u', 'v'):
        arguments['operands'][role] = None
        arguments['relationships'][role] = {'value': 'unknown', 'witnesses': []}
    for stage in ('contaminant', 'recovery', 'nuisance_condition'):
        arguments['correction_stages'][stage] = {'value': 'unknown', 'witnesses': []}
    requested = ['measured_endpoint_per_selected_amount', 'corrected_activity', 'effect_variance']
    context = replace(context, assignment={**context.assignment, REQUESTED: requested})
    binding = binding_for(store, context)
    result = asyncio.run(binding.execute(context, 'literature.assay.components.populate', arguments, 'partial-q-E'))
    assert result['status'] == 'completed', result
    current = replace(context, received_record_refs=(*context.received_record_refs, *result['record_refs']))
    form = form_with_facts({}, FORM, binding.facts(current, {'committed_record_refs': result['record_refs']}))
    binding.validate_report(current, form, FORM)
    saved = LiteratureCompiledAssayRepository(store, context.run_id).read(result['result']['sheet_ref'])
    ex = extraction(store, context, arguments)
    operands = ex['operands']
    q, e = (operands[role]['value'] for role in ('q', 'E'))
    assert q > 0 and e > 0
    assert saved['sheet']['cells']['measured_endpoint_per_selected_amount']['value'] == q/e
    assert all(operands[role] is None for role in ('g', 'k', 'u', 'v'))

    # The covariance is deliberately stipulated synthetic, not extracted paper
    # uncertainty. Every supplied owner/dependency belongs to the real rows.
    # Off-diagonal covariance is nonzero; independence is not presumed.
    matrix = [[.04, .005], [.005, .01]]
    cov = {'version': 'a105_compiled_assay_covariance_v1', 'primitive_order': ['q', 'E'],
        'operand_keys': [operands[r]['quantity_key'] for r in ('q', 'E')],
        'primitive_units': [operands[r]['unit'] for r in ('q', 'E')],
        'dependency_keys': [list(dict.fromkeys((*operands[r]['canonical_physical_keys'],
            *operands[r]['recorded_dependency_keys']))) for r in ('q', 'E')],
        'covariance': matrix, 'origin': 'synthetic',
        'basis': 'joint_covariance_of_canonical_compilation_operands'}
    failures = []
    for label, selected_order in [('actual_q_E_subset', ['q', 'E']),
                                  ('six_role_names_without_fabricating_owners', list(inputs.ROLES))]:
        data = deepcopy(cov); data['primitive_order'] = selected_order
        ref = add_source(store, canonical(data), 'synthetic_partial_covariance_' + label,
                         [arguments['source_ref']])
        ctx = replace(context, received_record_refs=(*context.received_record_refs, ref))
        args = deepcopy(arguments); args.update(covariance_source_ref=ref, variance_status='estimated')
        outcome = asyncio.run(binding.execute(ctx, 'literature.assay.components.populate', args, label))
        failures.append({'label': label, 'outcome': outcome})
        assert outcome['status'] != 'completed', outcome
    # Independent exact-arithmetic propagation from the declared q/E statistic.
    # This is an oracle demonstration, not a replacement production calculator.
    Q, E = Fraction(str(q)), Fraction(str(e))
    gradient = [1/E, -Q/(E*E)]
    variance = sum(gradient[i] * Fraction(str(matrix[i][j])) * gradient[j]
                   for i in range(2) for j in range(2))
    assert abs(variance - Fraction(391, 40000)) < Fraction('1e-16')  # upstream float q is near 1.8
    assert saved['sheet']['cells']['effect_variance']['value'] is None
    assert all(row['partial_uncertainty_status'] == 'unimplemented' for row in form['numerical_sections'])
    assert not store.list('observation') and not store.list('assessment')
    payload = {'scope': 'synthetic selected-binding diagnostic; no paper, model, runtime-loop or credit claim',
        'import_file': str(Path(inputs.__file__).resolve()),
        'actual_q_E': {'q': q, 'E': e, 'q_over_E': q/e},
        'selected_form': form, 'covariance_input_with_actual_owners': cov,
        'failed_selected_attempts': failures,
        'oracle': {'variance': float(variance), 'exact_variance': str(variance),
                   'standard_uncertainty': float(variance) ** .5,
                   'gradient': [str(v) for v in gradient]},
        'effective_values': saved['sheet']['effective_values'],
        'remaining_implementation_limits': saved['sheet']['remaining_implementation_limits'],
        'upstream_optical_saved_covariance': outputs['optical']['repo'].read(
            outputs['optical']['outcome']['result']['sheet_ref'])['extraction']['covariance_source'],
        'source_kind': 'synthetic_fixture',
        'did_not_fabricate': ['g', 'k', 'u', 'v', 'independence', 'residual_variance', 'known_variance']}
    (ROOT / 'DIAGNOSTIC_RESULT_001.json').write_text(json.dumps(payload, indent=2) + '\n')
assert all(hashlib.sha256((PIN / name).read_bytes()).hexdigest() == digest
           for name, digest in manifest.items())
print(json.dumps({'result': str(ROOT / 'DIAGNOSTIC_RESULT_001.json'),
                  'q_over_E': q/e, 'oracle_variance': float(variance),
                  'failures': failures}, indent=2))
