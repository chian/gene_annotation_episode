"""Nonempty original RNA callback plumbing; root executes serially.

Actual private constructor, BindingContext and both actual received_context
formatters are used. Their already-authenticated `_received` values are explicit
controlled ports. This probe tests missing callback delivery, not source/result
authentication or scientific correctness. No native operation is run.
"""
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources


PARENTS = ('hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')


def module(name):
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.a107.' + name.replace('/', '.'))


def probe(output, *, expected):
    if expected not in {'missing_original_branch', 'original_branch_restored'}:
        raise ValueError('explicit_expected_regression_phase_required')
    output.mkdir(parents=True)
    rows = []
    with module('state').Store(output / 'state') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']}
        run_id = 'a107-nonempty-rna-context'
        module('episode_journal').Journal(store, run_id)
        services = SimpleNamespace(annotation_task_required=lambda: False)
        structure = [{'fact_source': module('rna_structure_result_views').REFERENCE_SOURCE,
            'facts': ['source_controlled_original_rna_reference']}]
        comparison = [{'fact_source': module('rna_structure_comparison_views').PROJECTION_SOURCE,
            'facts': [{'controlled_nonempty_projection': 'original payload retained',
                'qualification': 'callback plumbing fixture; no scientific claim'}]}]
        for parent in PARENTS:
            for leaf in ('execution_job_submission', 'execution_result_acquisition'):
                home = parent + '/' + leaf
                owner = module(home + '/episode').ExecutionEpisode(services, store=store,
                    run_id=run_id, directory=output / 'workflow', resources=resources(), initial_information={},
                    tool_registry=None, handoff_unit=3, acquired_record_unit=2,
                    log_window_bytes=1024, log_roles=('stdout', 'stderr'))
                native = module('native_rna_structure_returns').NativeRNAStructureReturns(owner)
                compare = module('rna_structure_comparison_returns').RNAStructureComparisonReturns(owner)
                owner.native_rna_structure_returns, owner.rna_structure_comparison_returns = native, compare
                visits = []
                def native_received(context, **kwargs):
                    visits.append(('structure', context.role))
                    return {'groups': {structure[0]['fact_source']: deepcopy(structure[0]['facts'])},
                        'references': list(structure[0]['facts'])}
                def comparison_received(context):
                    visits.append(('comparison', context.role))
                    return {comparison[0]['fact_source']: deepcopy(comparison[0]['facts'])}
                with patch.object(native, '_received', native_received), patch.object(compare, '_received', comparison_received):
                    for role in ('annotation', 'scientific_process', 'launch', 'results'):
                        visits.clear()
                        path = ((role, 'controlled'),)
                        context = module('episode_bindings').BindingContext(run_id,
                            module('method_loop.identities').EpisodeRef(run_id, path).episode_id,
                            role, path, scope, {}, {'message': {'scope': scope, 'episode_assignment': {}}})
                        actual = owner.initial_decision_context(context)
                        wanted = expected == 'original_branch_restored' and role in {'annotation', 'scientific_process'}
                        if wanted:
                            assert actual['received_rna_structure_values'] == structure
                            assert actual['received_rna_comparison_values'] == comparison
                            assert visits == [('structure', role), ('comparison', role)]
                            assert module('providers')._rna_comparison_receiver_context(actual)
                        else:
                            assert 'received_rna_structure_values' not in actual
                            assert 'received_rna_comparison_values' not in actual
                            assert visits == []
                        rows.append({'home': home, 'context_role': role, 'received_keys': sorted(actual),
                            'adapter_visits': list(visits), 'expected_original_branch': wanted,
                            'nonempty_structure': structure, 'nonempty_comparison': comparison})
    record = {'expected': expected, 'checks': rows,
        'controlled_port': 'RNA adapters already-authenticated _received values; actual received_context and private callback execute',
        'scientific_evidence_authenticated': False, 'native_or_model_actions': 0}
    (output / 'rna_context_probe.json').write_text(json.dumps(record, indent=2) + '\n')
    return {'checks': len(rows), 'expected': expected, 'output': str(output)}
