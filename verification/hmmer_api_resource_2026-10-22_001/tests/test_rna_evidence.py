"""Infernal adapter checks, not unknown annotation or biological benchmarks.

The native integration uses the already acquired Rfam model and an Infernal
tutorial tRNA. Protocol/parser fixtures are explicitly synthetic or saved replay.
No annotation model or network is called by these tests.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import threading

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, RfamModelSnapshots, SourceSnapshot
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError, REASONING_SCHEMA
from gene_annotation_episode.rna_evidence import model_header, parse_fmt3, search_settings
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def fixture_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "validation/providers/rfam-native/acquisition.json").is_file():
            return parent
    pytest.skip("Rfam/native adapter calibration resources not installed")


class SavedRfam:
    """Replay of pinned HTTP bodies; this is not a new service response."""
    ncbi_email = None

    def __init__(self, root, *, metadata_error=False, model_content=None, metadata_content=None):
        self.root, self.metadata_error, self.model_content = root, metadata_error, model_content
        self.metadata_content = metadata_content
        self.calls = []

    def rfam_model(self, accession):
        self.calls.append(accession)
        directory = self.root / "validation/providers/rfam-native"
        records = json.loads((directory / "acquisition.json").read_text())["records"]
        snapshots = {}
        for record in records:
            if record["accession"] != accession:
                continue
            body = (self.root / record["body_path"]).read_bytes()
            assert hashlib.sha256(body).hexdigest() == record["body_sha256"]
            if self.metadata_content is not None and record["kind"] == "family_metadata":
                body = self.metadata_content
            snapshots[record["kind"]] = SourceSnapshot(
                "rfam_covariance_model" if record["kind"] == "covariance_model" else "rfam_family_metadata",
                record["requested_url"], {"accession": accession}, record["retrieved_at"],
                self.model_content if self.model_content is not None and record["kind"] == "covariance_model" else body,
                record["headers"]["Content-Type"],
                {"representation": "saved_actual_http_bytes" if self.model_content is None and self.metadata_content is None else "explicitly_modified_error_fixture",
                    "response": {"status": 200, "headers": record["headers"]}})
        return RfamModelSnapshots(snapshots["covariance_model"],
            None if self.metadata_error else snapshots["family_metadata"],
            AcquisitionError("provider_http_503", phase="http_response") if self.metadata_error else None)


def tutorial_sequence(root):
    from Bio import SeqIO
    return str(next(SeqIO.parse(root / "resources/software/infernal-1.1.5/tutorial/mrum-tRNAs10.fa", "fasta")).seq)


def binary(root):
    path = root / "resources/software/infernal-1.1.5-install/bin/cmsearch"
    if not path.is_file():
        pytest.skip("Infernal native binary not installed")
    manifest = json.loads((root / "resources/software/infernal-1.1.5-build.json").read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["binaries"]["cmsearch"]["sha256"]
    return path


def acquire(tools, accession="RF00005", key="rfam-model"):
    result = tools.execute("public.rfam.model", {"accession": accession}, operation_key=key)
    assert result["status"] == "completed", result
    return result


def test_fmt3_preserves_reverse_partial_reported_only_and_model_coordinates():
    # Synthetic native-shaped row for parser semantics, not a real RNA hit.
    row = parse_fmt3(b"operand - tRNA RF00005 cm 5 65 89 20 - 5' 2 0.55 1.1 27.9 0.02 ? 71 100 source description\n")[0]
    assert row["target_interval"] == [19, 89]
    assert row["model_consensus_interval"] == [4, 65]
    assert row["inclusion"] == "?" and row["truncation"] == "5'"
    assert row["algorithm"] == "cm" and row["model_length"] == 71
    assert row["native_target_name"] == "operand" and row["native_query_name"] == "tRNA"
    hmm = parse_fmt3(b"operand - model - hmm 1 10 2 11 + - 6 0.4 0.0 1.0 2e-2 ! 10 11\n")[0]
    assert hmm["algorithm"] == "hmm" and hmm["truncation"] == "-"
    assert parse_fmt3(b"# no matches\n") == []
    with pytest.raises(ContractError, match="invalid_cmsearch_fmt3_values"):
        parse_fmt3(b"operand - tRNA RF00005 cm 5 65 20 89 - no 1 .5 0 20 1 ! 71 100\n")


def test_native_threshold_defaults_and_cutoff_choices_are_distinct():
    defaults = search_settings()
    assert defaults["report_evalue"] == 10 and defaults["inclusion_evalue"] == .01
    assert "model_cutoff" not in defaults and defaults["alignment_output"] is True
    chosen = search_settings({"model_cutoff": "ga"})
    assert "report_evalue" not in chosen and "inclusion_evalue" not in chosen
    chosen = search_settings({"report_bitscore": -2, "inclusion_bitscore": 5})
    assert chosen["report_bitscore"] == -2 and "report_evalue" not in chosen
    with pytest.raises(ContractError, match="model_cutoff_sets"):
        search_settings({"model_cutoff": "ga", "report_evalue": 1})
    assert "native_cmsearch" not in REASONING_SCHEMA["properties"]["observations"]["items"]["properties"]


def test_rfam_client_documents_both_fixed_requests_without_search_or_threshold_policy():
    client, calls = PublicClients(), []
    def http(service, url, params, media_type, **options):
        calls.append((service, url, params, media_type, options))
        return SourceSnapshot(service, url, params, "2026-10-20T00:00:00Z", b"body", media_type, {})
    client._http = http
    bundle = client.rfam_model("RF00005")
    assert bundle.model.request == {"accession": "RF00005"}
    assert calls == [("rfam_covariance_model", "https://rfam.org/family/RF00005/cm", {}, "text/plain", {"accept": "*/*"}),
        ("rfam_family_metadata", "https://rfam.org/family/RF00005", {"content-type": "application/json"}, "application/json", {})]
    with pytest.raises(ValueError, match="invalid_rfam_accession"):
        client.rfam_model("RF00005/../../")


def test_saved_rfam_acquisition_preserves_model_identity_and_partial_metadata(tmp_path):
    root = fixture_root()
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="ACGT")
        clients = SavedRfam(root)
        tools = ToolRegistry(store, clients=clients)
        first = acquire(tools)
        family = store.get(first["result"]["model_ref"])
        assert family["reference_type"] == "family"
        assert family["length"] is family["molecule"] is family["sequence_ref"] is None
        assert first["result"]["model_header"]["consensus_length"] == 71
        model_source = store.get(family["source_ref"])
        assert model_header(store.get_artifact(model_source["artifact_ref"]))["accession"] == "RF00005"
        assert tools.execute("public.rfam.model", {"accession": "RF00005"}, operation_key="rfam-model") == first
        assert clients.calls == ["RF00005"] and store.problem() == problem
        assert not store.current_annotations() and project_credit(store).credit == 0
        tools.clients = SavedRfam(root, metadata_error=True)
        partial = tools.execute("public.rfam.model", {"accession": "RF00001"}, operation_key="partial-model")
        assert partial["status"] == "partial" and partial["feedback"]["cause_code"] == "provider_http_503"
        assert store.get(partial["result"]["model_ref"])["accession"] == "RF00001"
        assert partial["record_refs"] and not store.current_annotations()


def test_malformed_optional_metadata_retains_usable_actual_model_and_specific_feedback(tmp_path):
    root = fixture_root()
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ACGT")
        tools = ToolRegistry(store, clients=SavedRfam(root, metadata_content=b'{"malformed":'))
        result = tools.execute("public.rfam.model", {"accession": "RF00005"}, operation_key="malformed-metadata")
        assert result["status"] == "partial" and result["feedback"]["code"] == "rfam_metadata_invalid_json"
        family = store.get(result["feedback"]["detail"]["model_ref"])
        assert family["id"] in result["record_refs"] and family["accession"] == "RF00005"
        assert family["reference_type"] == "family" and family["length"] is None
        source = store.get(family["source_ref"])
        assert model_header(store.get_artifact(source["artifact_ref"]))["accession"] == "RF00005"
        metadata = store.get(result["feedback"]["detail"]["metadata_source_ref"])
        assert store.get_artifact(metadata["artifact_ref"]) == b'{"malformed":'
        assert tools.execute("public.rfam.model", {"accession": "RF00005"}, operation_key="malformed-metadata") == result
        assert project_credit(store).credit == 0 and not store.current_annotations()


def test_actual_native_tutorial_rna_preserves_all_provenance_and_replays_once(tmp_path, monkeypatch):
    root = fixture_root()
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence=tutorial_sequence(root), molecule="rna")["subject_refs"][0]
        original = store.get_input(target)
        tools = ToolRegistry(store, clients=SavedRfam(root), cmsearch_executable=binary(root), cmsearch_cpu=1)
        model = acquire(tools)["result"]["model_ref"]
        import gene_annotation_episode.tools as module
        original_runner = module.run_cmsearch
        threads = []
        def observed(**kwargs):
            threads.append(threading.get_ident())
            assert not store.db.in_transaction
            return original_runner(**kwargs)
        monkeypatch.setattr(module, "run_cmsearch", observed)
        owner = threading.get_ident()
        args = {"subject_ref": target, "model_ref": model}
        result = tools.execute("rna.cmsearch", args, operation_key="tutorial-native")
        assert result["status"] == "completed", result
        assert threads and threads[0] != owner
        assert result["result"]["reported_hit_count"] >= 1
        observation = store.get(result["result"]["records"][0]["observation_ref"])
        native = observation["native_cmsearch"]
        assert native["native_query_model_ref"] == model and native["native_target_subject_ref"] == target
        assert native["native_query_accession"] == "RF00005" and native["native_target_name"] == target
        assert native["algorithm"] == "cm" and native["inclusion"] == "!"
        assert observation["subject_refs"] == [target] and observation["source_subject_refs"] == [model]
        assert len(observation["operand_intervals"]) == 1
        assert observation["operand_intervals"][0]["subject_ref"] == target
        assert store.get(model)["length"] is None
        raw = result["result"]["raw_artifacts"]
        assert raw["native_version"] == "1.1.5" and raw["returncode"] == 0
        assert raw["configuration"] == tools.resource_binding()["cmsearch"]
        assert b"tRNA" in store.get_artifact(raw["stdout_ref"])
        assert b"RF00005" in store.get_artifact(raw["table_ref"])
        assert store.get_artifact(raw["input_fasta_ref"]).startswith((">" + target).encode())
        read = tools.execute("source.read", {"source_ref": result["result"]["source_ref"], "limit": 1000})
        assert read["status"] == "completed" and "cmsearch" in read["result"]["text"]
        assert tools.execute("rna.cmsearch", args, operation_key="tutorial-native") == result
        assert len(threads) == 1
        assert store.get_input(target) == original
        assert not store.list("feature") and not store.list("hypothesis") and not store.current_annotations()
        assert project_credit(store).credit == 0


def test_actual_native_no_reported_hit_is_only_its_searched_scope(tmp_path):
    root = fixture_root()
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="ACGTACGTACGT")['subject_refs'][0]
        tools = ToolRegistry(store, clients=SavedRfam(root), cmsearch_executable=binary(root))
        model = acquire(tools)["result"]["model_ref"]
        result = tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model})
        assert result["status"] == "completed", result
        assert result["result"]["reported_hit_count"] == 0
        assert result["result"]["searched_scope"] == {"subject_ref": target, "start": 0, "end": 12, "unit": "symbol"}
        assert "not_organism_absence" in result["result"]["result_meaning"]
        assert not store.list("hypothesis") and not store.current_annotations() and project_credit(store).credit == 0


@pytest.mark.parametrize("variant", ["reverse", "five_prime_fragment"])
def test_actual_native_reverse_and_truncated_tutorial_coordinates(tmp_path, variant):
    from Bio.Seq import Seq
    root = fixture_root()
    original = tutorial_sequence(root)
    sequence = str(Seq(original).reverse_complement_rna()) if variant == "reverse" else original[10:]
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence=sequence, molecule="rna")["subject_refs"][0]
        tools = ToolRegistry(store, clients=SavedRfam(root), cmsearch_executable=binary(root))
        model = acquire(tools)["result"]["model_ref"]
        result = tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model})
        assert result["status"] == "completed", result
        assert result["result"]["reported_hit_count"] >= 1
        hit = max(result["result"]["records"], key=lambda row: row["bitscore"])
        assert hit["strand"] == ("-" if variant == "reverse" else "+")
        assert hit["target_interval"] == [min(hit["target_from"], hit["target_to"]) - 1,
                                            max(hit["target_from"], hit["target_to"])]
        if variant == "five_prime_fragment":
            assert hit["truncation"] == "5'"
            assert hit["model_from"] > 1 and hit["target_interval"][0] == 0
        observation = store.get(hit["observation_ref"])
        assert observation["native_cmsearch"]["model_consensus_interval"] == [hit["model_from"] - 1, hit["model_to"]]
        assert observation["operand_intervals"][0]["end"] <= len(sequence)
        assert not store.list("feature") and not store.current_annotations()


def test_actual_native_external_rna_is_source_only_and_reported_rows_not_filtered(tmp_path):
    root = fixture_root()
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACT", molecule="protein")
        tools = ToolRegistry(store, clients=SavedRfam(root), cmsearch_executable=binary(root))
        model = acquire(tools)["result"]["model_ref"]
        sequence = tutorial_sequence(root)
        source = store.put("source", {"provider": "infernal_tutorial_calibration", "accession": None,
            "uri": None, "artifact_ref": store.artifact(sequence), "text_ref": None,
            "request_ref": None, "version": "1.1.5", "retrieved_at": None}, origin="external")
        external = store.put("reference", {"reference_type": "rna", "source_ref": source["id"],
            "accession": "mrum-tRNA.1", "label": "Known Infernal tutorial RNA",
            "sequence_ref": store.artifact(sequence), "molecule": "rna", "length": len(sequence),
            "term_refs": [], "context_refs": []}, origin="external")
        result = tools.execute("rna.cmsearch", {"subject_ref": external["id"], "model_ref": model,
            "parameters": {"report_bitscore": 20, "inclusion_bitscore": 10000}})
        assert result["status"] == "completed", result
        assert result["result"]["reported_hit_count"] >= 1
        for hit in result["result"]["records"]:
            observation = store.get(hit["observation_ref"])
            assert observation["native_cmsearch"]["inclusion"] == "?"
            assert observation["subject_refs"] == [external["id"]]
            assert store.roots(observation["id"]) == [] and store.coverage(external["id"]) == []
        assert len(store.targets()) == 1 and store.targets()[0]["molecule"] == "protein"
        assert not store.current_annotations() and project_credit(store).credit == 0


def test_actual_native_mixed_threshold_limitation_preserves_native_flag(tmp_path):
    root = fixture_root()
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence=tutorial_sequence(root), molecule="rna")["subject_refs"][0]
        tools = ToolRegistry(store, clients=SavedRfam(root), cmsearch_executable=binary(root))
        model = acquire(tools)["result"]["model_ref"]
        result = tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model,
            "parameters": {"report_evalue": 10, "inclusion_bitscore": 10000}})
        assert result["status"] == "completed", result
        assert result["result"]["raw_artifacts"]["native_version"] == "1.1.5"
        assert result["result"]["native_limitations"] == ["infernal_1_1_5_inclusion_uses_reporting_threshold_mode"]
        # This is the actual native1.1.5 behavior, not the intended meaning of
        # the chosen inclusion bitscore. The adapter must never rewrite it.
        assert result["result"]["records"][0]["bitscore"] < 10000
        assert result["result"]["records"][0]["inclusion"] == "!"
        assert result["result"]["native_settings"]["inclusion_bitscore"] == 10000
        assert not store.current_annotations() and project_credit(store).credit == 0


def test_native_errors_have_actionable_raw_diagnostics_without_science(tmp_path):
    root = fixture_root()
    # Invalid CM body with a syntactically valid header; explicitly modified
    # local error fixture, not the actual downloaded model or biological result.
    invalid_model = b"INFERNAL1/a [error fixture]\nNAME tRNA\nACC RF00005\nCLEN 71\nALPH RNA\nCM\n//\n"
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence=tutorial_sequence(root), molecule="rna")["subject_refs"][0]
        tools = ToolRegistry(store, clients=SavedRfam(root, model_content=invalid_model), cmsearch_executable=binary(root))
        model = acquire(tools)["result"]["model_ref"]
        before = store.count("observation")
        result = tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model}, operation_key="native-error")
        assert result["status"] == "failed" and result["feedback"]["code"] == "cmsearch_native_error", result
        assert result["feedback"]["native_returncode"] != 0
        diagnostic = json.loads(store.get_artifact(result["feedback"]["diagnostic_ref"]))
        assert diagnostic["returncode"] != 0 and store.get_artifact(diagnostic["stderr_ref"])
        assert result["feedback"]["native_stderr_tail"]
        assert store.count("observation") == before and result["record_refs"] == []
        assert tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model}, operation_key="native-error") == result


def test_configuration_absence_is_operational_not_science(tmp_path):
    root = fixture_root()
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence="ACGT")["subject_refs"][0]
        tools = ToolRegistry(store, clients=SavedRfam(root))
        model = acquire(tools)["result"]["model_ref"]
        result = tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model})
        assert result["status"] == "unavailable" and result["feedback"]["code"] == "cmsearch_not_configured"
        assert result["record_refs"] == [] and not store.list("observation")


def test_new_native_measurement_records_actual_resources_without_invalidating_replay(tmp_path):
    root = fixture_root()
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence=tutorial_sequence(root), molecule="rna")["subject_refs"][0]
        tools = ToolRegistry(store, clients=SavedRfam(root), cmsearch_executable=binary(root))
        model = acquire(tools)["result"]["model_ref"]
        args = {"subject_ref": target, "model_ref": model}
        first = tools.execute("rna.cmsearch", args, operation_key="native-initial-resource")
        assert first["status"] == "completed"
        # Simulate an outdated initial identity and a new caller CPU choice.
        # The immutable installed binary is never changed by the test.
        tools.cmsearch_configuration["executable_sha256"] = "outdated-registry-observation"
        tools.cmsearch_configuration["cpu"] = 0
        assert tools.execute("rna.cmsearch", args, operation_key="native-initial-resource") == first
        next_result = tools.execute("rna.cmsearch", args, operation_key="native-changed-resource")
        assert next_result["status"] == "completed", next_result
        binding = next_result["result"]["resource_binding"]
        assert binding["cpu"] == 0 and binding["executable_sha256"] == hashlib.sha256(binary(root).read_bytes()).hexdigest()
        assert first["result"]["resource_binding"]["cpu"] == 1
        assert not store.current_annotations() and project_credit(store).credit == 0


def test_cli_resource_choice_and_catalog_are_caller_owned(tmp_path, capsys):
    from gene_annotation_episode.cli import main
    config = tmp_path / "local.toml"
    config.write_text('[local_tools]\ncmsearch_executable="/explicit/caller/cmsearch"\ncmsearch_cpu=3\n')
    with Store(tmp_path / "workspace") as store:
        store.create_problem(raw_sequence="ACGT")
    assert main(["capabilities", "--workspace", str(tmp_path / "workspace"), "--config", str(config)]) == 0
    catalog = json.loads(capsys.readouterr().out)
    native = catalog["rna.cmsearch"]["configuration"]
    assert native["executable"] == "/explicit/caller/cmsearch" and native["cpu"] == 3
    assert native["executable_sha256"] is None and native["work_timeout"] is None
    assert native["native_default_settings"]["report_evalue"] == 10


def test_native_observation_field_is_adapter_only_and_scope_is_not_expanded(tmp_path):
    root = fixture_root()
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence=tutorial_sequence(root), molecule="rna")["subject_refs"][0]
        tools = ToolRegistry(store, clients=SavedRfam(root), cmsearch_executable=binary(root))
        model = acquire(tools)["result"]["model_ref"]
        result = tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model})
        assert result["status"] == "completed"
        actual = store.get(result["result"]["records"][0]["observation_ref"])
        payload = {key: value for key, value in actual.items() if key not in {"id", "origin", "record_type"}}
        with pytest.raises(ContractError, match="native_cmsearch_requires_native_tool_source"):
            store.put("observation", payload, origin="extracted")
        prior = store.count("observation")
        denied = tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model},
            scope={"subject_refs": [target], "segments": [{"target_ref": target, "start": 0, "end": 10, "unit": "nt"}]})
        assert denied["status"] == "invalid" and denied["feedback"]["code"] == "requested_measurement_outside_assigned_segments"
        assert store.count("observation") == prior
        assert store.get_input(target)["length"] == len(tutorial_sequence(root))


def test_corrupt_trailing_output_preserves_already_published_native_hit(tmp_path, monkeypatch):
    from dataclasses import replace
    import gene_annotation_episode.tools as module
    root = fixture_root()
    original_runner = module.run_cmsearch
    def corrupt(**kwargs):
        native = original_runner(**kwargs)
        return replace(native, table=native.table + b"invalid trailing synthetic parser fixture\n",
            metadata={**native.metadata, "test_fixture": "injected_invalid_trailing_row"})
    monkeypatch.setattr(module, "run_cmsearch", corrupt)
    with Store(tmp_path) as store:
        target = store.create_problem(raw_sequence=tutorial_sequence(root), molecule="rna")["subject_refs"][0]
        tools = ToolRegistry(store, clients=SavedRfam(root), cmsearch_executable=binary(root))
        model = acquire(tools)["result"]["model_ref"]
        result = tools.execute("rna.cmsearch", {"subject_ref": target, "model_ref": model})
        assert result["status"] == "partial" and result["feedback"]["code"] == "invalid_cmsearch_fmt3_row"
        assert result["feedback"]["detail"]["line"] > 1
        observations = [store.get(ref) for ref in result["record_refs"] if ref.startswith("observation_")]
        assert observations and all(row["native_cmsearch"]["native_target_subject_ref"] == target for row in observations)
        assert not store.current_annotations() and project_credit(store).credit == 0
