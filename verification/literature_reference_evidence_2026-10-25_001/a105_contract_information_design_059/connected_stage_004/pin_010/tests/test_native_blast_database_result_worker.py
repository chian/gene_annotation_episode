"""Independent R numerical oracles; synthetic native-format inputs, no BLAST."""
from copy import deepcopy
import builtins
import hashlib
import json
import os
import shutil
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from gene_annotation_episode import native_blast_database_result_worker as worker
from gene_annotation_episode import native_blast_database_result_views as views
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
from gene_annotation_episode.blast_profile_inputs import populate_blast_profile_sheet
from gene_annotation_episode.blast_vdb_inputs import populate_blast_vdb_sheet
from tests import test_blast_iteration_inputs as iteration
from tests import test_blast_profile_inputs as profile
from tests import test_blast_vdb_inputs as vdb
from tests import test_blast_vdb_calculators as vdb_calc
from tests import test_blast_pssm_calculators as pssm
from tests import test_blast_sequence_database as sequence
from tests import test_blast_iteration_calculators as iteration_calc

CALCULATION_ID = "a" * 64
ATTEMPT = dict(run_id="synthetic:318", episode_id="synthetic:child", resource_id="synthetic:hpc", operation_key="synthetic:operation",
    attempt_id="b" * 64, assignment_sha256="c" * 64, requested_job_sha256="d" * 64, submission_token="e" * 64, execution_id="synthetic:job")


def sheet_set(collection, *, iteration_sheet=None, profile_sheet=None, vdb_sheet=None, pssm_sheets=()):
    return dict(schema="native_blast_database_sheet_set_v1", collection=deepcopy(collection),
        prepared_inputs={"metadata": []}, derived_search_bindings=[], sequence=[],
        profile=[] if profile_sheet is None else [dict(search_key=deepcopy(profile_sheet["search"]["search_key"]), sheet=profile_sheet)],
        vdb=[] if vdb_sheet is None else [dict(search_key=deepcopy(vdb_sheet["search"]["search_key"]), sheet=vdb_sheet)],
        pssm=list(pssm_sheets), msa=[], iteration=iteration_sheet,
        metadata_parse_results=[], metadata_binding_results=[], issues=[])


def collection_for(search):
    ctx = search["program_context"]
    inv = dict(execution_program=ctx["execution_program"], scientific_mode="database", resource_kind="hpc",
        query_kind=ctx["query_kind"], reference_kind=ctx["reference_kind"], request={"synthetic": True},
        effective_options={}, operands=[deepcopy(search["operand_binding"])] if search["operand_binding"] else [],
        completion={"native_returncode": 0, "producer_complete": True})
    key = search["search_key"]["artifact_key"]
    return parse_blast_report_collection({key: json.dumps(search["normalized"]["native"]["document"]).encode()},
        artifacts=[dict(artifact_key=key, role="primary_report", format="json15", fields=None, delimiter=None)], invocation=inv)


def calculate_rows(sheets, model=None, calculation_id=CALCULATION_ID):
    components = worker.calculate_native_blast_database_sheets(sheets, sequence_model=model)
    rows = worker.build_native_blast_database_rows(bundle_identity=ATTEMPT,
        calculation_id=calculation_id, sheet_set=sheets, calculations=components)
    return components, rows


def metric(row, name):
    return next(c for c in row["measurements"] if c["name"] == name)


def family(rows, name):
    return [r for r in rows if r["family"] == name]


def psi_sheets(**kwargs):
    args = iteration.make_inputs(**kwargs)
    return sheet_set(args["collection"], iteration_sheet=populate_blast_iteration_sheet(**args))


def profile_sheets(program="rpsblast", **kwargs):
    args = profile.make_inputs(program, **kwargs)
    collection = collection_for(args["search"])
    args["search"] = collection["searches"][0]
    return sheet_set(collection, profile_sheet=populate_blast_profile_sheet(**args))


def vdb_sheets(values=None):
    values = vdb.inputs() if values is None else values
    collection = collection_for(values["search"])
    values["search"] = collection["searches"][0]
    return sheet_set(collection, vdb_sheet=populate_blast_vdb_sheet(**values))


