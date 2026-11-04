"""Literal human views of the registered, retained MACS2 peak packet.

Only declared provenance slots are omitted. Scientific strings and native
tokens are never searched or rewritten. Validation and rendering use no File,
native process, calculator, receipt or publication authority.
"""
from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Mapping

from .macs2_peak_result_contracts import validate_macs2_peak_return


_METADATA = ("macs_version", "name", "format", "control_presence", "paired_end", "broad",
    "scaling_direction", "local_lambda")
_NUMBER_UNITS = {
    "effective_genome_size_bp": "bp", "band_width_bp": "bp", "model_fold_lower": "fold",
    "model_fold_upper": "fold", "qvalue_cutoff": "1", "pvalue_cutoff": "1",
    "large_local_window_bp": "bp", "tag_size_bp": "bp", "fragment_size_bp": "bp",
    "treatment_total_tags": "tags", "treatment_postfilter_tags": "tags",
    "treatment_max_duplicates": "native duplicate count", "treatment_redundant_rate": "fraction",
    "control_total_tags": "tags", "control_postfilter_tags": "tags",
    "control_max_duplicates": "native duplicate count", "control_redundant_rate": "fraction",
    "treatment_total_fragments": "fragments", "treatment_postfilter_fragments": "fragments",
    "control_total_fragments": "fragments", "control_postfilter_fragments": "fragments",
    "shift_bp": "bp", "d_bp": "bp",
}
_ROW_UNITS = {
    "start1": "bp; one_based_inclusive", "end1": "bp; one_based_inclusive",
    "abs_summit1": "bp; one_based", "length_bp": "bp",
    "start0": "bp; zero_based_half_open", "end0": "bp; zero_based_half_open",
    "summit_offset0": "bp offset from start0", "pileup": "native pileup",
    "minus_log10_pvalue": "-log10(p)", "minus_log10_qvalue": "-log10(q)",
    "fold_enrichment": "fold", "display_score": "native display score",
    "signal_value": "native signal value", "score": "native summit score",
}


