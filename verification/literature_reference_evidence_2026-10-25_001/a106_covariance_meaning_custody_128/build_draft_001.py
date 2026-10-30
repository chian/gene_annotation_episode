from pathlib import Path
import ast, difflib, hashlib, json
BASE=Path(__file__).resolve().parent
DRAFT=BASE/'draft'
BASELINE=json.loads((BASE/'BASELINE_001.json').read_text())['files']
ROOT=Path.cwd()
def edit(name,old,new):
 p=DRAFT/'gene_annotation_episode'/name
 body=p.read_text()
 assert body.count(old)==1,(name,body.count(old),old[:70])
 p.write_text(body.replace(old,new))

edit('literature_perturbation_summary.py','''        _keys(covariance, COV_FIELDS, field)
        row = deepcopy(covariance)
''','''        has_basis = isinstance(covariance, dict) and "interpretation_basis" in covariance
        _keys(covariance, (*COV_FIELDS, "interpretation_basis") if has_basis else COV_FIELDS, field)
        row = deepcopy(covariance)
        if has_basis:
            _choice(row["interpretation_basis"], INTERPRETATION_BASES, field + ".interpretation_basis")
''')
edit('literature_perturbation_summary.py','''    return {"version": VERSION, "inputs": deepcopy(inputs), "primitive_order": list(ROLES), "cells": cells,
            "summary_descriptors": descriptors}
''','''    result = {"version": VERSION, "inputs": deepcopy(inputs), "primitive_order": list(ROLES), "cells": cells,
              "summary_descriptors": descriptors}
    captured = covariance_descriptors(summary)
    if captured is not None:
        result["covariance_descriptors"] = captured
    return result


def covariance_descriptors(summary):
    """Capture explicitly requested covariance meaning, never numerical values.

    An absent basis remains absent in the source and null in this new snapshot.
    Old inputs without any deliberate qualifier acquire no new snapshot.
    """
    if not any("interpretation_basis" in row for row in summary["covariances"]):
        return None
    selected = {frozenset((row["first"], row["second"])): row for row in summary["covariances"]}
    result = []
    for first, second in (("W", "K"), ("W", "R"), ("K", "R")):
        row = selected.get(frozenset((first, second)))
        result.append({"first": first, "second": second,
            "selection": "selected" if row is not None else "unreported",
            "kind": row["kind"] if row is not None else "unknown",
            "interpretation_basis": row.get("interpretation_basis") if row is not None else None,
            "variance_status": ("estimated" if row["kind"] == "paired_units" else row["variance_status"])
                if row is not None else "unknown",
            "witnesses": deepcopy(row["witnesses"]) if row is not None else []})
    return result
''')
edit('literature_perturbation_summary_storage.py','from .domain import ContractError, canonical, validate_schema','from .domain import ContractError, canonical, identity, obj, validate_schema')
edit('literature_perturbation_summary_storage.py','    INTERPRETATION_BASIS_FIELDS, INTERPRETATION_BASES,','    INTERPRETATION_BASIS_FIELDS, INTERPRETATION_BASES, covariance_descriptors,')
edit('literature_perturbation_summary_storage.py','def perturbation_summary_cells_schema(*, include_interpretation_basis=True):','def perturbation_summary_cells_schema(*, include_interpretation_basis=True, include_covariance_interpretations=True):')
edit('literature_perturbation_summary_storage.py','''        for roles, names in groups.items()]
    return schema
''','''        for roles, names in groups.items()]
    if not include_covariance_interpretations:
        # Exact122 registered56-field contract, including its original allOf.
        return schema
    properties["covariance_interpretations"] = _covariance_schema()
    for pairs in ((), (("W", "K"),), (("K", "R"),), (("W", "K"), ("W", "R"), ("K", "R"))):
        names = [name for name in COMPONENTS if _covariance_pairs(name) == pairs]
        schema["items"]["allOf"].append({"if": {"properties": {"component": {"enum": names}}},
            "then": {"properties": {"covariance_interpretations": _covariance_schema(pairs) if pairs else False}}})
    return schema
''')
edit('literature_perturbation_summary_storage.py','''        return saved

    def project_cells''','''        validate_covariance_meanings(saved, self.store)
        return saved

    def project_cells''')
