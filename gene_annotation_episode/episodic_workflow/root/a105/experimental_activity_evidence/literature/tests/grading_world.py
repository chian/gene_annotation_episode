"""A real held world for this episode: a Store with the problem, a reaction term and the proposed annotation (the claim),
passed to the entry Episode in custody. No search, paper or source is given: the chain finds them."""
from gene_annotation_episode.state import Store

FLAGS = ('assay_grading_population', 'ratio_source_population', 'controlled_response_population', 'gel_population',
         'completion_time_population', 'product_partition_population', 'active_site_population',
         'parent_depletion_population', 'stoichiometric_balance_population', 'compiled_assay_population',
         'channel_population', 'ion_discrimination_population')
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}, 'rate_population': False,
            **{name: False for name in FLAGS},
            'tool_registry': {'pdfinfo_executable': None, 'pdftotext_executable': None, 'pdftoppm_executable': None,
                              'job_limits': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
            'knowledge_library_directory': None, 'launch_instruction_directory': None}
# A real model run: each unit costs 0.1 credit, so the controller stops the Episode when its forecast yield of a
# further unit no longer exceeds that.
MODEL_SETTINGS = {**SETTINGS, 'cost': 0.1}


def held_world(directory):
    """The Store, the entry input of the episode at ``literature_assignment_v1`` and the records the model would name."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    target = store.problem()['subject_refs'][0]
    scope = {'subject_refs': [target]}
    artifact = store.artifact('The question context.', 'text/plain')
    context = store.put('source', {'provider': 'synthetic_context', 'accession': None, 'uri': None,
                                   'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                   'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                        origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'hydrolysis', 'label': 'Hydrolysis',
                                  'term_type': 'reaction', 'source_ref': context, 'anchor': None},
                         origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'catalyzes',
                                        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []},
                         origin='reasoning')['id']
    task = {'version': 'literature_local_task_v1', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
            'credit_unit': 1.0}
    held = [target, context, artifact, reaction, proposed]
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [context],
                  'literature_task': task, 'proposed_annotation_ref': proposed, 'scope': scope,
                  'received_record_refs': held}
    names = {'store': store, 'target': target, 'context': context, 'reaction': reaction, 'proposed': proposed,
             'scope': scope}
    return {**names, 'input': {'assignment': assignment, 'message': {'objective': 'find the evidence'},
                               'selection': []}}
