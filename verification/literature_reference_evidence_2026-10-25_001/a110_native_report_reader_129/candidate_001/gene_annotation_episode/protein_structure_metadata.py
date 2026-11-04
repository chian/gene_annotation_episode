"""Exact native uncertainty/QA joins, separate from structural fit calculations."""
from __future__ import annotations
from copy import deepcopy
import re

from .protein_structure_contracts import (
    ParsedStructure, StructureSequence, SuppliedMetadata, StructureMetadata,
    canonical, issue, same, validate_parsed_structure, validate_structure_sequence,
    validate_file_identity, validate_metadata_document, validate_structure_metadata,
)
from .protein_structure_formats import (absent_token, category_rows, get_token,
    native_number, native_integer, pdb_field, token_text, _pdb_contexts, pdb_residue_identity)
from .protein_structure_sequences import (_selected_atoms, _address, residue_position_key, residue_component_id)


def _cell(value=None, *, state="missing", reason="native_field_missing", unit="unknown", origin="observed"):
    return {"value": value, "state": "present" if value is not None else state,
            "reason": None if value is not None else reason, "unit": unit, "origin": origin}


def _native_cell(number, unit, *, origin="observed", scale=1.0, minimum=None, maximum=None, integer=False):
    if number["state"] == "present":
        value = number["value"]
        if minimum is not None and value < minimum or maximum is not None and value > maximum or integer and value != int(value):
            return _cell(state="invalid", reason="native_field_invalid", unit=unit, origin=origin)
        value = int(value) if integer else value * scale
        return _cell(value, unit=unit, origin=origin)
    return _cell(state=number["state"], reason="native_field_missing" if number["state"] == "missing" else "native_field_invalid", unit=unit, origin=origin)


def _conflict(result, row, field):
    problem = issue("metadata_join_conflict", stage="metadata", role=result["structure_role"], atom=row.get("atom_row_key"), field=field)
    row["issues"].append(problem)
    result["issues"].append(deepcopy(problem))
    if "qualifications" in row and "uncertainty_join_conflict" not in row["qualifications"]:
        row["qualifications"].append("uncertainty_join_conflict")


def _unjoined(result, key, addresses, reason="metadata_join_conflict"):
    result["unjoined_rows"].append({"row_key": key, "native_addresses": addresses, "reason": reason})
    result["issues"].append(issue("metadata_join_conflict", stage="metadata", role=result["structure_role"], field="native_metadata"))


def _supplied(selected, supplied_metadata):
    if type(supplied_metadata) is not list:
        raise ValueError("invalid_schema")
    supplied = []
    for item in supplied_metadata:
        if type(item) is not dict or set(item) != {"file_identity", "document"}:
            raise ValueError("invalid_schema")
        file, document = validate_file_identity(item["file_identity"]), validate_metadata_document(item["document"])
        if file["format"] != "protein_structure_metadata_v1":
            raise ValueError("unsupported_format")
        if any(d["evidence_artifact_ref"] == file["artifact_ref"] for d in document["semantics_declarations"] + document["metric_unit_declarations"]):
            raise ValueError("metadata_join_conflict")
        supplied.append({"file_identity": file, "document": document})
    if len({canonical(s["file_identity"]) for s in supplied}) != len(supplied):
        raise ValueError("duplicate_selection")
    evidence = selected["semantics_evidence"]
    if evidence is not None:
        matches = [decl for item in supplied if same(item["file_identity"], evidence["file_identity"])
                   for decl in item["document"]["semantics_declarations"] if decl["declaration_id"] == evidence["declaration_id"]]
        scope = {"structure_file": selected["file_identity"], "data_block": selected["data_block"], "model_key": selected["model_key"], "chain_key": selected["chain_key"]}
        if len(matches) != 1 or not same(matches[0]["scope"], scope) or matches[0]["bfactor_semantics"] != selected["bfactor_semantics"]:
            raise ValueError("metadata_join_conflict")
    return supplied