# Helpers are metadata-only; old payloads never call a publication path.
p=DRAFT/'gene_annotation_episode/literature_perturbation_summary_storage.py'
body=p.read_text();at=body.index('\n\nclass LiteraturePerturbationSummaryProjection')
helpers='''

_COVARIANCE_USES = ("used_selected_covariance", "unknown_covariance_enclosure", "component_unavailable")


def _covariance_pairs(component):
    if component in ("perturbation_mean_variance", "perturbation_variance_lower", "perturbation_variance_upper"):
        return (("W", "K"),)
    if component in ("restoration_mean_variance", "restoration_variance_lower", "restoration_variance_upper"):
        return (("K", "R"),)
    if component == "shared_contrast_covariance":
        return (("W", "K"), ("W", "R"), ("K", "R"))
    return ()


def _covariance_schema(pairs=None):
    reference = {"type": "string", "format": "reference", "x-reference-namespace": "reference"}
    fields = {"first": {"type": "string", "enum": ["W", "K", "R"]},
        "second": {"type": "string", "enum": ["W", "K", "R"]},
        "selection": {"type": "string", "enum": ["selected", "unreported"]},
        "kind": {"type": "string", "enum": ["unknown", "mean_covariance", "uncorrelated", "paired_units"]},
        "interpretation_basis": {"type": ["string", "null"], "enum": [None, *INTERPRETATION_BASES]},
        "variance_status": {"type": "string", "enum": list(VARIANCE_STATUSES)},
        "use": {"type": "string", "enum": list(_COVARIANCE_USES)},
        "support_refs": {"type": "array", "uniqueItems": True, "items": reference}}
    result = {"type": "array", "minItems": 1, "maxItems": 3, "items": obj(fields)}
    if pairs is not None:
        result.update(minItems=len(pairs), maxItems=len(pairs), items=False,
            prefixItems=[obj({**deepcopy(fields), "first": {"type": "string", "const": first},
                "second": {"type": "string", "const": second}}) for first, second in pairs])
    return result


def _publish_covariance_support(descriptors, publish):
    result = {}
    for row in descriptors:
        references = []
        for witness in row["witnesses"]:
            anchor = {name: witness[name] for name in ("source_ref", "artifact_ref", "start", "end", "quote")}
            references.append(publish("reference", {"reference_type": "literature_result",
                "source_ref": witness["source_ref"], "accession": identity("perturbation_literal", {
                    "field": "covariance_support", "first": row["first"], "second": row["second"], **anchor}),
                "label": "Covariance interpretation support", "sequence_ref": None, "molecule": None,
                "length": None, "term_refs": [], "context_refs": [], "anchor": anchor}))
        result[row["first"] + "_" + row["second"]] = list(dict.fromkeys(references))
    return result


def _qualified_covariance_cells(sheet, descriptors, bindings):
    selected = {(row["first"], row["second"]): row for row in descriptors}
    result = {}
    for name, cell in sheet["cells"].items():
        pairs = _covariance_pairs(name)
        if not pairs:
            continue
        qualifiers = []
        for pair in pairs:
            source = selected[pair]
            use = ("component_unavailable" if cell["value"] is None else
                "unknown_covariance_enclosure" if source["kind"] == "unknown" else "used_selected_covariance")
            qualifiers.append({**{key: deepcopy(value) for key, value in source.items() if key != "witnesses"},
                "use": use, "support_refs": deepcopy(bindings[pair[0] + "_" + pair[1]])})
        result[name] = qualifiers
    return result


def publish_covariance_meanings(extraction, sheet, publish):
    """Publish only deliberate new covariance metadata, with no arithmetic."""
    descriptors = sheet.get("covariance_descriptors")
    if descriptors is None:
        return None, []
    if descriptors != covariance_descriptors(extraction["summary_data"]):
        raise ContractError("literature_perturbation_covariance_saved_mismatch")
    bindings = _publish_covariance_support(descriptors, publish)
    for name, qualifiers in _qualified_covariance_cells(sheet, descriptors, bindings).items():
        sheet["cells"][name]["covariance_interpretations"] = qualifiers
    return bindings, list(dict.fromkeys(ref for rows in bindings.values() for ref in rows))


def validate_covariance_meanings(saved, store):
    """Validate original saved meanings/references without source I/O or fitting."""
    expected = covariance_descriptors(saved["extraction"]["summary_data"])
    sheet = saved["sheet"]
    if expected is None:
        if ("covariance_descriptors" in sheet or "covariance_support_bindings" in saved
                or any("covariance_interpretations" in cell for cell in sheet["cells"].values())):
            raise ContractError("literature_perturbation_covariance_saved_mismatch")
        return
    if expected != sheet.get("covariance_descriptors"):
        raise ContractError("literature_perturbation_covariance_saved_mismatch")
    def published(kind, record):
        reference = identity(kind, {"origin": "tool", "record": record})
        if store.get(reference) != {"id": reference, "record_type": kind, "origin": "tool", **record}:
            raise ContractError("literature_perturbation_covariance_support_mismatch")
        return reference
    bindings = _publish_covariance_support(expected, published)
    if bindings != saved.get("covariance_support_bindings"):
        raise ContractError("literature_perturbation_covariance_support_mismatch")
    qualifiers = _qualified_covariance_cells(sheet, expected, bindings)
    for name, cell in sheet["cells"].items():
        if ((name in qualifiers and cell.get("covariance_interpretations") != qualifiers[name])
                or (name not in qualifiers and "covariance_interpretations" in cell)):
            raise ContractError("literature_perturbation_covariance_saved_mismatch")
'''
p.write_text(body[:at]+helpers+body[at:])
edit('literature_perturbation_storage.py','''            payload['experimental_bindings'] = bindings
            artifact = self.store.artifact''','''            payload['experimental_bindings'] = bindings
            covariance_refs = []
            if summary:
                from .literature_perturbation_summary_storage import publish_covariance_meanings
                covariance_bindings, covariance_refs = publish_covariance_meanings(extraction, sheet, publish)
                if covariance_bindings is not None:
                    payload['covariance_support_bindings'] = covariance_bindings
            artifact = self.store.artifact''')
