"""Explicit structure selections, complete protein maps, and supporting inventories."""
from __future__ import annotations
from copy import deepcopy
from typing import Literal

from .protein_structure_contracts import (
    ParsedStructure, StructureSelection, StructureSequence, InventorySelection, StructureInventory, ResidueIdentity, PositionKey,
    canonical, issue, same, validate_parsed_structure, validate_structure_selection,
    validate_structure_sequence, validate_inventory_selection, validate_structure_inventory,
)
from .protein_structure_formats import (absent_token, category_rows, get_token,
    native_integer, pdb_field, token_text)

COMPONENT_SYMBOLS = dict(zip(
    "ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL ASX GLX".split(),
    "ARNDCQEGHILKMFPSTWYVBZ"))
_NATIVE_EXTRA = {"SEC": "U", "PYL": "O", "XLE": "J", "UNK": "X"}
_ALPHABET = set("ARNDCQEGHILKMFPSTWYVBZX")


def _address(parsed, block, row_key, field):
    # Scalar categories contain one actual native row per field.
    if block is not None:
        for table in parsed["cif_blocks"][block]["tables"]:
            if table["form"] == "scalar" and table["row_keys"] and any(t["text"].lower() == field.lower() for t in table["tags"]):
                row_key = table["row_keys"][0]
                break
    return {"file_sha256": parsed["file_identity"]["sha256"], "block_ordinal_0based": block,
            "record_key": row_key, "field_name": field}


def _value(row, key):
    return token_text(get_token(row, key))


def _distinct(values):
    result = []
    for value in values:
        if not any(same(value, x) for x in result):
            result.append(value)
    return result


def _component(residue):
    return residue["component_id"] if residue["format"] == "pdb_3x_text" else token_text(residue["label_comp_id"])


def _position(residue):
    if residue["format"] == "pdb_3x_text":
        return deepcopy(residue["position_key"])
    seq = native_integer(residue["label_seq_id"], positive=True)
    chain = token_text(residue["label_asym_id"])
    if seq is None or not chain:
        return None
    return {"namespace": "label_seq_id", "file_sha256": residue["file_sha256"],
        "block_ordinal_0based": residue["block_ordinal_0based"], "model_key": deepcopy(residue["model_key"]),
        "chain_key": {"namespace": "label_asym_id", "label_asym_id": chain}, "label_seq_id": seq}


def _selected_atoms(parsed, selection):
    block = selection["data_block"]["ordinal_0based"] if selection["data_block"] else None
    chain = next((r for r in parsed["chains"] if r["block_ordinal_0based"] == block and same(r["model_key"], selection["model_key"]) and same(r["chain_key"], selection["chain_key"])), None)
    keys = set(chain["atom_row_keys"]) if chain else set()
    return [a for a in parsed["atoms"] if a["identity"]["atom_row_key"] in keys]


def _selection_failure(parsed, selection):
    if not same(parsed["file_identity"], selection["file_identity"]):
        raise ValueError("input_digest_mismatch")
    block = selection["data_block"]["ordinal_0based"] if selection["data_block"] else None
    if block is not None:
        if block >= len(parsed["cif_blocks"]) or parsed["cif_blocks"][block]["name"] != selection["data_block"]["name"]:
            return "unselected_data_block"
        if parsed["cif_blocks"][block]["state"] != "complete":
            return "polymer_mapping_unavailable"
    if not any(r["block_ordinal_0based"] == block and same(r["model_key"], selection["model_key"]) for r in parsed["models"]):
        return "model_not_found"
    if not any(r["block_ordinal_0based"] == block and same(r["model_key"], selection["model_key"]) and same(r["chain_key"], selection["chain_key"]) for r in parsed["chains"]):
        # A declared label chain may have no coordinates in this actual model.
        if block is None or selection["sequence_basis"] != "mmcif_declared_polymer" or not any(_value(r, "id") == selection["chain_key"]["label_asym_id"] for _, r in category_rows(parsed, block, "_struct_asym")):
            return "chain_not_found"
    if block is None and any(i["field"] == "model_key" for i in parsed["issues"]):
        return "conflicting_identity"
    for atom in parsed["atoms"]:
        key = atom["identity"]["atom_row_key"]
        if atom["identity"]["residue"] is not None or block is not None and not key.startswith(f"cif_block_{block}_"):
            continue
        # A damaged residue field can still have a trustworthy model/chain
        # context. Preserve independent selected groups; never drop the raw
        # damaged row or pretend an unassigned row has a resolved membership.
        chains = [r for r in parsed["chains"] if key in r["atom_row_keys"]]
        if chains:
            if any(r["block_ordinal_0based"] == block and same(r["model_key"], selection["model_key"]) and same(r["chain_key"], selection["chain_key"]) for r in chains):
                return "polymer_mapping_unavailable"
            continue
        models = [r for r in parsed["models"] if key in r["atom_row_keys"]]
        if models and not any(r["block_ordinal_0based"] == block and same(r["model_key"], selection["model_key"]) for r in models):
            continue
        return "polymer_mapping_unavailable"
    return None