def _literal(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "[]"
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", "<br>")
    return "\n".join(["| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)])


def macs2_peak_scientific_job_view(value):
    """Project an authenticated private job to its exact scientific selection."""
    from .native_macs2_peak_execution import validate_macs2_peak_native_job
    job = validate_macs2_peak_native_job(value)
    request = deepcopy(job['request'])
    for row in request['inputs']:
        row['file'] = {key: row['file'][key] for key in ('artifact_ref', 'format')}
    return {'request': request}


def select_macs2_peak_execution_values(value):
    """Recognize only the new registered native/compact execution shapes."""
    if not isinstance(value, Mapping):
        return None
    from .execution_contracts import checked
    from .macs2_peak_request_binding import (
        is_compact_assignment, scientific_request_schema, validate_compact_assignment,
    )
    from .native_macs2_peak_execution import (
        REQUEST_VERSION, validate_macs2_peak_requested_job, validate_macs2_peak_bindings,
    )
    try:
        if set(value) == {'argv', 'environment', 'native_macs2_peak'}:
            job = validate_macs2_peak_requested_job(dict(value))
            return {'native_macs2_peak': macs2_peak_scientific_job_view(job['native_macs2_peak'])}
        if set(value) == {'request', 'software', 'input_bindings'}:
            return macs2_peak_scientific_job_view(dict(value))
        if set(value) == {'request'} and value['request'].get('version') == REQUEST_VERSION:
            return {'request': checked(value['request'], scientific_request_schema(), 'macs2_peak_presentation_invalid')}
        if is_compact_assignment(dict(value)):
            return validate_compact_assignment(dict(value), value['resource_id'])
        if set(value) == {'operation', 'mode', 'software'}:
            binding, = validate_macs2_peak_bindings([dict(value)])
            return {key: binding[key] for key in ('operation', 'mode')}
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        return None
    return None


def macs2_peak_schema_view(value):
    """Replace only exact private MACS2 RequestedJob schemas with public operands.

    The compiler, rather than this view, supplies backend fields. Unknown and
    altered schemas remain literal so projection cannot create an invocation.
    """
    if not isinstance(value, Mapping):
        return None
    from .execution_contracts import canonical
    from .native_macs2_peak_execution import macs2_peak_execution_schema, validate_macs2_peak_bindings
    base = macs2_peak_execution_schema('RequestedJob')
    bindings = None
    if canonical(value) != canonical(base):
        try:
            choices = value['allOf'][1]['anyOf']
            bindings = []
            for choice in choices:
                native = choice['properties']['native_macs2_peak']['properties']
                bindings.append(dict(operation=native['request']['properties']['operation']['const'],
                    mode=native['request']['properties']['mode']['const'], software=native['software']['const']))
            bindings = validate_macs2_peak_bindings(bindings)
            if canonical(value) != canonical(macs2_peak_execution_schema('RequestedJob', bindings=bindings)):
                return None
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    from .macs2_peak_request_binding import scientific_request_schema
    result = {'type': 'object', 'description': (
        'Host-compiled native execution. The public scientific assignment supplies the selected request, '
        'resource and binding ordinal; the host supplies software, File identities and execution coordinates.'),
        'properties': {'request': scientific_request_schema()}, 'required': ['request'], 'additionalProperties': False}
    if bindings is not None:
        result['properties']['binding_ordinal_0based'] = {'enum': list(range(len(bindings)))}
    return result


def _macs2_peak_context(state):
    from .native_macs2_peak_execution import OPERATION, MODE
    process = state.get('scientific_process', {})
    information = process.get('child_tool_info', ()) if isinstance(process, Mapping) else ()
    if isinstance(information, (list, tuple)) and any(isinstance(row, Mapping)
            and row.get('name') == OPERATION and row.get('resources') == 'local' for row in information):
        return True
    task = state.get('selected_execution_task', {})
    if not isinstance(task, Mapping) or task.get('version') != 'selected_execution_task_v1':
        return False
    requests = task.get('requests', ())
    if not isinstance(requests, (list, tuple)):
        return False
    for row in requests:
        if not isinstance(row, Mapping):
            continue
        job = row.get('job', {})
        selected = select_macs2_peak_execution_values(job)
        request = None if selected is None else selected.get('request')
        if request is not None and request.get('operation') == OPERATION and request.get('mode') == MODE:
            return True
    return False


def _macs2_peak_progress_view(value):
    """Project only a supplied MACS2 progress envelope, never infer a file role."""
    if not isinstance(value, Mapping) or value.get('version') != 'progress_snapshot_v1':
        return None
    status = value.get('execution_status')
    if not isinstance(status, Mapping) or status.get('version') != 'resource_execution_status_v1':
        return None
    native = status.get('native')
    physical = native.get('native') if isinstance(native, Mapping) else None
    plan = physical.get('native_macs2_peak_plan') if isinstance(physical, Mapping) else None
    if not isinstance(plan, Mapping):
        return None
    from pathlib import PurePosixPath
    from .native_macs2_peak_execution import validate_macs2_peak_run_plan
    from .progress_records import validate_resource_status
    try:
        validate_resource_status(dict(status))
        plan = validate_macs2_peak_run_plan(dict(plan))
    except (ValueError, TypeError, KeyError):
        return None
    declarations = {str(PurePosixPath(plan['attempt_directory']) / row['relative_path']): row
        for row in plan['outputs']}
    outputs = []
    for row in native.get('outputs', ()):
        if not isinstance(row, Mapping):
            return None
        shown = {key: deepcopy(row[key]) for key in ('role', 'available', 'bytes', 'writer_closed') if key in row}
        role = row.get('role')
        if isinstance(role, str) and role.startswith('requested_output:'):
            declared = declarations.get(role.removeprefix('requested_output:'))
            shown['role'] = declared['role'] if declared is not None else 'requested_output'
            shown['format'] = declared['format'] if declared is not None else None
        outputs.append(shown)
    # This is the existing public progress selection, not its host control
    # envelope. Preserve actual measurements and missingness without a poll.
    result = {key: deepcopy(value[key]) for key in ('version', 'progress_ref', 'target_handle',
        'observed_at', 'result_available', 'committed_record_refs', 'measurements', 'log_windows', 'dependencies')
        if key in value}
    result['execution_status'] = {key: deepcopy(status[key]) for key in ('version', 'handle',
        'observed_at', 'lifecycle_state', 'liveness', 'result_available', 'return_available', 'failure', 'resource_kind')
        if key in status}
    result['execution_status']['native'] = {key: deepcopy(native[key]) for key in ('state', 'outcome',
        'returncode', 'failure_code', 'elapsed_seconds', 'duration_measure', 'measurements') if key in native}
    metadata = physical.get('metadata', {})
    metadata = metadata if isinstance(metadata, Mapping) else {}
    for key in ('elapsed_seconds', 'duration_measure', 'observed_scratch_bytes'):
        if key in metadata:
            result['execution_status']['native'][key] = deepcopy(metadata[key])
    result['execution_status']['native']['outputs'] = outputs
    return result


def select_macs2_peak_capture_presentation(state, *, lookup_results=()):
    """Detach human capture/progress views from declared MACS2 decision slots.

    Source operands, acquisition states and generic unverified provenance stay
    literal. This view neither authenticates a producer nor changes a stored
    outcome, report schema, receipt or requested scientific value.
    """
    if not isinstance(state, Mapping) or not _macs2_peak_context(state):
        return dict(context=state, lookup_results=lookup_results, captures=[])
    from .execution_contracts import canonical, checked
    from .local_file_capture_results import OUTCOME_SCHEMA, OUTCOMES_SCHEMA
    sources = state.get('available_report_facts', {})
    source = sources.get('execution_file_capture_outcomes', {}) if isinstance(sources, Mapping) else {}
    source = source if isinstance(source, Mapping) else {}
    declared = canonical(source.get('report_schema')) == canonical(OUTCOMES_SCHEMA)
    roles = {'macs2_peaks_xls_narrow': 'peaks_xls', 'macs2_narrowpeak10': 'narrowpeak',
        'macs2_summits_bed5': 'summits', 'macs2_model_r': 'model', 'native_stdout': 'stdout',
        'native_stderr': 'stderr', 'macs2_peak_command_seal_v1': 'seal'}
    captures, keys = [], []
    def project(value):
        if isinstance(value, Mapping):
            if declared and value.get('version') == 'execution_file_source_outcome_v1':
                try:
                    original = checked(dict(value), OUTCOME_SCHEMA, 'macs2_peak_capture_view_invalid')
                except (ValueError, TypeError, KeyError):
                    return value
                if any(row['format'] not in roles for row in original['files']):
                    return value
                # Generic stdout alone does not establish a MACS2 profile.
                if original['files'] and not any(row['format'].startswith('macs2_') for row in original['files']):
                    return value
                key = canonical(original)
                if key not in keys:
                    keys.append(key)
                    captures.append(dict(operation=original['operation'], job=deepcopy(original['job']),
                        provenance=deepcopy(original['provenance']), failure=deepcopy(original['failure']),
                        files=[dict(role=roles[row['format']], **{name: deepcopy(row[name]) for name in
                            ('format', 'source_ref', 'availability', 'size_bytes', 'failure')})
                            for row in original['files']]))
                return 'Selected MACS2 file capture ' + str(keys.index(key) + 1)
            progress = _macs2_peak_progress_view(value)
            if progress is not None:
                return progress
            return {key: project(child) for key, child in value.items()}
        if isinstance(value, (list, tuple)):
            return [project(child) for child in value]
        return value
    shown = dict(state)
    # Do not traverse instructions, tool schemas or arbitrary scientific input
    # context. Only supplied outcome/report/progress channels enter this view.
    for field in ('child_reports', 'last_local_outcome', 'current_report_update', 'waiting_support'):
        if field in shown:
            shown[field] = project(shown[field])
    lookups = [project(value) for value in lookup_results]
    return dict(context=shown, lookup_results=lookups, captures=captures)


def render_macs2_peak_captures(captures):
    parts = []
    for index, capture in enumerate(captures, 1):
        parts.extend(['Selected MACS2 file capture ' + str(index), '',
            _table(('Capture property', 'Literal value'), ((name, _literal(capture[name]))
                for name in ('operation', 'job', 'provenance', 'failure'))), '',
            _table(('Requested file role', 'Format', 'Acquisition state', 'Callable Source', 'Retained bytes', 'Failure'),
                ((row['role'], row['format'], row['availability'], _literal(row['source_ref']),
                    _literal(row['size_bytes']), _literal(row['failure'])) for row in capture['files']))])
    return '\n\n'.join(parts)


def render_macs2_peak_result(value, number=1):
    """Render the exact validated selection; no counts or geometry are derived."""
    packet = validate_macs2_peak_return(value)
    window = packet["peak_window"]
    parts = ["Selected molecular result " + str(number), "", "Native MACS2 peak measurements", "",
        _table(("Result property", "Supplied value"), [
            ("Callable result Source", packet["source_ref"]), ("Status", packet["status"]),
            ("Original native outcome", packet["native_outcome"]), ("Run", packet["run_key"]),
            ("Reference", packet["reference_id"]),
            ("Selected row offset", _literal(window["row_window"]["offset"])),
            ("Selected row limit", _literal(window["row_window"]["limit"])),
            ("Native representation rows available", _literal(window["total_rows"])),
            ("Native row extent", window["row_extent"])]), "",
        "Native counts by representation", "",
        _table(("Run", "Representation", "Literal count", "Unit", "Extent"),
            ((row["run_key"], row["representation"], _literal(row["count"]), "native rows", row["extent"])
                for row in packet["native_peak_counts"])), "",
        "XLS, narrowPeak and summit rows are representations of the native peaks, not separate peak populations.",
        "", "Native reported metadata", "",
        _table(("Field", "Literal value", "Native locations"),
            ((name, _literal(packet["reported_metadata"][name]),
                _literal(packet["reported_metadata"]["field_locations"].get(name, []))) for name in _METADATA)),
        "", "Native reported numbers", "",
        _table(("Field", "Literal value", "Original lexeme", "State", "Unit", "Native locations"),
            ((name, _literal(row["value"]), _literal(row["lexeme"]), row["state"], _NUMBER_UNITS[name],
                _literal(row["locations"])) for name, row in packet["reported_numbers"].items()))]
    for index, selected in enumerate(window["rows"], 1):
        row, source = selected["row"], selected["source"]
        parts.extend(["", "Selected native row " + str(index), "",
            _table(("Row property", "Literal value"), [
                ("Run", _literal(selected["callpeak_run_key"])),
                ("Representation", _literal(selected["representation"])),
                ("Row ordinal", _literal(row["row_ordinal"])),
                ("Native location", _literal(row["locator"])),
                ("Original field tokens", _literal(row["original_fields"]))]), "",
            _table(("Field", "Literal native value", "Unit"),
                ((name, _literal(child), _ROW_UNITS.get(name, "native field"))
                    for name, child in row.items() if name not in {"row_ordinal", "locator", "original_fields"})),
            "", "Retained representation qualifications", "",
            _table(("Property", "Literal value"), ((name, _literal(source[name])) for name in
                ("format", "supplied_extent", "producer_outcome", "writer_closed", "origin")))])
        geometry = selected["geometry"]
        parts.extend(["", "Stored geometry", "", ("null" if geometry is None else
            _table(("Field", "Literal value", "Unit"), ((name, _literal(child),
                "bp; zero_based" if name in {"start0", "end0", "summit0"} else "bp" if name == "span_bp"
                else "native field") for name, child in geometry.items())))])
        link = selected["peak_link"]
        parts.extend(["", "Stored representation correspondence", "", ("null" if link is None else
            _table(("Field", "Literal value"), ((name, _literal(child)) for name, child in link.items())))])
    parts.extend(["", "Native data qualifications", "",
        _table(("Code", "Binding", "Row ordinals", "Native locations", "Field", "Requirement"),
            ((row["code"], _literal(row["binding_key"]), _literal(row["row_ordinals"]),
                _literal(row["locations"]), _literal(row["field"]), row["requirement"])
                for row in packet["issues"])), "", "Recorded execution and capture failures", "",
        _table(("Code", "Stage", "Step", "File role", "Binding", "Native location", "Field pointer", "Requirement"),
            ((row["code"], row["stage"], _literal(row["step_key"]), _literal(row["file_key"]),
                _literal(row["binding_key"]), _literal(row["locator"]), _literal(row["field_path"]),
                row["requirement"]) for row in packet["failures"]))])
    return "\n".join(parts)


__all__ = ["render_macs2_peak_result", "macs2_peak_scientific_job_view",
    "select_macs2_peak_execution_values", "macs2_peak_schema_view",
    "select_macs2_peak_capture_presentation", "render_macs2_peak_captures"]
