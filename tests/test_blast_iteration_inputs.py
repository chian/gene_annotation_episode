"""Synthetic iteration contracts; no native PSI/DELTA search is performed."""
from copy import deepcopy
import hashlib
import io
import json
import zipfile

import pytest

from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet as populate
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm
from tests.test_blast_sequence_database import inputs as sequence_inputs, operand, hsp, invocation
from tests.test_blast_profile_inputs import model_record, synthetic_hit, provenance as profile_provenance


def provenance(pointer="/source"):
    return {"source_ref": "synthetic:retained-producer-record", "pointer": pointer}


def digest(name):
    return hashlib.sha256(name.encode()).hexdigest()


def make_inputs(hit_sets=None, *, labels=None, stages=None, program="psiblast", archive=False,
                query=None, query_kind="sequence", raw_searches=None, params=None, completion=None):
    hit_sets = [["A", "B"], ["A", "B"]] if hit_sets is None else hit_sets
    labels = list(range(1, len(hit_sets) + 1)) if labels is None else labels
    stages = ["sequence_database"] * len(hit_sets) if stages is None else stages
    query = operand() if query is None else query
    full = query["length"]
    length = query["selected_interval"][1] - query["selected_interval"][0] if query["selected_interval"] else full
    searches = []
    for names, label, stage in zip(hit_sets, labels, stages):
        hits = []
        for i, name in enumerate(names):
            if stage == "domain_database":
                hits.append(synthetic_hit(int(name[1:])))
            else:
                hits.append(dict(num=i+1, len=10, description=[dict(id=name, accession=name+".1", title="synthetic "+name, taxid=1)],
                                 hsps=[hsp(40 if name == "A" else 39)]))
        searches.append(dict(iter_num=label, search=dict(query_id="q", query_title="q", query_len=length, hits=hits)))
    if raw_searches is not None:
        searches = [dict(iter_num=n, search=s) for n, s in zip(labels, raw_searches)]
    doc = {"BlastOutput2": [{"report": dict(program=program, version=program.upper()+" 2.17.0+",
        search_target={"db": "synthetic_db"}, params={"include": .002} if params is None else params,
        results={"iterations": searches})}]}
    raw = json.dumps(doc).encode()
    descriptor = dict(artifact_key="synthetic-report", role="primary_report", format="json15", fields=None, delimiter=None)
    if archive:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as output:
            output.writestr("one.json", raw)
            output.writestr("two.json", raw + b"\n")
        raw = buffer.getvalue()
        descriptor["format"] = "json2_archive"
    inv = invocation(program, query_kind, query, effective_options={"requested_hit_limit": 9,
        "requested_hsp_limit": 8, "inclusion_ethresh": .002, "domain_inclusion_ethresh": .05})
    if completion is not None:
        inv["completion"] = completion
    collection = parse_blast_report_collection({"synthetic-report": raw}, artifacts=[descriptor], invocation=inv)
    return from_collection(collection, stages=stages * (2 if archive else 1))