def _modres(parsed):
    result = []
    for record in parsed["pdb_records"]:
        if record["record_name"] == "MODRES":
            result.append({"component": (token_text(pdb_field(record, 12, 15)) or "").strip(),
                "chain": pdb_field(record, 16, 17)["text"], "number": native_integer(pdb_field(record, 18, 22)),
                "insertion": pdb_field(record, 22, 23)["text"],
                "parent": (token_text(pdb_field(record, 24, 27)) or "").strip(),
                "address": _address(parsed, None, record["record_key"], "MODRES.stdRes")})
    return result


def _pdb_population(parsed, selection):
    mods = _modres(parsed)
    groups = {}
    valid = True
    for atom in _selected_atoms(parsed, selection):
        residue = atom["identity"]["residue"]
        if residue is None:
            valid = False; continue
        p, comp = residue["position_key"], residue["component_id"]
        parents = [m for m in mods if m["component"] == comp and m["chain"] == p["chain_key"]["chain_id"] and m["number"] == p["residue_number"] and m["insertion"] == p["insertion_code"]]
        if not (residue["record_class"] == "ATOM" and comp in (COMPONENT_SYMBOLS | _NATIVE_EXTRA) or parents):
            continue
        key = canonical(p)
        group = groups.setdefault(key, {"position": p, "components": [], "atoms": [], "declared": None, "parents": {}})
        if comp not in group["components"]:
            group["components"].append(comp)
        group["parents"][comp] = parents
        group["atoms"].append(atom)
    return list(groups.values()), None, valid


