"""Original runtime envelope/receipt expressions versus existing private owners.

Only typed message assembly and supplied receipt/progress callbacks execute.
Scientific choice, native work, persistence restoration and full workflows are
outside these controlled global-resolution checks.
"""
import ast
from copy import deepcopy
import hashlib
from pathlib import Path
from types import FunctionType, SimpleNamespace
from unittest.mock import patch

from .. import runtime
from ..scientific_process.episode import ScientificProcessEpisode
from ..method_loop import Context, EpisodeTree, Grain

ORIGINAL_SHA256 = 'e176fabb8f9a31c45a344dd37f18dfdefa4e6ef2a18f3352d9ebd3a25e89e40e'
ROUTES = (
    ('launch', 'execution_job_submission'),
    ('results', 'execution_result_acquisition'),
    ('hpc', 'hpc_work_planning'),
    ('literature', 'published_evidence_assessment'),
    ('scientific_process', 'scientific_process'))
SCHEMA = {'type': 'object', 'properties': {'qualification': {'type': 'string', 'const': 'unresolved'}},
          'required': ['qualification'], 'additionalProperties': False}


def forbidden(*args, **kwargs):
    raise AssertionError('outside original typed envelope/receipt boundary')


class EmptyCatalog:
    def as_record(self):
        return {'fixture': 'no scientific choices or execution'}

    def headers(self):
        return ()

    resolve = staticmethod(forbidden)


def parent_binding():
    return ScientificProcessEpisode(SimpleNamespace(), library=EmptyCatalog(),
        tool_library=EmptyCatalog(), child_roles=tuple(role for role, _ in ROUTES))


def original_function(boundary):
    path = Path(__file__).parent / 'fixtures/organization_original/implicit_parent_runtime.py.source'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_SHA256
    tree = ast.parse(raw)
    cls, = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Workflow']
    method_name = 'build' if boundary == 'request' else '_receive_form'
    method, = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name]
    if boundary == 'request':
        branch, = [node for node in method.body if isinstance(node, ast.If)
                   and ast.dump(node.test) == ast.dump(ast.parse('request_assembler is None', mode='eval').body)]
        body = deepcopy(branch.body)
        assert isinstance(body[0], ast.Assign) and ast.unparse(body[0].targets[0]) == 'path'
        assert isinstance(body[-1], ast.Assign) and ast.unparse(body[-1].targets[0]) == 'request'
        body.append(ast.parse('return path, goal, message, identity, request').body[0])
    else:
        starts = [index for index, node in enumerate(method.body) if isinstance(node, ast.If)
                  and ast.dump(node.test) == ast.dump(ast.parse('self.receipts is not None and (not redelivery) and (not self.is_job_source(source))', mode='eval').body)]
        assert len(starts) == 1
        body = deepcopy(method.body[starts[0]:])
        assert isinstance(body[-1], ast.Return) and ast.unparse(body[-1].value) == 'references'
    oracle = deepcopy(method)
    oracle.name = '_original_scientific_parent_boundary'
    oracle.decorator_list = []
    oracle.body = body
    namespace = dict(vars(runtime))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[oracle], type_ignores=[])),
                 str(path), 'exec'), namespace)
    # Actual original expressions keep the real runtime module dictionary;
    # copying that dictionary would incorrectly freeze callback-time rebindings.
    value = namespace[oracle.name]
    return FunctionType(value.__code__, vars(runtime), value.__name__, value.__defaults__), value.__kwdefaults__


def oracle(boundary):
    function, defaults = original_function(boundary)
    function.__kwdefaults__ = defaults
    return function


