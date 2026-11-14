"""Four A106 Scientific incoming owners; original saved/nonreceipt semantics.

Direct admission comparisons use declared receipt ports. Selector checks use a
real standalone Scientific root, its actual registry and configured defining
classes. This distinct caller configuration does not repair the unsupported
receipt-enabled annotation path or establish nested Scientific construction.
No child acquisition, native science or whole restoration is claimed.
"""
import ast
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from .test_implicit_annotation_parent import module, original_member, no_external
from .test_implicit_parent_outgoing import scientific_standalone_workflow


def original_admission(name):
    selected = original_member('Workflow', 'selected')
    node, = [n for n in selected.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name == ('report' if name == 'admit_unowned_return' else 'admitted_report')]
    if name == 'admit_unowned_return':
        boundary, = [i for i, n in enumerate(node.body) if isinstance(n, ast.If)
                     and ast.unparse(n.test) == 'child_exchange is not None']
        node.body = node.body[boundary + 1:]
    else:
        assert ast.unparse(node.body[0].test) == 'child_exchange is not None'
        node.body = node.body[1:]
    # The original report is async because its earlier receipt-resolution
    # branch awaits. The selected nonreceipt tail has no async operations;
    # the actual private extraction exposes that exact tail synchronously.
    assert not any(isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith))
                   for statement in node.body for n in ast.walk(statement))
    if isinstance(node, ast.AsyncFunctionDef):
        assert name == 'admit_unowned_return'
        node = ast.FunctionDef(name=node.name, args=node.args, body=node.body,
            decorator_list=node.decorator_list, returns=node.returns,
            type_comment=node.type_comment, type_params=node.type_params)
    node.name = name
    node.args = ast.parse('def f(self, source, child, index, schema, contract, result, request): pass').body[0].args
    namespace = dict(vars(module('runtime')))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 '<authenticated-original-A106-Scientific-admission>', 'exec'), namespace)
    return namespace[name]




@pytest.mark.parametrize('role,home,preparer_name', [
    ('launch', 'execution_job_submission', 'prepare_commission'),
    ('monitor', 'execution_progress_assessment', 'prepare_commission'),
    ('results', 'execution_result_acquisition', 'prepare_commission'),
    ('literature', 'published_evidence_assessment', 'prepare_request'),
])
def test_scientific_selector_uses_actual_standalone_context(scientific_standalone_workflow, monkeypatch, role, home, preparer_name):
    store, workflow = scientific_standalone_workflow
    rt = module('runtime')
    science = workflow.scientific_process_binding
    scope = store.validate_scope()
    # This is the original explicit standalone entry recipe. The preparation
    # context is a caller operand, not an invented recorded commissioning parent.
    preparation = module('episode_bindings').BindingContext(workflow.run_id, 'preparation', 'annotation',
        (('annotation', 'preparation'),), scope, {}, {'message': {'scope': scope, 'episode_assignment': {}}})
    class EngineeringProjector:
        def __call__(self, store, scope, **arguments):
            assert arguments == {}
            return {'credit': 0, 'proposed_annotations': [], 'comparisons': []}
        def as_record(self):
            return {'version': 'standalone_engineering_credit_fixture_v1',
                'meaning': 'Explicit caller test operand; no executed scientific progress.', 'credit_input': 0}
    projector = EngineeringProjector()
    monkeypatch.setattr(workflow, 'project_credit', projector)
    numerical = module('numerical')
    monkeypatch.setattr(workflow, 'controller_factory', lambda _path, initial, **_kwargs:
        numerical.YieldController('a106_standalone_selector', initial, 0.5,
            numerical.YieldParameters(uncertainty_alpha=0.05)))
    schema = {'type': 'object', 'properties': {'constructor_input_supplied': {'type': 'boolean',
        'description': 'Whether the caller supplied this engineering-only report form.'}},
        'required': ['constructor_input_supplied'], 'additionalProperties': False}
    contract = rt.TypedReportContract('Return engineering fixture metadata', schema, lambda *_: True)
    assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': science.library.reference('A106'), 'thought_pattern': science.library.reference('P01'),
        'child_tool_info': []}, 'evidence_refs': [], 'constraints': {}, 'context': {'evidence_task': {
            'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': 'A106', 'credit_unit': 1}}}
    with pytest.raises(module('domain').ContractError, match='scientific_parent_invocation_required'):
        science.prepare_assignment(None, 'scientific_process', assignment, scope, 'no-parent')
    prepared = science.prepare_invocation(preparation, 'scientific_process', assignment, scope, 'explicit:prepare',
        invocation={'objective': 'Inspect the original standalone selector', 'purpose': contract.decision,
            'report_schema': schema, 'initial_report': {'constructor_input_supplied': True}})
    episode = workflow.build('scientific_process', 'standalone_' + role, 'Inspect the original standalone selector',
        scope, contract=contract, initial={'constructor_input_supplied': True},
        episode_assignment=prepared['assignment'], scientific_process=prepared['scientific_process'])
    source = episode.source
    assert workflow.root_role == 'scientific_process' and workflow.receipts is None
    assert type(source) is science.decision_source_type
    assert source.path == (('scientific_process', 'standalone_' + role),)
    context = workflow.binding_context(source)
    science.validate_context(context)
    assert workflow.scientific_projector_for_context(context) is projector
    assert workflow.source_credit_view(source)['credit'] == 0
    child = workflow.episode_bindings.for_child(source.path, role)
    assert child.binding_path == 'scientific_process/' + home
    preparer = getattr(module('scientific_process.to_child_' + home), preparer_name)
    selected_preparer = science.child_request_preparer(role)
    if selected_preparer is None:
        selected_preparer = science.child_request_preparer_for_binding(role, child.binding_path)
    assert selected_preparer is preparer
    owners = module('scientific_process.incoming_message_owners')
    selected = owners.admission_for_prepared_request(workflow, source, preparer, role)
    incoming = module('scientific_process.from_child_' + home)
    assert selected == (incoming.admit_return, incoming.admit_unowned_return)
    assert owners.admission_for_prepared_request(workflow, preparation, preparer, role) is None
    # A custom callable retains the pre-existing shared admission path.
    assert owners.admission_for_prepared_request(workflow, source, lambda *_args: None, role) is None
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