def _cif_population(parsed, selection):
    block = selection["data_block"]["ordinal_0based"]
    chain = selection["chain_key"]["label_asym_id"]
    asym = [r for _, r in category_rows(parsed, block, "_struct_asym") if _value(r, "id") == chain]
    entities = {_value(r, "entity_id") for r in asym}
    if len(asym) != 1 or len(entities) != 1 or None in entities:
        return [], None, False
    entity = next(iter(entities))
    polymer = [r for _, r in category_rows(parsed, block, "_entity_poly") if _value(r, "entity_id") == entity]
    if len(polymer) != 1 or (_value(polymer[0], "type") or "").lower() not in ("polypeptide(l)", "polypeptide(d)"):
        return [], None, False
    groups = {}
    for key, row in category_rows(parsed, block, "_entity_poly_seq"):
        if _value(row, "entity_id") != entity:
            continue
        number = native_integer(get_token(row, "num"), positive=True)
        comp = _value(row, "mon_id")
        if number is None or not comp:
            return [], None, False
        group = groups.setdefault(number, {"position": {"namespace": "label_seq_id", "file_sha256": parsed["file_identity"]["sha256"],
            "block_ordinal_0based": block, "model_key": deepcopy(selection["model_key"]), "chain_key": deepcopy(selection["chain_key"]), "label_seq_id": number},
            "components": [], "atoms": [], "declared": [], "entity": entity, "parents": {}})
        if comp in group["components"]:
            return list(groups.values()), None, False
        group["components"].append(comp)
    if not groups:
        return [], None, False
    valid = True
    for key, row in category_rows(parsed, block, "_pdbx_poly_seq_scheme"):
        if _value(row, "asym_id") != chain:
            continue
        number = native_integer(get_token(row, "seq_id"), positive=True)
        comp = _value(row, "mon_id")
        if number not in groups or comp not in groups[number]["components"] or _value(row, "entity_id") != entity:
            valid = False; continue
        groups[number]["declared"].append((key, row))
    for group in groups.values():
        for comp in group["components"]:
            candidates = [r for _, r in group["declared"] if _value(r, "mon_id") == comp]
            # Different author addresses at the same declared component cannot
            # be resolved by a first-row choice.
            if not candidates or len({canonical({k: (get_token(r, k)["text"], get_token(r, k)["lexical_state"]) for k in ("pdb_strand_id", "auth_seq_num", "pdb_ins_code")}) for r in candidates}) != 1:
                valid = False
    for atom in _selected_atoms(parsed, selection):
        residue = atom["identity"]["residue"]
        if residue is None:
            valid = False; continue
        number = native_integer(residue["label_seq_id"], positive=True)
        if number is None:
            continue  # Native nonpolymer atoms are retained, not protein sites.
        comp = token_text(residue["label_comp_id"])
        if number not in groups or comp not in groups[number]["components"] or token_text(residue["label_entity_id"]) != entity:
            valid = False; continue
        scheme = [r for _, r in groups[number]["declared"] if _value(r, "mon_id") == comp]
        for declared in scheme:
            for native_field, declared_field in (("auth_asym_id", "pdb_strand_id"), ("auth_seq_id", "auth_seq_num")):
                left, right = token_text(residue[native_field]), _value(declared, declared_field)
                if left is not None and right is not None and left != right:
                    valid = False
        groups[number]["atoms"].append(atom)
    for group in groups.values():
        for comp in group["components"]:
            residues = [a["identity"]["residue"] for a in group["atoms"] if _component(a["identity"]["residue"]) == comp]
            for field in ("auth_asym_id", "auth_seq_id", "auth_comp_id", "group_pdb", "insertion_code"):
                known = {(r[field]["text"], r[field]["lexical_state"]) for r in residues if r[field]["lexical_state"] not in ("cif_unknown", "absent")}
                if len(known) > 1:
                    valid = False
    ordered = [groups[n] for n in sorted(groups)]
    length = len(ordered) if valid else None
    if selection["sequence_basis"] == "observed_polymer":
        ordered = [g for g in ordered if g["atoms"]]
    return ordered, length, valid


