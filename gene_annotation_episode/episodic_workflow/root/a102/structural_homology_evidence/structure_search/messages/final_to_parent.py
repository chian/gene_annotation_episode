"""The return: controlled data only; no path and no text, no protein name. EVERY RETURNED RECORD LIST IS CLOSED UNDER NAMING:
``internal_summary`` builds each with ``job_records.returned_with_names`` (the records the child returns together with
everything they name among the records it holds), so the parent holds what the returned records name and nothing private is
named (the summary is where the closing runs: ``final_to_parent`` receives no reader). Always: ``credit`` and the ``finding``:
the state of the search (``no_model``, ``model_held``, ``estimated``, ``launched``, ``finished``, ``extracted`` or ``failed``);
the model facts (origin, residues, mean pLDDT 0 to 100); once graded the hit, named, not-asked and candidate counts of the
sheet (the names themselves stay in the graded sheet, which the head reads), the control count and the naming's batches and
stop reason; the shared wait notice, estimate and observed seconds and last failure code (``structure_search_child.
COMMON_FINDING``). Selectable: ``execution_handoff_refs``, ``execution_check_refs``, ``execution_closure_refs`` and
``graded_refs`` (the graded records: the model's product row, the result, the hit metadata and the grading sheet, their
sources and artifacts). The model's product row is the record a later commission passes back as its model."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.foldseek_search import (
    MODEL_ORIGINS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    COMMON_FINDING, STATES, common_finding)

FINDING_FORM = RecordForm({
    'state': ChoiceField('text', 'The search: no_model (no model held), model_held (a model, no estimate), estimated (a '
                                 'model and an estimate held, nothing launched), launched (accepted, not finished), '
                                 'finished (the service finished it; not yet extracted), extracted (graded) or failed',
                         STATES),
    'model_origin': ChoiceField('text', 'Where the model of the target came from: alphafold_db (a prediction held by '
                                        'AlphaFold DB for the exact sequence) or esmfold (a prediction of the sequence)',
                                MODEL_ORIGINS, required=False),
    'model_residues': Field('integer', 'The residues the model covers', required=False),
    'model_mean_plddt': Field('number', 'The mean pLDDT of the model, 0 to 100: the model\'s own confidence, not similarity',
                              required=False),
    'hit_count': Field('integer', 'The hits of the graded sheet', required=False),
    'named_count': Field('integer', 'The hits that carry a product name from UniProt', required=False),
    'not_asked_count': Field('integer', 'The hits never asked about (the naming stopped): not asked, which is not '
                                        'asked-and-missing', required=False),
    'candidate_count': Field('integer', 'The product candidates with a value in the graded test (the mean index B of their '
                                        'hits)', required=False),
    'control_count': Field('integer', 'The hits that are the model itself (a control: it gives no value to any candidate)',
                           required=False),
    'data_request_count': Field('integer', 'The requests made to UniProt for the names of the hits', required=False),
    'naming_batch_count': Field('integer', 'The batches of 100 hits named', required=False),
    'naming_stopped': ChoiceField('text', 'Why the naming stopped: settled (a batch admitted no new product and moved no '
                                          'candidate\'s score by more than 0.01) or all_named', ('settled', 'all_named'),
                                  required=False),
    **COMMON_FINDING,
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The state of the search and its controlled facts', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The handoff records of the searches launched', required=False),
    'execution_check_refs': Field('record_refs', 'The status records of the search', required=False),
    'execution_closure_refs': Field('record_refs', 'The closure record of the fetched result', required=False),
    'graded_refs': Field('record_refs', 'The graded records: the model\'s product row, the result data product, the hit '
                                        'metadata, the grading sheet, their sources and the artifacts they name',
                         required=False),
})


def final_to_parent(summary, completion, selection):
    finding = {'state': summary['state'], **common_finding(summary)}
    model = summary['model']
    if model is not None:
        finding.update(model_origin=model['origin'], model_residues=model['residues'],
                       model_mean_plddt=model['mean_plddt'])
    if summary['counts']:
        counts = summary['counts'][-1]
        finding.update(hit_count=counts['hit_count'], named_count=counts['named_count'],
                       not_asked_count=counts['not_asked_count'], candidate_count=counts['candidate_count'],
                       control_count=counts['control_count'], data_request_count=counts['metadata_request_count'],
                       naming_batch_count=counts['naming_batch_count'], naming_stopped=counts['naming_stopped'])
    facts = {'execution_handoff_refs': list(summary['handoff_refs']), 'execution_check_refs': list(summary['check_refs']),
             'execution_closure_refs': list(summary['closure_refs']), 'graded_refs': list(summary['graded_refs'])}
    return {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
