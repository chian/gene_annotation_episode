"""The binding model repository on the custody-scoped store: a model sheet saved over a binding sheet the same
Episode produced, read back through the binding repository's checks, and its cells projected."""
from .evolutionary_history_world import call, read, run, source, world  # noqa: F401
from .test_evolutionary_history_binding_storage import REPOSITORY as BINDING, SHEET, arguments, table

MODEL = 'literature_binding_model_storage:LiteratureBindingModelRepository'
MODEL_SHEET = {'from_step': 1, 'path': ['result', 'sheet_ref']}


def test_a_model_sheet_without_a_supplied_model_is_saved_read_back_and_projected(world):
    reference, artifact = source(world, table(), 'application/json')
    binding, model, held, saved, cells = run(world, 'binding_model', [
        call(BINDING, 'populate', arguments(reference), scope=world['scope']),
        call(MODEL, 'populate', {'source_ref': SHEET, 'model_source_ref': None, 'model_witnesses': []},
             scope=world['scope']),
        read(MODEL, 'held_sheet_refs'),
        read(MODEL, 'read', MODEL_SHEET),
        read(MODEL, 'project_cells', [MODEL_SHEET])], held=[reference, artifact])
    sheet = model['result']['sheet_ref']
    assert model['status'] == 'completed' and sheet != binding['result']['sheet_ref']
    assert held == [sheet]
    assert saved['input_source_ref'] == binding['result']['sheet_ref']
    assert model['result']['model_source_ref'] is None
    assert {row['sheet_ref'] for row in cells} == {sheet}
    assert {row['component'] for row in cells} == set(model['result']['cells'])