def _symbol(parsed, group, component, selection):
    native, mapped, origin, evidence = None, None, "unresolved", []
    if component is None:
        return native, mapped, origin, evidence, []
    if parsed["file_identity"]["format"] == "pdb_3x_text":
        native = (COMPONENT_SYMBOLS | _NATIVE_EXTRA).get(component)
        parents = group["parents"].get(component, [])
        if parents:
            evidence += [m["address"] for m in parents]
            parent_ids = {m["parent"] for m in parents}
            if len(parent_ids) == 1:
                mapped = COMPONENT_SYMBOLS.get(next(iter(parent_ids)))
                origin = "pdb_modres_parent" if mapped else "unresolved"
        elif component in COMPONENT_SYMBOLS:
            mapped, origin = COMPONENT_SYMBOLS[component], "standard_amino_acid"
    else:
        block = selection["data_block"]["ordinal_0based"]
        chem = [(key, r) for key, r in category_rows(parsed, block, "_chem_comp") if _value(r, "id") == component]
        native_codes = {_value(r, "one_letter_code") for _, r in chem if _value(r, "one_letter_code") is not None}
        if len(native_codes) == 1:
            native = next(iter(native_codes))
        elif not native_codes:
            native = (COMPONENT_SYMBOLS | _NATIVE_EXTRA).get(component)
        parents = set()
        for key, row in chem:
            if "one_letter_code" in row:
                evidence.append(_address(parsed, block, key, "_chem_comp.one_letter_code"))
            parent = _value(row, "mon_nstd_parent_comp_id")
            if parent:
                parents.update(x.strip() for x in parent.split(","))
                evidence.append(_address(parsed, block, key, "_chem_comp.mon_nstd_parent_comp_id"))
        # A native code, standard component and chemical parent must agree.
        # Unknown/multi-character native codes cannot silently become a parent
        # code or the first supported letter.
        standard = COMPONENT_SYMBOLS.get(component)
        parent_symbol = COMPONENT_SYMBOLS.get(next(iter(parents))) if len(parents) == 1 else None
        native_symbol = next(iter(native_codes)) if len(native_codes) == 1 else None
        candidates = {x for x in (standard, parent_symbol, native_symbol) if x is not None}
        conflict = (len(native_codes) > 1 or len(parents) > 1
            or native_symbol is not None and native_symbol not in _ALPHABET - {"X"}
            or len(candidates) > 1)
        if not conflict:
            if standard is not None:
                mapped, origin = standard, "standard_amino_acid"
            elif parent_symbol is not None:
                mapped, origin = parent_symbol, "mmcif_chemical_parent"
            elif native_symbol is not None:
                mapped, origin = native_symbol, "mmcif_native_one_letter"
    overrides = {x["component_id"]: x["alignment_symbol"] for x in selection["symbol_policy"]["explicit_component_overrides"]}
    qualifications = []
    if component in overrides:
        mapped, origin = overrides[component], "explicit_override"
        qualifications.append("explicit_symbol_override")
    elif mapped is None and selection["symbol_policy"]["unknown"] == "explicit_X":
        mapped, origin = "X", "explicit_unknown_X"
        qualifications.append("explicit_unknown_symbol_X")
    return native, mapped, origin, evidence, qualifications


def _ca(group, component, selection):
    atoms = [a for a in group["atoms"] if _component(a["identity"]["residue"]) == component and (token_text(a["identity"]["atom_name"]) or "").strip() == "CA" and (token_text(a["identity"]["element"]) or "").strip().upper() in ("", "C")]
    keys = [a["identity"]["atom_row_key"] for a in atoms]
    choice = next((r["atom_row_key"] for r in selection["ca_selection"]["choices"] if same(r["position_key"], group["position"])), None)
    if choice is not None and choice not in keys:
        raise ValueError("invalid_coordinate_identity")
    selected = next((a for a in atoms if a["identity"]["atom_row_key"] == choice), None) if choice is not None else atoms[0] if len(atoms) == 1 else None
    reason = "ambiguous_residue_variant" if component is None else "ambiguous_ca" if len(atoms) > 1 and choice is None else "ca_missing" if selected is None else None
    state = "invalid" if component is None else "ambiguous" if reason == "ambiguous_ca" else "missing" if reason else "available"
    qualifiers = []
    if selected is not None:
        codes = {i["code"] for i in selected["issues"]}
        occupancy = selected["occupancy"]
        if "conflicting_identity" in codes or "invalid_coordinate_identity" in codes:
            state, reason = "invalid", "invalid_coordinate_identity"
        elif any(n["state"] != "present" for n in selected["xyz_A"]):
            state, reason = "invalid", "nonfinite_coordinate"
        elif occupancy["state"] == "invalid" or occupancy["state"] == "present" and not 0 <= occupancy["value"] <= 1:
            state, reason = "invalid", "invalid_occupancy"
        elif occupancy["state"] == "present" and occupancy["value"] == 0 and selection["zero_occupancy_policy"] == "exclude":
            state, reason = "excluded", "zero_occupancy_excluded"
        if occupancy["state"] == "missing":
            qualifiers.append("occupancy_not_reported")
    return {"candidate_atom_row_keys": keys, "selected_atom_row_key": selected["identity"]["atom_row_key"] if selected else None,
            "state": state, "primary_reason": reason, "qualifications": qualifiers}, selected


