"""Fixtures for finite producer integration, always inside the bounded runner.

Event values and report text below are labelled synthetic/source-format inputs.
Actual FlowIO/FlowUtils execute; this fixture does not claim a molecular assay.
"""
from copy import deepcopy
import importlib
import importlib.metadata
import io
from pathlib import Path
import shutil
import sys

from fluorescence_flowio_test_support import require_bounded_runtime

require_bounded_runtime()

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.fluorescence_execution_common import identity
from gene_annotation_episode.native_fluorescence_contracts import IMPLEMENTATION_NAMES
from gene_annotation_episode.native_fluorescence_storage import file_pin
from test_native_fluorescence_contracts import event_input, job, pin, software


EXTRA_IMPLEMENTATIONS = (
    'native_fluorescence_prepared_contracts.py', 'native_fluorescence_prepared_driver.py',
    'fluorescence_preparation_contracts.py', 'fluorescence_preparation_readers.py',
    'fluorescence_event_preparation.py', 'fluorescence_fcs_reader.py',
    'fluorescence_native_report_contracts.py', 'fluorescence_native_reports.py',
)
SCALE = 'fcs_scale_flowio_1_4_0'
COMPENSATE = 'spill_compensate_flowutils_1_2_2'
FACS = 'biomni_facs_log_548_v1'


def file_input(directory, name, raw, format_='json'):
    path = Path(directory) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return dict(file=identity(raw, format=format_), path=str(path))


def declared_software(*, fcs=True):
    """Declaration-only fixture; finite_driver explicitly disables trust claims."""
    result = software(fcs=fcs)
    root = Path(result['module_root']) / 'gene_annotation_episode'
    existing = {row['path'] for row in result['implementation_files']}
    result['implementation_files'].extend(pin(root / name) for name in EXTRA_IMPLEMENTATIONS
        if str(root / name) not in existing)
    if fcs:
        result['distributions'].extend([dict(name='numpy', version='2.2.6', requires=[]),
            dict(name='FlowUtils', version='1.2.2', requires=['numpy<3.0,>=2.0'])])
        result['runtime_files'].extend(pin('/declared-software/dependencies/' + name) for name in (
            'numpy/__init__.py', 'numpy-2.2.6.dist-info/METADATA',
            'flowutils/__init__.py', 'flowutils-1.2.2.dist-info/METADATA'))
    return result


def v2_job(directory, *, operation='perform_facs_cell_sorting', inputs=None):
    selected = job(directory, inputs=inputs, operation=operation)
    selected.update(version='native_fluorescence_job_v2', preparations=[], report_inputs=[],
        software=declared_software(fcs=any(row['parser'] == 'fcs_encoded' for row in selected['inputs'])))
    return selected


def selected_preparation(selected, directory, *, method, parent_kind='event_input', parent_index=0,
                         key='scaled', matrix_file=None, output_basis=None):
    if parent_kind == 'event_input':
        binding = selected['inputs'][parent_index]
        domain, channels = binding['domain'], binding['channels']
    else:
        domain = selected['preparations'][parent_index]['output']
        channels = domain['channels']
    output = dict(key=key, source_key=key + '.source', sample_key=domain['sample_key'],
        channels=[{**{name: row[name] for name in ('ordinal', 'native_name', 'label', 'unit', 'analyte')},
            'key': f'{key}.c{row["ordinal"]}'} for row in channels],
        comparison_basis=deepcopy(output_basis if output_basis is not None else domain['comparison_basis']))
    if method == SCALE:
        params = dict(metadata_policy='strict_present_fcs_metadata_v1')
        for row in output['channels']:
            if row['native_name'].lower() == 'time':
                row['unit'] = 'seconds'
    else:
        params = dict(matrix_file=deepcopy(matrix_file or selected['inputs'][0]['source']['file']), dataset_position=0,
            keyword='spill', input_domain_basis=deepcopy(domain['comparison_basis']),
            axes=[dict(native_label=row['native_name'], input_channel_key=row['key'], input_ordinal=row['ordinal'])
                for row in channels if row['native_name'] in ('A', 'B')])
    recipe = dict(version='fluorescence_preparation_recipe_v1', method=method, parameters=params)
    support = file_input(directory, key + '.recipe.json', core.canonical(recipe) + b'\n')
    selected['support_inputs'].append(support)
    request = dict(key=key, input=dict(kind=parent_kind, index=parent_index), output=output,
        recipe_file=support['file'], recipe=recipe)
    selected['preparations'].append(request)
    return request


def add_facs_report(selected, directory, *, association=True, key='native.report'):
    # Literal format fixture; this was not obtained by executing the upstream
    # FACS wrapper. R590/root retain authentic-wrapper verification separately.
    raw = (b'# FACS-based Cell Sorting and Enrichment Research Log\n'
        b'## Applying Gating Strategy for A\n'
        b'## Enrichment Results\nOriginal population: 2 cells\nSorted population: 2 cells\n'
        b'Enrichment percentage: 100.00%\n')
    item = file_input(directory, key + '.log', raw, 'text')
    field = dict(key=key + '.percent', locator=dict(kind='facs_metric', metric='selected_percent', occurrence=0),
        component_request=core._request('fraction', 'selected_percent', gate_key='gate-0', denominator='parent'))
    report = dict(**item, source_key=key, profile=FACS, fields=[field], association_file=None)
    if association:
        event = selected['inputs'][0]
        body = dict(version='fluorescence_report_association_v1', report_file=item['file'], fields=[dict(
            report_key=field['key'], component_request=field['component_request'],
            event_sources=[dict(file=event['source']['file'], dataset_position=event['source']['dataset_position'])],
            sample_keys=[event['sample']['key']], domain_keys=[event['domain']['key']],
            gates=[selected['definitions']['gates'][0]], control_pair=None)])
        support = file_input(directory, key + '.association.json', core.canonical(body) + b'\n')
        selected['support_inputs'].append(support)
        report['association_file'] = support['file']
    selected['report_inputs'].append(report)
    selected['parameters']['native_comparison_requests'].append(field['key'])
    return report


