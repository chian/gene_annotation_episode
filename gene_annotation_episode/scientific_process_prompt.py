"""Text presentation for published scientific investigation instructions.

The decision journal and response contracts keep their existing JSON. This
module only selects already supplied information and renders it for the model;
it neither reads evidence nor selects an action, interprets a finding or fits a
yield estimate. Legacy scientific processes and other roles are not handled.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
from .episode_work_report import render_completed_action_reports

from .decision_context import INSTRUCTIONS, TEXT_INSTRUCTIONS
from .execution_contracts import digest
from .alignment_result_presentation import alignment_report_presentation
from .infernal_result_presentation import infernal_receiver_context
from .rna_structure_comparison_presentation import (
    render_rna_comparison_lookup, render_rna_comparison_own_outcome,
    render_rna_comparison_projections, select_rna_comparison_presentation,
)
from .rna_structure_presentation import (
    render_rna_structure_groups, render_rna_structure_lookup,
    render_rna_structure_own_outcome, render_rna_structure_own_progress,
    select_rna_structure_presentation,
)
from .schema_information_text import render_schema_information, schema_fingerprint


INSTRUCTION_STATUS = "published_investigation_instructions"


def is_published_scientific_context(context):
    process = context.get("scientific_process") if isinstance(context, Mapping) else None
    axis = process.get("evidence_axis") if isinstance(process, Mapping) else None
    return isinstance(axis, Mapping) and axis.get("instruction_status") == INSTRUCTION_STATUS


def has_molecular_receiver_context(context):
    """Recognize registered capabilities and exact interval return channels.

    Empty initial values need no synthetic received group or native deployment.
    Molecular capabilities require their exact supplied declarations. Interval
    returns additionally use their existing closed Projection validators in
    declared outcome/report slots; arbitrary input records remain opaque.
    """
    if not isinstance(context, Mapping):
        return False
    sources = context.get("available_report_facts", {})
    sources = sources if isinstance(sources, Mapping) else {}
    from .molecular_result_facts import molecular_fact_sources
    for name, registered in molecular_fact_sources().items():
        supplied = sources.get(name)
        if not isinstance(supplied, Mapping):
            continue
        try:
            if schema_fingerprint(supplied) == schema_fingerprint(registered):
                return True
        except (ValueError, TypeError, KeyError, RecursionError):
            continue
    from .genomic_overlap_return_views import genomic_overlap_fact_sources
    from .chromatin_interaction_return_views import chromatin_fact_sources
    from .atac_differential_return_views import atac_fact_sources
    from .expression_nmf_return_views import expression_nmf_fact_sources
    for registered_sources in (genomic_overlap_fact_sources(), chromatin_fact_sources(),
            atac_fact_sources(), expression_nmf_fact_sources()):
        for name, registered in registered_sources.items():
            supplied = sources.get(name)
            if not isinstance(supplied, Mapping):
                continue
            try:
                if schema_fingerprint(supplied) == schema_fingerprint(registered):
                    return True
            except (ValueError, TypeError, KeyError, RecursionError):
                continue
    from .genomic_overlap_presentation import select_genomic_overlap_presentation
    from .chromatin_interaction_presentation import select_chromatin_presentation
    from .atac_differential_presentation import select_atac_presentation
    from .expression_nmf_presentation import select_expression_nmf_presentation
    from .native_profile_presentation import has_native_profile_receiver_context
    return bool(select_genomic_overlap_presentation(context)['projections']
        or select_chromatin_presentation(context)['projections']
        or select_atac_presentation(context)['projections']
        or select_expression_nmf_presentation(context)['projections']
        or has_native_profile_receiver_context(context))


def text_instructions(instructions):
    """Replace only the existing exchange protocol's JSON-reading directions."""
    return instructions.replace(INSTRUCTIONS, TEXT_INSTRUCTIONS).replace(
        "After its decision_lookup_result arrives", "After the requested information arrives")


