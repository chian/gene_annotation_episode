"""The calls the experiment-assessment tests make inside the probe episode: they save sheets through ``ctx.store``
and call the assessment functions of one module (the shared one or one of the three axis copies)."""
import json
from importlib import import_module

TYPES = {'literature_experiment_assessments': 'partner_assay'}
DEFAULT_TYPE = 'intervention_response'


class SheetReader:
    """The part of a literature repository the assessment functions use: the store the sheets are in, the
    experiment types it offers, and the reading of a saved sheet from its artifact."""

    def __init__(self, store, experiment_types):
        self.store, self.experiment_types = store, experiment_types

    def read(self, sheet_ref):
        return json.loads(self.store.get_artifact(self.store.get(sheet_ref)['artifact_ref']))


def reader(ctx, module):
    kind = TYPES.get(module.__name__.rsplit('.', 1)[1], DEFAULT_TYPE)
    return SheetReader(ctx.store, {kind: {}}), kind


def save_sheet(store, experiment_ref, assessment):
    saved = {'experiment_assessment': assessment, 'experimental_bindings': {'experiment_ref': experiment_ref}}
    artifact = store.artifact(json.dumps(saved, sort_keys=True), 'application/json')
    request = store.artifact(json.dumps({'sheet_for': assessment['assessment_key'], 'revises': assessment['revises_sheet_ref']},
                                        sort_keys=True), 'application/json')
    return store.put('source', {'provider': 'probe_sheets', 'accession': None, 'uri': None, 'artifact_ref': artifact,
                                'text_ref': artifact, 'request_ref': request, 'version': None, 'retrieved_at': None},
                     origin='tool')['id']


def assessment(experiment_ref, kind, conclusion, revises=None):
    return {'experiment_ref': experiment_ref, 'experiment_type': kind, 'assessment_key': 'does_the_intervention_matter',
            'scientific_question': 'What does the intervention establish?', 'conclusion': conclusion,
            'limitations': ['one replicate'], 'revision_reason': None if revises is None else 'new replicate',
            'revises_sheet_ref': revises}


def refused(module, call):
    try:
        call()
    except module.ContractError as error:
        return str(error)
    return None


def begin(ctx, module):
    """The first assessment of an experiment: its sheet and the row that keeps the assessment."""
    module, store = import_module(module), ctx.store
    repository, kind = reader(ctx, module)
    source = store.put('source', {'provider': 'probe_papers', 'accession': None, 'uri': None,
                                  'artifact_ref': store.artifact('Experiment A: one assay.', 'text/plain'),
                                  'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None},
                       origin='caller')['id']
    experiment = store.put('reference', {'reference_type': 'assay', 'source_ref': source, 'accession': 'assay_a',
                                         'label': 'Experiment A', 'sequence_ref': None, 'molecule': None, 'length': None,
                                         'term_refs': [], 'context_refs': [],
                                         'anchor': {'source_ref': source, 'artifact_ref': store.get(source)['artifact_ref'],
                                                    'start': 0, 'end': 12, 'quote': 'Experiment A'}},
                           origin='caller')['id']
    first = assessment(experiment, kind, 'the intervention matters')
    sheet = save_sheet(store, experiment, first)
    row = module.record_assessment(store, sheet, first)
    return {'sheet': sheet, 'experiment': experiment, 'row': row['id'], 'heads': module.current_assessments(repository)}


def revise(ctx, module):
    """A revision of the head: a revision that names no predecessor is refused, the right one is saved."""
    module = import_module(module)
    store = ctx.store
    repository, kind = reader(ctx, module)
    head = module.current_assessments(repository)[0]
    blind = assessment(head['experiment_ref'], kind, 'a rival conclusion')
    second = assessment(head['experiment_ref'], kind, 'the intervention matters little', revises=head['sheet_ref'])
    answers = {'blind': refused(module, lambda: module.check_revision(repository, blind))}
    module.check_revision(repository, second)
    sheet = save_sheet(store, head['experiment_ref'], second)
    module.record_assessment(store, sheet, second)
    return {**answers, 'sheet': sheet, 'revises': head['sheet_ref']}


def inspect(ctx, module):
    """The heads, the history of the head, and the saved-assessment check against the operation that saved it."""
    module = import_module(module)
    repository, kind = reader(ctx, module)
    heads = module.current_assessments(repository)
    rows = ctx.store.table(module.ASSESSMENTS).select()
    first, second = rows[0]['sheet_ref'], rows[1]['sheet_ref']
    saved = repository.read(second)
    expected = saved['experiment_assessment']
    request = {'episode_id': rows[1]['episode_id'], 'operation_key': rows[1]['operation_key'],
               'arguments': {'experiment_assessment': expected}}
    module.validate_saved_assessment(repository, saved, request, second)
    other = {**expected, 'conclusion': 'another conclusion'}
    return {'heads': [head['sheet_ref'] for head in heads], 'history': [item['sheet_ref'] for item in
                                                                          module.assessment_history(repository, second)],
            'first_row_unit': rows[0]['unit'], 'second_row_unit': rows[1]['unit'],
            'wrong_assessment': refused(module, lambda: module.validate_saved_assessment(
                repository, saved, {**request, 'arguments': {'experiment_assessment': other}}, second)),
            'wrong_operation': refused(module, lambda: module.validate_saved_assessment(
                repository, saved, request, first))}
