"""Infernal adapter checks, not unknown annotation or biological benchmarks.

The native integration uses the already acquired Rfam model and an Infernal
tutorial tRNA. Protocol/parser fixtures are explicitly synthetic or saved replay.
No annotation model or network is called by these tests.
"""
from __future__ import annotations

import json

import pytest

from gene_annotation_episode.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode.domain import ContractError, REASONING_SCHEMA
from gene_annotation_episode.episodic_workflow.root.library.rna_evidence import parse_fmt3, search_settings
from gene_annotation_episode.state import Store


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
    assert native["executable_sha256"] is None and "work_timeout" not in native  # the timeout setting no longer exists
    assert native["native_default_settings"]["report_evalue"] == 10