def extract_structure_sequence(parsed: ParsedStructure, *, selection: StructureSelection) -> StructureSequence:
    parsed = validate_parsed_structure(parsed)
    selection = validate_structure_selection(selection)
    return _extract_validated_structure_sequence(parsed, selection=selection)


def _extract_validated_structure_sequence(parsed, *, selection):
    """Host-only fast path immediately after the strict parser has validated.

    The public port above still validates arbitrary supplied objects. Native
    workers may avoid a second full token-tree validation/copy of the parser's
    own result; all population and selection checks below are identical.
    """
    role = selection["structure_role"]
    result = {"version": "protein_structure_sequence_v1", "state": "complete", "selection": selection,
        "alignment_sequence": None, "native_symbols": [], "residues": [], "sequence_length": None,
        "declared_polymer_length": None, "sequence_available": False, "issues": [], "qualifications": []}
    failure = _selection_failure(parsed, selection)
    if failure:
        result.update(state="unavailable", issues=[issue(failure, stage="selection", role=role)])
        return validate_structure_sequence(result)
    pdb = parsed["file_identity"]["format"] == "pdb_3x_text"
    groups, declared_length, valid = _pdb_population(parsed, selection) if pdb else _cif_population(parsed, selection)
    result["declared_polymer_length"] = declared_length
    if selection["sequence_basis"] == "observed_polymer":
        result["qualifications"].append("observed_sequence_not_full_polymer")
    positions = {canonical(g["position"]): g for g in groups}
    for choices in (selection["residue_variant_choices"], selection["ca_selection"]["choices"]):
        if any(canonical(r["position_key"]) not in positions for r in choices):
            raise ValueError("map_endpoint_missing")
    for index, group in enumerate(groups):
        choice = next((r["selected_native_component_id"] for r in selection["residue_variant_choices"] if same(r["position_key"], group["position"])), None)
        if choice is not None and choice not in group["components"]:
            raise ValueError("ambiguous_residue_variant")
        component = choice if choice is not None else group["components"][0] if len(group["components"]) == 1 else None
        identities = _distinct([a["identity"]["residue"] for a in group["atoms"]])
        selected_ids = [r for r in identities if _component(r) == component]
        if pdb and len({r["record_class"] for r in selected_ids}) > 1:
            result["issues"].append(issue("conflicting_identity", stage="sequence", role=role, position=group["position"], field="component_id"))
            component = None; selected_ids = []
        native, symbol, origin, evidence, qualifiers = _symbol(parsed, group, component, selection)
        ca, selected_atom = _ca(group, component, selection)
        selected_identity = deepcopy(selected_atom["identity"]["residue"] if selected_atom else selected_ids[0] if selected_ids else None)
        declared = None
        if not pdb and selected_identity is None and component is not None:
            scheme = [(key, r) for key, r in group["declared"] if _value(r, "mon_id") == component]
            if scheme:
                first = scheme[0][1]
                declared = {"file_sha256": parsed["file_identity"]["sha256"], "block_ordinal_0based": selection["data_block"]["ordinal_0based"],
                    "model_key": deepcopy(selection["model_key"]), "label_asym_id": selection["chain_key"]["label_asym_id"],
                    "label_entity_id": group["entity"], "label_seq_id": group["position"]["label_seq_id"], "component_id": component,
                    "scheme_row_keys": [key for key, _ in scheme], "auth_asym_id": get_token(first, "pdb_strand_id"),
                    "auth_seq_id": get_token(first, "auth_seq_num"), "insertion_code": get_token(first, "pdb_ins_code")}
        row = {"sequence_position_0based": index, "position_key": deepcopy(group["position"]), "native_component_ids": group["components"],
            "selected_component_id": component, "native_one_letter": native, "alignment_symbol": symbol,
            "symbol_mapping_origin": origin, "symbol_evidence": evidence, "observed_residue_identities": identities,
            "selected_residue_identity": selected_identity, "no_coordinate_identity": declared, "ca": ca}
        result["residues"].append(row); result["native_symbols"].append(native)
        for qualification in qualifiers + ca["qualifications"]:
            if qualification not in result["qualifications"]:
                result["qualifications"].append(qualification)
        if component is None or symbol is None:
            result["issues"].append(issue("ambiguous_residue_variant" if component is None else "unsupported_alignment_symbol", stage="sequence", role=role, position=group["position"], field="component_id" if component is None else "symbol"))
        if ca["primary_reason"] is not None:
            result["issues"].append(issue(ca["primary_reason"], stage="selection", role=role, position=group["position"], atom=ca["selected_atom_row_key"], field="xyz"))
    result["sequence_length"] = len(groups) if valid else None
    result["sequence_available"] = valid and bool(groups) and all(r["alignment_symbol"] is not None for r in result["residues"])
    if result["sequence_available"]:
        result["alignment_sequence"] = "".join(r["alignment_symbol"] for r in result["residues"])
    if not valid:
        result["issues"].append(issue("polymer_mapping_unavailable", stage="sequence", role=role, field="residue_map"))
    elif not groups:
        result["issues"].append(issue("empty_sequence", stage="sequence", role=role, field="sequence"))
    if result["issues"]:
        result["state"] = "partial" if result["residues"] else "unavailable"
    return validate_structure_sequence(result)