edit('literature_perturbation_storage.py','''                'record_refs': list(dict.fromkeys([sheet_ref, *parents, *(ref for ref in bindings.values() if ref)])),''','''                'record_refs': list(dict.fromkeys([sheet_ref, *parents, *(ref for ref in bindings.values() if ref), *covariance_refs])),''')
edit('communication.py','''            # Only these two complete registered fact contracts permit their
''','''            # Only these complete registered fact contracts permit their
''')
edit('communication.py','''            expected = (perturbation_summary_cells_schema(),
                perturbation_summary_cells_schema(include_interpretation_basis=False))''','''            expected = (perturbation_summary_cells_schema(),
                perturbation_summary_cells_schema(include_covariance_interpretations=False),
                perturbation_summary_cells_schema(include_interpretation_basis=False))''')
edit('literature_experimental_prompt.py','''    selected = {}
    for reference in pending:
''','''    covariance_support = set(_covariance_support_refs((state.get("last_local_outcome", {}),
        state.get("child_reports", ()), state.get("current_report_update", {}), lookup_results)))
    selected = {}
    for reference in pending:
''')
edit('literature_experimental_prompt.py','''        row = records[reference]
        selected[reference] = row
''','''        row = records[reference]
        if reference in covariance_support:
            # The selected support identity is returned, not its raw operands.
            # Exact anchors remain durable; source reading stays explicit.
            row = {**row, "anchor": None, "visual_anchor": None}
        selected[reference] = row
''')
# New pure presentation functions stay in the already fingerprinted module.
p=DRAFT/'gene_annotation_episode/literature_experimental_prompt.py';body=p.read_text();at=body.index('\ndef _source_result(')
helpers='''

def _covariance_support_refs(value):
    if isinstance(value, Mapping):
        rows = value.get("covariance_interpretations")
        if isinstance(rows, (list, tuple)):
            for row in rows:
                if isinstance(row, Mapping):
                    yield from (ref for ref in row.get("support_refs", ()) if isinstance(ref, str))
        for child in value.values():
            yield from _covariance_support_refs(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _covariance_support_refs(child)


def _covariance_meanings(parts, rows, records):
    records = records or {}
    rendered = []
    for row in rows:
        for covariance in row.get("covariance_interpretations", ()):
            support = []
            for reference in covariance["support_refs"]:
                record = records.get(reference)
                support.append(record.get("label", "anchored source support") if isinstance(record, Mapping)
                    else "meaning unavailable in the received scientific records")
            rendered.append((row["component"], covariance["first"] + "," + covariance["second"],
                covariance["selection"], covariance["kind"], covariance["interpretation_basis"] or "unreported",
                covariance["variance_status"], covariance["use"], "; ".join(support) or "none supplied"))
    if rendered:
        _section(parts, "Selected covariance meanings", _table(("Component", "Arm pair", "Selection",
            "Covariance kind", "Interpretation basis", "Variance status", "Component use", "Source support"), rendered))

'''
p.write_text(body[:at]+helpers+body[at:])
edit('literature_experimental_prompt.py','''        _amount_metadata(parts, content)
    assay = content.get("assay_interpretation")''','''        _amount_metadata(parts, content)
        _covariance_meanings(parts, ({"component": name, **cell} for name, cell in cells.items()), controlled_records)
    assay = content.get("assay_interpretation")''')
