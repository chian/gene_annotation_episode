"""Original molecular value presentation for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping
import json
from .arsenic_received_values import _arsenic_speciation_text
from .esm_embedding_received_values import _esm_gene_embedding_text
from .glycosylation_received_values import _glycosylation_text
from .homer_motif_received_values import _homer_motif_text
from .molecular_provenance_display import _molecular_failure_view
from .molecular_provenance_display import _molecular_literal
from .molecular_provenance_display import _molecular_provenance_role
from .molecular_provenance_display import _molecular_stored_view
from .glycosylation_received_values import _n_glycosylation_text
from .primer_received_context import _primer_placement_context_text
from .protease_received_context import _protease_context_text
from .protein_disorder_received_values import _protein_disorder_text
from .decision_prompt_text import _rows
from .molecular_result_recognition import _selected_molecular_packet
from .somatic_variant_received_values import _somatic_variant_text
from .decision_prompt_text import _table
from .tf_binding_received_values import _tf_binding_text
from .vcf_received_values import _vcf_result_text


def _selected_molecular_text(packet, number):
    """Display exact selected cells and factor only identical complete qualifiers."""
    if packet.get("version") == "ordinary_somatic_variant_values_v1":
        return _somatic_variant_text(packet, number)
    if packet.get("version") == "esm_gene_embedding_values_v1":
        return _esm_gene_embedding_text(packet, number)
    if packet.get("version") == "ordinary_protein_phylogeny_values_v1":
        from gene_annotation_episode.protein_phylogeny_result_views import render_protein_phylogeny_result
        return render_protein_phylogeny_result(packet, number)
    if packet.get("version") == "ordinary_protein_conservation_values_v1":
        from gene_annotation_episode.protein_conservation_result_views import render_protein_conservation_result
        return render_protein_conservation_result(packet, number)
    if packet.get("version") == "ordinary_protein_disorder_values_v1":
        return _protein_disorder_text(packet, number)
    if packet.get("version") == "ordinary_arsenic_speciation_values_v1":
        return _arsenic_speciation_text(packet, number)
    if packet.get("version") == "vcf_result_return_v1":
        return _vcf_result_text(packet, number)
    if packet.get("version") in (
            "ordinary_itc_values_v1", "ordinary_itc_partial_values_v1", "itc_parameter_return_v1"):
        from gene_annotation_episode.itc_binding_presentation import render_itc_binding_result
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
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_presentation import render_macs2_peak_result
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