def rebind_structure_sequence(sequence: StructureSequence, *, structure_role: Literal["single", "fixed", "moving"]) -> StructureSequence:
    result = validate_structure_sequence(sequence)
    if type(structure_role) is not str or structure_role not in ("single", "fixed", "moving"):
        raise ValueError("invalid_schema")
    result["selection"]["structure_role"] = structure_role
    for problem in result["issues"]:
        if problem["structure_role"] is not None:
            problem["structure_role"] = structure_role
    return validate_structure_sequence(result)


def inspect_structure(parsed: ParsedStructure, *, inventory_selection: InventorySelection) -> StructureInventory:
    parsed = validate_parsed_structure(parsed)
    selection = validate_inventory_selection(inventory_selection)
    pdb = parsed["file_identity"]["format"] == "pdb_3x_text"
    if pdb and selection["blocks"]["kind"] != "all":
        raise ValueError("unselected_data_block")
    blocks = {b["ordinal_0based"]: {"ordinal_0based": b["ordinal_0based"], "name": b["name"]} for b in parsed["cif_blocks"]}
    if selection["blocks"]["kind"] == "explicit":
        if any(not same(blocks.get(b["ordinal_0based"]), b) for b in selection["blocks"]["blocks"]):
            raise ValueError("unselected_data_block")
        allowed = {b["ordinal_0based"] for b in selection["blocks"]["blocks"]}
    else:
        allowed = set(blocks) | {None}
    include = set(selection["include"])
    result = {"version": "protein_structure_inventory_v1", "state": parsed["state"], "file_identity": parsed["file_identity"],
        "selection": selection, "models": [], "chains": [], "positions": [], "metadata": [], "issues": deepcopy(parsed["issues"])}
    if "models" in include:
        for index, row in enumerate(parsed["models"]):
            if row["block_ordinal_0based"] in allowed:
                result["models"].append({"row_key": f"model_{index}", "block": blocks.get(row["block_ordinal_0based"]), "model_key": row["model_key"], "atom_count": len(row["atom_row_keys"])})
    chains = deepcopy(parsed["chains"])
    if not pdb:
        # Declared chains without any atoms are still discoverable within an
        # actually inventoried model; this creates no model or residue labels.
        for model in parsed["models"]:
            block = model["block_ordinal_0based"]
            if block not in allowed:
                continue
            for _, native in category_rows(parsed, block, "_struct_asym"):
                label = _value(native, "id")
                if label is None:
                    continue
                key = {"namespace": "label_asym_id", "label_asym_id": label}
                if any(r["block_ordinal_0based"] == block and same(r["model_key"], model["model_key"]) and same(r["chain_key"], key) for r in chains):
                    continue
                auth = _distinct([get_token(r, "pdb_strand_id") for _, r in category_rows(parsed, block, "_pdbx_poly_seq_scheme") if _value(r, "asym_id") == label])
                chains.append({"block_ordinal_0based": block, "model_key": deepcopy(model["model_key"]), "chain_key": key,
                    "auth_chain_tokens": auth, "entity_tokens": [get_token(native, "entity_id")], "atom_row_keys": []})
    for index, row in enumerate(chains):
        if row["block_ordinal_0based"] not in allowed:
            continue
        probe = {"structure_role": "single", "file_identity": parsed["file_identity"], "data_block": blocks.get(row["block_ordinal_0based"]),
            "model_key": row["model_key"], "chain_key": row["chain_key"], "sequence_basis": "observed_polymer" if pdb else "mmcif_declared_polymer", "residue_variant_choices": [],
            "symbol_policy": {"unknown": "reject", "explicit_component_overrides": []}, "ca_selection": {"policy": "unambiguous_only", "choices": []},
            "zero_occupancy_policy": "exclude", "bfactor_semantics": "unspecified", "semantics_evidence": None}
        groups, declared, valid = _pdb_population(parsed, probe) if pdb else _cif_population(parsed, probe)
        if _selection_failure(parsed, probe) is not None:
            valid, declared = False, None
        if include & {"chains", "sequence_bases"}:
            result["chains"].append({"row_key": f"chain_{index}", "block": probe["data_block"], "model_key": row["model_key"], "chain_key": row["chain_key"],
                "auth_chain_tokens": row["auth_chain_tokens"], "entity_tokens": row["entity_tokens"], "atom_count": len(row["atom_row_keys"]),
                "observed_polymer_position_count": sum(bool(g["atoms"]) for g in groups) if valid and "sequence_bases" in include else None,
                "declared_polymer_position_count": declared if "sequence_bases" in include else None,
                "available_sequence_bases": (["observed_polymer"] + (["mmcif_declared_polymer"] if declared is not None else [])) if valid and "sequence_bases" in include else []})
        if include & {"residue_variants", "ca_candidates"}:
            for ordinal, group in enumerate(groups):
                ca_keys = [a["identity"]["atom_row_key"] for a in group["atoms"] if (token_text(a["identity"]["atom_name"]) or "").strip() == "CA" and (token_text(a["identity"]["element"]) or "").strip().upper() in ("", "C")]
                result["positions"].append({"row_key": f"position_{index}_{ordinal}", "position_key": group["position"],
                    "component_ids": group["components"] if "residue_variants" in include else [],
                    "ca_candidate_atom_row_keys": ca_keys if "ca_candidates" in include else []})
    if "native_metadata" in include:
        if pdb:
            for record in parsed["pdb_records"]:
                if record["record_name"] not in ("ATOM", "HETATM", "MODEL", "ENDMDL", "TER", "END"):
                    result["metadata"].append({"row_key": "metadata_" + record["record_key"], "block": None,
                        "native_addresses": [_address(parsed, None, record["record_key"], record["record_name"] or "record")],
                        "native_tokens": [pdb_field(record, 0, len(record["text"].rstrip("\r\n")))]})
        else:
            for block in parsed["cif_blocks"]:
                if block["ordinal_0based"] not in allowed:
                    continue
                for table in block["tables"]:
                    if any(t["text"].lower().startswith("_atom_site.") for t in table["tags"]):
                        continue
                    for key, row in zip(table["row_keys"], table["rows"]):
                        result["metadata"].append({"row_key": "metadata_" + key, "block": blocks[block["ordinal_0based"]],
                            "native_addresses": [_address(parsed, block["ordinal_0based"], key, t["text"]) for t in table["tags"]], "native_tokens": row})
    return validate_structure_inventory(result)

__all__ = ["inspect_structure", "extract_structure_sequence", "rebind_structure_sequence",
           "residue_position_key", "residue_component_id"]


def residue_position_key(residue: ResidueIdentity) -> PositionKey | None:
    """Pure physical position crosswalk; native author fields/spans stay intact."""
    return _position(residue)


def residue_component_id(residue: ResidueIdentity) -> str | None:
    """Selected chemical component in its native label namespace."""
    return _component(residue)