def observation(role, boundary, timing, *, original):
    events = []
    parent = parent_binding()
    owner = (parent.child_request_assembler(role) if boundary == 'request'
             else parent.execution_child_report_receiver(role))
    child = dict(ROUTES)[role]
    expected_module = runtime.__package__ + '.scientific_process.' + ('to' if boundary == 'request' else 'from') + '_child_' + child
    assert owner.__module__ == expected_module
    # Owner import is deliberately complete before replacement of its provider.
    function = oracle(boundary) if original else owner
    injected = LookupError('original supplied late provider failure')
    original_record = runtime.Record
    def make_record(label):
        def value(message):
            events.append(('Record', label))
            if timing == 'during-error' and label == 'late':
                raise injected
            return original_record(message)
        return value
    def references(label):
        def value(*args, **kwargs):
            events.append(('references', label))
            if timing == 'during-error' and label == 'late':
                raise injected
            return ['supplied-' + label]
        return value
    late_record = make_record('late')
    late_references = references('late')
    def materialize(value):
        events.append(('materialize', value))
        if timing != 'before-call':
            runtime.Record = late_record
    def receive_progress(*args):
        events.append('progress_callback')
        if timing != 'before-call':
            runtime._references_in = late_references
    def bind(child_id, parent_id):
        events.append(('bind', child_id, parent_id))
        return {'fixture_parent_id': parent_id}
    scope = {'subject_refs': []}
    grains = {name: Grain(name, 'original objective', 'typed report', forbidden)
              for name in tuple(role for role, _ in ROUTES)}
    context = Context(tree=EpisodeTree(grains['scientific_process'], {
        grains['scientific_process']: tuple(grains.values()),
        **{grain: () for name, grain in grains.items() if name != 'scientific_process'}},
        self_nesting=('scientific_process',)), run_id='scientific-global-boundary')
    workflow = SimpleNamespace(context=context, grains=grains, run_id='scientific-global-boundary',
        inprocess_completion_order=None, scientific_process_binding=parent,
        launch_instructions=SimpleNamespace(materialize=materialize),
        receipts=SimpleNamespace(bind=bind, receive=lambda *args, **kw: events.append(('receive', args, kw))),
        progress_provider=SimpleNamespace(receive_form=receive_progress),
        specialist=lambda source: None, is_job_source=lambda source: False,
        store=SimpleNamespace(get=forbidden, reference_subset=forbidden),
        episode_bindings=SimpleNamespace(received_form_references=lambda *args: []),
        binding_context=lambda source: SimpleNamespace(episode_id=source.episode_id),
        native_timing_information=None, job_episodes=None,
        receive_tool_attributions=lambda *args, **kw: [])
    source = SimpleNamespace(episode_id='scientific-parent', scope=scope)
    contract = runtime.TypedReportContract('Preserve original typed message', SCHEMA,
        lambda *args: True, lambda *args: None)
    parent_goal = runtime.EpisodeGoal.root(objective='Original parent', result_contract=SCHEMA)
    result, error, identical_error = None, None, False
    with patch.object(runtime, 'Record', make_record('before')), patch.object(runtime, '_references_in', references('before')):
        try:
            if boundary == 'request':
                path, goal, message, identity, request = function(workflow, role, 'child',
                    'Original child', scope, parent=parent_goal,
                    parent_path=(('scientific_process', 'parent'),), contract=contract,
                    initial={'qualification': 'unresolved'},
                    episode_assignment={'launch_instructions': None})
                result = {'path': path, 'goal': goal.as_record(), 'message': message,
                          'episode_id': identity.episode_id, 'request': request.as_record()}
            else:
                result = function(workflow, source, {'qualification': 'unresolved'}, SCHEMA, 7, redelivery=True)
        except Exception as caught:
            error = (type(caught).__name__, str(caught))
            identical_error = caught is injected
    return {'events': events, 'result': result, 'error': error, 'identical_error': identical_error}


def paired(role, boundary, timing):
    before = observation(role, boundary, timing, original=True)
    after = observation(role, boundary, timing, original=False)
    assert after == before
    assert after['identical_error'] is (timing == 'during-error')
    if timing != 'during-error':
        assert after['error'] is None and after['result'] is not None
    marker = ('Record' if boundary == 'request' else 'references',
              'before' if timing == 'before-call' else 'late')
    assert marker in after['events']
    first_callback = 'progress_callback' if boundary == 'receipt' else ('materialize', None)
    assert after['events'].index(first_callback) < after['events'].index(marker)
    return after