def test_psi_dispatch_once_nested_full_selected_and_native_axes(monkeypatch):
    sheets = psi_sheets(hit_sets=[["A"]])
    calls = []
    original = worker._iteration.calculate_blast_iteration_components
    def observe(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(worker._iteration, "calculate_blast_iteration_components", observe)
    before = deepcopy(sheets)
    components, rows = calculate_rows(sheets)
    assert calls == [1] and sheets == before
    assert components["profile"] == components["vdb"] == components["pssm"] == []
    raw = family(rows, "hsp")[0]
    hit = family(rows, "sequence_hit")[0]
    assert metric(raw, "paired_query_units")["value"] == 4
    assert metric(raw, "reported_query_coverage")["value"] == .5
    assert metric(raw, "reported_query_length")["value"] == 8
    assert metric(hit, "query_paired_coverage")["value"] == 4 / 12
    assert metric(hit, "query_paired_coverage")["denominator"] == 12
    assert metric(hit, "selected_query_coverage")["value"] == .5
    assert components["iteration"]["searches"][0]["sequence_components"] is not None


@pytest.mark.parametrize("program", ["rpsblast", "rpstblastn"])
def test_standalone_profile_dispatch_and_model_coverage(program, monkeypatch):
    sheets = profile_sheets(program)
    calls = []
    original = worker._profile.calculate_blast_profile_components
    monkeypatch.setattr(worker._profile, "calculate_blast_profile_components", lambda s: (calls.append(1), original(s))[1])
    monkeypatch.setattr(worker._iteration, "calculate_blast_iteration_components", lambda *a, **k: pytest.fail("unexpected iteration"))
    components, rows = calculate_rows(sheets)
    assert calls == [1] and components["iteration"] is None
    model = family(rows, "profile_model")[0]
    assert metric(model, "paired_model_positions")["value"] == 50
    assert metric(model, "model_coverage")["value"] == .5
    assert metric(model, "paired_query_units")["value"] == (150 if program == "rpstblastn" else 50)
    hsp = family(rows, "profile_hsp_model")[0]
    assert metric(hsp, "specific_bits_margin")["value"] == 2
    assert metric(hsp, "reporting_bits_margin")["value"] == 7
    assert metric(family(rows, "hsp")[0], "paired_reference_units")["unit"] == "model_position"
    assert not family(rows, "sequence_function")


def test_pssm_all_cells_position_statistics_and_independent_arrays():
    args = iteration.make_inputs(hit_sets=[["A"]])
    args["pssm_sheets"].append(pssm.read(pssm.model(data='''finalData { scores { -2, 0, 5, 7, -32768, 9 }, lambda { 3, 10, -1 }, kappa { 4, 10, -2 }, h 1 },
        intermediateData { freqRatios { 0, 1, 2, 3, 4 }, sigma { 1, 2, 3 } }''')))
    sheets = sheet_set(args["collection"], iteration_sheet=populate_blast_iteration_sheet(**args))
    components, rows = calculate_rows(sheets)
    assert len(family(rows, "pssm_cell")) == 6 and len(family(rows, "pssm_position")) == 3
    assert [metric(r, "scores")["value"] for r in family(rows, "pssm_cell")] == [-2, 0, 5, 7, -32768, 9]
    assert all(metric(r, "freqRatios")["value"] is None for r in family(rows, "pssm_cell"))
    assert [metric(r, "sigma")["value"] for r in family(rows, "pssm_position")] == [1, 2, 3]
    assert metric(family(rows, "pssm_matrix")[0], "lambda")["value"] == .3
    assert components["iteration"]["pssms"]


def test_iteration_query_convergence_and_explicit_set_comparison():
    args = iteration.make_inputs(hit_sets=[["A", "B"], ["B", "C"]])
    iteration.add_pair(args)
    pkey = iteration.add_pssm(args)
    iteration.add_members(args, pkey, names=("A", "B", "B"))
    iteration.add_convergence(args, query_only=True)
    _, rows = calculate_rows(sheet_set(args["collection"], iteration_sheet=populate_blast_iteration_sheet(**args)))
    convergence = family(rows, "iteration_convergence")[0]
    assert convergence["identity"]["scope"] == "query" and convergence["identity"]["search_key"] is None
    assert convergence["booleans"][0]["value"] is True
    assert all(next(c for c in r["booleans"] if c["name"] == "native_converged")["value"] is None for r in family(rows, "search"))
    compared = family(rows, "iteration_comparison")[0]
    assert [metric(compared, n)["value"] for n in ("added_count", "removed_count", "retained_count")] == [1, 1, 1]
    inclusion = family(rows, "iteration_inclusion")[0]
    assert [metric(inclusion, n)["value"] for n in ("member_record_count", "duplicate_member_count", "included_sequence_count")] == [3, 1, 2]


def test_vdb_distinct_reads_groups_samples_and_preserved_codon_maps():
    components, rows = calculate_rows(vdb_sheets())
    membership = family(rows, "vdb_membership")[0]
    assert [metric(membership, n)["value"] for n in ("origin_read_count", "demonstrated_group_count", "observed_origin_sample_count")] == [2, 1, 2]
    assert len(family(rows, "vdb_subject")) == 2 and len(family(rows, "vdb_sample")) == 2
    assert not family(rows, "sequence_function")
    components, rows = calculate_rows(vdb_sheets(vdb_calc.translated_case(reverse=True)))
    native = components["vdb"][0]["components"]
    codons = native["feature_components"][0]["translation_map"]["codons"]
    assert [c["member_positions"] for c in codons] == [[8, 7, 6], [5, 4, 3], [2, 1, 0]]
    assert [c["oriented_triplet"] for c in codons] == ["ATG", "GCT", "AAA"]
    feature = family(rows, "vdb_feature")[0]
    assert metric(feature, "feature_paired_residue_coverage")["value"] == 1
    assert metric(family(rows, "vdb_feature_hsp")[0], "identical_query_feature_residues")["value"] == 3


def test_invalid_original_hsp_slots_and_sibling_scores_retained():
    args = iteration.make_inputs(hit_sets=[["A"]], raw_searches=[dict(query_id="q", query_title="q", query_len=8,
        hits=[dict(len=10, description=[dict(id="A", accession="A.1", title="synthetic A", taxid=1)], hsps=[None, iteration.hsp(40)])])])
    sheets = sheet_set(args["collection"], iteration_sheet=populate_blast_iteration_sheet(**args))
    components, rows = calculate_rows(sheets)
    native = family(rows, "hsp")
    assert [r["identity"]["row_key"]["hsp_ordinal"] for r in native] == [0, 1]
    assert metric(native[0], "native_score_bits")["value"] is None
    assert metric(native[0], "native_score_bits")["reason"] == "invalid_native_row"
    assert metric(native[1], "native_score_bits")["value"] == 40
    search = family(rows, "search")[0]
    assert metric(search, "reported_hsp_count")["value"] == 2
    assert metric(search, "parsed_hsp_count")["value"] == 1


def test_pure_calculation_count_and_row_ports_have_no_io(monkeypatch):
    sheets = psi_sheets(hit_sets=[["A"]])
    def forbidden(*args, **kwargs):
        raise AssertionError("I/O forbidden")
    for owner, names in ((builtins, ["open"]), (Path, ["read_bytes", "read_text", "write_bytes", "write_text", "open"]),
            (socket, ["socket", "create_connection"]), (subprocess, ["Popen", "run"])):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)
    components, rows = calculate_rows(sheets)
    facts = worker.populate_native_blast_database_search_facts(sheets["collection"],
        source_statuses=[dict(search_key=s["search_key"], status="available") for s in sheets["collection"]["searches"]],
        search_bindings=sheets["iteration"]["search_bindings"])
    assert len(rows) > 2 and facts[0]["counts"]["reported_hit_count"]["value"] == 1


