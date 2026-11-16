"""Original lumpy record schemas, separate from native execution."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library import native_atac_differential_contracts as shared

OPERATION = 'detect_and_characterize_structural_variations'
MODE = 'lumpy_pe_sr_vcf'
RUN_PLAN_FILENAME = 'lumpy-plan.json'
ATTEMPT_DIRECTORY_NAME = 'lumpy-attempt'
OWNER_FILENAME = '.native-lumpy-owner.json'
STARTED_FILENAME = '.native-lumpy-started.json'
SEAL_FILENAME = 'lumpy-seal.json'
REQUEST_VERSION = 'lumpy_request_v1'
PLAN_VERSION = 'lumpy_run_plan_v1'
SEAL_VERSION = 'lumpy_command_seal_v1'
POLICY = deepcopy(shared.POLICY)
require, canonical, digest = shared.require, shared.canonical, shared.digest
failure, unique_failures = shared.failure, shared.unique_failures
obj, arr, enum, nullable = shared._obj, shared._arr, shared._enum, shared._null
TEXT, ID, BOOL = deepcopy(shared._TEXT), deepcopy(shared._ID), deepcopy(shared._BOOL)
FILE, PIN = deepcopy(shared._FILE), deepcopy(shared._PIN)
INTEGER = {'type': 'integer', 'minimum': -(2**31), 'maximum': 2**31 - 1}
NATIVE_TOKEN = {'type': 'string', 'minLength': 1, 'maxLength': 512,
    'pattern': r'^[^\x00-\x20\x7f,:]+$'}
SONAME = {'type': 'string', 'minLength': 1, 'maxLength': 255,
    'pattern': r'^[A-Za-z0-9_+.-]+\.so(?:\.[A-Za-z0-9_+.-]+)*$'}
DECIMAL = {'type': 'string', 'minLength': 1, 'maxLength': 512,
    'pattern': r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$'}
_COMMON = dict(signal_key={**ID, 'maxLength': 500}, output_sample_label=NATIVE_TOKEN,
    declared_sample_id=nullable(TEXT), reference_id=nullable(TEXT), bam=FILE,
    read_group=nullable(NATIVE_TOKEN))
PE = obj(kind={'const': 'paired_end'}, **_COMMON, histogram=FILE,
    parameters=obj(mean=DECIMAL, stdev=DECIMAL, read_length=INTEGER,
        min_non_overlap=INTEGER, discordant_z=INTEGER, back_distance=INTEGER,
        weight=INTEGER, min_mapping_threshold=INTEGER))
SR = obj(kind={'const': 'split_read'}, **_COMMON,
    parameters=obj(back_distance=INTEGER, min_non_overlap=INTEGER, weight=INTEGER,
        min_mapping_threshold=INTEGER, min_clip=INTEGER))
REQUEST = obj(version={'const': REQUEST_VERSION}, operation={'const': OPERATION},
    mode={'const': MODE}, run_key=ID, signals=arr({'oneOf': [PE, SR]}, minItems=1),
    parameters=obj(minimum_sample_weight=INTEGER, trim_threshold=DECIMAL, probability_output=BOOL))
NATIVE_RUNTIME = obj(executable=PIN, loader=PIN,
    libraries=arr(obj(name=SONAME, file=PIN)), reported_version=nullable(TEXT))
SOFTWARE = obj(driver_runtime=shared.driver_runtime_schema(), native_runtime=NATIVE_RUNTIME)
JOB = obj(request=REQUEST, software=SOFTWARE,
    input_bindings=arr(obj(input_key=ID, file=FILE, path=TEXT), minItems=1))
REQUESTED = obj(argv=arr(TEXT, minItems=6, maxItems=6), environment=deepcopy(shared._ENV), native_lumpy=JOB)
SPEC = obj(file_key=ID, role=enum('vcf', 'stderr', 'bam_header', 'seal'),
    relative_path=TEXT, format=ID, required=BOOL)
PLAN = obj(version={'const': PLAN_VERSION}, identity=deepcopy(shared._IDENTITY),
    requested_job=REQUESTED, attempt_directory=TEXT, policy={'const': POLICY}, outputs=arr(SPEC, minItems=4))
INPUT_SEAL = obj(input_key=ID, signal_key=ID, role=enum('bam', 'histogram'),
    file=FILE, staging_state=enum('verified', 'failed', 'not_attempted'),
    staged=deepcopy(shared._DECL), staging_temporary=deepcopy(shared._DECL))
SEAL = obj(version={'const': SEAL_VERSION}, identity=deepcopy(shared._IDENTITY),
    producer_ref=ID, software_sha256=deepcopy(shared._SHA), argv=arr(TEXT), environment=deepcopy(shared._ENV),
    inputs=arr(INPUT_SEAL, minItems=1), input_inspections=arr(shared.atac_execution_schema('HeaderExtraction')),
    started_at=nullable(TEXT), finished_at=nullable(TEXT), returncode=nullable({'type': 'integer'}),
    outcome=enum('succeeded', 'failed', 'not_run'),
    outputs=arr(obj(specification=SPEC, declaration=deepcopy(shared._DECL)), minItems=3),
    failures=arr(shared.atac_execution_schema('Failure')))
SCHEMAS = {'Binding': obj(operation={'const': OPERATION}, mode={'const': MODE}, software=SOFTWARE),
    'NativeRuntime': NATIVE_RUNTIME, 'SoftwareBinding': SOFTWARE, 'Request': REQUEST, 'NativeJob': JOB, 'RequestedJob': REQUESTED,
    'RunPlan': PLAN, 'CommandSeal': SEAL}
def lumpy_execution_schema(kind, *, bindings=None):
    require(type(kind) is str and kind in SCHEMAS, 'unsupported_lumpy_execution_schema')
    schema = deepcopy(SCHEMAS[kind])
    if bindings is not None:
        require(kind == 'RequestedJob', 'unsupported_lumpy_execution_schema')
        from gene_annotation_episode.episodic_workflow.root.library.native_lumpy_execution import validate_lumpy_bindings
        choices = [{'properties': {'native_lumpy': {'properties': {
            'software': {'const': row['software']}, 'request': {'properties': {
                'operation': {'const': OPERATION}, 'mode': {'const': MODE}}}}}}}
            for row in validate_lumpy_bindings(bindings)]
        schema = {'allOf': [schema, {'anyOf': choices} if choices else {'not': {}}]}
    return schema