def _atom_row(atom, selection, parsed):
    key, semantics = atom["identity"]["atom_row_key"], selection["bfactor_semantics"]
    native = atom["b_iso"]
    b = _native_cell(native, "native_b_column")
    physical = _native_cell(native, "angstrom_squared") if semantics == "native_atomic_displacement" else _cell(state="not_applicable" if semantics == "declared_plddt" else "unavailable", reason="mode_not_applicable" if semantics == "declared_plddt" else "semantics_unspecified", unit="angstrom_squared")
    plddt = _native_cell(native, "score_0_100", origin="native_predicted", minimum=0, maximum=100) if semantics == "declared_plddt" else _cell(state="unavailable", reason="not_supplied", unit="score_0_100", origin="native_predicted")
    quals = ["uncertainty_not_used_as_weight"]
    if semantics == "unspecified":
        quals.append("bfactor_semantics_unspecified")
    if plddt["state"] == "unavailable":
        quals.append("confidence_not_supplied")
    elif plddt["state"] == "present":
        quals.append("predicted_score_not_function_probability")
    if b["value"] == 0:
        quals.append("native_zero_b_not_proof_of_measured_uncertainty")
    if atom["occupancy"]["state"] == "missing":
        quals.append("occupancy_not_reported")
    block = selection["data_block"]["ordinal_0based"] if selection["data_block"] else None
    prefix = "_atom_site." if block is not None else "ATOM."
    return {"row_key": "uncertainty_" + key, "structure_role": selection["structure_role"], "atom_row_key": key,
        "residue_identity": deepcopy(atom["identity"]["residue"]), "occupancy": _native_cell(atom["occupancy"], "fraction", minimum=0, maximum=1),
        "b_factor_native": b, "physical_b_A2": physical, "plddt": plddt,
        "coordinate_standard_uncertainty_xyz_A": [_cell(unit="angstrom") for _ in range(3)],
        "anisotropic_U_A2": [_cell(unit="angstrom_squared") for _ in range(6)],
        "anisotropic_U_standard_uncertainty_A2": [_cell(unit="angstrom_squared") for _ in range(6)],
        "native_addresses": [_address(parsed, block, key, prefix + "occupancy"), _address(parsed, block, key, prefix + ("B_iso_or_equiv" if block is not None else "tempFactor"))],
        "qualifications": quals, "issues": []}


def _pdb_uncertainty(parsed, result, atoms, by_atom):
    _, contexts, _ = _pdb_contexts(parsed["pdb_records"])
    selected = result["selection"]
    rows = {}
    for record in parsed["pdb_records"]:
        kind = record["record_name"]
        if kind not in ("SIGATM", "ANISOU", "SIGUIJ"):
            continue
        ctx = contexts.get(record["record_key"])
        if ctx is not None and (not same(ctx[0], selected["model_key"]) or not same(ctx[1], selected["chain_key"])):
            continue
        addresses = [_address(parsed, None, record["record_key"], kind)]
        matches = []
        for atom in atoms:
            identity = atom["identity"]
            residue = pdb_residue_identity(record, parsed["file_identity"]["sha256"], ctx, record_class=identity["residue"]["record_class"])
            if not same(residue, identity["residue"]):
                continue
            if all(pdb_field(record, start, end)["text"] == identity[field]["text"] for field, start, end in (("serial_or_atom_site_id", 6, 11), ("atom_name", 12, 16), ("alt_id", 16, 17))):
                matches.append(atom)
        if len(matches) != 1:
            _unjoined(result, record["record_key"], addresses); continue
        key = matches[0]["identity"]["atom_row_key"]
        rows.setdefault((key, kind), []).append(record)
    for (key, kind), records in rows.items():
        output = by_atom[key]
        field = {"SIGATM": "coordinate_standard_uncertainty_xyz_A", "ANISOU": "anisotropic_U_A2", "SIGUIJ": "anisotropic_U_standard_uncertainty_A2"}[kind]
        count = 3 if kind == "SIGATM" else 6
        unit = "angstrom" if kind == "SIGATM" else "angstrom_squared"
        if len(records) != 1:
            output[field] = [_cell(state="invalid", reason="metadata_join_conflict", unit=unit) for _ in range(count)]
            _conflict(result, output, "coordinate_esd" if kind == "SIGATM" else "anisotropic_u")
            for record in records:
                _unjoined(result, record["record_key"], [_address(parsed, None, record["record_key"], kind)])
            continue
        record = records[0]
        fields = [(30 + 8 * i, 38 + 8 * i) for i in range(3)] if kind == "SIGATM" else [(28 + 7 * i, 35 + 7 * i) for i in range(6)]
        values = []
        for start, end in fields:
            token = pdb_field(record, start, end)
            if kind != "SIGATM" and token["lexical_state"] == "value" and native_integer(token) is None:
                values.append(_cell(state="invalid", reason="native_field_invalid", unit=unit))
            else:
                values.append(_native_cell(native_number(token), unit, scale=1.0 if kind == "SIGATM" else 1e-4, minimum=0 if kind != "ANISOU" else None))
        output[field] = values
        output["native_addresses"].extend(_address(parsed, None, record["record_key"], kind + "." + name) for name in (("sigX", "sigY", "sigZ") if kind == "SIGATM" else ("U11", "U22", "U33", "U12", "U13", "U23")))


