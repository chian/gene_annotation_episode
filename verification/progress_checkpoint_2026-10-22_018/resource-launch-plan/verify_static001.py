"""Static packet checks only: no driver/helper/application import or DB open."""
from pathlib import Path
import ast
import hashlib
import json

P = Path(__file__).resolve().parent
TEMPLATE = Path('/tmp/configured-literature-launch-plan-20261022-001-li2s253s')
CODE = Path('/tmp/gene-annotation-configured-caller-20261022-007')
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001')
PIN = '3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842'

def d(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def load(path):
    return json.loads(path.read_bytes())

def save(name, value):
    with (P / name).open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')

def runtime():
    digest = hashlib.sha256()
    members = {}
    for path in sorted(path for package in ('gene_annotation_episode', 'method_loop') for path in (CODE / package).rglob('*.py')):
        relative = path.relative_to(CODE).as_posix()
        witness = d(path)
        members[relative] = witness
        digest.update(relative.encode() + b'\0')
        digest.update(bytes.fromhex(witness['sha256']))
    return {'sha256': digest.hexdigest(), 'file_count': len(members), 'members': members}

before = runtime()
assert before['sha256'] == PIN and before['file_count'] == 137
adaptation = load(P / 'ADAPTATION001.json')
template_manifest = load(TEMPLATE / 'MANIFEST_FINAL001.json')
template_members = template_manifest['members']
if isinstance(template_members, list):
    rows = [(row.get('path', row.get('relative_path')), row) for row in template_members]
else:
    rows = list(template_members.items())
for name, expected in rows:
    path = Path(name) if Path(name).is_absolute() else TEMPLATE / name
    actual = d(path)
    assert all(actual[key] == expected[key] for key in ('sha256', 'bytes'))

for name in ('launch_driver001.py', 'inspect_first_request001.py'):
    original = (TEMPLATE / name).read_text()
    expected = original
    for old, new in adaptation['exact_text_replacements']:
        expected = expected.replace(old, new)
    assert (P / name).read_text() == expected
    assert d(P / name) == adaptation['code_diffs'][name]['modified']

files = ['LAUNCH_COMMAND_DRAFT001.json', 'launch_driver001.py', 'inspect_first_request001.py',
    'INDEPENDENT_PREPARATION_VERIFICATION001.json', 'CHECKPOINT_TABLE_METADATA001.json',
    *[path.name for path in sorted(P.glob('prepared-*'))]]
assert len(files) == 13
inputs = {'version': 'configured_resource_launch_plan_inputs_v1',
    'status': 'unadopted_not_executed', 'members': {name: d(P / name) for name in files}}
save('INPUTS001.json', inputs)
command = load(P / 'LAUNCH_COMMAND_DRAFT001.json')
assert command['argv'] == ['/home/chia/repos/gene_annotation_episode/.venv/bin/python', '-m',
    'gene_annotation_episode.case_execution', 'run', '--run-dir', str(RUN), '--policy',
    str(CODE / 'gene_annotation_episode/api_planning_case_policy.py'), '--parameters',
    str(RUN / 'caller-inputs/parameters.json')]
assert command['cwd'] == str(CODE)
assert command['environment_overrides'] == {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(CODE)}
assert '--resume' not in command['argv'] and command['runtime_files'] == 137
assert command['resume'] is False and command['retry'] is False and command['cancellation'] is False and command['timeout'] is None
assert command['inputs']['parameters.json']['sha256'] == '651d132265e6c7b974dd06c152ed6498b2c5b4ed5bae0130836278743695b6cb'
assert command['inputs']['config.toml']['sha256'] == 'a62d1d4c3dc34c4b7829dc14c9fa0a04b50d79f1261c5911e661eedd077369a2'
assert command['inputs']['focus.txt']['sha256'] == 'b2f718a545a1829b8521f6cd437ff1c0688ad4068b5f739d033e9d8ce151c7bf'
assert command['working_database_before_launch']['sha256'] == 'c8b8529c643f7bf2a3eaab690cae04510856b3290698143c92d28487ba70d68a'
for name, expected in command['inputs'].items():
    actual = d(P / ('prepared-' + name))
    assert all(actual[key] == expected[key] for key in ('sha256', 'bytes'))
verification = load(P / 'INDEPENDENT_PREPARATION_VERIFICATION001.json')
assert d(P / 'INDEPENDENT_PREPARATION_VERIFICATION001.json')['sha256'] == '764be765e71d3354ca64aa8372f71b7592629b2c9512b5257a38378c765d7964'
assert verification['status'] == 'verified_prepared_not_started' and verification['selected_inputs_unchanged'] is True
assert verification['external_preparation_exit_code'] == 0
assert verification['source_pin'] == {'sha256': PIN, 'file_count': 137}
assert verification['external_preparation_process_receipt']['sha256'] == command['external_preparation_invocation']['sha256'] == 'c837af2fc9bd11851598d65ce064c4c1c33f53f87b3f120cd60824a027c7612d'
working = next(row for row in verification['checks'] if row['check'] == 'working_file_hash_only')
assert working['hashes_equal'] is True
assert working['current_post_prepare'] == command['working_database_before_launch']
assert len(verification['witnesses']) == 688
prepared = load(P / 'prepared-PREPARATION_RESULT001.json')
receipt = load(P / 'prepared-scientific-checkpoint-fork.json')
parameters = load(P / 'prepared-parameters.json')
assert prepared['status'] == 'prepared_not_started' and prepared['inherited_refs'] == 200
assert parameters['policy']['scientific_progress']['initial_known_record_refs'] == receipt['initial_known_record_refs']
assert len(receipt['initial_known_record_refs']) == len(set(receipt['initial_known_record_refs'])) == 200
assert command['native_registry_ref'] == parameters['policy']['operational']['registry_ref'] == 'execution_registry_cd714f8f3cb7422f825ee2fc891d798a'
assert command['public_search_registry_ref'] == parameters['services']['public_search_registry']['registry_ref'] == 'execution_registry_1411c4378f584a40b65ed74178e1cb05'

parsed = {name: ast.parse((P / name).read_text(), filename=str(P / name)) for name in
    ('launch_driver001.py', 'inspect_first_request001.py', 'build_launch_inputs001.py')}
driver, helper = parsed['launch_driver001.py'], parsed['inspect_first_request001.py']
modules = {name.name.split('.')[0] for node in ast.walk(driver) if isinstance(node, ast.Import) for name in node.names}
modules |= {node.module.split('.')[0] for node in ast.walk(driver) if isinstance(node, ast.ImportFrom)}
assert modules <= {'pathlib', 'datetime', 'argparse', 'hashlib', 'json', 'os', 'shutil', 'stat', 'subprocess', 'sys', 'time'}
popen = [node for node in ast.walk(driver) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'Popen']
assert len(popen) == 1 and 'timeout' not in [keyword.arg for keyword in popen[0].keywords]
wait = [node for node in ast.walk(driver) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'wait']
assert len(wait) == 1 and not wait[0].args and not wait[0].keywords
for tree in (driver, helper):
    calls = [node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else None
        for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert not set(calls) & {'kill', 'terminate', 'send_signal', 'run_prepared_case', 'run_workflow', 'Workflow',
        'Store', 'Journal', 'ModelConnection', 'capture', 'project_credit', 'sleep'}
    assert not any(isinstance(node, (ast.While, ast.AsyncFor)) for node in ast.walk(tree))
connect = [node for node in ast.walk(helper) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'connect']
assert len(connect) == 1 and ast.unparse(connect[0].args[0]) == "dbpath.as_uri() + '?mode=ro'"
snapshot = next(node for node in ast.walk(helper) if isinstance(node, ast.FunctionDef) and node.name == 'snapshot')
assert any(isinstance(node, ast.Try) and node.finalbody for node in ast.walk(snapshot))
assert len([node for node in ast.walk(snapshot) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'close']) == 1
assert any(isinstance(node, ast.Constant) and node.value == 'PRAGMA query_only=ON' for node in ast.walk(snapshot))
assert any(isinstance(node, ast.Constant) and node.value == 'BEGIN' for node in ast.walk(snapshot))

tables_path = P / 'CHECKPOINT_TABLE_METADATA001.json'
tables = {row['name']: set(row['column_names']) for row in load(tables_path)['tables']}
required = {'inputs': {'id', 'data'}, 'records': {'id', 'record_type', 'data'}, 'material_members': {'id', 'data'}, 'artifacts': {'id'},
    'runtime_runs': {'run_id', 'settings'}, 'runtime_episodes': {'run_id', 'episode_id', 'path', 'request', 'initial_credit'},
    'runtime_model_calls': {'run_id', 'episode_id', 'call_index', 'purpose', 'request', 'response'},
    'runtime_record_receipts': {'receipt_index', 'run_id', 'episode_id', 'record_ref', 'receipt_kind', 'source_index'},
    'runtime_receipt_inheritance': {'run_id', 'episode_id', 'parent_episode_id', 'through_receipt_index'},
    'runtime_execution_bindings': {'run_id', 'selection', 'settings_sha256', 'runtime_binding'}}
for table, columns in required.items():
    assert columns <= tables[table], table
frame_ast = ast.parse((CODE / 'gene_annotation_episode/local_commission_frame.py').read_text())
frame = next(node for node in frame_ast.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_local_commission_frame')
assert [arg.arg for arg in frame.args.args] == ['value'] and [arg.arg for arg in frame.args.kwonlyargs] == ['run_id', 'episode_id', 'pending', 'controller_credit']
presentation_ast = ast.parse((CODE / 'gene_annotation_episode/model_context_presentation.py').read_text())
presentation = next(node for node in presentation_ast.body if isinstance(node, ast.FunctionDef) and node.name == 'validate_model_context_presentation')
assert [arg.arg for arg in presentation.args.args] == ['presentation'] and [arg.arg for arg in presentation.args.kwonlyargs] == ['original_context', 'run_id', 'episode_id', 'before_decision_index', 'preview_size']
prepare = next(node for node in presentation_ast.body if isinstance(node, ast.FunctionDef) and node.name == '_prepare')
serialize = [node for node in ast.walk(prepare) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and ast.unparse(node.func) == 'json.dumps']
assert len(serialize) == 1 and ast.unparse(serialize[0]) == 'json.dumps(projected, allow_nan=False)'
helper_serial = [node for node in ast.walk(helper) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    and ast.unparse(node.func) == 'json.dumps' and node.args and ast.unparse(node.args[0]) == "presentation['context']"]
assert len(helper_serial) == 1 and [(item.arg, ast.literal_eval(item.value)) for item in helper_serial[0].keywords] == [('allow_nan', False)]
identity_source = (CODE / 'method_loop/identities.py').read_text()
assert 'normalize_structural_path(self.path)' in identity_source and 'isinstance(value, (tuple, list))' in identity_source
after = runtime()
assert after == before

readset = {'version': 'configured_resource_launch_static_readset_v1',
    'prior_complete_template_consumer_readset': d(TEMPLATE / 'READSET001.json'),
    'template_manifest': d(TEMPLATE / 'MANIFEST_FINAL001.json'), 'template_members_verified': len(rows),
    'full_templates_and_authoring_code': {name: d(P / name) for name in parsed},
    'frozen_source_signature_and_serialization_reinspection': {name: d(CODE / name) for name in
        ('gene_annotation_episode/local_commission_frame.py', 'gene_annotation_episode/model_context_presentation.py', 'method_loop/identities.py')},
    'source_reading_limit': 'Existing complete consumer reading is recorded by the unchanged template readset; this static invocation rechecks hashes, named signatures and serialization, not all runtime semantics.',
    'table_manifest_metadata_only': d(tables_path), 'required_SQL_columns': {key: sorted(value) for key, value in required.items()},
    'independent_actual_verification': command['independent_preparation_verification'],
    'external_preparation_invocation': command['external_preparation_invocation'],
    'metadata_sources': adaptation['copied_prepared_sources'],
    'pure_validation_future_use': {'SQL_closed_first': True,
        'frame_signature': ['value', '*', 'run_id', 'episode_id', 'pending', 'controller_credit'],
        'presentation_signature': ['presentation', '*', 'original_context', 'run_id', 'episode_id', 'before_decision_index', 'preview_size'],
        'EpisodeRef_path_input': 'Actual JSON list of two-string segments is accepted and normalized.',
        'model_context_serialization': 'Exactly json.dumps(projected, allow_nan=False); default ensure_ascii, insertion order and separators.'}}
save('READSET001.json', readset)
checks = {'version': 'configured_resource_launch_static_checks_v1', 'status': 'passed_static_only_not_launched_or_inspected',
    'runtime_pin': PIN, 'runtime_files': 137, 'runtime_source_bytes_unchanged': True, 'runtime_members': before['members'],
    'inputs': d(P / 'INPUTS001.json'), 'core_input_members': 13, 'ordinary_CLI_argv_exact': True,
    'complete_template_logic_preserved_by_exact_replacements': True, 'driver_stdlib_only': True,
    'one_Popen_and_one_wait_no_timeout': True, 'no_signal_retry_private_loop': True,
    'helper_one_ro_active_connection_no_immutable': True, 'helper_BEGIN_query_only_finally_close': True,
    'helper_SQL_columns_grounded': True, 'pure_validator_signatures_match': True,
    'model_serialization_matches_producer': True, 'EpisodeRef_JSON_path_supported': True,
    'independent_preparation_verification_bound': True, 'external_preparation_exit_bound': True,
    'working_historical_hashes_equal_as_observed': True, 'copied_inherited_ref_count': 200,
    'counts': {'launches': 0, 'helper_invocations': 0, 'application_imports': 0, 'application_constructors': 0,
        'DB_opens': 0, 'models': 0, 'HTTP': 0, 'native_jobs': 0, 'tests': 0, 'permanent_writes': 0},
    'failure_metadata': [], 'limits': ['No current working DB hash or SQL is performed during authoring.',
        'The688 verification witness descriptors are parsed as metadata; their original file paths are not followed.',
        'Initial credit/history/forecast values remain future observations, never manufactured expectations.']}
save('STATIC_CHECKS001.json', checks)
print(json.dumps({'status': checks['status'], 'inputs': d(P / 'INPUTS001.json'), 'readset': d(P / 'READSET001.json'),
    'checks': d(P / 'STATIC_CHECKS001.json'), 'driver': d(P / 'launch_driver001.py'), 'helper': d(P / 'inspect_first_request001.py')}, sort_keys=True))