def implementation():
    files = [dict(module=name, path=str(Path(module.__file__).resolve()), sha256=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest())
        for name, module in worker._implementation_modules().items()]
    return dict(files=files, manifest_sha256=worker.native_blast_database_implementation_identity(files))


def request_fixture(tmp_path, program="psiblast", *, metadata_payload=None, metadata_tuples=None):
    """Use actual N capture of a clearly synthetic emitter, never BLAST."""
    from tests import test_native_blast_database_driver as native
    path, plan, _ = native.fixture(tmp_path / "captured", program=program, checkpoint_output=False)
    job = plan["requested_job"]["native_blast_database"]
    if metadata_payload is None:
        job["inputs"] = job["inputs"][:1]; job["metadata_inputs"] = []
        plan["input_paths"] = {"query": plan["input_paths"]["query"]}
    else:
        raw_metadata = metadata_payload if type(metadata_payload) is bytes else worker._json_bytes(metadata_payload)
        job["inputs"][1].update(native.write(Path(job["inputs"][1]["path"]), raw_metadata))
        job["metadata_inputs"] = metadata_tuples
    native_program = program.removesuffix("_vdb")
    h = dict(query_from=1, query_to=4, hit_from=1, hit_to=4, align_len=4, identity=4,
        qseq="ACGT", hseq="ACGT", gaps=0, bit_score=20, score=40, evalue=0.0)
    document = {"BlastOutput2": [{"report": dict(program=native_program, version=native_program.upper() + " 2.17.0+",
        search_target={"db": "target"}, params={}, results={"search": dict(query_id="one", query_title="one", query_len=4,
            hits=[dict(len=4, description=[dict(id="A", accession="A.1", title="synthetic A")], hsps=[h])])})}]}
    raw = json.dumps(document).encode()
    script = ("#!" + sys.executable + "\nimport pathlib, sys\n"
        "pathlib.Path(sys.argv[sys.argv.index('-out')+1]).write_bytes(" + repr(raw) + ")\n"
        "pathlib.Path('synthetic-emitter-invoked').write_text('one synthetic emission')\n").encode()
    software = native.write(Path(job["software"]["executable"]), script)
    job["software"].update(executable=software["path"], sha256=software["sha256"])
    native.refresh_plan(path, plan)
    process, bundle = native.run_fixture(path, plan)
    assert process.returncode == 0, process.stderr
    native.validate_bundle(bundle, plan)
    capture = native.file_identity(path.parent / "bundle.json")
    request = dict(version="native_blast_database_result_worker_request_v1", calculation_id="0" * 64,
        bundle=bundle, bundle_artifact_ref="artifact:synthetic-bundle", bundle_capture={k: capture[k] for k in ("path", "sha256", "size_bytes")},
        authenticated_attempt=dict(identity=bundle["identity"], attempt_directory=plan["attempt_directory"], plan_sha256=native.c._digest(plan)),
        artifacts=[dict(artifact_key=r["artifact_key"], artifact_ref="artifact:" + r["artifact_key"],
            path=str(path.parent / r["relative_path"]), sha256=r["sha256"], size_bytes=r["size_bytes"]) for r in bundle["artifacts"]],
        metadata_descriptors=[dict(**descriptor, origin="original_job_input", artifact_ref="artifact:" + artifact["artifact_key"], sha256=artifact["sha256"], size_bytes=artifact["size_bytes"])
            for descriptor in job["metadata_inputs"] for artifact in bundle["artifacts"] if artifact["input_key"] == descriptor["input_key"]],
        retained_sources=[], subject_snapshots=[], implementation=implementation(),
        output_directory=str(tmp_path / "generation1"), reuse=None, sequence_model=None)
    request["calculation_id"] = worker.native_blast_database_calculation_identity(
        input_identity=worker.native_blast_database_input_identity(request), input_implementation_sha256=request["implementation"]["manifest_sha256"],
        sequence_model=None, implementation_manifest_sha256=request["implementation"]["manifest_sha256"])["calculation_id"]
    return request


def run_request(tmp_path, request, name="request.json", *, cli=False):
    path = tmp_path / name; path.write_bytes(worker._json_bytes(request))
    if cli:
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]), PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, "-B", "-m", "gene_annotation_episode.native_blast_database_result_worker", str(path)],
            cwd=tmp_path, env=env, capture_output=True, check=False)
        (tmp_path / (name + ".stdout")).write_bytes(result.stdout)
        (tmp_path / (name + ".stderr")).write_bytes(result.stderr)
        assert result.returncode == 0, result.stderr.decode() + str(request["output_directory"])
        return json.loads((Path(request["output_directory"]) / "worker-manifest.json").read_bytes())
    return worker.run_native_blast_database_result_worker(str(path))