def _esd(native, separate, unit, result, output, field):
    embedded = native["embedded_standard_uncertainty"]
    explicit = _native_cell(separate, unit, minimum=0)
    if embedded is not None and explicit["state"] == "present" and embedded != explicit["value"] or explicit["state"] == "invalid":
        _conflict(result, output, field)
        return _cell(state="invalid", reason="metadata_join_conflict", unit=unit)
    if explicit["state"] == "present":
        return explicit
    return _cell(embedded, unit=unit)


def _qualifier_matches(supplied, native):
    if supplied["lexical_state"] in ("absent", "cif_unknown"):
        return True
    return supplied["lexical_state"] == native["lexical_state"] and supplied["text"] == native["text"]


def _cif_uncertainty(parsed, result, atoms, by_atom):
    block = result["selection"]["data_block"]["ordinal_0based"]
    native_rows = dict(category_rows(parsed, block, "_atom_site"))
    for atom in atoms:
        key = atom["identity"]["atom_row_key"]
        native = native_rows[key]
        output = by_atom[key]
        for i, axis in enumerate("xyz"):
            explicit = native_number(get_token(native, "cartn_" + axis + "_esd"))
            output["coordinate_standard_uncertainty_xyz_A"][i] = _esd(atom["xyz_A"][i], explicit, "angstrom", result, output, "coordinate_esd")
            for field in ("cartn_" + axis, "cartn_" + axis + "_esd"):
                if field in native:
                    output["native_addresses"].append(_address(parsed, block, key, "_atom_site." + field))
    joined = {}
    block_atoms = [a for a in parsed["atoms"] if a["identity"]["residue"] is not None and a["identity"]["residue"].get("block_ordinal_0based") == block]
    for key, row in category_rows(parsed, block, "_atom_site_anisotrop"):
        addresses = [_address(parsed, block, key, "_atom_site_anisotrop." + field) for field in row]
        identifier = token_text(get_token(row, "id"))
        candidates = [a for a in block_atoms if token_text(a["identity"]["serial_or_atom_site_id"]) == identifier and identifier is not None]
        matching = []
        for atom in candidates:
            identity, residue = atom["identity"], atom["identity"]["residue"]
            qualifiers = {
                "type_symbol": identity["element"], "pdbx_label_atom_id": identity["atom_name"],
                "pdbx_auth_atom_id": identity["auth_atom_name"], "pdbx_auth_atom_name": identity["auth_atom_name"],
                "pdbx_pdb_atom_name": identity["auth_atom_name"], "pdbx_label_alt_id": identity["alt_id"], "pdbx_auth_alt_id": identity["alt_id"],
                "pdbx_label_asym_id": residue["label_asym_id"], "pdbx_auth_asym_id": residue["auth_asym_id"],
                "pdbx_pdb_strand_id": residue["auth_asym_id"], "pdbx_label_comp_id": residue["label_comp_id"],
                "pdbx_auth_comp_id": residue["auth_comp_id"], "pdbx_pdb_residue_name": residue["auth_comp_id"],
                "pdbx_label_seq_id": residue["label_seq_id"], "pdbx_auth_seq_id": residue["auth_seq_id"],
                "pdbx_pdb_residue_no": residue["auth_seq_id"], "pdbx_pdb_ins_code": residue["insertion_code"],
                "pdbx_label_ins_code": residue["insertion_code"], "pdbx_pdb_model_num": residue["model_key"]["native_serial_token"],
            }
            if all(_qualifier_matches(get_token(row, field), native) for field, native in qualifiers.items()):
                matching.append(atom)
        if len(matching) != 1:
            _unjoined(result, key, addresses); continue
        atom_key = matching[0]["identity"]["atom_row_key"]
        if atom_key not in by_atom:
            continue
        joined.setdefault(atom_key, []).append((key, row, addresses))
    for atom_key, records in joined.items():
        output = by_atom[atom_key]
        if len(records) != 1:
            output["anisotropic_U_A2"] = [_cell(state="invalid", reason="metadata_join_conflict", unit="angstrom_squared") for _ in range(6)]
            output["anisotropic_U_standard_uncertainty_A2"] = deepcopy(output["anisotropic_U_A2"])
            _conflict(result, output, "anisotropic_u")
            for key, row, addresses in records:
                _unjoined(result, key, addresses)
            continue
        key, row, addresses = records[0]
        output["native_addresses"].extend(addresses)
        for i, name in enumerate(("u[1][1]", "u[2][2]", "u[3][3]", "u[1][2]", "u[1][3]", "u[2][3]")):
            native, explicit = native_number(get_token(row, name)), native_number(get_token(row, name + "_esd"))
            output["anisotropic_U_A2"][i] = _native_cell(native, "angstrom_squared")
            output["anisotropic_U_standard_uncertainty_A2"][i] = _esd(native, explicit, "angstrom_squared", result, output, "anisotropic_u")


