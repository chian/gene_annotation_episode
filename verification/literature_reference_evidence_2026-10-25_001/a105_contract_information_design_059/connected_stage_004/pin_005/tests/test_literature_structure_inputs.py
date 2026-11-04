"""Synthetic CIF/XML custody fixtures only; no paper or real-source findings."""
from copy import deepcopy

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_structure_inputs import (
    LITERAL_FIELDS, SCOPE, VERSION, read_structure_inputs, structure_population_schema,
)

SOURCE = "source_" + "1" * 24
COORD = "source_" + "2" * 24
REPORT = "source_" + "3" * 24
ART = "artifact_" + "4" * 24
TEXT = "µ molecule M construct C condition X experiment E"
COLS = ("group_PDB", "id", "auth_atom_id", "auth_comp_id", "auth_asym_id", "auth_seq_id",
        "label_alt_id", "pdbx_PDB_ins_code", "Cartn_x", "Cartn_y", "Cartn_z", "occupancy",
        "B_iso_or_equiv", "pdbx_PDB_model_num")


def selector(chain="A", seq="1", *, comp="GLU", alt=".", ins="", atoms=None):
    result = dict(auth_chain=chain, auth_seq_id=seq, insertion_code=ins, comp_id=comp, alt_id=alt)
    if atoms is not None:
        result["atom_names"] = atoms
    return result


def atom(atom="OE1", seq="1", *, chain="A", comp="GLU", alt=".", ins="?", model="1", x="0", y="0", z="0", ident="1"):
    return dict(zip(COLS, ["ATOM", ident, atom, comp, chain, seq, alt, ins, x, y, z, ".60", "14.5", model]))


def cif(rows):
    return ("data_1ABC\n_entry.id 1ABC\n_exptl.method 'X-RAY DIFFRACTION'\n"
        "loop_\n_pdbx_audit_revision_history.ordinal\n_pdbx_audit_revision_history.revision_date\n"
        "1 2020-01-02\n2 2021-02-03\n#\nloop_\n" + "\n".join("_atom_site." + col for col in COLS)
        + "\n" + "\n".join(" ".join(row[col] for col in COLS) for row in rows) + "\n#\n").encode()


