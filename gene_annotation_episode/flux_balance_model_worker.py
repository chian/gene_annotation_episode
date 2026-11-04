"""One selected Store-free model inspection/edit request; no optimization."""
from copy import deepcopy
from pathlib import Path, PurePosixPath
import sys

from . import flux_balance_model_tools as model_tools
from .execution_contracts import canonical
from .native_flux_balance_contracts import path_value, validate_flux_balance_software
from .native_flux_balance_storage import confined_file, immutable_json, read_json


WORKER_MODULE = 'gene_annotation_episode.flux_balance_model_worker'
MODEL_MODULE_FILES = ('flux_balance_model_worker.py', 'flux_balance_model_tools.py')


def _require(condition, code):
    if not condition:
        raise ValueError('fba_model_worker_' + code)


def validate_flux_balance_model_worker_request(value):
    """Check the complete selected envelope without loading a model or files."""
    _require(type(value) is dict and set(value) == {
        'request', 'model_path', 'output_directory', 'software'}, 'request_invalid')
    request = model_tools.validate_flux_balance_model_request(value['request'])
    software = validate_flux_balance_software(value['software'])
    model = path_value(value['model_path'], absolute=True)
    output = path_value(value['output_directory'], absolute=True)
    protected = [model, PurePosixPath(software['python_home']), PurePosixPath(software['module_root']),
        *(PurePosixPath(path) for path in software['dependency_roots']),
        *(PurePosixPath(pin['path']) for pin in [software['python'], *software['implementation_files'],
            *software['runtime_files'], *software['solver_runtime_files']])]
    _require(all(not path.is_relative_to(output) and not output.is_relative_to(path)
        for path in protected), 'input_output_overlap')
    required = {str(PurePosixPath(software['module_root']) / 'gene_annotation_episode' / name)
        for name in MODEL_MODULE_FILES}
    _require(required <= {pin['path'] for pin in software['implementation_files']}, 'implementation_unbound')
    return deepcopy({'request': request, 'model_path': str(model),
        'output_directory': str(output), 'software': software})


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    _require(len(arguments) == 2, 'arguments_invalid')
    request_path, result_path = [Path(path_value(path, absolute=True)) for path in arguments]
    _require(request_path != result_path, 'control_path_conflict')
    confined_file(result_path.parent, result_path.name)
    _require(not result_path.exists(), 'result_exists')
    value = validate_flux_balance_model_worker_request(read_json(request_path))
    root = PurePosixPath(result_path.parent)
    protected = [PurePosixPath(value['model_path']), PurePosixPath(value['software']['python_home']),
        PurePosixPath(value['software']['module_root']),
        *(PurePosixPath(path) for path in value['software']['dependency_roots']),
        *(PurePosixPath(pin['path']) for pin in [value['software']['python'],
            *value['software']['implementation_files'], *value['software']['runtime_files'],
            *value['software']['solver_runtime_files']])]
    _require(all(not path.is_relative_to(root) and not root.is_relative_to(path)
        for path in protected), 'input_output_overlap')
    _require(request_path != Path(value['model_path']) and result_path != Path(value['model_path'])
        and not result_path.is_relative_to(Path(value['output_directory'])), 'control_path_conflict')
    implementations = {pin['path'] for pin in value['software']['implementation_files']}
    _require({str(Path(__file__).resolve()), str(Path(model_tools.__file__).resolve())} <= implementations,
        'executing_implementation_unbound')
    result = model_tools.run_flux_balance_model_request(value['request'], model_path=value['model_path'],
        output_directory=value['output_directory'], software=value['software'])
    result = model_tools.validate_flux_balance_model_result(result)
    _require(canonical(result['request']) == canonical(value['request']), 'result_request_conflict')
    immutable_json(result_path, result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