def _qa(parsed, sequence, result, by_atom):
    selection = sequence["selection"]
    block, chain = selection["data_block"]["ordinal_0based"], selection["chain_key"]["label_asym_id"]
    metrics = {}
    for key, row in category_rows(parsed, block, "_ma_qa_metric"):
        identifier = token_text(get_token(row, "id"))
        if identifier is None:
            _unjoined(result, key, [_address(parsed, block, key, "_ma_qa_metric.id")]); continue
        native_type = (token_text(get_token(row, "type")) or "").lower()
        # Only exact declared dictionary meanings supply these units; neither
        # metric names nor numeric range identify a prediction score.
        meaning, unit = (("plddt", "score_0_100") if native_type == "plddt" else ("pae", "angstrom") if native_type == "pae" else ("other", "fraction") if native_type in ("normalized score", "contact probability", "plddt in [0,1]") else ("other", "dimensionless") if native_type in ("zscore", "boolean") else ("unknown", "unknown"))
        evidence = [_address(parsed, block, key, "_ma_qa_metric.type")] if unit != "unknown" else []
        declarations = [d for supplied in result["supplied_metadata"] for d in supplied["document"]["metric_unit_declarations"]
            if same(d["structure_file"], parsed["file_identity"]) and d["block_ordinal_0based"] == block and d["metric_id"] == identifier]
        declared_id = None
        if len(declarations) > 1 or declarations and meaning != "unknown" and (declarations[0]["meaning"] != meaning or declarations[0]["unit"] != unit):
            _unjoined(result, key, [_address(parsed, block, key, "_ma_qa_metric.type")]); continue
        if declarations:
            declaration = declarations[0]
            meaning, unit, declared_id = declaration["meaning"], declaration["unit"], declaration["declaration_id"]
        metric = {"metric_key": "metric_" + key, "block_ordinal_0based": block,
            "native_metric_id": get_token(row, "id"), "name": get_token(row, "name"), "type": get_token(row, "type"),
            "mode": get_token(row, "mode"), "software_group_id": get_token(row, "software_group_id"), "native_row_key": key,
            "meaning": meaning, "unit": unit, "interpretation_evidence": evidence, "supplied_declaration_id": declared_id}
        metrics.setdefault(identifier, []).append(metric)
    for entries in metrics.values():
        if len(entries) == 1:
            result["metric_definitions"].append(entries[0])
        else:
            for metric in entries:
                _unjoined(result, metric["native_row_key"], metric["interpretation_evidence"])
    positions = {r["position_key"]["label_seq_id"]: r for r in sequence["residues"]}
    serial = token_text(selection["model_key"]["native_serial_token"])
    local_plddt = {}
    for category, scope in (("_ma_qa_metric_global", "global"), ("_ma_qa_metric_local", "local"), ("_ma_qa_metric_local_pairwise", "ordered_pair")):
        for key, row in category_rows(parsed, block, category):
            if token_text(get_token(row, "model_id")) != serial or serial is None:
                continue
            addresses = [_address(parsed, block, key, category + "." + field) for field in row]
            choices = metrics.get(token_text(get_token(row, "metric_id")), [])
            if len(choices) != 1 or choices[0] not in result["metric_definitions"]:
                _unjoined(result, key, addresses); continue
            metric = choices[0]
            native_mode = (token_text(metric["mode"]) or "").lower()
            if native_mode and native_mode != {"global": "global", "local": "local", "ordered_pair": "local-pairwise"}[scope]:
                _unjoined(result, key, addresses); continue
            endpoints, conflict = [], False
            if scope != "global":
                for suffix in (("",) if scope == "local" else ("_1", "_2")):
                    label = token_text(get_token(row, "label_asym_id" + suffix))
                    number = native_integer(get_token(row, "label_seq_id" + suffix), positive=True)
                    comp = token_text(get_token(row, "label_comp_id" + suffix))
                    if not label or number is None:
                        conflict = True; break
                    mapped = positions.get(number) if label == chain else None
                    if mapped and comp is not None and comp != mapped["selected_component_id"]:
                        conflict = True
                    endpoints.append({"model_key": deepcopy(selection["model_key"]), "label_asym_id": label, "label_seq_id": number,
                        "selected_position_0based": mapped["sequence_position_0based"] if mapped else None})
                if endpoints and all(e["label_asym_id"] != chain for e in endpoints):
                    continue
            if conflict:
                _unjoined(result, key, addresses); continue
            native = native_number(get_token(row, "metric_value"))
            value = _native_cell(native, metric["unit"], origin="native_predicted" if metric["meaning"] in ("pae", "plddt") else "observed",
                                 minimum=0 if metric["meaning"] in ("pae", "plddt") else None, maximum=100 if metric["meaning"] == "plddt" else None)
            qa = {"row_key": "qa_" + key, "structure_role": result["structure_role"], "scope": scope, "metric_key": metric["metric_key"],
                "endpoint_1": endpoints[0] if endpoints else None, "endpoint_2": endpoints[1] if len(endpoints) == 2 else None,
                "native_value": native, "value": value, "native_addresses": addresses, "issues": []}
            result["qa_rows"].append(qa)
            if metric["unit"] == "unknown" and "native_qa_unit_unknown" not in result["qualifications"]:
                result["qualifications"].append("native_qa_unit_unknown")
            if scope == "local" and metric["meaning"] == "plddt" and endpoints[0]["selected_position_0based"] is not None:
                local_plddt.setdefault(endpoints[0]["label_seq_id"], []).append(qa)
    for output in by_atom.values():
        p = residue_position_key(output["residue_identity"])
        values = local_plddt.get(p["label_seq_id"], []) if p else []
        if not values:
            continue
        if len(values) != 1 or output["plddt"]["state"] == "present" and not same(output["plddt"], values[0]["value"]):
            output["plddt"] = _cell(state="invalid", reason="metadata_join_conflict", unit="score_0_100", origin="native_predicted")
            _conflict(result, output, "plddt")
        else:
            output["plddt"] = deepcopy(values[0]["value"])
            output["native_addresses"].extend(values[0]["native_addresses"])
            output["qualifications"] = [q for q in output["qualifications"] if q != "confidence_not_supplied"]
            if "predicted_score_not_function_probability" not in output["qualifications"]:
                output["qualifications"].append("predicted_score_not_function_probability")