def xml(rows=None, *, entry="1abc", revision="2", day="2021-02-03"):
    if rows is None:
        rows = [dict(model="1", chain="A", resnum="1", icode=" ", altcode=" ", resname="GLU", rscc=".9", extra="retained"),
                dict(model="1", chain="A", resnum="2", icode=" ", altcode=" ", resname="GLU", rscc=".8")]
    attrs = " ".join(f'{key}="{value}"' for key, value in dict(pdbid=entry,
        **{"PDB-revision-number": revision, "PDB-revision-date": day, "XMLcreationDate": "2025-01-01"}).items())
    members = "".join("<ModelledSubgroup " + " ".join(f'{k}="{v}"' for k, v in row.items()) + "/>" for row in rows)
    return (f'<wwPDB-validation-information xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            f'xsi:noNamespaceSchemaLocation="synthetic.xsd"><Entry {attrs}/>{members}</wwPDB-validation-information>').encode()


def witness():
    quote = "molecule M"
    start = TEXT.encode().index(quote.encode())
    return dict(source_ref=SOURCE, representation="original", start=start, end=start + len(quote.encode()), quote=quote)


def fixture():
    args = dict(source_ref=SOURCE, coordinate_source_ref=COORD, validation_source_ref=REPORT,
        source_kind="synthetic_fixture", model_number=1, literals=dict.fromkeys(LITERAL_FIELDS),
        geometry_panel=[dict(endpoint_a=selector(atoms=["OE1", "OE2"]),
            endpoint_b=selector(seq="2", atoms=["OE1"]), positive_max_A=3.5, incompatible_min_A=4.5)],
        local_panel=[selector(), selector(seq="2")], evaluation_scope=SCOPE)
    args["literals"]["molecule"] = witness()
    rows = [atom(ident="1"), atom("OE2", x="1", ident="2"), atom(seq="2", x="4", ident="3")]
    payloads = {SOURCE: dict(artifact_ref=ART, content=TEXT.encode()),
        COORD: dict(artifact_ref="artifact_coord", content=cif(rows)),
        REPORT: dict(artifact_ref="artifact_report", content=xml())}
    calls = []
    def callback(ref, representation):
        calls.append((ref, representation))
        return payloads[ref]
    return args, payloads, rows, calls, callback


def read(fix):
    return read_structure_inputs(fix[0], read_source=fix[4])


def set_rows(fix):
    fix[1][COORD]["content"] = cif(fix[2])


def test_complete_synthetic_source_bindings_native_rows_and_calculator_contract():
    fix = fixture()
    validate_schema(fix[0], structure_population_schema())
    out = read(fix)
    assert out["version"] == VERSION
    assert set(out) == {"version", "source_ref", "source_kind", "coordinate_source_ref", "validation_source_ref",
        "model_number", "evaluation_scope", "literals", "source_refs", "coordinate_metadata", "validation_metadata",
        "native_geometry", "native_local", "calculation_inputs"}
    assert out["source_refs"] == [SOURCE, COORD, REPORT]
    assert fix[3] == [(ref, "original") for ref in out["source_refs"]]
    assert out["literals"]["molecule"] == dict(value="molecule M", witness={**witness(), "artifact_ref": ART})
    assert out["coordinate_metadata"]["revision_number"] == 2
    assert out["coordinate_metadata"]["revision_date"] == "2021-02-03"
    assert out["coordinate_metadata"]["method"] == ["X-RAY DIFFRACTION"]
    assert out["validation_metadata"]["creation_date"] == "2025-01-01"
    assert out["validation_metadata"]["schema_location"] == "synthetic.xsd"
    assert out["calculation_inputs"] == dict(geometry_members=[dict(endpoint_a=[[0., 0., 0.], [1., 0., 0.]],
        endpoint_b=[[4., 0., 0.]], positive_max_A=3.5, incompatible_min_A=4.5, unavailable_reason=None)],
        local_members=[dict(rscc=.9, unavailable_reason=None), dict(rscc=.8, unavailable_reason=None)],
        validation_binding="matching_entry_revision", origin="synthetic", evaluation_scope=SCOPE)
    native = out["native_geometry"][0]["endpoint_a"]["selected_atom_rows"][0]
    assert native["raw_attributes"] == fix[2][0]
    assert native["occupancy_parameter"] == .6
    assert native["B_iso_or_equiv_A2"] == 14.5
    assert native["source_ref"] == COORD and native["artifact_ref"] == "artifact_coord"
    assert out["native_local"][0]["validation_rows"][0]["raw_attributes"]["extra"] == "retained"
    assert not any("population" in key for key in native)
    fix[0]["geometry_panel"][0]["endpoint_a"]["atom_names"].append("FAKE")
    assert out["native_geometry"][0]["endpoint_a"]["selector"]["atom_names"] == ["OE1", "OE2"]


def test_no_validation_and_empty_panels_preserve_scientific_unknowns():
    fix = fixture()
    fix[0]["validation_source_ref"] = None
    out = read(fix)
    assert out["validation_metadata"] is None
    assert out["calculation_inputs"]["validation_binding"] == "not_supplied"
    assert out["calculation_inputs"]["local_members"] == [dict(rscc=None, unavailable_reason="local_rscc_unreported")] * 2
    fix[0]["geometry_panel"] = []
    fix[0]["local_panel"] = []
    out = read(fix)
    assert out["native_geometry"] == out["native_local"] == []
    assert out["calculation_inputs"]["geometry_members"] == out["calculation_inputs"]["local_members"] == []


@pytest.mark.parametrize("changes,binding", [
    ({"entry": "2xyz"}, "entry_mismatch"), ({"revision": "3"}, "revision_mismatch"),
    ({"day": "2021-02-04"}, "revision_mismatch"), ({"revision": "?"}, "binding_unreported")])
def test_metadata_join_preserves_native_geometry_and_rscc_without_cryptographic_claim(changes, binding):
    fix = fixture()
    fix[1][REPORT]["content"] = xml(**changes)
    out = read(fix)
    assert out["calculation_inputs"]["validation_binding"] == binding
    assert out["native_local"][0]["rscc"] == .9
    assert out["calculation_inputs"]["geometry_members"][0]["endpoint_a"] is not None
    assert not any("digest" in key for key in out["validation_metadata"])


@pytest.mark.parametrize("field,value,reason", [("auth_comp_id", "ASP", "endpoint_identity_mismatch"),
    ("label_alt_id", "A", "endpoint_identity_mismatch"), ("auth_asym_id", "B", "endpoint_unmodeled"),
    ("pdbx_PDB_ins_code", "A", "endpoint_unmodeled"), ("Cartn_x", "?", "coordinate_unreported"),
    ("Cartn_y", ".", "coordinate_unreported")])
def test_strict_endpoint_identity_and_missing_coordinate_leave_group_unavailable(field, value, reason):
    fix = fixture()
    for row in fix[2][:2]:
        row[field] = value
    set_rows(fix)
    out = read(fix)
    member = out["calculation_inputs"]["geometry_members"][0]
    assert member["endpoint_a"] is None and member["unavailable_reason"] == reason
    assert member["endpoint_b"] == [[4., 0., 0.]]


def test_one_missing_atom_preserves_other_selected_rows_without_partial_group_distance():
    fix = fixture()
    fix[2].pop(1)
    set_rows(fix)
    out = read(fix)
    endpoint = out["native_geometry"][0]["endpoint_a"]
    assert len(endpoint["selected_atom_rows"]) == 1
    assert endpoint["coordinates_A"] is None
    assert endpoint["unavailable_reason"] == "endpoint_unmodeled"


def test_ambiguous_selected_atom_never_chooses_highest_occupancy():
    fix = fixture()
    other = deepcopy(fix[2][0])
    other.update(id="4", occupancy=".99", Cartn_x="100")
    fix[2].append(other)
    set_rows(fix)
    out = read(fix)
    endpoint = out["native_geometry"][0]["endpoint_a"]
    assert endpoint["unavailable_reason"] == "ambiguous_atom_selection"
    assert len(endpoint["selected_atom_rows"]) == 3
    assert endpoint["coordinates_A"] is None


def test_selected_model_alt_insertion_and_author_atom_are_exact():
    fix = fixture()
    fix[2].extend([atom(alt="B", ins="Q", model="2", x="20", ident="4"),
                   atom("OE2", alt="B", ins="Q", model="2", x="21", ident="5"),
                   atom(seq="2", model="2", x="24", ident="6")])
    fix[0]["model_number"] = 2
    fix[0]["geometry_panel"][0]["endpoint_a"].update(alt_id="B", insertion_code="Q")
    fix[0]["local_panel"] = [selector(alt="B", ins="Q")]
    set_rows(fix)
    fix[1][REPORT]["content"] = xml([dict(model="2", chain="A", resnum="1", icode="Q", altcode="B", resname="GLU", rscc="-.2")])
    out = read(fix)
    assert out["calculation_inputs"]["geometry_members"][0]["endpoint_a"] == [[20., 0., 0.], [21., 0., 0.]]
    assert out["calculation_inputs"]["local_members"] == [dict(rscc=-.2, unavailable_reason=None)]


@pytest.mark.parametrize("rows,reason", [([], "local_rscc_unreported"),
    ([dict(model="1", chain="A", resnum="1", icode=" ", altcode=" ", resname="GLU")], "local_rscc_unreported"),
    ([dict(model="1", chain="A", resnum="1", icode=" ", altcode=" ", resname="ASP", rscc=".9")], "local_identity_mismatch"),
    ([dict(model="1", chain="A", resnum="1", icode=" ", altcode=" ", resname="GLU", rscc=".9")] * 2, "ambiguous_local_selection")])
def test_absent_wrong_identity_or_duplicate_validation_stays_unknown(rows, reason):
    fix = fixture()
    fix[1][REPORT]["content"] = xml(rows)
    local = read(fix)["native_local"][0]
    assert local["rscc"] is None and local["unavailable_reason"] == reason
    assert len(local["validation_rows"]) == len(rows)


@pytest.mark.parametrize("kind", ["same", "reversed", "atom_order", "cutoff_renaming"])
def test_duplicate_physical_geometry_invalid_even_when_order_or_cutoff_changes(kind):
    fix = fixture()
    duplicate = deepcopy(fix[0]["geometry_panel"][0])
    if kind == "reversed":
        duplicate["endpoint_a"], duplicate["endpoint_b"] = duplicate["endpoint_b"], duplicate["endpoint_a"]
    if kind == "atom_order":
        duplicate["endpoint_a"]["atom_names"].reverse()
    if kind == "cutoff_renaming":
        duplicate["positive_max_A"] = 3
    fix[0]["geometry_panel"].append(duplicate)
    with pytest.raises(ExperimentalContractError, match="duplicate_geometry_selection"):
        read(fix)
    assert fix[3] == []


def test_duplicate_local_residue_and_duplicate_atom_names_rejected_before_source_read():
    fix = fixture()
    fix[0]["local_panel"].append(deepcopy(fix[0]["local_panel"][0]))
    with pytest.raises(ExperimentalContractError, match="duplicate_local_selection"):
        read(fix)
    fix = fixture()
    fix[0]["geometry_panel"][0]["endpoint_a"]["atom_names"] = ["OE1", "OE1"]
    with pytest.raises(ExperimentalContractError, match="duplicate_atom_selection"):
        read(fix)
    assert fix[3] == []


@pytest.mark.parametrize("bad", [True, False, 0, -1, 1., "1"])
def test_model_is_positive_integer_never_bool(bad):
    fix = fixture()
    fix[0]["model_number"] = bad
    with pytest.raises(ExperimentalContractError, match="positive_integer_model_required"):
        read(fix)


@pytest.mark.parametrize("positive,incompatible", [(True, 4), (float("nan"), 4), (0, float("inf")), (-1, 4), (4, 4), (5, 4)])
def test_proposed_cutoffs_finite_disjoint_not_point_measurements(positive, incompatible):
    fix = fixture()
    fix[0]["geometry_panel"][0].update(positive_max_A=positive, incompatible_min_A=incompatible)
    with pytest.raises(ExperimentalContractError):
        read(fix)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999", "1e-999", "-1e-999", "0.1 Angstrom"])
def test_coordinates_reject_nonfinite_lexical_underflow_or_units(token):
    fix = fixture()
    fix[2][0]["Cartn_x"] = token
    set_rows(fix)
    with pytest.raises(ExperimentalContractError):
        read(fix)


@pytest.mark.parametrize("token", ["1.01", "-1.01", "NaN", "Infinity", "1e-999", "-1e-999"])
def test_native_rscc_rejects_nonfinite_out_of_native_range_or_lexical_underflow(token):
    fix = fixture()
    fix[1][REPORT]["content"] = xml([dict(model="1", chain="A", resnum="1", icode=" ", altcode=" ", resname="GLU", rscc=token)])
    with pytest.raises(ExperimentalContractError):
        read(fix)


@pytest.mark.parametrize("token", ["-1", "1", "0", "5e-324", ".", "?"])
def test_native_rscc_endpoints_zero_subnormal_and_missing_preserved(token):
    fix = fixture()
    fix[1][REPORT]["content"] = xml([dict(model="1", chain="A", resnum="1", icode=" ", altcode=" ", resname="GLU", rscc=token)])
    out = read(fix)["native_local"][0]
    assert out["rscc"] == (None if token in (".", "?") else float(token))


@pytest.mark.parametrize("raw", [b"", b"garbage", b"data_x\n_entry.id", b"data_x\n_entry.id 1abc\n_entry.id 1abc",
    b"data_x\nloop_\n_a.x\n_a.y\n1 2 3", b"data_x\nloop_\n_a.x\n", b"data_x\n_a.x 'unclosed",
    b"data_x\n_a.x\n;unclosed", b"data_x\n_a.x 1\ndata_y\n_a.y 2", b"\xff"])
def test_malformed_structure_syntax_never_passes_permissive_parser_silently(raw):
    fix = fixture()
    fix[1][COORD]["content"] = raw
    with pytest.raises(ExperimentalContractError):
        read(fix)


@pytest.mark.parametrize("mutation", [lambda text: text.replace("0 0 0 .60 14.5 1", "0 0 .60 14.5 1", 1),
    lambda text: text.replace("_atom_site.Cartn_x", "_atom_site.bad_x"),
    lambda text: text.replace("_entry.id 1ABC", "_entry.id nonsense"),
    lambda text: text.replace("1 2020-01-02", "1 2020-99-02"),
    lambda text: text.replace("2 2021-02-03", "1 2021-02-03")])
def test_bad_columns_entry_or_revision_rejected(mutation):
    fix = fixture()
    fix[1][COORD]["content"] = mutation(fix[1][COORD]["content"].decode()).encode()
    with pytest.raises(ExperimentalContractError):
        read(fix)


@pytest.mark.parametrize("raw", [b'<!DOCTYPE x><wwPDB-validation-information><Entry/></wwPDB-validation-information>',
    b'<!DOCTYPE x [<!ENTITY a "bad">]><wwPDB-validation-information><Entry/></wwPDB-validation-information>',
    b'<wrong><Entry/></wrong>', b'<wwPDB-validation-information/>',
    b'<wwPDB-validation-information><Entry/><Entry/></wwPDB-validation-information>', b'<unclosed>', b'\xff'])
def test_xml_forbids_doctype_entity_bad_root_multiple_entry_and_bad_syntax(raw):
    fix = fixture()
    fix[1][REPORT]["content"] = raw
    with pytest.raises(ExperimentalContractError):
        read(fix)


@pytest.mark.parametrize("mutation", [{"start": True}, {"start": -1}, {"end": 99999},
    {"quote": "invented"}, {"representation": "bad"}, {"extra": "field"}])
def test_literal_witness_exact_byte_custody(mutation):
    fix = fixture()
    fix[0]["literals"]["molecule"].update(mutation)
    with pytest.raises(ExperimentalContractError):
        read(fix)


def test_schema_and_runtime_closed_fields_disallow_llm_point_operands_and_other_scope():
    fix = fixture()
    schema = structure_population_schema()
    schema["properties"]["source_kind"]["enum"].append("bad")
    assert "bad" not in structure_population_schema()["properties"]["source_kind"]["enum"]
    for extra in ({"coordinates": [[0, 0, 0]]}, {"rscc": .9}, {"origin": "reported"}):
        with pytest.raises(ContractError):
            validate_schema({**fix[0], **extra}, structure_population_schema())
        with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
            read_structure_inputs({**fix[0], **extra}, read_source=fix[4])
    fix[0]["evaluation_scope"] = "unconditional_population"
    with pytest.raises(ExperimentalContractError, match="unsupported_evaluation_scope"):
        read(fix)
    assert fix[3] == []


@pytest.mark.parametrize("result", [{"artifact_ref": ART, "content": "not bytes"},
    {"artifact_ref": "", "content": b""}, {"artifact_ref": ART, "content": b"", "extra": 1}])
def test_callback_requires_closed_byte_custody(result):
    with pytest.raises(ExperimentalContractError):
        read_structure_inputs(fixture()[0], read_source=lambda *_: result)


def test_authority_callback_failure_propagates_without_reacquisition():
    fix = fixture()
    def callback(ref, representation):
        if ref == COORD:
            raise PermissionError("not received")
        return fix[4](ref, representation)
    with pytest.raises(PermissionError, match="not received"):
        read_structure_inputs(fix[0], read_source=callback)
    assert fix[3] == [(SOURCE, "original")]


@pytest.mark.parametrize("literal", ["_category.name", "data_literal", "save_literal", "loop_", "stop_", "global_", "_", ""])
@pytest.mark.parametrize("quote", ["'", '"'])
def test_valid_quoted_scalar_and_first_loop_column_preserve_literal_syntax(literal, quote):
    fix = fixture()
    extra = (f"_synthetic.scalar {quote}{literal}{quote}\nloop_\n_synthetic.name\n_synthetic.value\n"
             f"{quote}{literal}{quote} 3\n")
    fix[1][COORD]["content"] += extra.encode()
    assert read(fix)["calculation_inputs"]["validation_binding"] == "matching_entry_revision"


@pytest.mark.parametrize("literal", ["_category.name", "data_literal", "loop_", "save_literal"])
def test_valid_semicolon_scalar_and_loop_literals_preserve_syntax(literal):
    fix = fixture()
    fix[1][COORD]["content"] += ("_synthetic.scalar\n;" + literal + "\n;\n"
        "loop_\n_synthetic.name\n_synthetic.value\n;" + literal + "\n;\n3\n").encode()
    assert read(fix)["calculation_inputs"]["validation_binding"] == "matching_entry_revision"


def test_selector_schema_uses_only_semantic_scientific_token_formats():
    schema = structure_population_schema()["properties"]
    endpoint = schema["geometry_panel"]["items"]["properties"]["endpoint_a"]["properties"]
    local = schema["local_panel"]["items"]["properties"]
    for node in (endpoint, local):
        for field in ("auth_chain", "comp_id", "alt_id"):
            assert node[field] == {"type": "string", "format": "structure_identifier"}
        assert node["auth_seq_id"] == {"type": "string", "format": "structure_residue_number"}
        assert node["insertion_code"] == {"type": "string", "format": "structure_insertion_code"}
    assert endpoint["atom_names"]["items"] == {"type": "string", "format": "structure_identifier"}


@pytest.mark.parametrize("field", ["auth_chain", "comp_id", "alt_id", "insertion_code", "atom_names"])
@pytest.mark.parametrize("token", ["bad token", "bad\ttoken", "bad\ntoken", " bad", "bad ", "é", "Aµ", "\x00", "\x7f"])
def test_synthetic_selector_rejects_non_ascii_whitespace_and_control_tokens(field, token):
    fix = fixture()
    endpoint = fix[0]["geometry_panel"][0]["endpoint_a"]
    endpoint[field] = [token] if field == "atom_names" else token
    with pytest.raises(ExperimentalContractError):
        read(fix)
    assert fix[3] == []


@pytest.mark.parametrize("token", ["1.0", "+1", "1e2", "1 2", "- 1", "−1", "１", "é", "", ".", "?", " 1", "1\n"])
def test_synthetic_selector_residue_number_must_be_complete_signed_decimal_integer(token):
    fix = fixture()
    fix[0]["local_panel"][0]["auth_seq_id"] = token
    with pytest.raises(ExperimentalContractError):
        read(fix)
    assert fix[3] == []


@pytest.mark.parametrize("token", ["0", "-1", "001", "-0002", "12345678901234567890"])
def test_synthetic_selector_preserves_complete_integer_residue_identifier(token):
    fix = fixture()
    fix[0]["local_panel"][0]["auth_seq_id"] = token
    out = read(fix)
    assert out["native_local"][0]["selector"]["auth_seq_id"] == token
    assert out["native_local"][0]["rscc"] is None