def from_collection(collection, stages=None):
    result = dict(collection=collection, report_sources=[], query_bindings=[], search_bindings=[], pssm_sheets=[],
        checkpoint_bindings=[], sequence_metadata=[], profile_metadata=[], comparison_pairs=[], inclusion_records=[],
        convergence_records=[], invocation_source=provenance("/effective_options"), target_context=None)
    stages = ["sequence_database"] * len(collection["searches"]) if stages is None else stages
    for i, (search, stage) in enumerate(zip(collection["searches"], stages)):
        args, key = sequence_inputs(search), search["search_key"]
        args["search_binding"]["stage"] = stage
        args["search_binding"]["biological_round"] = i + 1
        result["report_sources"].append(dict(search_key=deepcopy(key), report_source=args["report_source"]))
        result["query_bindings"].append(dict(search_key=deepcopy(key), query_binding=args["query_binding"]))
        result["search_bindings"].append(args["search_binding"])
        seq = dict(search_key=deepcopy(key), **{name: args[name] for name in
            ("reference_metadata", "description_bindings", "sequence_identity_bindings", "database_profile")})
        seq["database_profile"] = None
        for hit, link in zip(search["normalized"]["hits"], seq["sequence_identity_bindings"]):
            name = hit["descriptions"][0]["id"] if hit["descriptions"] else str(hit["hit_index"])
            value = digest(name)
            link["binding"].update(digest=value, sequence_group="sha256:"+value)
        result["sequence_metadata"].append(seq)
        if stage == "domain_database":
            records, links = [], []
            for hit, mapping in zip(search["normalized"]["hits"], search["row_map"]):
                if not hit["descriptions"]:
                    continue
                description = hit["descriptions"][0]
                n = int(description["accession"][2:7])
                record = model_record(n, "deltablast")
                if record not in records:
                    records.append(record)
                links.append(dict(search_key=deepcopy(key), hit_ordinal=hit["hit_index"], description_ordinal=mapping["description_ordinals"][0],
                    profile_key=record["profile_key"], native_description={f: description.get(f) for f in ("id", "accession", "title", "taxid")},
                    provenance=profile_provenance()))
            if records:
                args["search_binding"]["database_identity"] = deepcopy(records[0]["database_identity"])
            result["profile_metadata"].append(dict(search_key=deepcopy(key), profile_records=records, profile_bindings=links,
                function_bindings=[], model_relations=[]))
    return result


def add_pair(arguments, earlier=0, later=1, basis="full_sequence_digest", key="comparison"):
    arguments["comparison_pairs"].append(dict(comparison_key=key,
        earlier_search_key=deepcopy(arguments["collection"]["searches"][earlier]["search_key"]),
        later_search_key=deepcopy(arguments["collection"]["searches"][later]["search_key"]),
        identity_basis=basis, relation_source=provenance("/explicit_same_axis_and_order")))


def add_pssm(arguments, *, key="checkpoint", length=12, sequence=None, role="after_search", search_index=0):
    sequence = sequence or "A" * length
    text = ('PssmWithParameters ::= { pssm { numRows 2, numColumns '+str(length)+', rowLabels { "A", "C" }, '
            'query seq { inst { repr raw, mol aa, length '+str(length)+', seq-data ncbieaa "'+sequence+'" } }, '
            'finalData { scores { '+', '.join(str(i-2) for i in range(2*length))+' }, '
            'lambda { 3, 10, -1 }, kappa { 4, 10, -2 }, h 1 } } }')
    pssm = read_blast_pssm(text.encode(), format="scoremat_asn_text", artifact_key=key, source_ref="synthetic:checkpoint")
    arguments["pssm_sheets"].append(pssm)
    pkey = pssm["pssms"][0]["pssm_key"]
    if role is not None:
        search_key = deepcopy(arguments["collection"]["searches"][search_index]["search_key"]) if role != "output" else None
        arguments["checkpoint_bindings"].append(dict(pssm_key=pkey, role=role, search_key=search_key,
            biological_round=search_index+1 if search_key else None, provenance=provenance("/checkpoint_relation")))
    return pkey


def evidence(original=None):
    return dict(origin="supplied_source_record", source=provenance("/observation"), source_format="synthetic_contract_record_v1",
                original_record={"synthetic_supplied_record": True} if original is None else original, extractor=None)


def add_members(arguments, pkey, names=("A", "B", "B"), *, record_key="membership", complete=True, search_index=0):
    arguments["inclusion_records"].append(dict(record_key=record_key, pssm_key=pkey,
        search_key=deepcopy(arguments["collection"]["searches"][search_index]["search_key"]) if search_index is not None else None,
        membership_kind="checkpoint_sequence_members", query_membership="unknown", complete=complete,
        members=[dict(identity=dict(namespace="native_member", value=name, version=None), provenance=provenance(f"/members/{i}")) for i, name in enumerate(names)],
        evidence=evidence({"checkpoint": pkey, "members": list(names), "complete": complete})))