def _metadata_values(parsed, result):
    selection = result["selection"]
    role = result["structure_role"]
    if selection["data_block"] is None:
        for record in parsed["pdb_records"]:
            kind = record["record_name"]
            if kind == "EXPDTA":
                result["metadata_values"].append({"row_key": "metadata_" + record["record_key"], "structure_role": role, "kind": "method",
                    "native_text": pdb_field(record, 10, len(record["text"].rstrip("\r\n"))), "value": None,
                    "native_addresses": [_address(parsed, None, record["record_key"], "EXPDTA.technique")]})
            elif kind == "SEQRES" and pdb_field(record, 11, 12)["text"] == selection["chain_key"]["chain_id"]:
                result["metadata_values"].append({"row_key": "metadata_" + record["record_key"], "structure_role": role, "kind": "declared_sequence_length",
                    "native_text": pdb_field(record, 13, 17), "value": _native_cell(native_number(pdb_field(record, 13, 17)), "residue", integer=True, minimum=0),
                    "native_addresses": [_address(parsed, None, record["record_key"], "SEQRES.numRes")]})
            elif kind == "REMARK" and record["text"][7:10].strip() == "2":
                match = re.search(r"RESOLUTION\.\s+([0-9.]+)\s+ANGSTROMS", record["text"])
                if match:
                    token = pdb_field(record, match.start(1), match.end(1))
                    result["metadata_values"].append({"row_key": "metadata_" + record["record_key"], "structure_role": role, "kind": "resolution",
                        "native_text": token, "value": _native_cell(native_number(token), "angstrom", minimum=0),
                        "native_addresses": [_address(parsed, None, record["record_key"], "REMARK_2.resolution")]})
    else:
        block = selection["data_block"]["ordinal_0based"]
        for category, field, kind in (("_exptl", "method", "method"), ("_refine", "ls_d_res_high", "resolution"), ("_em_3d_reconstruction", "resolution", "resolution")):
            for key, row in category_rows(parsed, block, category):
                token = get_token(row, field)
                result["metadata_values"].append({"row_key": "metadata_" + key + "_" + field, "structure_role": role, "kind": kind,
                    "native_text": token, "value": None if kind == "method" else _native_cell(native_number(token), "angstrom", minimum=0),
                    "native_addresses": [_address(parsed, block, key, category + "." + field)]})