def _scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _cell(value):
    return _scalar(value).replace("|", "\\|").replace("\n", "<br>")


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "None supplied."
    return "\n".join(["| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)])


def _rows(value, path=""):
    """Exact finite values, with paths retaining arbitrary caller field names."""
    if isinstance(value, Mapping):
        if not value:
            yield path or "value", "empty object"
        for name, child in value.items():
            yield from _rows(child, f"{path}.{name}" if path else name)
    elif isinstance(value, (list, tuple)):
        if not value:
            yield path or "value", "empty array"
        for index, child in enumerate(value):
            yield from _rows(child, f"{path}[{index}]")
    else:
        yield path or "value", _scalar(value)


def _selected_molecular_packet(value):
    """Recognize only a complete registered selected-value packet."""
    if isinstance(value, Mapping) and value.get("version") == "ordinary_somatic_variant_values_v1":
        from .somatic_variant_contracts import validate_somatic_return
        from .communication import plain
        try:
            return validate_somatic_return(plain(value))
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "esm_gene_embedding_values_v1":
        from .esm_gene_embedding_contracts import validate_esm_embedding_return
        from .communication import plain
        try:
            return validate_esm_embedding_return(plain(value))
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_protein_phylogeny_values_v1":
        from .protein_phylogeny_result_views import select_protein_phylogeny_values
        return select_protein_phylogeny_values(value)
    if isinstance(value, Mapping) and value.get("version") == "ordinary_protein_conservation_values_v1":
        from .protein_conservation_result_views import select_protein_conservation_values
        return select_protein_conservation_values(value)
    if isinstance(value, Mapping) and value.get("version") == "ordinary_primer_placement_values_v1":
        from .primer_placement_result_contracts import validate_ordinary_primer_placement_return
        try:
            return validate_ordinary_primer_placement_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_protein_disorder_values_v1":
        from .protein_disorder_result_contracts import validate_ordinary_disorder_return
        try:
            return validate_ordinary_disorder_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_arsenic_speciation_values_v1":
        from .arsenic_speciation_result_contracts import validate_ordinary_arsenic_return
        try:
            return validate_ordinary_arsenic_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "vcf_result_return_v1":
        from .vcf_result_measurements import validate_vcf_return
        try:
            return validate_vcf_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") in (
            "ordinary_itc_values_v1", "ordinary_itc_partial_values_v1", "itc_parameter_return_v1"):
        from .itc_binding_presentation import select_itc_binding_result
        return select_itc_binding_result(value)
    if isinstance(value, Mapping) and value.get("version") == "ordinary_o_glycosylation_values_v1":
        from .molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
        try:
            return validate_ordinary_molecular_sequence_return(value,
                operation="predict_o_glycosylation_hotspots")
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_n_glycosylation_values_v1":
        from .molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
        try:
            return validate_ordinary_molecular_sequence_return(value,
                operation="find_n_glycosylation_motifs")
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "tf_binding_return_v1":
        from .tf_binding_result_contracts import validate_tf_binding_return
        try:
            return validate_tf_binding_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_protease_kinetics_values_v1":
        from .protease_kinetics_result_contracts import validate_ordinary_protease_kinetics_return
        try:
            return validate_ordinary_protease_kinetics_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "homer_motif_return_v1":
        from .homer_motif_result_contracts import validate_homer_motif_return
        try:
            return validate_homer_motif_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_macs2_peak_result_v1":
        from .macs2_peak_result_contracts import validate_macs2_peak_return
        try:
            return validate_macs2_peak_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if not isinstance(value, Mapping) or value.get("version") != "ordinary_orf_values_v1":
        return None
    from .molecular_sequence_result_contracts import validate_ordinary_orf_return
    try:
        # This delegates to the common selected-value validator. It performs
        # no custody lookup, File read, native work or scientific calculation.
        return validate_ordinary_orf_return(value)
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        return None


def _molecular_literal(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _molecular_provenance_role(reference, packet):
    if packet.get("version") == "ordinary_arsenic_speciation_values_v1":
        return "unavailable" if reference is None else "retained provenance"
    values = packet["values"]
    if reference is None:
        return "unavailable"
    for role in ("components", "sheet"):
        if reference == values["source_" + role + "_ref"]:
            return role
    return "retained provenance"


def _molecular_stored_view(cell, packet):
    """Replace only a declared provenance address, never a scientific value."""
    result = {key: deepcopy(value) for key, value in cell.items() if key not in ("source_ref", "unit_sources")}
    result["source_role"] = _molecular_provenance_role(cell["source_ref"], packet)
    if "unit_sources" in cell:
        result["unit_sources"] = [_molecular_stored_view(value, packet) for value in cell["unit_sources"]]
    return result


def _molecular_failure_view(issue, packet):
    result = {key: deepcopy(value) for key, value in issue.items() if key != "source_ref"}
    if issue.get("source_ref") is not None:
        result["source_role"] = issue.get("role") or _molecular_provenance_role(issue["source_ref"], packet)
    if (packet.get("version") in {"ordinary_protease_kinetics_values_v1", "ordinary_arsenic_speciation_values_v1",
            "ordinary_primer_placement_values_v1"}
            and result.get("diagnostic_ref") is not None):
        result.pop("diagnostic_ref")
        result["diagnostic_role"] = "retained diagnostic association"
    return result


def _protease_context_text(packet):
    """Present retained global qualifications, including an empty row selection."""
    def members(value, path=""):
        if isinstance(value, Mapping) and value:
            for key, child in value.items():
                yield from members(child, path + "." + key if path else key)
        elif isinstance(value, (list, tuple)) and value:
            for index, child in enumerate(value):
                yield from members(child, path + "[" + str(index) + "]")
        else:
            yield path, value

    def cells(value, path=""):
        if "value_state" in value:
            yield path, value
        else:
            for key, child in value.items():
                if key != "schema":
                    yield from cells(child, path + "." + key if path else key)

    rows = []
    for field, cell in cells(packet["values"]["context"]):
        values = members(cell["value"]) if field in ("assay", "population") else (("", cell["value"]),)
        for member, literal in values:
            name = field + ("." + member if member else "")
            rows.append((name, _molecular_literal(literal), cell["value_state"],
                _molecular_provenance_role(cell["source_ref"], packet), cell["source_state"], cell["source_pointer"]))
    return "\n\n".join(["Retained protease assay and qualification context",
        _table(("Retained field/member", "Literal value", "Value state", "Source role", "Source state", "Source pointer"), rows)])


def _homer_motif_text(packet, number):
    """Show fixed HOMER measurements without reopening or calculating data."""
    series_labels = {series['series_id']: 'Series ' + str(index)
        for index, series in enumerate(packet['available_series'], 1)}
    parts = ['Selected molecular result ' + str(number), '',
        _table(('Callable operand', 'Retained value'), [
            ('Result Source', packet['source_ref']),
            ('Selected series in caller order', _molecular_literal([
                series_labels[series_id] for series_id in packet['selector']['series_ids']])),
            ('Selection offset', packet['selector']['offset']),
            ('Selection limit', packet['selector']['limit'])]), '',
        'Retained series available for saved selection', '',
        _table(('Series', 'Callable series ID', 'Role', 'Requested motif length (bp)',
            'Capture state', 'Native outcome'), [
            (series_labels[series['series_id']], series['series_id'], series['role'],
                series['requested_motif_length_bp'], series['capture_state'], series['native_outcome'])
            for series in packet['available_series']]), '',
        'Recorded execution', '', _table(('Field', 'Retained value'), packet['execution'].items()), '',
        'Captured input population facts', '',
        _table(('Field', 'Retained value'), _rows(packet['population_facts'])), '',
        'Sums of reported input weights', '',
        _table(('Group', 'Value', 'State', 'Unit', 'Origin', 'Method', 'Numerator',
            'Denominator', 'Uncertainty', 'Qualifications'), [
            (summary['group'], summary['cell']['value'], summary['cell']['state'],
                summary['cell']['unit'], summary['cell']['origin'], summary['cell']['method_id'],
                summary['cell']['numerator'], summary['cell']['denominator'],
                _molecular_literal(summary['cell']['uncertainty']),
                _molecular_literal(summary['issues']))
            for summary in packet['reported_input_weight_sums']]), '',
        'These sums use reported input weights. Effective native motif denominators remain separate.', '',
        _table(('Series', 'Role', 'Captured occurrences', 'Selected occurrences',
            'Capture state', 'Native outcome'), [
            (series_labels[count['series_id']], count['role'], count['captured_occurrences'],
                count['selected_occurrences'], count['capture_state'], count['native_outcome'])
            for count in packet['counts']])]
    for series in packet['selected_series']:
        parts.extend(['', series_labels[series['series_id']] + ': ' + series['role'], '',
            _table(('Series property', 'Retained value'), [
                ('Phase', series['phase']), ('Capture state', series['capture_state']),
                ('Native outcome', series['native_outcome']),
                ('Original column headings', _molecular_literal(series['raw_header'])),
                ('Qualifications', _molecular_literal(series['issues']))]), '',
            'Wrapper display totals inferred from the first rounded motif', '',
            _table(('Group', 'Native token', 'Value', 'State'), [
                (group, None if series['displayed_totals'][group] is None else
                    series['displayed_totals'][group]['raw_token'],
                    None if series['displayed_totals'][group] is None else
                    series['displayed_totals'][group]['value'],
                    'not_provided' if series['displayed_totals'][group] is None else
                    series['displayed_totals'][group]['state'])
                for group in ('target', 'background')])])
        for occurrence in series['observations']:
            parts.extend(['', 'Original motif occurrence ' + str(occurrence['ordinal_0based']), '',
                _table(('Property', 'Retained value'), [
                    ('Name', occurrence['name']), ('Consensus', occurrence['consensus']),
                    ('Parse state', occurrence['parse_state']), ('PWM state', occurrence['pwm_state']),
                    ('Qualifications', _molecular_literal(occurrence['issues']))])])
            if occurrence['parse_state'] in ('malformed', 'truncated'):
                parts.extend(['', 'Original fields: ' + _molecular_literal(occurrence['raw_fields'])])
            for representation in occurrence['representations']:
                parts.extend(['', 'Native representation: ' + representation['kind'], '',
                    _table(('Measurement', 'Availability', 'Native token', 'Value', 'State', 'Token kind', 'Unit',
                        'Print precision'), [
                        (field, cell['availability'],
                            None if cell['number'] is None else cell['number']['raw_token'],
                            None if cell['number'] is None else cell['number']['value'],
                            'not_provided' if cell['number'] is None else cell['number']['state'],
                            'not_provided' if cell['number'] is None else cell['number']['token_kind'],
                            cell['unit'], cell['precision'])
                        for field, cell in representation['numbers'].items()]), '',
                    _table(('Representation property', 'Retained value'), [
                        ('Native gap field', representation['native_gap_field']),
                        ('Additional native fields', _molecular_literal(representation['extra_fields'])),
                        ('Unreported auxiliary fields', _molecular_literal(
                            representation['native_auxiliary_absent_fields'])),
                        ('Qualifications', _molecular_literal(representation['issues']))])])
                if representation['pwm_rows']:
                    parts.extend(['', 'Ordered PWM rows; native column order A, C, G, T', '',
                        _table(('Original row', 'Native tokens in original order', 'Cell states'), [
                            (row['ordinal_0based'], _molecular_literal(row['raw_fields']),
                                _molecular_literal([cell['state'] for cell in row['cells']]))
                            for row in representation['pwm_rows']])])
                for auxiliary in representation['native_auxiliary_measurements']:
                    number_cell = auxiliary['reported']
                    parts.extend(['', 'Native auxiliary measurement: ' + auxiliary['field'], '',
                        _table(('Property', 'Retained value'), [
                            ('Original field', auxiliary['raw_field']),
                            ('Extra field ordinal', auxiliary['extra_field_ordinal_0based']),
                            ('Token ordinal', auxiliary['token_ordinal_0based']),
                            ('Native token', number_cell['number']['raw_token']),
                            ('Value', number_cell['number']['value']),
                            ('State', number_cell['number']['state']),
                            ('Unit', number_cell['unit']), ('Print precision', number_cell['precision']),
                            *((field, _molecular_literal(auxiliary[field]) if field == 'qualifications'
                                else auxiliary[field]) for field in ('definition', 'population',
                                    'coordinate_origin', 'weighting', 'denominator', 'qualifications'))])])
    parts.extend(['', 'Result qualifications: ' + _molecular_literal(packet['issues'])])
    return '\n'.join(parts)


def _tf_binding_text(packet, number):
    """Display literal TF values without reading Files or calculating scores."""
    sequences = {row['sequence_id']: row for row in packet['sequences']}
    matrices = {row['matrix_occurrence_id']: row for row in packet['matrices']}
    models = {row['model_id']: row for row in packet['matrices']}
    parts = ['Selected molecular result ' + str(number), '',
        _table(('Callable operand', 'Retained value'), [
            ('Result Source', packet['source_ref']), ('Result state', packet['status']),
            ('Raw log2-odds threshold', packet['selection']['raw_threshold']),
            ('Selection offset', packet['selection']['offset']),
            ('Selection limit', packet['selection']['limit'])]), '',
        'Selected scans in caller order', '',
        _table(('Callable scan ID',), ((scan,) for scan in packet['selection']['scan_ids'])), '',
        'Declared input parameters before native normalization', '',
        _table(('Base', 'Declared background', 'Declared pseudocount'), [
            (base, packet['parameters']['background'][base], packet['parameters']['pseudocounts'][base])
            for base in 'ACGT']), '',
        'Recorded execution and numerical convention', '',
        _table(('Field', 'Retained value'), [*packet['execution'].items(),
            *((name, packet['numeric_authority'][name]) for name in ('biopython_version',
                'numpy_version', 'threshold_operand', 'comparison', 'relative', 'relative_bounds'))]), '',
        'Supplied input capture states', '',
        _table(('Input', 'Role', 'Format', 'Capture state', 'Capture end (exclusive)', 'Original bytes'), [
            (row['input_id'], row['role'], row['format'], row['capture']['state'],
                row['capture']['byte_end_0based_exclusive'], row['capture']['original_size_bytes'])
            for row in packet['inputs']]), '',
        'Original sequence occurrences', '',
        _table(('Input', 'Original record ordinal', 'Identifier', 'Length', 'State'), [
            (row['input_id'], row['record_ordinal_0based'], row['identifier'], row['length'], row['state'])
            for row in packet['sequences']]), '',
        'Original matrix occurrences', '',
        _table(('Input', 'Original record ordinal', 'Native matrix ID', 'Name', 'Length', 'State'), [
            (row['input_id'], row['record_ordinal_0based'], row['native_matrix_id'], row['name'],
                row['length'], row['state']) for row in packet['matrices']]), '',
        'Retained scans available for saved selection', '',
        _table(('Callable scan ID', 'Sequence input', 'Sequence record', 'Matrix input', 'Matrix record',
            'Strand', 'Possible positions', 'Coverage', 'Declared count', 'Captured complete elements',
            'Usable elements', 'Trailing bytes', 'Excess elements'), [
            (row['scan_id'], sequences[row['sequence_id']]['input_id'],
                sequences[row['sequence_id']]['record_ordinal_0based'],
                matrices[row['matrix_occurrence_id']]['input_id'],
                matrices[row['matrix_occurrence_id']]['record_ordinal_0based'], row['strand'],
                row['possible_positions'], row['coverage']['state'], row['coverage']['declared_count'],
                row['coverage']['captured_complete_elements'], row['coverage']['usable_elements'],
                row['coverage']['trailing_bytes'], row['coverage']['excess_elements'])
            for row in packet['available_scans']]), '',
        'Retained counts for the selected scans', '',
        _table(('Quantity', 'Literal value', 'State', 'Unit', 'Origin', 'Numerator', 'Denominator', 'Uncertainty'), [
            (name.replace('_', ' '), cell['value'], cell['state'], cell['unit'], cell['origin'],
                cell['numerator'], cell['denominator'], _molecular_literal(cell['uncertainty']))
            for name, cell in packet['totals'].items()]), '',
        'Returned raw-threshold rows; coordinates are zero-based forward-sequence intervals', '',
        _table(('Callable scan ID', 'Sequence record', 'Matrix record', 'Strand', 'Start', 'End (exclusive)',
            'Forward sequence', 'Motif-oriented sequence', 'Raw score (bits)', 'Raw score class',
            'Relative score', 'Relative class', 'Relative state', 'Relative reason', 'Model normalization eligible'), [
            (row['scan_id'], row['sequence_record_ordinal_0based'], row['matrix_record_ordinal_0based'],
                row['strand'], row['start_0based'], row['end_0based_exclusive'], row['forward_sequence'],
                row['motif_oriented_sequence'], row['score']['value'], row['score']['classification'],
                row['relative_score']['value'], row['relative_score']['classification'],
                row['relative_score']['state'], row['relative_score']['reason_code'],
                row['model_normalization_eligible']) for row in packet['raw_threshold_matches']])]
    for row in packet['relative_normalizations']:
        matrix = models[row['model_id']]
        parts.extend(['', 'Retained relative normalization', '',
            _table(('Property', 'Retained value'), [
                ('Matrix input', matrix['input_id']), ('Original matrix record', matrix['record_ordinal_0based']),
                *((name, row[name]) for name in
                    ('bounds_strand', 'operand_dtype', 'scientific_state', 'reason_code'))]), '',
            _table(('Operand', 'Literal value', 'Class', 'State', 'Unit'), [
                (name, row[name]['value'], row[name]['classification'], row[name]['state'], row[name]['unit'])
                for name in ('minimum', 'maximum', 'span')])])
    parts.extend(['', 'Result qualifications', '',
        _table(('Code', 'Phase', 'Input/record pointer', 'Severity'), [
            (row['code'], row['phase'], row['path'], row['severity']) for row in packet['issues']])])
    return '\n'.join(parts)


def _n_glycosylation_text(packet, number):
    return _glycosylation_text(packet, number)


def _glycosylation_text(packet, number):
    """Render retained glyco cells and qualifications without reading or calculating."""
    values, context = packet["values"], packet["values"]["context"]
    o_density = values["operation"] == "predict_o_glycosylation_hotspots"
    input_cell = context["input"]["input_ref"]
    associations = [input_cell["value"]] if input_cell["value_state"] == "stored_value" else []

    def subject_label(reference):
        if reference not in associations:
            associations.append(reference)
        return "Input association" if reference == input_cell["value"] else "Mapped subject " + str(associations.index(reference) + 1)

    def literal(value):
        if isinstance(value, (dict, list)):
            return "; ".join(name + "=" + shown for name, shown in _rows(value))
        return _scalar(value)

    selected, qualifications = [], []
    for row in values["rows"]:
        value = row["value"]
        if row["field"].endswith("source_intervals") and isinstance(value, list):
            shown = "; ".join(subject_label(segment["subject_ref"]) + " [" + str(segment["start"])
                + "," + str(segment["end"]) + ") " + segment["unit"] + " " + segment["strand"]
                for segment in value) if value else "empty array"
        else:
            shown = literal(value)
        selected_row = (literal(row["row_id"]), row["field"], shown, row["value_state"],
            row["unit"], row["population_id"], _molecular_provenance_role(row["source_ref"], packet), row["source_pointer"])
        if o_density:
            operands = literal([_molecular_stored_view(cell, packet) for cell in row["denominators"]])
            selected_row = (*selected_row[:6], operands, *selected_row[6:])
        selected.append(selected_row)
        for name, cell in row["scientific_qualifiers"]["states"].items():
            qualification = (literal(row["row_id"]), name, literal(cell["value"]), cell["value_state"])
            if qualification not in qualifications:
                qualifications.append(qualification)

    retained = [("component_status", context["component_status"])]
    for group in ("parameters", "input", "mapping"):
        retained.extend((group + "." + name, cell) for name, cell in context[group].items())
    retained.append(("completeness", context["completeness"]))
    facts = []
    for name, cell in retained:
        shown = ("supplied input association" if cell["value_state"] == "stored_value" else "null") if name == "input.input_ref" else literal(cell["value"])
        facts.append((name, shown, cell["value_state"], _molecular_provenance_role(cell["source_ref"], packet), cell["source_pointer"]))

    columns = ("Row identity", "Field", "Literal value", "Value state", "Unit", "Population", "Source role", "Source pointer")
    if o_density:
        columns = (*columns[:6], "Denominator operands", *columns[6:])
    interpretation = ("Interpretation: S/T density in reported windows under the selected heuristic. Candidate hotspots do not establish measured glycosylation, occupancy, calibrated probability or protein function."
        if o_density else "Interpretation: literal N-X-S/T motifs with X different from P. Occupancy and experimental glycosylation are unestablished.")
    parts = ["Selected molecular result " + str(number), "", interpretation, "",
        _table(("Result property", "Supplied value"), [("Callable result Source", packet["source_ref"]),
            ("Operation", values["operation"]), ("Values origin", values["source_kind"]),
            ("Original attempt association", values["original_attempt_association"])]), "",
        _table(("Retained file role", "State"), packet["file_states"].items()), "",
        _table(columns, selected), "",
        _table(("Retained property", "Literal value", "Value state", "Source role", "Source pointer"), facts), "",
        _table(("Row identity", "Original qualifier", "Literal value", "Value state"), qualifications)]

    metadata = context["native"]["metadata_occurrences"]
    native_rows = []
    if metadata["value_state"] == "stored_value":
        native_rows = [(item["kind"], literal(item["values"]), item["line_number"], item["native_line"])
            for item in metadata["value"]]
    parts.extend(["", "Original native header occurrences (order and duplicates retained)", "",
        _table(("Kind", "Literal reported values", "Log line", "Original native line"), native_rows)
            if metadata["value_state"] == "stored_value" else metadata["value_state"], "",
        "Selected native headers", "",
        _table(("Literal value", "Value state"), [(literal(context["native"]["selected_metadata"]["value"]),
            context["native"]["selected_metadata"]["value_state"])])])

    issue_rows = []
    if context["row_issues"] is None:
        issue_rows.append(("retained row issues", "unavailable", "null"))
    issue_groups = [("components", context["component_issues"]),
        *([] if context["row_issues"] is None else [("retained row " + str(row["row_ordinal"]), row["issues"])
            for row in context["row_issues"]])]
    for group, cell in issue_groups:
        if cell["value_state"] != "stored_value":
            issue_rows.append((group, cell["value_state"], "null"))
        else:
            issue_rows.extend((group, cell["value_state"], literal(issue)) for issue in cell["value"])
    parts.extend(["", "Original component and row issues", "",
        _table(("Population", "Value state", "Original issue"), issue_rows) if issue_rows else "Known empty issue arrays."])
    for title, failures in (("Result failures", packet["failures"]), ("Selected-value failures", values["failures"])):
        rendered_failures = []
        for issue in failures:
            shown = _molecular_failure_view(issue, packet)
            if shown.get("diagnostic_ref") is not None:
                shown.pop("diagnostic_ref")
                shown["diagnostic_role"] = "retained diagnostic association"
            rendered_failures.append((literal(shown),))
        parts.extend(["", title, "", _table(("Original failure",),
            rendered_failures) if failures else "[]"])
    return "\n".join(parts)


def _vcf_result_text(packet, number):
    """Render retained VCF values; do not parse bytes or calculate populations."""
    value = packet["value"]
    population, header = value["population"], value["header"]
    def token(item):
        return None if item is None else "[undecodable bytes]" if item["raw_token"] is None else item["raw_token"]
    selection = value["selection"]
    parts = ["Selected molecular result " + str(number), "",
        _table(("Result property", "Retained value"), [
            ("Callable result Source", packet["source_ref"]),
            ("Declared VCF version", header["fileformat"]), ("Decoder", header["decoder"]),
            ("Header state", header["state"]), ("Capture state", population["capture_state"]),
            ("Captured byte extent (exclusive)", value["input"]["capture"]["byte_end_0based_exclusive"]),
            ("Original size if supplied", value["input"]["capture"]["original_size_bytes"]),
            ("Record population complete", population["record_population_complete"])]), "",
        "Selected original ordinals and native field keys; null selects all, [] selects none", "",
        _table(("Selection", "Supplied value"), [(key, _molecular_literal(selection[key])) for key in
            ("record_ordinals", "sample_ordinals", "info_keys", "format_keys", "offset", "limit")]), "",
        "Retained populations; record slots, ALT tokens and sample cells have separate units", "",
        _table(("Population", "Literal count or state"), [(key, population[key]) for key in
            ("total_original_record_slots", "retained_record_slots", "selected_record_slots", "returned_record_slots",
             "omitted_by_window_record_slots", "selected_alt_tokens", "returned_alt_tokens", "selected_sample_cells",
             "returned_sample_cells", "selected_observed_sample_cells", "returned_observed_sample_cells",
             "selected_genotype_slots", "returned_genotype_slots", "has_more")]), "",
        _table(("Returned record fraction", "Numerator", "Denominator", "Unit", "Missing reason"), [
            tuple(population["returned_record_fraction"][key] for key in
                ("value", "numerator", "denominator", "unit", "missing_reason"))]), "",
        "Original sample columns", "",
        _table(("Sample ordinal", "Column ordinal", "Native name"), [
            (row["sample_ordinal_0based"], row["column_ordinal_0based"], token(row["name"])) for row in header["samples"]]), "",
        "Native field definitions; units and meanings remain as declared, otherwise unknown", "",
        _table(("Definition ordinal", "Namespace", "ID", "Number", "Type", "Description", "State"), [
            tuple(row[key] for key in ("definition_ordinal_0based", "namespace", "id", "number", "type", "description", "state"))
            for row in header["definitions"]]), "",
        "Returned original records; native POS retains VCF coordinates and any telomeric sentinel", "",
        _table(("Record ordinal", "Physical line", "State", "CHROM", "POS", "ID", "REF", "ALT", "QUAL (phred)", "FILTER", "Filter state"), [
            (row["record_ordinal_0based"], row["locator"]["line_start_1based"], row["state"], row["chrom"],
             row["pos_1based"], token(row["fixed"]["id"]), row["ref"], token(row["fixed"]["alt"]),
             token(row["fixed"]["qual"]), token(row["filter"]["token"]), row["filter"]["state"])
            for row in value["records"]])]
    fields, elements, genotypes, qualifiers = [], [], [], []
    def field_rows(record, sample, namespace, field):
        identity = (record, sample, namespace, field["field_ordinal_0based"], field["key"])
        card = field["cardinality"]
        fields.append((*identity, field["declared_type"], field["declared_number"], field["state"],
            token(field["value_token"]), field["flag"], card["observed"], card["expected"], card["state"],
            card["ploidy"], card["ploidy_basis"]))
        for element in field["values"]:
            elements.append((*identity, element["value_ordinal_0based"], token(element["token"]),
                element["decoded"]["kind"], element["decoded"]["value"], element["allele_index"],
                element["genotype_index_0based"], _molecular_literal(element["genotype_allele_indices"])))
        qualifiers.extend((record, sample, field["key"], issue["code"], issue["severity"])
            for issue in field["issues"])
    for record in value["records"]:
        ordinal = record["record_ordinal_0based"]
        for field in record["info"]:
            field_rows(ordinal, None, "INFO", field)
        for sample in record["samples"]:
            sample_ordinal = sample["sample_ordinal_0based"]
            for field in sample["fields"]:
                field_rows(ordinal, sample_ordinal, "FORMAT", field)
            genotype = sample["genotype"]
            if genotype is not None:
                for allele in genotype["alleles"]:
                    genotypes.append((ordinal, sample_ordinal, token(genotype["token"]), genotype["state"],
                        genotype["ploidy"], allele["allele_ordinal_0based"], token(allele["token"]),
                        allele["allele_index"], allele["state"]))
        qualifiers.extend((ordinal, None, None, issue["code"], issue["severity"]) for issue in record["issues"])
    parts.extend(["", "Selected native fields and declared cardinalities", "",
        _table(("Record", "Sample", "Namespace", "Field ordinal", "Key", "Type", "Number", "State", "Native value",
            "Flag", "Observed elements", "Expected elements", "Cardinality state", "GT slot count", "Ploidy basis"), fields), "",
        "Retained value elements and native allele/genotype associations", "",
        _table(("Record", "Sample", "Namespace", "Field ordinal", "Key", "Value ordinal", "Native token", "Decoded kind",
            "Decoded value", "Allele index", "Genotype index", "Genotype allele indices"), elements), "",
        "Literal GT slots; slot count is retained genotype syntax", "",
        _table(("Record", "Sample", "Native GT", "State", "GT slot count", "Slot ordinal", "Native allele", "Allele index", "Allele state"), genotypes), "",
        "Record and field qualifications", "",
        _table(("Record", "Sample", "Field", "Code", "Severity"), qualifiers), "",
        "Input and header qualifications", "",
        _table(("Code", "Path", "Severity"), [(issue["code"], issue["path"], issue["severity"])
            for issue in [*value["issues"], *header["issues"]]])])
    return "\n".join(parts)


def _arsenic_speciation_text(packet, number):
    """Present every retained selected field without recalculating quantities."""
    shown = {key: deepcopy(value) for key, value in packet.items()
        if key not in {"source_ref", "version"}}
    shown["failures"] = [_molecular_failure_view(issue, packet) for issue in packet["failures"]]
    return "\n\n".join(["Selected molecular result " + str(number),
        _table(("Result property", "Supplied value"), [
            ("Callable result Source", packet["source_ref"]),
            ("Operation", "analyze_arsenic_speciation_hplc_icpms")]),
        _table(("Retained field/member", "Literal value"), _rows(shown))])


def _protein_disorder_text(packet, number):
    """Display stored disorder cells and context; qualify declared addresses only."""
    values = deepcopy(packet["values"])
    context = values["context"]
    subjects = []

    def subject(reference):
        if not _execution_opaque_reference(reference):
            return reference
        if reference not in subjects:
            subjects.append(reference)
        return "Supplied mapping subject " + str(subjects.index(reference) + 1)

    def spans(value):
        if not isinstance(value, list):
            return value
        return [{**row, "subject_ref": subject(row["subject_ref"])}
            if isinstance(row, Mapping) and set(row) == {"subject_ref", "start", "end", "unit", "strand"}
            else row for row in value]

    def mapping(value):
        if (not isinstance(value, Mapping) or set(value) != {"version", "units_per_symbol", "symbol_length", "path"}
                or value["version"] != "oriented_source_subject_path_v2"):
            return value
        return {**value, "path": spans(value["path"])}

    # These fields are declared provenance slots. An opaque caller value in a
    # different field, including a malformed supplied mapping, stays literal.
    reference = context["input"]["input_ref"]
    if _execution_opaque_reference(reference):
        context["input"]["input_ref"] = "Retained input provenance"
    context["input"]["input_mapping"] = mapping(context["input"]["input_mapping"])
    context["mapping"]["supplied"] = mapping(context["mapping"]["supplied"])
    context["source_profile"] = {key: value for key, value in context["source_profile"].items()
        if key not in {"module_sha256", "callable_sha256"}}
    values["data_identity"] = {key: value for key, value in values["data_identity"].items()
        if key not in {"sheet_canonical_sha256", "components_canonical_sha256"}}
    for row in values["rows"]:
        if row["field"] == "source_intervals":
            row["value"] = spans(row["value"])
        qualifiers = row["scientific_qualifiers"]
        if qualifiers.get("kind") == "residue" and qualifiers.get("value") is not None:
            cells = qualifiers["value"]["cells"]
            cells["source_intervals"] = spans(cells["source_intervals"])
    return "\n\n".join(["Selected molecular result " + str(number),
        _table(("Result property", "Supplied value"), [
            ("Callable result Source", packet["source_ref"]),
            ("Operation", "predict_protein_disorder_regions")]),
        _table(("Retained field/member", "Literal value"),
            _rows({"selection": packet["selection"]["rows"], "values": values}))])


def _primer_placement_context_text(packet):
    """Show retained operand and population metadata without projecting new hits."""
    context = packet["context"]

    def sequence(value):
        if isinstance(value, str) and len(value) > 120:
            return str(len(value)) + " symbols retained in the result context"
        return _molecular_literal(value)

    inputs, operand_rows = context["input"], []
    if inputs is not None:
        operand_rows.append(("target_sequence", sequence(inputs["target_sequence"])))
        primers = inputs["primers"]
        operand_rows.append(("primer input form", "ordered list" if isinstance(primers, list) else "scalar"))
        if isinstance(primers, list):
            operand_rows.extend(("primers[" + str(index) + "]", sequence(value)) for index, value in enumerate(primers))
            if not primers:
                operand_rows.append(("primers", "[]"))
        else:
            operand_rows.append(("primers", sequence(primers)))
        operand_rows.extend((name, _molecular_literal(inputs[name])) for name in
            ("target_ref", "primer_refs", "target_mapping", "primer_mappings"))
    metadata = [(name, _molecular_literal(context[name])) for name in
        ("sheet_state", "components_state", "native_outcome", "component_status", "source_assumptions")]
    for name in ("population", "group_populations", "definitions", "issues"):
        metadata.extend(_rows(context[name], name))
    return "\n\n".join(["Retained primer-placement operands and populations",
        _table(("Original operand property", "Supplied value"), operand_rows) if inputs is not None else "Original operands unavailable.",
        _table(("Retained property", "Supplied value"), metadata)])


def _somatic_variant_text(packet, number):
    """Copy selected native fields and qualifications; omit declared custody slots."""
    context = packet["context"]
    shown = {
        "inputs": [{"role": row["role"],
            "file_metadata": {key: row["file"][key] for key in ("format", "size_bytes")},
            "source_association": "retained supplied-input provenance" if row["source_ref"] is not None else None}
            for row in context["inputs"]],
        "sample_ids": context["sample_ids"], "reference_id": context["reference_id"],
        "software": {key: context["software"][key] for key in ("reported_versions", "loaded_dependencies_verified")},
        "annotation_database": {key: context["annotation_database"][key] for key in ("id", "reference_association")},
        "parameters": context["parameters"], "stages": context["stages"],
        "outputs": [{key: row[key] for key in ("role", "size_bytes")} for row in context["outputs"]],
        "issues": context["issues"], "definitions": context["definitions"],
    }
    return "\n\n".join([
        _vcf_result_text({"source_ref": packet["source_ref"], "value": packet["value"]}, number),
        "Recorded somatic native context; process completion is separate from biological truth",
        _table(("Selected native stage", "Retained value"), [("Stage", packet["selection"]["stage"])]),
        _table(("Context field", "Literal value"), _rows(shown))])


def _esm_gene_embedding_text(packet, number):
    """Display literal selected representations without private custody slots."""
    context = deepcopy(packet["context"])
    # These are declared provenance slots, not fields in opaque scientific
    # headers, symbols or caller-supplied protein/isoform/gene identifiers.
    context.pop("selected_checkpoint_sha256")
    context.pop("selected_regression_checkpoint_sha256")
    original_file = context.pop("input_file")
    context["input_file_metadata"] = {key: original_file[key] for key in ("format", "size_bytes")}
    context["input_source_ref"] = ("Retained supplied-input provenance"
        if context["input_source_ref"] is not None else None)
    return "\n\n".join(["Selected molecular result " + str(number),
        _table(("Result property", "Supplied value"), [
            ("Callable result Source", packet["source_ref"]),
            ("Operation", "generate_gene_embeddings_with_ESM_models"),
            ("Meaning", "Literal model representations; no function-probability interpretation")]),
        _table(("Retained field/member", "Literal value"), _rows({
            "selection": packet["selection"], "context": context,
            **{name: packet[name] for name in ("residues", "proteins", "isoforms", "genes")}}))])


def _selected_molecular_text(packet, number):
    """Display exact selected cells and factor only identical complete qualifiers."""
    if packet.get("version") == "ordinary_somatic_variant_values_v1":
        return _somatic_variant_text(packet, number)
    if packet.get("version") == "esm_gene_embedding_values_v1":
        return _esm_gene_embedding_text(packet, number)
    if packet.get("version") == "ordinary_protein_phylogeny_values_v1":
        from .protein_phylogeny_result_views import render_protein_phylogeny_result
        return render_protein_phylogeny_result(packet, number)
    if packet.get("version") == "ordinary_protein_conservation_values_v1":
        from .protein_conservation_result_views import render_protein_conservation_result
        return render_protein_conservation_result(packet, number)
    if packet.get("version") == "ordinary_protein_disorder_values_v1":
        return _protein_disorder_text(packet, number)
    if packet.get("version") == "ordinary_arsenic_speciation_values_v1":
        return _arsenic_speciation_text(packet, number)
    if packet.get("version") == "vcf_result_return_v1":
        return _vcf_result_text(packet, number)
    if packet.get("version") in (
            "ordinary_itc_values_v1", "ordinary_itc_partial_values_v1", "itc_parameter_return_v1"):
        from .itc_binding_presentation import render_itc_binding_result
        return render_itc_binding_result(packet, number)
    if packet.get("version") == "ordinary_n_glycosylation_values_v1":
        return _n_glycosylation_text(packet, number)
    if packet.get("version") == "ordinary_o_glycosylation_values_v1":
        return _glycosylation_text(packet, number)
    if packet.get("version") == "tf_binding_return_v1":
        return _tf_binding_text(packet, number)
    if packet.get("version") == "homer_motif_return_v1":
        return _homer_motif_text(packet, number)
    if packet.get("version") == "ordinary_macs2_peak_result_v1":
        from .macs2_peak_presentation import render_macs2_peak_result
        return render_macs2_peak_result(packet, number)
    values, qualifiers, keys, rows = packet["values"], [], [], []
    for row in values["rows"]:
        qualification = row["scientific_qualifiers"]
        key = json.dumps(qualification, sort_keys=True, allow_nan=False)
        if key not in keys:
            keys.append(key)
            qualifiers.append(qualification)
        label = "Q" + str(keys.index(key) + 1)
        rows.append((_molecular_literal(row["row_id"]), row["field"], _molecular_literal(row["value"]),
            row["value_state"], row["unit"], row["population_id"],
            _molecular_literal([_molecular_stored_view(cell, packet) for cell in row["denominators"]]),
            _molecular_provenance_role(row["source_ref"], packet), row["source_state"], row["source_pointer"], label))
    parts = ["Selected molecular result " + str(number), "", _table(("Result property", "Supplied value"), [
        ("Callable result Source", packet["source_ref"]),
        ("Operation", values["operation"]), ("Values origin", values["source_kind"]),
        ("Selected row fields", _molecular_literal(packet["selection"])),
        ("Original attempt association", values["original_attempt_association"]),
        ("Components schema", values["components_schema"])]), "",
        _table(("Retained file role", "State"), packet["file_states"].items()), "",
        _table(("Row identity", "Field", "Literal value", "Value state", "Unit", "Population",
            "Denominator operands", "Source role", "Source state", "Source pointer", "Original component qualifiers"), rows)]
    if packet.get("version") == "ordinary_protease_kinetics_values_v1":
        parts.extend(["", _protease_context_text(packet)])
    if packet.get("version") == "ordinary_primer_placement_values_v1":
        parts.extend(["", _primer_placement_context_text(packet)])
    for index, qualification in enumerate(qualifiers, 1):
        parts.extend(["", "Original component qualifiers Q" + str(index), "",
            _table(("Property", "Supplied value"), [(key, value) for key, value in qualification.items() if key != "states"]), "",
            _table(("Retained component fact", "Literal value", "Value state", "Source role", "Source state", "Source pointer"),
                (("native_outcome (original retained components)" if name == "native_outcome" else name,
                    _molecular_literal(cell["value"]), cell["value_state"],
                    _molecular_provenance_role(cell["source_ref"], packet), cell["source_state"], cell["source_pointer"])
                    for name, cell in qualification["states"].items()))])
    failure_groups = [("Result failures", packet["failures"])]
    if values["failures"] != packet["failures"]:
        failure_groups.append(("Selected-value failures", values["failures"]))
    for title, failures in failure_groups:
        parts.extend(["", title, "", (_table(("Supplied failure",),
            ((_molecular_literal(_molecular_failure_view(issue, packet)),) for issue in failures))
            if failures else "[]")])
    return "\n".join(parts)


def _selected_molecular_view(value):
    """Detach presentation copies; equality never crosses Source/selection views."""
    packets, keys = [], []
    def project(item):
        packet = _selected_molecular_packet(item)
        if packet is not None:
            # Complete typed equality includes the Source, ordered selection,
            # cell states and qualifiers. Equal numeric values alone do not join.
            key = json.dumps(packet, sort_keys=True, allow_nan=False)
            if key not in keys:
                keys.append(key)
                packets.append(packet)
            return "Selected molecular result " + str(keys.index(key) + 1)
        if isinstance(item, Mapping):
            # Another versioned profile, including a malformed candidate, keeps
            # its complete prior rendering. It is not a generic packet wrapper.
            if "version" in item:
                return item
            shown = {key: project(child) for key, child in item.items()}
            own = _selected_molecular_packet(item.get("result"))
            if (own is not None and "source_ref" in own and item.get("status") in ("completed", "partial")
                    and isinstance(item.get("record_refs"), list) and own["source_ref"] in item["record_refs"]):
                # These are declared outcome association fields. Preserve their
                # membership with the same display label; do not scrub matching
                # strings in arbitrary caller/scientific fields or values.
                for name in ("record_refs", "changed_record_refs"):
                    if isinstance(item.get(name), list):
                        shown[name] = [shown["result"] if reference == own["source_ref"] else reference
                            for reference in item[name]]
            return shown
        if isinstance(item, (list, tuple)):
            return [project(child) for child in item]
        return item
    return project(value), packets


def _values(value):
    shown, packets = _selected_molecular_view(value)
    if not packets:
        return _table(("Field", "Supplied value"), _rows(value))
    return "\n\n".join([_table(("Field", "Supplied value"), _rows(shown)),
        *(_selected_molecular_text(packet, index) for index, packet in enumerate(packets, 1))])


def _section(parts, title, body):
    if body is not None:
        parts.extend(["", title, "", body])


def _pick(value, names):
    return {name: value[name] for name in names if name in value}


def _schema_rows(schema, path="return", presence="required"):
    """Explain actual declared fields without converting contracts to prose guesses.

    Unusual JSON-schema keywords remain explicit constraint rows; the separate
    output schema is still the authoritative response contract. No constraints
    are inferred or weakened for presentation.
    """
    if isinstance(schema, bool):
        yield path, presence, "any value" if schema else "no permitted value", ""
        return
    kind = schema.get("type", "declared value")
    if isinstance(kind, list):
        kind = " or ".join(kind)
    meaning = schema.get("description", "")
    if "x-source" in schema:
        meaning += ("; " if meaning else "") + "recorded fact from " + schema["x-source"]
    if "format" in schema:
        kind += "; " + schema["format"]
    if "x-reference-namespace" in schema:
        kind += " to " + schema["x-reference-namespace"]
    yield path, presence, kind, meaning
    special = {"type", "description", "properties", "required", "items", "anyOf", "oneOf",
        "allOf", "if", "then", "else", "not", "$defs", "definitions", "title", "$schema", "$id",
        "format", "x-source", "x-reference-namespace"}
    for name, value in schema.items():
        if name not in special:
            for field, literal in _rows(value, name):
                yield path, "constraint", field, literal
    for name, child in schema.get("properties", {}).items():
        yield from _schema_rows(child, path + "." + name,
            "required" if name in schema.get("required", ()) else "optional")
    if "items" in schema:
        yield from _schema_rows(schema["items"], path + "[]", "each item")
    for operator in ("anyOf", "oneOf", "allOf"):
        for index, branch in enumerate(schema.get(operator, ())):
            yield from _schema_rows(branch, f"{path} ({operator} {index + 1})", operator)
    for operator in ("if", "then", "else", "not"):
        if operator in schema:
            yield from _schema_rows(schema[operator], f"{path} ({operator})", operator)
    for field in ("$defs", "definitions"):
        for name, child in schema.get(field, {}).items():
            yield from _schema_rows(child, field + "/" + name, "definition")


def _schema(schema, path, *, named_definitions=False):
    if named_definitions:
        return render_schema_information(schema, title=path)
    return _table(("Field", "Presence", "Type or constraint", "Meaning or value"),
        _schema_rows(schema, path))


def _registered_return_schema_view(form, sources):
    """Project only exact supplied registered arrays whose values the host fills.

    The complete original schema remains the host contract. Unmatched schemas,
    caller-composed fields and constraints outside the registered item tree keep
    their complete presentation; source names alone never authorize projection.
    """
    shown = deepcopy(form)
    if not isinstance(shown, Mapping) or not isinstance(sources, Mapping):
        return shown
    for name, node in shown.get("properties", {}).items():
        if not isinstance(node, Mapping) or node.get("type") != "array":
            continue
        source = node.get("x-source")
        registered = sources.get(source) if isinstance(source, str) else None
        if not isinstance(registered, Mapping) or "report_schema" not in registered:
            continue
        if schema_fingerprint(node) != schema_fingerprint(registered["report_schema"]):
            continue
        shallow = {key: value for key, value in node.items() if key != "items"}
        meanings = [node.get("description", ""), "Automatically supplied recorded values.",
            registered.get("meaning", "")]
        shallow["description"] = " ".join(value for value in meanings if value)
        shown["properties"][name] = shallow
    return shown


def _operation_schema_view(schema):
    """Omit proven operation host content pins, retaining caller schema identities."""
    from .macs2_peak_presentation import macs2_peak_schema_view
    macs2 = macs2_peak_schema_view(schema)
    if macs2 is not None:
        return macs2
    prefixes = ("urn:gene-annotation:ordinary-fba-tool:", "urn:gene-annotation:ordinary-orf-tool:")
    if not isinstance(schema, Mapping):
        return schema
    prefix = next((value for value in prefixes if str(schema.get("$id", "")).startswith(value)), None)
    if prefix is None:
        return schema
    shown = {key: value for key, value in schema.items() if key != "$id"}
    if schema["$id"] != prefix + digest(shown):
        return schema
    def has_reference(value):
        if isinstance(value, Mapping):
            return bool({"$ref", "$dynamicRef", "$recursiveRef"}.intersection(value)) or any(
                has_reference(child) for child in value.values())
        return isinstance(value, (list, tuple)) and any(has_reference(child) for child in value)
    return schema if has_reference(shown) else shown


# These are host record envelope fields, not arbitrary parent context or result
# fields. Semantic references (including content-addressed artifact operands)
# remain exact when a selected read, reasoned commitment or form needs them.
_RECORD_TRACKING = frozenset({"origin", "record_type", "operation_key", "run_id",
    "episode_id", "problem_ref", "sha256", "digest", "created_at", "updated_at",
    "parse_key", "parser_version", "metadata_preview_characters", "auxiliary_artifact_refs"})


def _record(record):
    if not isinstance(record, Mapping):
        return record
    return {key: value for key, value in record.items() if key not in _RECORD_TRACKING}


def _task(state, instructions):
    process = state["scientific_process"]
    assignment = process.get("assignment", {})
    goal = state.get("goal", {})
    parts = ["TASK", "", text_instructions(instructions)]
    assigned_goal = _pick(goal, ("objective", "task_context")) if isinstance(goal, Mapping) else goal
    _section(parts, "Assigned work", _values(assigned_goal) if isinstance(goal, Mapping) else _scalar(goal))
    if isinstance(goal, Mapping) and "result_contract" in goal:
        contract, form = goal["result_contract"], state.get("requested_form")
        # An identical return contract is displayed once in Parent return form.
        # A distinct supplied goal contract retains its complete separate view.
        if form is None or schema_fingerprint(contract) != schema_fingerprint(form):
            _section(parts, "Assigned result contract", _schema(_registered_return_schema_view(
                contract, state.get("available_report_facts", {})), "result_contract", named_definitions=True))
    _section(parts, "Fixed scope", _values(state.get("scope", {})))
    _section(parts, "Parent constraints", _values(assignment.get("constraints", {})))
    _section(parts, "Parent-supplied context", _values(assignment.get("context", {})))
    if assignment.get("evidence_refs"):
        _section(parts, "Parent-selected evidence operands", _values(assignment["evidence_refs"]))

    working = state.get("working_state", {})
    material = {name: [_record(row) for row in working[name]] for name in
        ("subjects", "materials", "collections", "material_links") if working.get(name)}
    material.update(_pick(working, ("target_binding", "read_library_access", "supplied_context_source_refs")))
    if material:
        _section(parts, "Supplied material and scoped access", _values(material))

    selected_sources = set(assignment.get("evidence_refs", ())) | set(
        working.get("supplied_context_source_refs", ()))
    source_operands = [{"source_ref": row["id"], **_pick(row,
        ("origin", "provider", "accession", "version", "uri"))}
        for row in working.get("sources", ()) if row.get("id") in selected_sources]
    if source_operands:
        _section(parts, "Selected source operands (metadata only)",
            "These are received source identities and provenance for navigation. "
            "Read the actual contents to establish what each source supports.\n\n"
            + _values(source_operands))

    axis = process["evidence_axis"]
    _section(parts, "Investigate the supplied target: " + axis.get("name", ""),
        axis["investigation_instructions"])
    thought = process.get("thought_pattern", {})
    _section(parts, "Reason about the evidence: " + thought.get("name", ""),
        "\n\n".join(_scalar(thought[name]) for name in ("description", "use_when") if name in thought))
    for field, label in (("live_alternatives", "Alternatives to distinguish"),
            ("decision_guidance", "How to choose and revise the investigation")):
        if thought.get(field):
            _section(parts, label, "\n".join("- " + item for item in thought[field]))
    if thought.get("outcome_contingencies"):
        _section(parts, "How outcomes affect the next choice", _table(
            ("If observed", "Then consider"), ((row["if_observed"], row["then_consider"])
                for row in thought["outcome_contingencies"])))
    _section(parts, "Limits of this reasoning approach", thought.get("boundary"))

    for tool in process.get("child_tool_info", ()):
        _section(parts, "Selected tool: " + tool["name"] + " (" + tool["resources"] + ")",
            tool["description"] + "\n\n" + tool["instructions"])
    selected_manuals = state.get("selected_launch_instructions") or {}
    for section in selected_manuals.get("sections", ()):
        _section(parts, "Assigned software or resource instructions: " + section["entry_id"]
            + " / " + section["section_id"], section["text"])
    tools = state.get("tools", ())
    if tools:
        _section(parts, "Callable operations", _table(("Operation", "Meaning"),
            ((tool["name"], tool.get("description", "")) for tool in tools)))
        for tool in tools:
            if "input_schema" in tool:
                _section(parts, "Operands for " + tool["name"],
                    _schema(_operation_schema_view(tool["input_schema"]), "arguments", named_definitions=True))
    _section(parts, "Permitted child roles", _values(process.get("permitted_children", [])))
    _section(parts, "Child construction and requested facts", state.get("child_options"))
    _section(parts, "Evidence through child returns",
        "Choose each child's return facts to carry the evidence needed for your question. "
        "committed_record_refs carries the acquired scientific record references; select the provider's "
        "coverage/completeness facts when interpreting acquired rows or an empty result. "
        "A job handle, usable handoff or null failure field alone does not return the search data. "
        "Keep a completed empty acquisition distinct from partial or unavailable acquisition, and "
        "keep those acquisition facts separate from evidence for a biological function.")
    if state.get('contract_information_profile') == 'operation_contract_information_v1':
        _section(parts, "Discover and select exact return contracts",
            "Within this pending decision, request_context with view=composition_information, "
            "operation=episode.return_contract and arguments containing the permitted child's role "
            "and source returns its exact frozen fact type and meaning. In your chosen closed child "
            "form, a top-level field may contain only $ref with value episode-fact:<source>. "
            "For example, records can reference episode-fact:committed_record_refs. "
            "The host expands your explicit selection to its original type and fills recorded facts; "
            "leave those fact fields out of initial_report_json. Choose the relevant sources and "
            "return their actual saved grading results, numerical status, qualifications and missing inputs. "
            "Reporting does not require another supported/contradicted, function, path or scope verdict: "
            "use the grading sheet's existing criteria and status, without inventing a score threshold "
            "or asking a child to judge the same result again. Contract lookup creates no evidence, "
            "child, completed action or credit.")
    _section(parts, "Information requested by the parent", state.get("requested_report_purpose"))
    if state.get("requested_form") is not None:
        form = state["requested_form"]
        sources = state.get("available_report_facts", {})
        _section(parts, "Parent return form", _schema(_registered_return_schema_view(form, sources), "return"))
        used = {row.get("x-source") for row in form.get("properties", {}).values()}
        _section(parts, "Meaning of requested recorded facts", _table(("Source", "Meaning"),
            ((name, sources[name].get("meaning", "")) for name in sources if name in used)))
    _section(parts, "Return interpretation timing", state.get("report_lifecycle"))

    # These are the exact values required by a separately chosen child's typed
    # assignment, not scientific evidence or narrated library provenance.
    if process.get("selection"):
        _section(parts, "Callable selection operands for child assignment (copy exact values)",
            _values(process["selection"]))
    return "\n".join(parts)


def _band(band):
    if not isinstance(band, Mapping):
        return "unavailable", "unavailable"
    code = band.get("status_code")
    if code not in (None, 0):
        status = {-1: "insufficient completed actions", -2: "unidentifiable"}.get(code,
            "unavailable (status " + str(code) + ")")
        return "unavailable", status
    if "value" not in band:
        return "unavailable", "unavailable"
    uncertainty = "lower=" + _scalar(band.get("lower")) + "; upper=" + _scalar(band.get("upper"))
    if "uncertainty_code" in band:
        uncertainty += "; " + {0: "exact", 1: "Chebyshev bound", 2: "approximate Laplace model band"}.get(
            band["uncertainty_code"], "unavailable uncertainty")
    if "alpha" in band:
        uncertainty += "; alpha=" + _scalar(band["alpha"])
    return _scalar(band["value"]), uncertainty


def _references(value):
    if isinstance(value, Mapping):
        for key, child in value.items():
            if (key in {"id", "ref"} or key.endswith("_ref")) and isinstance(child, str):
                yield child
            elif (key == "dependencies" or key.endswith("_refs")) and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _received_records(state):
    """Only current interpretations and records explicitly linked to this turn.

    Do not turn a scoped source inventory into received source content. No Store
    reads are performed; unresolved references remain operands for a later read.
    """
    working = state.get("working_state", {})
    # A Source is a storage/provenance envelope, not the acquired source's
    # scientific content. Do not expand received references into metadata here.
    # Explicit source operands remain in supplied material and action outcomes.
    fields = ("features", "products", "terms", "references", "contexts", "observations",
        "hypotheses", "assessments", "annotations", "interpretation_accounts")
    records = {row["id"]: row for field in fields for row in working.get(field, ())
        if isinstance(row, Mapping) and isinstance(row.get("id"), str)}
    revision_status = {row["record_ref"]: row["is_current_revision"]
        for row in working.get("received_revision_status", ())}
    current = [row["id"] for field in ("annotations", "interpretation_accounts")
        for row in working.get(field, ()) if revision_status.get(row["id"], True)]
    selected = list(dict.fromkeys([*current,
        *state.get("scientific_process", {}).get("assignment", {}).get("evidence_refs", ()),
        *state.get("current_report_basis_refs", ()),
        *_references(state.get("current_report_update", {})),
        *_references(state.get("last_local_outcome", {})),
        *_references(state.get("child_reports", []))]))
    found = {}
    for reference in selected:
        if reference in found or reference not in records:
            continue
        row = records[reference]
        found[reference] = _record(row)
        selected.extend(ref for ref in _references(row) if ref not in found)
    return list(found.values())


def _feedback(value):
    """Keep actionable feedback without its private host diagnostic address."""
    if not isinstance(value, Mapping):
        return value
    return {key: child for key, child in value.items() if key != "diagnostic_ref"}


def _outcome(value):
    if not isinstance(value, Mapping):
        return value
    # Native result and feedback values are exact; operation receipts and full
    # estimator/tracking envelopes are not presentation. Revision preparation
    # is the exception: its origin is an operand required to commission it.
    shown = _pick(value, ("status", "record_refs", "changed_record_refs", "result", "feedback",
        "error_code", "errors", "conflicts", "notices", "aliases",
        "revision_origin", "automatic_preview", "visual_inputs", "child_completion"))
    if "feedback" in shown:
        shown["feedback"] = _feedback(shown["feedback"])
    proposal = shown.get("result")
    if isinstance(proposal, Mapping) and proposal.get("version") == "scientific_process_child_selection_v1":
        from .scientific_process_records import (
            SELECTION_VERSION, selector_selection, validate_child_selection, validate_revision_origin)
        from .tool_information import parent_view
        try:
            prepared = validate_child_selection(proposal)
            validate_revision_origin(shown.get("revision_origin"))
        except (ValueError, TypeError):
            return shown
        selected = prepared["selection"]
        if selected["version"] == SELECTION_VERSION:
            # The existing child-assignment interface accepts exact selectors
            # and restores/authenticates the original pinned tool information.
            # Full child instructions remain in the saved preparation, rather
            # than being copied into this parent's latest-outcome table.
            shown["result"] = {**prepared, "selection": selector_selection(selected)}
            shown["prepared_child_tools"] = parent_view(selected["child_tool_info"])
            shown["preparation_use"] = (
                "Commission a separate scientific_process child with result.selection and revision_origin. "
                "The host restores the complete pinned tool descriptions and instructions and authenticates "
                "them against the original preparation. This preparation does not change the current episode.")
    return shown


def _lookup(result):
    """Render only the explicit reply, never the recorded exchange transcript."""
    comparison = render_rna_comparison_lookup(result)
    if comparison is not None:
        return comparison
    original_rna = render_rna_structure_lookup(result)
    if original_rna is not None:
        return original_rna
    if not isinstance(result, Mapping):
        return _values(result)
    if result.get("view") == "own_attempts":
        parts = [_table(("Attempt operand", "Category", "Status", "Completed gain"),
            ((row["decision_index"], row.get("category"), row["status"], row.get("completed_gain"))
                for row in result.get("records", ())))]
        for row in result.get("records", ()):
            data = {"inputs": _bounded_inputs(row.get("inputs", {}))}
            publications = row.get("published_references", {})
            data["published_references"] = _pick(publications, ("values", "total", "included", "complete"))
            if not row.get("input_fields", {}).get("complete", True):
                data["more_input_query"] = row["input_fields"].get("detail_query")
            _section(parts, "Attempt " + str(row["decision_index"]), _values(data))
        _section(parts, "Lookup page", _values(_pick(result,
            ("total", "offset", "returned_count", "next_query", "unavailable_reasons"))))
        return "\n".join(parts)
    if result.get("view") == "own_attempt_detail":
        return _values(_bounded_inputs(_pick(result, ("decision_index", "pointer", "slice_unit",
            "offset", "total", "included", "values", "has_more", "next_query"))))
    content = result.get("result", result)
    if isinstance(content, Mapping) and content.get('information_kind') in (
            'operation_contract_information_v1', 'return_contract_information_v1'):
        parts = [_scalar(content.get('meaning', ''))]
        if content.get('information_kind') == 'return_contract_information_v1':
            parts.append('Child role: '+_scalar(content['role'])+'; fact source: '+_scalar(content['source']))
            parts.append('Explicit form reference: episode-fact:'+_scalar(content['source']))
        parts.append(_scalar(content['text']))
        return '\n\n'.join(parts)
    if isinstance(content, Mapping) and "text" in content:
        parts = [_scalar(content["text"])]
        page = _pick(content, ("entry_id", "section_id", "coordinate_unit", "offset", "returned_lines",
            "total_lines", "next_query"))
        if page:
            _section(parts, "Selected instruction window", _values(page))
        return "\n".join(parts)
    # Composition lookups have an ordinary outcome envelope. Library-specific
    # projections remove the instruction provenance while retaining selectable
    # option operands; no evidence records are fetched to decorate this reply.
    return _values(_information(_outcome(result) if "status" in result else result))


def _bounded_inputs(value):
    if isinstance(value, Mapping):
        if value.get("representation") == "bounded_selected_input_v1":
            return {"value_type": value["value_type"], **_pick(value,
                ("total", "included", "complete", "detail_query")),
                **({"values": _bounded_inputs(value["values"])} if "values" in value else {})}
        return {key: _bounded_inputs(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_bounded_inputs(child) for child in value]
    return value


def _molecular_source_metadata_view(value):
    """Show callable Source operands without private artifact addresses."""
    if (value.get("record_type") != "source" or value.get("origin") != "tool"
            or (value.get("provider"), value.get("version")) not in {
                ("analyze_protease_kinetics", "ordinary_protease_kinetics_result_v1"),
                ("analyze_arsenic_speciation_hplc_icpms", "ordinary_arsenic_speciation_result_v1"),
                ("predict_protein_disorder_regions", "ordinary_protein_disorder_result_v1"),
                ("generate_gene_embeddings_with_ESM_models", "esm_gene_embedding_result_v1"),
                ("analyze_protein_phylogeny", "ordinary_protein_phylogeny_result_v1"),
                ("detect_and_annotate_somatic_mutations", "ordinary_somatic_variant_result_v1"),
                ("analyze_protein_conservation", "ordinary_protein_conservation_result_v1")}):
        return None
    from .communication import plain
    from .domain import RECORD_SCHEMAS, identity, validate_schema
    try:
        source = plain(value)
        expected_fields = {"id", "record_type", "origin", "provider", "version", "accession", "uri",
            "artifact_ref", "text_ref", "request_ref", "retrieved_at", "parent_source_refs", "auxiliary_artifact_refs"}
        if set(source) != expected_fields:
            return None
        body = {key: child for key, child in source.items() if key not in {"id", "record_type", "origin"}}
        validate_schema(body, RECORD_SCHEMAS["source"])
        if source["id"] != identity("source", {"origin": source["origin"], "record": body}):
            return None
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return None
    if source["provider"] in {"analyze_protein_conservation", "analyze_protein_phylogeny", "generate_gene_embeddings_with_ESM_models", "detect_and_annotate_somatic_mutations"}:
        return {"source_ref": source["id"], "operation": source["provider"], "origin": source["origin"],
            "recorded_file_associations": {
                "selected_values": "recorded" if source["artifact_ref"] is not None else None,
                "verification_control": "recorded" if source["request_ref"] is not None else None,
                "text": "recorded" if source["text_ref"] is not None else None,
                "parent_sources": ["retained provenance" for _ in source["parent_source_refs"]],
                "auxiliary": ["recorded" for _ in source["auxiliary_artifact_refs"]]}}
    return {"source_ref": source["id"], "operation": source["provider"], "origin": source["origin"],
        "accession": source["accession"], "uri": source["uri"],
        "parent_source_refs": deepcopy(source["parent_source_refs"]),
        "recorded_file_associations": {
            "selected_values": "recorded" if source["artifact_ref"] is not None else None,
            "verification_control": "recorded" if source["request_ref"] is not None else None,
            "text": "recorded" if source["text_ref"] is not None else None,
            "auxiliary": ["recorded" for _ in source["auxiliary_artifact_refs"]]}}


def _information(value):
    if isinstance(value, Mapping):
        if value.get("version") in {"ordinary_protease_kinetics_values_v1", "ordinary_arsenic_speciation_values_v1",
                "ordinary_protein_disorder_values_v1", "ordinary_primer_placement_values_v1",
                "ordinary_protein_conservation_values_v1", "esm_gene_embedding_values_v1"}:
            packet = _selected_molecular_packet(value)
            if packet is not None:
                return packet
        source_metadata = _molecular_source_metadata_view(value)
        if source_metadata is not None:
            return source_metadata
        # P entries retain their source rows in the immutable library. They are
        # instruction provenance, not target evidence in a lookup continuation.
        if value.get("slot") == "thought_pattern":
            return {key: _information(child) for key, child in value.items() if key != "evidence"}
        if "option_ref" in value and "entry" in value:
            return {"option_ref": value["option_ref"], "entry": _information(value["entry"])}
        if "entries" in value and "library" in value:
            return {key: _information(child) for key, child in value.items() if key != "library"}
        if value.get("content_role") in {"tool_and_resource_instructions_not_scientific_evidence",
                "launch_instructions_not_inventory_or_scientific_evidence"}:
            return {key: _information(child) for key, child in value.items() if key not in
                {"version", "library_id", "entry_count", "content_role", "section_sha256"}}
        return {key: _information(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_information(child) for child in value]
    return value


def _progress(row):
    """Current already-received progress, retaining measured facts and read operands."""
    result = _pick(row, ("target_handle", "observed_at", "result_available", "committed_record_refs"))
    status = row.get("execution_status", {})
    result["execution_status"] = _pick(status, ("handle", "observed_at", "lifecycle_state", "liveness",
        "result_available", "return_available", "failure", "resource_kind"))
    if isinstance(status.get("native"), Mapping):
        result["native_status"] = _pick(status["native"], ("state", "outcome", "returncode", "failure_code",
            "elapsed_seconds", "duration_measure", "measurements", "outputs"))
    result["measurements"] = row.get("measurements", [])
    result["log_windows"] = [_pick(window, ("source_ref", "artifact_ref", "start_byte", "end_byte",
        "observed_at")) for window in row.get("log_windows", ())]
    result["dependencies"] = [_pick(child, ("handle", "kind", "observed_at", "state"))
        for child in row.get("dependencies", ())]
    return result


def _steering(state, lookup_results):
    parts = ["STEERING"]
    if 'completed_action_reports' in state:
        parts.extend(['', render_completed_action_reports(state['completed_action_reports'])])
    if state.get('pending_child_delivery') is not None:
        _section(parts, 'Complete the original child return', _values(state['pending_child_delivery']))
    if state.get('resource_context') is not None:
        _section(parts, 'Local budget, shared capacity and Aurora planning', _values(state['resource_context']))
    if state.get('execution_initial_information') or state.get('execution_resource_information'):
        for name, title in (
                ('execution_resource_capabilities', 'Actual configured execution resources'),
                ('execution_initial_information', 'Retained initial resource observations'),
                ('execution_resource_information', 'Retained resource observations')):
            if state.get(name) not in (None, {}, []):
                _section(parts, title, json.dumps({name: state[name]}, ensure_ascii=False,
                    allow_nan=False, separators=(',', ':')))
    if state.get('shared_information_context') is not None:
        _section(parts, 'Shared-parent information needs and available deliveries',
            _values(state['shared_information_context']))
    # These channels are resolved against this receiver's actual receipts by
    # the scientific binding. Preserve their numerical subsets, qualifications
    # and dependence rather than leaving them only in the unrendered context.
    for key, title in (
            ('component_axis_scoring_sheets',
             'Current A107/A110 scientific scoring sheets; updated automatically from received results'),
            ('received_partner_and_chemical_evidence',
             'Received A107/A110 scientific component reports; separate quantities'),
            ('received_partner_and_chemical_native_components',
             'Received A107/A110 native components and execution findings'),
            ('received_partner_and_chemical_qualifications',
             'Received A107/A110 per-use scientific qualifications'),
            ('received_gene_context_execution',
             'Received genomic execution outcomes and missing capabilities')):
        if state.get(key):
            # These versioned sheets already carry their complete structure.
            # Repeating a dotted field path for every cell and provenance
            # leaf can exceed the provider interface even for a small dataset.
            # Keep every supplied value and dependency in compact nested JSON.
            body = (_molecular_literal(state[key])
                    if key == 'component_axis_scoring_sheets' else _values(state[key]))
            _section(parts, title, body)
    yields = state.get("action_yields", {})
    rows = []
    for row in yields.get("rows", ()):
        expected = row.get("expected_yield", {})
        point, uncertainty = _band(expected.get("band"))
        if expected.get("status") == "unavailable":
            point = "unavailable"
            uncertainty = expected.get("unavailable_reason") or uncertainty
        rows.append((row["category"], row["completed_actions"], row["total_yield"], point,
            uncertainty, row.get("attempted_uncompleted")))
    _section(parts, "Own completed actions", _table(("Category", "Completed", "Total signed yield",
        "Expected next yield", "Uncertainty or unavailable reason", "Uncompleted attempts"), rows))
    controller = state.get("controller", {})
    estimate = controller.get("estimate", {})
    if estimate:
        point, uncertainty = _band(estimate.get("expected_next_gain"))
        _section(parts, "Current continuation expectation", _table(
            ("Completed actions", "Expected next gain", "Uncertainty", "Continuation cost"),
            [(estimate.get("turns"), point, uncertainty,
                controller.get("decision", {}).get("continuation_cost"))]))
    metrics = _pick(state, ("current_credit", "annotation_score", "monitoring_information_credit"))
    if metrics:
        _section(parts, "Current separate measures", _values(metrics))
    progress = {key: state[key] for key in ("credit_binding", "investigation_progress")
        if state.get(key) is not None}
    if progress:
        _section(parts, "Scientific progress definition and current findings",
            _molecular_literal(progress))
    if yields.get("unavailable_reasons"):
        _section(parts, "Yield information limits", _values(yields["unavailable_reasons"]))
    records = _received_records(state)
    if records:
        _section(parts, "Current interpretations and their received evidence", _values(records))
    if state.get("current_report_update"):
        _section(parts, "Current return interpretation", _values(state["current_report_update"]))
    # Completed-work accounts summarize outcomes and earned credit; they omit
    # source bodies, exact witnesses and command streams. Preserve the latest
    # authorized tool return so the episode can use what it actually acquired.
    if state.get("last_local_outcome") is not None:
        _section(parts, "Last own action outcome", _values(_information(_outcome(state["last_local_outcome"]))))
    if state.get("feedback") is not None and state["feedback"] != (state.get("last_local_outcome") or {}).get("feedback"):
        _section(parts, "Actionable feedback", _values(_feedback(state["feedback"])))
    if state.get("child_reports") and 'completed_action_reports' not in state:
        _section(parts, "Admitted child returns", _values([
            alignment_report_presentation(report) for report in state["child_reports"]]))
    if state.get("received_bvbrc_values"):
        _section(parts, "Received BV-BRC Data API values", _values([
            _pick(group, ("form_field", "fact_source", "facts", "cells", "unavailable"))
            for group in state["received_bvbrc_values"]]))
    pending = state.get("pending_work", {})
    if pending.get("items"):
        rows = []
        for row in pending["items"]:
            current = _pick(row, ("handle", "role", "lifecycle_state", "selected_at", "observed_at",
                "latest_progress_ref", "return_available", "event_target", "original_assignment"))
            resource = row.get("resource_selection")
            if resource is not None:
                current["resource_selection"] = _pick(resource, ("resource_id", "kind", "allocation"))
            rows.append(current)
        _section(parts, "Pending work", _values(rows))
        wanted = {row.get("latest_progress_ref") for row in pending["items"]}
        progress = [_progress(row) for row in state.get("waiting_support", {}).get("progress_records", ())
            if row.get("progress_ref") in wanted and row.get("progress_ref") is not None]
        if progress:
            _section(parts, "Latest received progress for pending work", _values(progress))
    if state.get("resource_tool_estimates"):
        _section(parts, "Execution duration expectations", _values([_pick(row,
            ("job_ref", "proposal_ref", "execution_class_ref", "current_condition_state", "status", "phase",
             "cpu_threads", "memory_limit_bytes", "scratch_limit_bytes", "successful_duration_samples",
             "outcome_support", "expected_total_seconds", "observed_min_seconds", "observed_max_seconds",
             "forecast_duration_measure", "elapsed_seconds", "timing_relation"))
            for row in state["resource_tool_estimates"]]))
    if state.get("job_execution_options"):
        _section(parts, "Operands for the duration expectations", _values(state["job_execution_options"]))
    if state.get("native_event_targets"):
        _section(parts, "Available native event operands", _values([
            {"target": _pick(row["target"], ("handle", "job_ref", "resource_id", "event", "cause")),
                "after_cursor": row["after_cursor"]} for row in state["native_event_targets"]]))
    deliveries = [row for row in state.get("report_deliveries", ())
        if row.get("status") == "pending" or row.get("timing_receipt_issues")]
    if deliveries:
        _section(parts, "Report delivery issues", _values(deliveries))
    parse_failures = [_record(row) for row in state.get("working_state", {}).get("parse_attempts", ())
        if row.get("status") not in {None, "completed"} or row.get("error_count", 0)]
    if parse_failures:
        _section(parts, "Supplied material parsing issues", _values(parse_failures))
    for result in lookup_results:
        _section(parts, "Requested information; continue the same decision", _lookup(result))
    return "\n".join(parts)


def _interval_result_presentation(state, lookup_results):
    """Select declared scientific-result channels before generic masking."""
    from .genomic_overlap_presentation import (
        select_genomic_overlap_presentation, render_genomic_overlap_projections)
    from .chromatin_interaction_presentation import (
        select_chromatin_presentation, render_chromatin_projections)
    from .atac_differential_presentation import (
        select_atac_presentation, render_atac_projections)
    from .expression_nmf_presentation import (
        select_expression_nmf_presentation, render_expression_nmf_projections)
    from .native_profile_presentation import (
        select_native_profile_presentation, render_native_profile_results)
    overlap = select_genomic_overlap_presentation(state, lookup_results=lookup_results)
    chromatin = select_chromatin_presentation(overlap['context'],
        lookup_results=overlap['lookup_results'])
    atac = select_atac_presentation(chromatin['context'],
        lookup_results=chromatin['lookup_results'])
    nmf = select_expression_nmf_presentation(atac['context'],
        lookup_results=atac['lookup_results'])
    profiles = select_native_profile_presentation(nmf['context'],
        lookup_results=nmf['lookup_results'])
    sections = []
    if overlap['projections']:
        sections.append(render_genomic_overlap_projections(overlap['projections']))
    if chromatin['projections']:
        sections.append(render_chromatin_projections(chromatin['projections']))
    if atac['projections']:
        sections.append(render_atac_projections(atac['projections']))
    if nmf['projections']:
        sections.append(render_expression_nmf_projections(nmf['projections']))
    if profiles['projections']:
        sections.append(render_native_profile_results(profiles['projections']))
    return profiles['context'], profiles['lookup_results'], sections


def _render_episode_steering(state, lookup_results, interval_sections):
    """Render a state whose interval channels have already been selected."""
    from .macs2_peak_presentation import select_macs2_peak_capture_presentation, render_macs2_peak_captures
    macs2 = select_macs2_peak_capture_presentation(state, lookup_results=lookup_results)
    state, lookup_results = macs2['context'], macs2['lookup_results']
    selected = select_rna_comparison_presentation(infernal_receiver_context(state))
    original = select_rna_structure_presentation(selected["context"])
    parts = [_steering(original["context"], lookup_results)]
    _section(parts, "Last own RNA comparison outcome",
        render_rna_comparison_own_outcome(selected["own_outcome"]))
    if selected["projections"]:
        _section(parts, "Selected RNA comparison facts",
            render_rna_comparison_projections(selected["projections"]))
    _section(parts, "Original RNA result delivery",
        render_rna_structure_own_progress(original["own_progress"]))
    _section(parts, "Last own original RNA result outcome",
        render_rna_structure_own_outcome(original["own_outcome"]))
    if original["groups"]:
        _section(parts, "Selected original RNA facts and callable operands",
            render_rna_structure_groups(original["groups"]))
    if macs2['captures']:
        parts.append(render_macs2_peak_captures(macs2['captures']))
    parts.extend(interval_sections)
    return "\n".join(parts)


def render_episode_steering(state, *, lookup_results=()):
    """Render supplied facts after detached, exact registered selection."""
    state, lookup_results, sections = _interval_result_presentation(state, lookup_results)
    return _render_episode_steering(state, lookup_results, sections)


def render_scientific_process_prompt(state, instructions, *, lookup_results=()):
    """Complete recurring TASK plus current, mechanically selected STEERING."""
    if not is_published_scientific_context(state):
        raise ValueError("published_scientific_instructions_required")
    return _task(state, instructions) + "\n\n" + render_episode_steering(state,
        lookup_results=lookup_results)


__all__ = ["is_published_scientific_context", "has_molecular_receiver_context", "text_instructions", "render_episode_steering",
    "render_scientific_process_prompt"]


def is_selected_execution_context(context):
    task = context.get("selected_execution_task") if isinstance(context, Mapping) else None
    return (isinstance(task, Mapping) and task.get("version") == "selected_execution_task_v1"
        and isinstance(task.get("scientific_question"), str)
        and isinstance(task.get("selected_tool_info"), (list, tuple))
        and isinstance(task.get("requests"), (list, tuple)) and bool(task["requests"]))


_EXECUTION_PRESENTATION_TRACKING = _RECORD_TRACKING | frozenset({
    "$id", "argv", "environment", "cwd", "workspace", "directory", "path", "relative_path",
    "staged_relative_path", "python_executable", "implementation_files", "driver_module", "worker_module",
    "custody", "original_custody", "handoff_proof", "intent", "bundle", "worker", "capture",
    "context_before", "context_after", "assignment_sha256", "original_operation_key", "operation_ref",
    "receipt_key", "result_receipt_key", "started_at", "finished_at", "captured_at", "observed_at",
    "execution_id", "assignment_id", "operational_credit_binding", "native_protein_structure",
    "result_selector_schema", "qualified_files", "family_artifact_refs", "calculation", "calculation_id",
})
_EXECUTION_OPAQUE_PREFIXES = ("artifact_", "source_", "observation_", "reference_", "operation_",
    "episode_", "goal_", "input_", "scientific_invocation_", "progress_", "execution_")


def _execution_opaque_reference(value):
    if not isinstance(value, str):
        return False
    for prefix in _EXECUTION_OPAQUE_PREFIXES:
        if value.startswith(prefix):
            suffix = value[len(prefix):]
            return 24 <= len(suffix) <= 64 and all(character in "0123456789abcdef" for character in suffix)
    return False


def _execution_presentation_values(value):
    """Keep supplied scientific values, without native custody or host coordinates."""
    if isinstance(value, Mapping):
        from .bvbrc_application_returns import select_application_execution_values
        application = select_application_execution_values(value)
        if application is not None:
            return application
        from .execution_prompt import select_profile_api_execution_values
        api = select_profile_api_execution_values(value)
        if api is not None:
            return api
        from .macs2_peak_presentation import select_macs2_peak_execution_values
        macs2 = select_macs2_peak_execution_values(value)
        if macs2 is not None:
            return macs2
        from .lumpy_request_binding import select_lumpy_execution_values
        lumpy = select_lumpy_execution_values(value)
        if lumpy is not None:
            return lumpy
        from .genomic_overlap_presentation import select_genomic_overlap_execution_values
        overlap = select_genomic_overlap_execution_values(value)
        if overlap is not None:
            return overlap
        from .chromatin_interaction_presentation import select_chromatin_execution_values
        chromatin = select_chromatin_execution_values(value)
        if chromatin is not None:
            return chromatin
        from .atac_differential_presentation import select_atac_execution_values
        atac = select_atac_execution_values(value)
        if atac is not None:
            return atac
        from .expression_nmf_presentation import select_expression_nmf_execution_values
        nmf = select_expression_nmf_execution_values(value)
        if nmf is not None:
            return nmf
        from .native_profile_presentation import select_native_profile_execution_values
        profile = select_native_profile_execution_values(value)
        if profile is not None:
            return profile
        result = {}
        for key, child in value.items():
            if (key in _EXECUTION_PRESENTATION_TRACKING or key.endswith("_sha256")
                    or key.endswith("_digest") or key.endswith("_path") or key.endswith("_paths")):
                continue
            if (key in {"id", "ref", "handle"} or key.endswith("_ref")) and _execution_opaque_reference(child):
                continue
            if (key.endswith("_refs") or key == "references") and isinstance(child, (list, tuple)):
                child = [item for item in child if not _execution_opaque_reference(item)]
            if key == "body" and isinstance(child, Mapping):
                child = _pick(child, ("native_success", "capture_complete", "issues", "observation",
                    "observation_origin"))
            elif key == "publication" and isinstance(child, Mapping):
                child = _pick(child, ("facts", "delivery_complete"))
            result[key] = _execution_presentation_values(child)
        return result
    if isinstance(value, (list, tuple)):
        result = []
        for child in value:
            result.append(_execution_presentation_values(child))
        return result
    return value


def _execution_schema_view(schema):
    """Remove only schema identity annotations; retain the declared constraints."""
    if isinstance(schema, Mapping):
        from .macs2_peak_presentation import macs2_peak_schema_view
        macs2 = macs2_peak_schema_view(schema)
        if macs2 is not None:
            return macs2
        return {key: _execution_schema_view(child) for key, child in schema.items() if key != "$id"}
    if isinstance(schema, (list, tuple)):
        return [_execution_schema_view(child) for child in schema]
    return schema


def _selected_execution_task(state, instructions):
    task = state["selected_execution_task"]
    parts = ["TASK"]
    _section(parts, "Scientific QUESTION", task["scientific_question"])
    _section(parts, "Assigned job", state.get("goal", {}).get("objective"))
    _section(parts, "Fixed scope", _values(state.get("scope", {})))
    _section(parts, "Parent constraints", _values(_execution_presentation_values(task.get("constraints", {}))))
    for tool in task["selected_tool_info"]:
        _section(parts, "Parent-selected tool guidance: " + tool["name"] + " (" + tool["resources"] + ")",
            tool["description"] + "\n\n" + tool["instructions"])
    for request in task["requests"]:
        _section(parts, "Selected work: " + str(request["resource_id"]),
            _values(_execution_presentation_values({key: request[key] for key in
                ("resource_id", "resource_kind", "endpoint", "constraints") if key in request})))
        _section(parts, "Configured resource", _values(_execution_presentation_values(request["resource"])))
        _section(parts, "Exact assigned scientific request",
            _values(_execution_presentation_values(request["job"])))
    if task.get("selector") is not None:
        _section(parts, "Original result selection", _values(_execution_presentation_values(task["selector"])))
    description = task.get("result_description")
    if isinstance(description, Mapping):
        selected = _pick(description, ("operation", "mode", "output_format", "status_meanings"))
        selected["extractors"] = [_pick(row, ("operation", "observation_basis", "fresh_native_observation",
            "scientific_result_acquisition", "completes_assignment", "calculation_basis",
            "calculator_parameters", "original_calculation_parameters", "original_sheet_and_baseline_preserved",
            "new_producer_observation", "return_fact_sources")) for row in description.get("extractors", ())]
        _section(parts, "Original result meanings", _values(_execution_presentation_values(selected)))
    _section(parts, "Execution method and decision rules", text_instructions(instructions))
    manuals = state.get("selected_launch_instructions") or {}
    for section in manuals.get("sections", ()):
        _section(parts, "Assigned software or resource instructions: " + section["entry_id"]
            + " / " + section["section_id"], section["text"])
    tools = state.get("tools", ())
    if tools:
        _section(parts, "Callable operations", _table(("Operation", "Meaning"),
            ((tool["name"], tool.get("description", "")) for tool in tools)))
        for tool in tools:
            if "instructions" in tool:
                _section(parts, "Supplied instructions for " + tool["name"], tool["instructions"])
            if "input_schema" in tool:
                _section(parts, "Operands for " + tool["name"],
                    _schema(_execution_schema_view(tool["input_schema"]), "arguments", named_definitions=True))
    _section(parts, "Information requested by the parent", state.get("requested_report_purpose"))
    form = state.get("requested_form")
    if form is not None:
        sources = state.get("available_report_facts", {})
        _section(parts, "Parent return form", _schema(_execution_schema_view(
            _registered_return_schema_view(form, sources)), "return"))
        used = {row.get("x-source") for row in form.get("properties", {}).values()}
        _section(parts, "Meaning of requested recorded facts", _table(("Source", "Meaning"),
            ((name, sources[name].get("meaning", "")) for name in sources if name in used)))
    _section(parts, "Return interpretation timing", state.get("report_lifecycle"))
    return "\n".join(parts)


def render_selected_execution_prompt(state, instructions, *, lookup_results=()):
    """Present the detached original execution TASK with current own STEERING."""
    if not is_selected_execution_context(state):
        raise ValueError("selected_execution_task_required")
    state, lookup_results, interval_sections = _interval_result_presentation(state, lookup_results)
    from .macs2_peak_presentation import select_macs2_peak_capture_presentation, render_macs2_peak_captures
    macs2 = select_macs2_peak_capture_presentation(state, lookup_results=lookup_results)
    state, lookup_results = macs2['context'], macs2['lookup_results']
    steering = _execution_presentation_values(_pick(state, ("action_yields", "controller", "current_credit",
        "completed_action_reports",
        "last_local_outcome", "feedback", "child_reports", "pending_work", "report_deliveries",
        "waiting_support", "resource_tool_estimates", "job_execution_options", "native_event_targets",
        "pending_child_delivery")))
    lookups = [_execution_presentation_values(value) for value in lookup_results]
    parts = [_selected_execution_task(state, instructions),
        _render_episode_steering(steering, lookups, interval_sections)]
    progress = {}
    if isinstance(state.get("execution_progress"), Mapping):
        progress["execution_progress"] = _pick(state["execution_progress"], ("execution_completed",))
    if isinstance(state.get("practical_progress"), Mapping):
        progress["practical_progress"] = _pick(state["practical_progress"],
            ("credit", "initial_credit", "operational_credit", "requirements", "satisfied_keys"))
    if "practical_completion" in state:
        progress["practical_completion"] = state["practical_completion"]
    if progress:
        _section(parts, "Current execution information", _values(_execution_presentation_values(progress)))
    if macs2['captures']:
        parts.append(render_macs2_peak_captures(macs2['captures']))
    return "\n\n".join(parts)


__all__ += ["is_selected_execution_context", "render_selected_execution_prompt"]