def test_identity_exact_canonical_recipe_path_invariance_and_model_changes(tmp_path):
    request = request_fixture(tmp_path)
    identity = worker.native_blast_database_input_identity(request)
    moved = deepcopy(request)
    moved["output_directory"] = "/relocated/output"
    moved["bundle_capture"]["path"] = "/relocated/bundle"
    for row in moved["artifacts"] + moved["implementation"]["files"]:
        row["path"] = "/relocated/" + str(len(row["path"]))
    assert worker.native_blast_database_input_identity(moved) == identity
    assert worker.native_blast_database_implementation_identity(moved["implementation"]["files"]) == request["implementation"]["manifest_sha256"]
    files = [{k: r[k] for k in ("module", "sha256")} for r in request["implementation"]["files"]]
    independent = hashlib.sha256(json.dumps(dict(version="native_blast_database_implementation_identity_v1", files=sorted(files, key=lambda r: r["module"])),
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert independent == request["implementation"]["manifest_sha256"]
    old = worker.native_blast_database_calculation_identity(input_identity=identity, input_implementation_sha256=independent,
        sequence_model=None, implementation_manifest_sha256=independent)
    new = worker.native_blast_database_calculation_identity(input_identity=identity, input_implementation_sha256=independent,
        sequence_model={"temperature_bits": 2}, implementation_manifest_sha256=independent)
    assert old["input_interpretation_id"] == new["input_interpretation_id"] and old["calculation_id"] != new["calculation_id"]


@pytest.mark.parametrize("program", views._PROGRAMS)
def test_actual_worker_cli_seals_all_artifacts_exact_byte_index_and_v2_sheet(tmp_path, program):
    request = request_fixture(tmp_path, program)
    manifest = run_request(tmp_path, request, cli=True)
    output = Path(request["output_directory"])
    assert manifest["status"] in ("complete", "partial")
    assert {r["role"] for r in manifest["artifacts"]} == set(worker._ARTIFACT_ROLES)
    for artifact in manifest["artifacts"]:
        raw = (output / artifact["relative_path"]).read_bytes()
        assert len(raw) == artifact["size_bytes"] and hashlib.sha256(raw).hexdigest() == artifact["sha256"]
    sheets = json.loads((output / "sheets.json").read_bytes())
    assert [r["role"] for r in sheets["collection"]["artifacts"]].count("native_log") == 2
    if program in ("psiblast", "deltablast"):
        assert sheets["iteration"]["schema"] == "blast_iteration_sheet_v2"
    else:
        assert sheets["iteration"] is None
        assert len(sheets["profile" if program in ("rpsblast", "rpstblastn") else "vdb"]) == 1
    assert sheets["prepared_inputs"]["query_records"][0]["sequence"] == "ACGT"
    raw_rows = (output / "rows.ndjson").read_bytes()
    index = json.loads((output / "row-index.json").read_bytes())
    rows = [json.loads(raw_rows[r["byte_start"]:r["byte_end"]]) for r in index["rows"]]
    assert metric(family(rows, "hsp")[0], "native_score_bits")["value"] == 20
    assert [r["ordinal"] for r in index["rows"]] == list(range(len(rows)))
    assert manifest["counts"] == dict(searches=1, native_hsp_slots=1, numerical_rows=len(rows))


def reuse_request(request, manifest):
    old = Path(request["output_directory"])
    new = deepcopy(request); new["output_directory"] = str(old.parent / "generation2")
    raw = (old / "worker-manifest.json").read_bytes()
    new["reuse"] = dict(manifest_path=str(old / "worker-manifest.json"), manifest_sha256=hashlib.sha256(raw).hexdigest(),
        manifest_size_bytes=len(raw), collection_path=str(old / "collection.json"), sheets_path=str(old / "sheets.json"))
    new["sequence_model"] = {"temperature_bits": 2}
    new["calculation_id"] = worker.native_blast_database_calculation_identity(input_identity=worker.native_blast_database_input_identity(new),
        input_implementation_sha256=manifest["input_implementation_sha256"], sequence_model=new["sequence_model"],
        implementation_manifest_sha256=new["implementation"]["manifest_sha256"])["calculation_id"]
    return new


def test_reuse_saved_sheets_without_prepare_populate_or_collection(tmp_path, monkeypatch):
    from gene_annotation_episode import native_blast_database_metadata as metadata
    request = request_fixture(tmp_path)
    first = run_request(tmp_path, request)
    assert first["status"] != "failed", json.loads((Path(request["output_directory"]) / "diagnostics.json").read_bytes())
    new = reuse_request(request, first)
    before = (Path(request["output_directory"]) / "rows.ndjson").read_bytes()
    def forbidden(*a, **kw):
        raise AssertionError("reuse attempted parsing/population")
    monkeypatch.setattr(metadata, "prepare_native_blast_database_inputs", forbidden)
    monkeypatch.setattr(metadata, "populate_native_blast_database_sheets", forbidden)
    monkeypatch.setattr(worker, "parse_blast_report_collection", forbidden)
    second = run_request(tmp_path, new, "request-reuse.json")
    assert second["status"] != "failed"
    assert first["input_identity"] == second["input_identity"] and first["input_interpretation_id"] == second["input_interpretation_id"]
    assert first["calculation_id"] != second["calculation_id"]
    after = (Path(new["output_directory"]) / "rows.ndjson").read_bytes()
    assert [json.loads(r)["record_key"] for r in before.splitlines()] == [json.loads(r)["record_key"] for r in after.splitlines()]
    assert (Path(request["output_directory"]) / "rows.ndjson").read_bytes() == before


def test_exact_function_census_taxonomy_and_quality_components():
    args = iteration.from_collection(sequence.collect())
    original = sequence.inputs(args["collection"]["searches"][0])
    args["sequence_metadata"][0]["database_profile"] = original["database_profile"]
    metadata = args["sequence_metadata"][0]["reference_metadata"]
    metadata[0].update(lineage=[dict(taxid=7, rank="species", name="A")],
        assembly=dict(accession="ASM_A", completeness_fraction=.95, contamination_fraction=1.2, quality_method="CheckM", contig_count=3, contig_n50=100))
    metadata[1].update(lineage=[dict(taxid=8, rank="species", name="B")])
    args["target_context"] = dict(query_operand=deepcopy(args["query_bindings"][0]["query_binding"]["operand"]),
        taxid=7, lineage=[dict(taxid=7, rank="species", name="A")], independent_of_search=True,
        source=dict(source_ref="synthetic:target", pointer="/target"))
    sheets = sheet_set(args["collection"], iteration_sheet=populate_blast_iteration_sheet(**args))
    _, rows = calculate_rows(sheets)
    functions = family(rows, "sequence_function")
    assert [metric(r, "function_mass")["value"] for r in functions] == [1, .25]
    assert [metric(r, "unadjusted_probability")["value"] for r in functions] == [.8, .2]
    assert [metric(r, "representation_adjusted_probability")["value"] for r in functions] == [.5, .5]
    assert all(r["booleans"][0]["value"] is False for r in functions)
    population = family(rows, "sequence_population")
    assert [metric(r, "database_sequence_count")["value"] for r in population] == [200, 50]
    assert [metric(r, "database_fraction")["value"] for r in population] == [.2, .05]
    quality = family(rows, "sequence_quality")
    assert {r["identity"]["function"] for r in quality} == {None, "F"}
    assert all(metric(r, "completeness_fraction")["value"] == .95 and metric(r, "contamination_fraction")["value"] == 1.2 for r in quality)
    assert all(metric(r, "total_sequence_length")["value"] is None for r in quality)
    rank = next(r for r in family(rows, "sequence_taxonomy") if r["identity"]["rank"] == "species" and r["identity"]["function"] is None)
    assert metric(rank, "target_matching_fraction")["value"] == .5
    _, changed = calculate_rows(sheets, model={"temperature_bits": 2})
    assert [metric(r, "unadjusted_probability")["value"] for r in family(changed, "sequence_function")] == [2 / 3, 1 / 3]
    assert [r["record_key"] for r in rows] == [r["record_key"] for r in changed]


@pytest.mark.parametrize("arguments", [dict(), dict(malformed=True), dict(zero=True), dict(empty=True), dict(malformed=True, delimiter="@")])
def test_public_raw_count_population_exact_parity_with_311(arguments):
    args = iteration_calc.table_inputs(**arguments)
    nested = worker._iteration.calculate_blast_iteration_components(populate_blast_iteration_sheet(**args))
    actual = worker.populate_native_blast_database_search_facts(args["collection"],
        source_statuses=[dict(search_key=r["search_key"], status=r["source_status"]) for r in nested["searches"]], search_bindings=args["search_bindings"])
    for expected, found in zip(nested["searches"], actual):
        for name, cell in expected["counts"].items():
            assert found["counts"][name]["value"] == cell["value"]
            assert found["counts"][name]["status"] == cell["status"]
            assert found["counts"][name]["reason"] == cell["unavailable_reason"]
            assert found["counts"][name]["origin"] == cell["origin"]
    if arguments.get("malformed"):
        components, rows = calculate_rows(sheet_set(args["collection"], iteration_sheet=populate_blast_iteration_sheet(**args)))
        native = family(rows, "hsp")
        assert len(native) == 4 and native[-1]["identity"]["row_key"]["hit_ordinal"] is None
        assert native[-1]["identity"]["row_key"]["hsp_ordinal"] == 3


def test_malformed_json_count_parity_and_unqualified_projection_preserves_raw():
    args = iteration.make_inputs(hit_sets=[["A"]], raw_searches=[dict(query_id="q", query_title="q", query_len=8,
        hits=[False, dict(len=10, description=[dict(id="A", accession="A.1", title="synthetic A", taxid=1)], hsps=[None, iteration.hsp(40)])])])
    facts = worker.populate_native_blast_database_search_facts(args["collection"], source_statuses=[dict(search_key=args["collection"]["searches"][0]["search_key"], status="available")], search_bindings=[])
    assert {k: c["value"] for k, c in facts[0]["counts"].items()} == dict(reported_hit_count=2, reported_hsp_count=None,
        observed_hsp_count=2, parsed_hit_count=1, parsed_hsp_count=1, declared_alignment_row_count=None)
    facts = worker.populate_native_blast_database_search_facts(args["collection"], source_statuses=[dict(search_key=args["collection"]["searches"][0]["search_key"], status="incompatible")], search_bindings=[])
    assert facts[0]["counts"]["observed_hsp_count"]["value"] == 2
    assert facts[0]["counts"]["parsed_hsp_count"]["value"] is None


def test_profile_overlap_conflicting_model_length_and_reverse_coordinates():
    args = profile.make_inputs(hits=[profile.synthetic_hit(), profile.synthetic_hit(2, start=21)])
    args["model_relations"] = [dict(left_profile_key="profile_1", right_profile_key="profile_2", relation="same_family", provenance=profile.provenance("/family"))]
    args["profile_records"][0]["num_columns"] = 120
    collection = collection_for(args["search"]); args["search"] = collection["searches"][0]
    _, rows = calculate_rows(sheet_set(collection, profile_sheet=populate_blast_profile_sheet(**args)))
    assert len(family(rows, "profile_model")) == 2
    assert metric(family(rows, "profile_overlap")[0], "paired_query_overlap_units")["value"] == 30
    model = family(rows, "profile_model")[0]
    assert metric(model, "model_coverage")["value"] is None and metric(model, "model_coverage")["reason"] == "incompatible_input"
    assert metric(model, "query_coverage")["value"] == .5
    assert metric(family(rows, "profile_hsp_model")[0], "specific_bits_margin")["value"] == 2
    calculated, rows = calculate_rows(profile_sheets("rpstblastn", reverse=True))
    profile_component = calculated["profile"][0]["components"]
    assert profile_component["models"][0]["observed_paired_query_intervals"] == [[150, 300]]
    assert metric(family(rows, "hsp")[0], "paired_query_units")["value"] == 150


def test_vdb_taxonomy_population_quality_literal_counts_and_filter_conflict():
    hits = [dict(len=8, description=[dict(id=f"r{i}", accession=f"r{i}")], hsps=[vdb.hsp()]) for i in range(3)]
    values = vdb.inputs(vdb.collect(hits=hits)["searches"][0], symbols=["ACGTACGT", "ACGTACGA", "ACGTACGC"])
    for i, taxid in enumerate([7, 7, 8]):
        row = next(m for m in values["reference_metadata"] if m["metadata_key"] == f"member{i}")
        row.update(taxid=taxid, taxid_scope="entity_organism", lineage=[dict(taxid=taxid, rank="species", name=str(taxid))])
    values["target_context"] = dict(query_operand=deepcopy(values["query_binding"]["operand"]), taxid=7,
        lineage=[dict(taxid=7, rank="species", name="A")], independent_of_search=True, source=vdb.provenance("/target"))
    values["reference_metadata"][0]["assembly"] = dict(identifier=vdb.identity("assembly"), completeness_percent=95, contamination_percent=120,
        contig_count=3, contig_n50=100, total_sequence_length=200, method="CheckM", method_version="synthetic",
        source=vdb.provenance("/checkm"), linkage_source=vdb.provenance("/member-to-assembly"))
    _, rows = calculate_rows(vdb_sheets(values))
    rank = family(rows, "vdb_taxonomy")[0]
    assert [metric(rank, n)["value"] for n in ("same_taxon_pair_count", "comparable_pair_count", "same_taxon_pair_fraction", "different_taxon_pair_fraction", "target_matching_fraction")] == [1, 3, 1 / 3, 2 / 3, 2 / 3]
    quality = family(rows, "vdb_quality")[0]
    assert metric(quality, "completeness_fraction")["value"] == .95 and metric(quality, "contamination_fraction")["value"] == 1.2
    values = vdb.inputs(); members = []
    for i in range(4):
        key = {k: deepcopy(values["member_bindings"][i % 2][k]) for k in ("dataset_key", "member_kind", "member_identifier")}
        if i >= 2:
            key["member_identifier"] = vdb.identity(f"extra{i}")
        members.append(vdb_calc.population_entity("read", member=key))
    fn = dict(namespace="EC", value="1.2.3.4")
    values["population_records"] = [vdb_calc.population(values, "reads", members,
        functions=[dict(function=fn, count=3, assignment_scope="whole_sequence", source=vdb.provenance("/function"))])]
    _, rows = calculate_rows(vdb_sheets(values))
    population = family(rows, "vdb_population")[0]
    assert metric(population, "observed_fraction_of_supplied_population")["value"] == .5
    assert metric(population, "total_count")["unit"] == "member"
    function = family(rows, "vdb_population_function")[0]
    assert metric(function, "population_function_fraction")["value"] == .75
    assert metric(function, "observed_function_entity_count")["value"] is None
    values["population_records"][0]["datasets"][0]["include_filtered_reads"] = True
    _, rows = calculate_rows(vdb_sheets(values))
    assert metric(family(rows, "vdb_population")[0], "observed_fraction_of_supplied_population")["value"] is None


def test_delta_uses311_once_and_standalone_vdb_pssm_calculates_unique_input(monkeypatch):
    sheets = psi_sheets(program="deltablast", hit_sets=[["P1"], ["A"]], stages=["domain_database", "sequence_database"],
        query=iteration.operand(length=100, selected_interval=None))
    calls = []; original = worker._iteration.calculate_blast_iteration_components
    monkeypatch.setattr(worker._iteration, "calculate_blast_iteration_components", lambda *a, **k: (calls.append(1), original(*a, **k))[1])
    calculated, rows = calculate_rows(sheets)
    assert calls == [1] and calculated["profile"] == []
    assert family(rows, "profile_model") and family(rows, "sequence_hit")
    sheets = vdb_sheets(vdb_calc.translated_case())
    supplied = pssm.read(pssm.model())
    sheets["pssm"] = [supplied, deepcopy(supplied)]
    calls = []; original_pssm = worker._pssm.calculate_blast_pssm_components
    monkeypatch.setattr(worker._pssm, "calculate_blast_pssm_components", lambda *a, **k: (calls.append(1), original_pssm(*a, **k))[1])
    calculated, rows = calculate_rows(sheets)
    assert calls == [1] and len(family(rows, "pssm_cell")) == 6


@pytest.mark.parametrize("change", ["bytes", "metadata", "manifest"])
def test_reuse_rejects_changed_bytes_or_input_identity_without_fallback(tmp_path, monkeypatch, change):
    from gene_annotation_episode import native_blast_database_metadata as metadata
    request = request_fixture(tmp_path); first = run_request(tmp_path, request)
    assert first["status"] != "failed"
    new = reuse_request(request, first)
    if change == "bytes":
        Path(new["reuse"]["sheets_path"]).write_bytes(b"{}\n")
    elif change == "manifest":
        Path(new["reuse"]["manifest_path"]).write_bytes(b"{}\n")
    else:
        new["metadata_descriptors"].append(dict(input_key="new", consumer="profile", schema_id="unregistered.synthetic",
            artifact_ref="artifact:new", sha256="f" * 64, size_bytes=0, origin="selected_results_input"))
        new["calculation_id"] = worker.native_blast_database_calculation_identity(input_identity=worker.native_blast_database_input_identity(new),
            input_implementation_sha256=first["input_implementation_sha256"], sequence_model=new["sequence_model"],
            implementation_manifest_sha256=new["implementation"]["manifest_sha256"])["calculation_id"]
    def forbidden(*a, **k):
        pytest.fail("changed reuse attempted reparsing")
    monkeypatch.setattr(metadata, "prepare_native_blast_database_inputs", forbidden)
    result = run_request(tmp_path, new, "changed-reuse.json")
    assert result["status"] == "failed"
    assert result["failures"][-1]["code"] == "native_blast_database_frozen_artifact_changed"
    assert not (Path(new["output_directory"]) / "rows.ndjson").exists()


@pytest.mark.parametrize("error", [RuntimeError("exact synthetic implementation error\nsecond line"), MemoryError("synthetic allocation limit")])
def test_worker_records_exact_exception_and_preserves_sealed_input_artifacts(tmp_path, monkeypatch, error):
    request = request_fixture(tmp_path)
    def fail(*a, **k):
        raise error
    monkeypatch.setattr(worker, "calculate_native_blast_database_sheets", fail)
    result = run_request(tmp_path, request)
    assert result["status"] == "failed"
    assert {r["role"] for r in result["artifacts"]} == {"inputs", "collection", "sheets", "diagnostics"}
    diagnostics = json.loads((Path(request["output_directory"]) / "diagnostics.json").read_bytes())
    assert diagnostics["errors"][-1] == dict(failure_index=len(result["failures"]) - 1,
        exception_type="builtins." + type(error).__name__, message=str(error))
    assert not (Path(request["output_directory"]) / "rows.ndjson").exists()
    assert not (Path(request["output_directory"]) / "worker-error.txt").exists()


@pytest.mark.parametrize("calculator", ["iteration", "profile", "vdb", "pssm"])
def test_thrown_calculator_error_propagates_without_partial_success(monkeypatch, calculator):
    if calculator == "iteration":
        sheets = psi_sheets(hit_sets=[["A"]])
    elif calculator == "profile":
        sheets = profile_sheets()
    else:
        sheets = vdb_sheets()
        if calculator == "pssm":
            sheets["pssm"] = [pssm.read(pssm.model())]
    error = ValueError("exact synthetic calculator error\nnot a successful numeric issue")
    def fail(*a, **k):
        raise error
    monkeypatch.setattr(getattr(worker, "_" + calculator), "calculate_blast_" + calculator + "_components", fail)
    with pytest.raises(ValueError) as caught:
        worker.calculate_native_blast_database_sheets(sheets, sequence_model=None)
    assert caught.value is error


def test_nested_calculator_error_is_failed_manifest_with_exact_diagnostics(tmp_path, monkeypatch):
    request = request_fixture(tmp_path)
    error = ValueError("exact nested calculator failure\nsecond line")
    def fail(*a, **k):
        raise error
    monkeypatch.setattr(worker._iteration, "calculate_blast_iteration_components", fail)
    result = run_request(tmp_path, request)
    assert result["status"] == "failed"
    assert {r["role"] for r in result["artifacts"]} == {"inputs", "collection", "sheets", "diagnostics"}
    assert result["failures"][-1] == dict(stage="calculation", code="native_blast_database_calculation_failed",
        detail_code="calculator_contract_invalid", artifact_key=None, input_key=None, search_key=None, record_key=None, pointer="")
    diagnostics = json.loads((Path(request["output_directory"]) / "diagnostics.json").read_bytes())
    assert diagnostics["errors"][-1] == dict(failure_index=len(result["failures"]) - 1,
        exception_type="builtins.ValueError", message=str(error))
    assert not (Path(request["output_directory"]) / "calculations.json").exists()
    assert not (Path(request["output_directory"]) / "rows.ndjson").exists()


def test_conflicting_pssm_artifact_identity_cannot_select_first_sheet():
    sheets = vdb_sheets(vdb_calc.translated_case())
    first = pssm.read(pssm.model())
    second = deepcopy(first)
    second["source_ref"] = "artifact:conflicting-source"
    sheets["pssm"] = [first, second]
    with pytest.raises(ValueError, match="native_blast_database_pssm_identity_conflict"):
        worker.calculate_native_blast_database_sheets(sheets, sequence_model=None)


def test_original_worker_generation_cannot_be_overwritten_and_invalid_model_is_rejected(tmp_path):
    request = request_fixture(tmp_path); first = run_request(tmp_path, request)
    output = Path(request["output_directory"])
    saved = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(FileExistsError, match="generation_directory_not_empty"):
        run_request(tmp_path, request, "same-generation.json")
    assert {p.name: p.read_bytes() for p in output.iterdir()} == saved
    new = reuse_request(request, first)
    new["sequence_model"] = {"temperature_bits": None}
    with pytest.raises(ValueError, match="native_blast_database_sequence_model_invalid"):
        run_request(tmp_path, new, "invalid-model.json")
    assert {p.name: p.read_bytes() for p in output.iterdir()} == saved
    assert not Path(new["output_directory"]).exists()


def test_changed_calculator_bytes_reuse_old_interpretation_without_parsers(tmp_path):
    request = request_fixture(tmp_path); first = run_request(tmp_path, request)
    assert first["status"] != "failed"
    new = reuse_request(request, first)
    package = Path(__file__).resolve().parents[1] / "gene_annotation_episode"
    copied = tmp_path / "changed-implementation" / "gene_annotation_episode"
    copied.mkdir(parents=True)
    for source in package.glob("*.py"):
        shutil.copyfile(source, copied / source.name)
    calculator = copied / "blast_iteration_calculators.py"
    calculator.write_bytes(calculator.read_bytes() + b"\n# Synthetic replay: changed retained calculator bytes.\n")
    request_path = tmp_path / "changed-code-request.json"
    request_path.write_bytes(worker._json_bytes(new))
    # The isolated process imports the changed local package. Actual M/293 are
    # prohibited after loading; real311/303 calculation still executes once.
    script = tmp_path / "changed-code-run.py"
    script.write_text('''import hashlib, json, pathlib, sys
from gene_annotation_episode import native_blast_database_result_worker as w
from gene_annotation_episode import native_blast_database_metadata as m
p = pathlib.Path(sys.argv[1]); r = json.loads(p.read_bytes())
files = [dict(module=n, path=str(pathlib.Path(v.__file__).resolve()), sha256=hashlib.sha256(pathlib.Path(v.__file__).read_bytes()).hexdigest()) for n,v in w._implementation_modules().items()]
r['implementation'] = dict(files=files, manifest_sha256=w.native_blast_database_implementation_identity(files))
old = json.loads(pathlib.Path(r['reuse']['manifest_path']).read_bytes())
r['calculation_id'] = w.native_blast_database_calculation_identity(input_identity=w.native_blast_database_input_identity(r), input_implementation_sha256=old['input_implementation_sha256'], sequence_model=r['sequence_model'], implementation_manifest_sha256=r['implementation']['manifest_sha256'])['calculation_id']
p.write_bytes(w._json_bytes(r))
def forbidden(*a, **k): raise AssertionError('saved interpretation was reparsed')
m.prepare_native_blast_database_inputs = forbidden
m.populate_native_blast_database_sheets = forbidden
w.parse_blast_report_collection = forbidden
calls = []; actual = w._iteration.calculate_blast_iteration_components
def calculate(*a, **k):
    calls.append(1)
    return actual(*a, **k)
w._iteration.calculate_blast_iteration_components = calculate
result = w.run_native_blast_database_result_worker(str(p))
assert result['status'] != 'failed', result
assert calls == [1]
''')
    result = subprocess.run([sys.executable, "-B", str(script), str(request_path)], cwd=tmp_path,
        env=dict(os.environ, PYTHONPATH=str(copied.parent), PYTHONDONTWRITEBYTECODE="1"), capture_output=True, check=False)
    (tmp_path / "changed-code.stdout").write_bytes(result.stdout); (tmp_path / "changed-code.stderr").write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr.decode()
    second = json.loads((Path(new["output_directory"]) / "worker-manifest.json").read_bytes())
    assert second["input_identity"] == first["input_identity"] and second["input_interpretation_id"] == first["input_interpretation_id"]
    assert second["input_implementation_sha256"] == first["implementation_manifest_sha256"]
    assert second["implementation_manifest_sha256"] != first["implementation_manifest_sha256"]
    assert second["calculation_id"] != first["calculation_id"]


def test_retained_native_pssm_full_matrix_values_are_not_compacted():
    """Retained NCBI source fixture: parser/math evidence, no new native run."""
    from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm
    supplied = read_blast_pssm((pssm.SOURCES / "pssm_zero_fratios.asn").read_bytes(), format="scoremat_asn_text",
        artifact_key="retained:ncbi-zero-fratios", source_ref="retained:pinned-primary-source")
    args = iteration.make_inputs(hit_sets=[["A"]]); args["pssm_sheets"] = [supplied]
    calculated, rows = calculate_rows(sheet_set(args["collection"], iteration_sheet=populate_blast_iteration_sheet(**args)))
    cells = family(rows, "pssm_cell"); positions = family(rows, "pssm_position")
    assert len(cells) == 232 * 28 and len(positions) == 232
    index = {(r["identity"]["position"], r["identity"]["residue_row"]): r for r in cells}
    assert [metric(index[pair], "scores")["value"] for pair in ((0, 0), (116, 10), (231, 27))] == [-32768, -1, -3]
    assert all(metric(r, "freqRatios")["value"] == 0 for r in cells)
    matrix = calculated["iteration"]["pssms"][0]["components"]["matrices"][0]
    assert len(matrix["matrix_values"]["scores"]) == 232
    assert matrix["native_statistics"]["kappa"] == .0402635999


def test_distinct_metadata_tuples_share_captured_bytes_without_overwrite(tmp_path):
    payload = dict(schema="native_blast_database_query_metadata_v1", documents=[], sequence_records=[],
        effective_msa_masters=[], master_subjects=[], search_bindings=[], target_contexts=[])
    tuples = [dict(input_key="metadata", consumer="query_identity", schema_id=payload["schema"]),
        dict(input_key="metadata", consumer="profile", schema_id="synthetic.unregistered.v2")]
    request = request_fixture(tmp_path, metadata_payload=payload, metadata_tuples=tuples)
    manifest = run_request(tmp_path, request)
    output = Path(request["output_directory"])
    assert manifest["status"] == "partial", json.loads((output / "diagnostics.json").read_bytes())
    prepared = json.loads((output / "inputs.json").read_bytes())
    assert [{k: r[k] for k in ("input_key", "consumer", "schema_id")} for r in prepared["metadata"]] == tuples
    assert [r["status"] for r in prepared["metadata"]] == ["valid", "unsupported"]
    assert all(r["payload"] == payload for r in prepared["metadata"])
    rows = [json.loads(line) for line in (output / "rows.ndjson").read_bytes().splitlines()]
    assert metric(family(rows, "hsp")[0], "native_score_bits")["value"] == 20
    for mutation in ("duplicate", "changed_identity", "query_alias"):
        changed = deepcopy(request); changed["output_directory"] = str(tmp_path / mutation)
        if mutation == "duplicate":
            changed["metadata_descriptors"].append(deepcopy(changed["metadata_descriptors"][0]))
        elif mutation == "changed_identity":
            changed["metadata_descriptors"][1]["sha256"] = "f" * 64
        else:
            row = deepcopy(changed["metadata_descriptors"][0]); row.update(input_key="query", origin="selected_results_input")
            changed["metadata_descriptors"].append(row)
        result = run_request(tmp_path, changed, mutation + ".json")
        assert result["status"] == "failed" and not (Path(changed["output_directory"]) / "rows.ndjson").exists()


@pytest.mark.parametrize("raw", [b'{"schema":"one","schema":"two"}', b'{"value":NaN}', b'not JSON\x00\xff'])
def test_malformed_metadata_bytes_preserve_native_sibling_measurements(tmp_path, raw):
    tuples = [dict(input_key="metadata", consumer="query_identity", schema_id="native_blast_database_query_metadata_v1")]
    request = request_fixture(tmp_path, metadata_payload=raw, metadata_tuples=tuples)
    result = run_request(tmp_path, request)
    output = Path(request["output_directory"])
    assert result["status"] == "partial", json.loads((output / "diagnostics.json").read_bytes())
    prepared = json.loads((output / "inputs.json").read_bytes())
    assert prepared["metadata"][0]["status"] == "invalid" and prepared["metadata"][0]["payload"] is None
    rows = [json.loads(line) for line in (output / "rows.ndjson").read_bytes().splitlines()]
    assert metric(family(rows, "hsp")[0], "native_score_bits")["value"] == 20
    source = next(r for r in request["artifacts"] if r["artifact_ref"] == request["metadata_descriptors"][0]["artifact_ref"])
    assert Path(source["path"]).read_bytes() == raw


def test_missing_nonreport_capture_keeps_valid_report_and_full_failure(tmp_path):
    request = request_fixture(tmp_path)
    log_key = next(a["artifact_key"] for a in request["bundle"]["artifacts"] if a["role"] == "stderr")
    missing = next(a for a in request["artifacts"] if a["artifact_key"] == log_key)
    Path(missing["path"]).unlink()
    result = run_request(tmp_path, request)
    assert result["status"] == "partial"
    assert any(f["artifact_key"] == log_key and f["code"] == "native_blast_database_artifact_missing" for f in result["failures"])
    rows = [json.loads(line) for line in (Path(request["output_directory"]) / "rows.ndjson").read_bytes().splitlines()]
    assert metric(family(rows, "hsp")[0], "native_score_bits")["value"] == 20
