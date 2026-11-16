"""Original macs2_peak record schemas, separate from native execution."""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library import native_atac_differential_contracts as shared

OPERATION = 'perform_chipseq_peak_calling_with_macs2'
MODE = 'macs2_2_2_9_1_auto_matched_control_native_model'
RUN_PLAN_FILENAME = 'macs2-peak-plan.json'
ATTEMPT_DIRECTORY_NAME = 'macs2-peak-attempt'
OWNER_FILENAME = '.native-macs2-peak-owner.json'
STARTED_FILENAME = '.native-macs2-peak-started.json'
SEAL_FILENAME = 'macs2-peak-seal.json'
POLICY = deepcopy(shared.POLICY)
REQUEST_VERSION = 'macs2_peak_request_v1'
PLAN_VERSION = 'macs2_peak_run_plan_v1'
SEAL_VERSION = 'macs2_peak_command_seal_v1'

require, canonical, digest = shared.require, shared.canonical, shared.digest
failure, unique_failures = shared.failure, shared.unique_failures
obj, arr, enum, nullable = shared._obj, shared._arr, shared._enum, shared._null
TEXT, ID, INT, BOOL = shared._TEXT, shared._ID, shared._INT, shared._BOOL
FILE = deepcopy(shared._FILE)
SOFTWARE = shared.atac_execution_schema('SoftwareBinding')
REFERENCE, SAMPLE = deepcopy(shared._REFERENCE), deepcopy(shared._SAMPLE)
INPUT = obj(input_key=ID, role=enum('treatment', 'control'), sample_id=ID, reference_id=ID, file=FILE)
REQUEST = obj(version={'const': REQUEST_VERSION}, operation={'const': OPERATION}, mode={'const': MODE},
    run_key=ID, condition_id=ID, reference=REFERENCE, samples=arr(SAMPLE, minItems=1, maxItems=2),
    inputs=arr(INPUT, minItems=2, maxItems=2),
    callpeak=obj(genome_size_argument=TEXT, qvalue_cutoff={'type': 'number', 'exclusiveMinimum': 0, 'maximum': 1}),
    output_prefix=TEXT)
JOB = obj(request=REQUEST, software=SOFTWARE,
    input_bindings=arr(obj(input_key=ID, file=FILE, path=TEXT), minItems=2, maxItems=2))
REQUESTED = obj(argv=arr(TEXT, minItems=6, maxItems=6), environment=shared._ENV, native_macs2_peak=JOB)
SPEC = obj(file_key=ID, role=enum('peaks_xls', 'narrowpeak', 'summits', 'model', 'stdout', 'stderr', 'seal'),
    relative_path=TEXT, format=ID, required=BOOL)
PLAN = obj(version={'const': PLAN_VERSION}, identity=deepcopy(shared._IDENTITY), requested_job=REQUESTED,
    attempt_directory=TEXT, policy={'const': POLICY}, outputs=arr(SPEC, minItems=7, maxItems=7))
SEAL = obj(version={'const': SEAL_VERSION}, identity=deepcopy(shared._IDENTITY), producer_ref=ID,
    argv=arr(TEXT), environment=shared._ENV,
    inputs=arr(obj(input_key=ID, role=enum('treatment', 'control'), file=FILE), minItems=2, maxItems=2),
    started_at=nullable(TEXT), finished_at=nullable(TEXT), returncode=nullable({'type': 'integer'}),
    outcome=enum('succeeded', 'failed', 'not_run'),
    outputs=arr(obj(specification=SPEC, declaration=deepcopy(shared._DECL)), minItems=6, maxItems=6),
    failures=arr(shared.atac_execution_schema('Failure')))
SCHEMAS = {'Binding': obj(operation={'const': OPERATION}, mode={'const': MODE}, software=SOFTWARE),
    'SoftwareBinding': SOFTWARE, 'Request': REQUEST, 'NativeJob': JOB, 'RequestedJob': REQUESTED,
    'RunPlan': PLAN, 'CommandSeal': SEAL}


def macs2_peak_execution_schema(kind, *, bindings=None):
    require(type(kind) is str and kind in SCHEMAS, 'unsupported_macs2_peak_execution_schema')
    schema = deepcopy(SCHEMAS[kind])
    if bindings is not None:
        require(kind == 'RequestedJob', 'unsupported_macs2_peak_execution_schema')
        from gene_annotation_episode.episodic_workflow.root.library.native_macs2_peak_execution import validate_macs2_peak_bindings
        choices = [{'properties': {'native_macs2_peak': {'properties': {
            'software': {'const': row['software']}, 'request': {'properties': {
                'operation': {'const': OPERATION}, 'mode': {'const': MODE}}}}}}}
            for row in validate_macs2_peak_bindings(bindings)]
        schema = {'allOf': [schema, {'anyOf': choices} if choices else {'not': {}}]}
    return schema