edit('literature_experimental_prompt.py','''    rate_domains = {}
    from .literature_controlled_response_render''','''    rate_domains = {}
    covariance_rows = []
    from .literature_controlled_response_render''')
edit('literature_experimental_prompt.py','''            else:
                remainder[name] = value
        if remainder:
''','''            else:
                if (isinstance(value, (list, tuple)) and value and all(isinstance(row, Mapping)
                        and row.get("evaluated_scope") == "interpreted_reference_perturbation" for row in value)
                        and any("covariance_interpretations" in row for row in value)):
                    covariance_rows.extend(value)
                    remainder[name] = [{key: child for key, child in row.items()
                        if key != "covariance_interpretations"} for row in value]
                else:
                    remainder[name] = value
        if remainder:
''')
edit('literature_experimental_prompt.py','''    if ordinary:
        _section(parts, "Admitted requested child returns", values(ordinary))
    native_sheets''','''    if ordinary:
        _section(parts, "Admitted requested child returns", values(ordinary))
    _covariance_meanings(parts, covariance_rows, records)
    native_sheets''')
# All five production files remain exactly their captured baselines.
patch=[];manifest={}
for name,before in BASELINE.items():
 source=ROOT/name;candidate=DRAFT/name
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before,(name,'production drift')
 ast.parse(candidate.read_text());manifest[name]=hashlib.sha256(candidate.read_bytes()).hexdigest()
 patch.extend(difflib.unified_diff(source.read_text().splitlines(True),candidate.read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
with (BASE/'PROPOSED_PATCH_001.diff').open('x') as f:f.writelines(patch)
with (BASE/'DRAFT_MANIFEST_001.json').open('x') as f:json.dump({'baseline':BASELINE,'candidate':manifest,'production_unchanged':True},f,indent=2)
print({'candidate_files':len(manifest),'patch_lines':len(patch),'production_unchanged':True})