def prepared_job(directory, *, operation='perform_facs_cell_sorting', scale=True, compensate=True,
                 report=True, separate_matrix=False, rows=((220, 120, 10), (40, 200, 20))):
    native = importlib.import_module('flowio')
    assert native.__version__ == '1.4.0'
    assert importlib.import_module('flowutils').__version__ == '1.2.2'
    stream = io.BytesIO()
    native.create_fcs(stream, [value for row in rows for value in row], ['A', 'B', 'Time'],
        metadata_dict=dict(p1g='2', p2g='2', timestep='0.1', spill='2,A,B,1,0.1,0.2,1'))
    raw = stream.getvalue()
    binding = event_input(directory, raw, parser='fcs_encoded', name='A')
    binding['channels'] = [dict(key=f'raw.c{index}', ordinal=index, native_name=name, label=None,
        unit='ticks' if name == 'Time' else 'instrument_units', analyte=None,
        measurement_origin='supplied_predicted') for index, name in enumerate(('A', 'B', 'Time'))]
    basis = file_input(directory, 'encoded-basis.txt', b'explicit synthetic encoded matrix basis', 'text')
    binding['domain']['comparison_basis'] = dict(key='encoded-basis', evidence_file=basis['file'])
    selected = v2_job(directory, operation=operation, inputs=[binding])
    selected['support_inputs'].append(basis)
    if scale:
        basis = file_input(directory, 'scaled-basis.txt', b'explicit synthetic scaled matrix basis', 'text')
        selected['support_inputs'].append(basis)
        selected_preparation(selected, directory, method=SCALE, key='scaled',
            output_basis=dict(key='scaled-basis', evidence_file=basis['file']))
    matrix_file = None
    if separate_matrix:
        matrix = io.BytesIO()
        native.create_fcs(matrix, [1, 2], ['A', 'B'], metadata_dict=dict(spill='2,A,B,1,0.1,0.2,1'))
        support = file_input(directory, 'matrix.fcs', matrix.getvalue(), 'fcs')
        selected['support_inputs'].append(support)
        matrix_file = support['file']
    if compensate:
        selected_preparation(selected, directory, method=COMPENSATE,
            parent_kind='preparation' if scale else 'event_input', key='compensated', matrix_file=matrix_file)
    if report:
        add_facs_report(selected, directory)
    return selected


def actual_software(directory):
    """Freeze the exact selected native dependency closure in the bounded run."""
    attempt = require_bounded_runtime()
    root = Path(__file__).resolve().parents[1]
    directory = Path(directory)
    package = directory / 'modules/gene_annotation_episode'
    package.mkdir(parents=True)
    implementation = []
    for name in (*IMPLEMENTATION_NAMES, *EXTRA_IMPLEMENTATIONS):
        source, target = root / 'gene_annotation_episode' / name, package / name
        shutil.copyfile(source, target)
        target.chmod(0o444)
        implementation.append(file_pin(target))
    binary = directory / 'python'
    shutil.copyfile(Path(sys.executable).resolve(strict=True), binary)
    binary.chmod(0o555)
    home = Path(sys.base_prefix).resolve(strict=True)
    assert home.is_relative_to(attempt)
    stdlib = home / 'lib' / ('python%d.%d' % sys.version_info[:2])
    paths = {path.resolve() for path in stdlib.rglob('*') if path.is_file()
        and not any(part in ('site-packages', 'dist-packages', '__pycache__') for part in path.relative_to(stdlib).parts)
        and path.suffix not in ('.pyc', '.pyo')}
    distributions, roots = [], []
    for name in ('FlowIO', 'FlowUtils', 'numpy'):
        distribution = importlib.metadata.distribution(name)
        distributions.append(dict(name=name, version=distribution.version, requires=distribution.requires or []))
        dependency_root = str(Path(distribution.locate_file('')).resolve(strict=True))
        assert Path(dependency_root).is_relative_to(attempt)
        if dependency_root not in roots:
            roots.append(dependency_root)
        assert distribution.files is not None
        for item in distribution.files:
            relative = Path(str(item))
            if '__pycache__' in relative.parts or relative.suffix in ('.pyc', '.pyo'):
                continue
            paths.add(Path(distribution.locate_file(item)).resolve(strict=True))
    return dict(version='fluorescence_software_v1', python=file_pin(binary), python_version=sys.version,
        python_home=str(home), module_root=str(package.parent), implementation_files=implementation,
        dependency_roots=roots, distributions=distributions, runtime_files=[file_pin(path) for path in sorted(paths)])