def extract_native_structure_metadata(parsed: ParsedStructure, *, selected_sequence: StructureSequence,
    supplied_metadata: list[SuppliedMetadata]) -> StructureMetadata:
    parsed, sequence = validate_parsed_structure(parsed), validate_structure_sequence(selected_sequence)
    selection = sequence["selection"]
    if not same(parsed["file_identity"], selection["file_identity"]):
        raise ValueError("input_digest_mismatch")
    supplied = _supplied(selection, supplied_metadata)
    result = {"version": "protein_structure_metadata_extracted_v1", "state": "complete", "structure_role": selection["structure_role"],
        "file_identity": parsed["file_identity"], "selection": deepcopy(selection), "supplied_metadata": supplied,
        "atom_uncertainty": [], "metric_definitions": [], "qa_rows": [], "metadata_values": [], "unjoined_rows": [],
        "issues": [], "qualifications": ["uncertainty_not_used_as_weight"]}
    atoms = [a for a in _selected_atoms(parsed, selection) if a["identity"]["residue"] is not None]
    result["atom_uncertainty"] = [_atom_row(a, selection, parsed) for a in atoms]
    by_atom = {a["atom_row_key"]: a for a in result["atom_uncertainty"]}
    if selection["data_block"] is None:
        _pdb_uncertainty(parsed, result, atoms, by_atom)
    else:
        block = selection["data_block"]["ordinal_0based"]
        if block >= len(parsed["cif_blocks"]) or parsed["cif_blocks"][block]["state"] != "complete":
            result.update(state="unavailable", issues=[issue("metadata_join_conflict", stage="metadata", role=selection["structure_role"], field="data_block")])
            return validate_structure_metadata(result)
        _cif_uncertainty(parsed, result, atoms, by_atom)
        _qa(parsed, sequence, result, by_atom)
    _metadata_values(parsed, result)
    if result["issues"]:
        result["state"] = "partial" if result["atom_uncertainty"] or result["qa_rows"] or result["metadata_values"] else "unavailable"
    return validate_structure_metadata(result)

__all__ = ["extract_native_structure_metadata"]