def add_convergence(arguments, value=True, *, key="convergence", search_index=0, query_only=False):
    arguments["convergence_records"].append(dict(record_key=key,
        search_key=None if query_only else deepcopy(arguments["collection"]["searches"][search_index]["search_key"]),
        query_operand=deepcopy(arguments["collection"]["invocation"]["operands"][0]), native_converged=value,
        evidence=evidence({"actual_explicit_state_in_synthetic_record": value})))


def test_population_exact_fields_complete_native_objects_and_detachment():
    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey)
    add_convergence(args)
    add_pair(args)
    original = deepcopy(args)
    sheet = populate(**args)
    assert set(sheet) == set(args) | {"schema"}
    assert {k: sheet[k] for k in args} == original
    args["collection"]["searches"][0]["native"]["search"]["hits"][0]["hsps"][0]["bit_score"] = -1
    assert sheet["collection"] == original["collection"]
    assert json.loads(json.dumps(sheet, allow_nan=False)) == sheet


@pytest.mark.parametrize("name", ["report_sources", "query_bindings", "search_bindings", "sequence_metadata", "profile_metadata"])
def test_duplicate_outer_associations_are_preserved_for_local_qualification(name):
    args = make_inputs(program="deltablast", hit_sets=[["P1"]], stages=["domain_database"], query=operand(length=100, selected_interval=None))
    args[name].append(deepcopy(args[name][0]))
    assert len(populate(**args)[name]) == 2


@pytest.mark.parametrize("mutation,code", [
    (lambda a: a["search_bindings"][0].update(extra=True), "input_fields_invalid"),
    (lambda a: a["query_bindings"][0]["query_binding"].update(full_length=True), "input_type_invalid"),
    (lambda a: a["collection"].update(extra=True), "collection_schema_invalid"),
    (lambda a: a["collection"]["searches"].append(deepcopy(a["collection"]["searches"][0])), "collection_search_key_duplicate"),
    (lambda a: a["collection"]["invocation"].update(execution_program="blastp"), "program_or_mode_unsupported"),
    (lambda a: a["collection"]["invocation"]["effective_options"].update(extra=float("nan")), "finite_json_required"),
    (lambda a: a["sequence_metadata"][0]["description_bindings"][0].update(extra=1), "input_fields_invalid"),
])
def test_closed_outer_shapes_errors_have_fixed_codes(mutation, code):
    args = make_inputs()
    mutation(args)
    with pytest.raises(ValueError) as raised:
        populate(**args)
    assert raised.value.args[0] == "blast_iteration_" + code
    if code.startswith("input_"):
        assert raised.value.args[1].startswith("/")


def test_duplicate_comparison_and_observation_names_are_structural_errors():
    args = make_inputs()
    add_pair(args)
    args["comparison_pairs"].append(deepcopy(args["comparison_pairs"][0]))
    with pytest.raises(ValueError, match="comparison_key_duplicate"):
        populate(**args)
    args["comparison_pairs"] = []
    add_convergence(args)
    args["convergence_records"].append(deepcopy(args["convergence_records"][0]))
    with pytest.raises(ValueError, match="observation_record_key_duplicate"):
        populate(**args)


def test_native_membership_is_a_typed_supplied_port_not_a_returned_hits_parser():
    args = make_inputs()
    pkey = add_pssm(args)
    add_members(args, pkey)
    args["inclusion_records"][0]["members"] = deepcopy(args["collection"]["searches"][0]["native"]["search"]["hits"])
    with pytest.raises(ValueError, match="input_fields_invalid"):
        populate(**args)
    args = make_inputs()
    add_convergence(args)
    args["convergence_records"][0]["evidence"].update(origin="native_extractor_output")
    with pytest.raises(ValueError, match="input_fields_invalid"):
        populate(**args)
