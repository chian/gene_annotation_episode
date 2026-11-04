from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

import gene_annotation_episode.phylogeny_raxml_inputs as native


_REPOSITORY = next(path for path in Path(__file__).resolve().parents
    if (path / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24/official_example").is_dir())
_EXAMPLES = _REPOSITORY / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24/official_example/test9_genome_dir"


def _artifact(data):
    return {"raw_artifact_ref": "raw/retained-raxml", "source_ref": "source-raxml",
            "sha256": hashlib.sha256(data).hexdigest()}


def _parse(data):
    return native.parse_raxml_run_log(data, artifact=_artifact(data), dialect="raxml_8")


def _log(body="", *, version="8.2.9", command="raxml -s 'input one.phy' -n run -f a -N 100", end=True):
    return (f"This is RAxML version {version} released by source.\n"
        f"RAxML was called as follows:\n\n{command}\n{body}"
        + ("Overall execution time for full ML analysis: 1.0 secs\n" if end else "")).encode()


def _observations(result, method):
    return [row for row in result["value"]["observations"] if row["method"] == method]


def test_actual_complete_raxml_log_retains_all_native_measurements_and_models():
    assert Path(native.__file__).resolve().parent == Path(__file__).resolve().parents[1] / "gene_annotation_episode"
    data = (_EXAMPLES / "RAxML_info.test9_genome_8taxa_10cds_10proteins_codonAndProteins").read_bytes()
    artifact = _artifact(data)
    before = deepcopy(artifact)
    result = native.parse_raxml_run_log(data, artifact=artifact, dialect="raxml_8")
    assert artifact == before
    assert result["status"] == "ok" and result["diagnostics"] == []
    value = result["value"]
    assert value["completeness"] == "complete"
    assert value["engine"]["version"] == "8.2.9"
    assert len(value["commands"]) == 1
    assert value["engine"]["command_ids"] == [value["commands"][0]["command_id"]]
    assert value["commands"][0]["origin"] == "observed"
    assert value["commands"][0]["role"] == "inference"
    assert len(value["observations"]) == 117
    assert _observations(result, "raxml_8_alignment_patterns")[0]["value"] == 1953
    assert [row["value"] for row in _observations(result, "raxml_8_partition_patterns")] == [318, 246, 502, 887]
    gap = _observations(result, "raxml_8_gap_undetermined_percent")[0]
    assert (gap["value"], gap["raw_token"], gap["unit"]) == (12.57, "12.57", "percent")
    assert gap["value"] != 17308 / 137700
    bootstrap = _observations(result, "raxml_8_bootstrap_log_likelihood")
    assert len(bootstrap) == 100
    assert len({row["population_id"] for row in bootstrap}) == 100
    assert bootstrap[0]["value"] == -56973.973102
    assert bootstrap[-1]["value"] == -56745.905848
    slow = _observations(result, "raxml_8_slow_search_log_likelihood")
    assert len(slow) == 10 and len({row["population_id"] for row in slow}) == 1
    final = _observations(result, "raxml_8_final_ml_log_likelihood")
    assert len(final) == 1 and final[0]["value"] == -56958.397755
    assert final[0]["unit"] == "natural_log_likelihood"
    assert final[0]["population_id"] == slow[0]["population_id"]
    models = value["models"]
    assert [row["partition_name"] for row in models] == ["codon1", "codon2", "codon3", "proteins"]
    assert [row["datatype"] for row in models] == ["dna", "dna", "dna", "protein"]
    assert [row["model_token"] for row in models] == ["GTR", "GTR", "GTR", "LG"]
    assert [len(row["parameters"]) for row in models] == [12, 12, 12, 212]
    assert {row["branch_optimization"] for row in models} == {"joint"}
    assert {row["native_run_label"] for row in models} == {"test9_genome_8taxa_10cds_10proteins_codonAndProteins"}
    for observation in value["observations"]:
        location = observation["location"]
        line = data[location["byte_start_0based"]:location["byte_end_0based_exclusive"]].decode()
        assert observation["raw_token"] in line
        assert location["artifact"] == artifact
        assert location["line_start_1based"] == location["line_end_1based_inclusive"]
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_zero_and_negative_likelihoods_remain_distinct_from_missing():
    result = _parse(_log("Slow ML Search 0 Likelihood: 0\nFinal ML Optimization Likelihood: -3.25\n"))
    assert [row["value"] for row in result["value"]["observations"]] == [0.0, -3.25]
    assert all(row["state"] == "available" for row in result["value"]["observations"])
    assert _parse(_log())["value"]["observations"] == []


@pytest.mark.parametrize("token", ["nan", "inf", "-inf", "1e999", "1e-999", "1_0", "not-a-number"])
def test_bad_number_is_not_zero_and_its_token_is_retained(token):
    result = _parse(_log(f"Final ML Optimization Likelihood: {token}\n"))
    assert result["status"] == "partial"
    row = result["value"]["observations"][0]
    assert (row["value"], row["state"], row["raw_token"]) == (None, "failed", token)
    assert any(row["code"] == "raxml_numeric_token_invalid" for row in result["diagnostics"])
    json.dumps(result, allow_nan=False)


def test_truncated_log_preserves_valid_earlier_quantities_without_completeness_claim():
    result = _parse(_log("Alignment has 1953 distinct alignment patterns\nBootstrap[0]: Time 1, bootstrap likelihood", end=False))
    assert result["status"] == "partial" and result["value"]["completeness"] == "partial"
    assert result["value"]["observations"][0]["value"] == 1953
    assert {row["code"] for row in result["diagnostics"]} >= {
        "raxml_measurement_syntax_invalid", "raxml_log_completion_unproven"}


def test_missing_version_and_command_never_come_from_declared_dialect():
    result = _parse(b"Final ML Optimization Likelihood: -4\n")
    assert result["value"]["engine"]["version"] is None
    assert result["value"]["commands"] == []
    assert result["value"]["observations"][0]["value"] == -4
    assert {row["code"] for row in result["diagnostics"]} >= {"raxml_version_missing", "raxml_command_missing"}


def test_conflicting_version_does_not_choose_the_first():
    result = _parse(_log("This is RAxML version 8.2.10 released by source.\nFinal ML Optimization Likelihood: -4\n"))
    assert result["status"] == "invalid" and result["value"]["engine"]["version"] is None
    assert result["value"]["observations"][0]["value"] == -4


@pytest.mark.parametrize("changes,code", [({"sha256": "0" * 64}, "raxml_artifact_hash_conflict"),
    ({"sha256": "not-a-hash"}, "raxml_artifact_invalid"), ({"extra": 1}, "raxml_artifact_invalid")])
def test_wrong_artifact_is_rejected_before_parsing(changes, code):
    data = _log()
    artifact = {**_artifact(data), **changes}
    result = native.parse_raxml_run_log(data, artifact=artifact, dialect="raxml_8")
    assert result["status"] == "invalid" and result["value"] is None
    assert result["diagnostics"][0]["code"] == code


def test_wrong_dialect_version_and_encoding_are_explicit():
    data = _log()
    assert native.parse_raxml_run_log(data, artifact=_artifact(data), dialect="raxml_ng")["status"] == "invalid"
    assert _parse(_log(version="9.0"))["status"] == "invalid"
    result = _parse(b"\xff")
    assert result["status"] == "invalid" and result["diagnostics"][0]["code"] == "raxml_encoding_invalid"


def test_partition_conflict_preserves_separate_records():
    result = _parse(_log("Partition: 0\nName: first\nDataType: DNA\nSubstitution Matrix: GTR\n"
        "Model Parameters of Partition 0, Name: different, Type of Data: AA\nalpha: 0.3\n"))
    assert result["status"] == "partial"
    models = result["value"]["models"]
    assert len(models) == 2
    assert [(row["partition_name"], row["datatype"]) for row in models] == [("first", "dna"), ("different", "protein")]
    assert models[0]["parameters"] == [] and models[1]["parameters"][0]["value"] == .3
    assert any(row["code"] == "raxml_partition_association_conflict" for row in result["diagnostics"])


def test_repeated_model_parameters_are_retained_and_qualified():
    result = _parse(_log("Model Parameters of Partition 0, Name: one, Type of Data: DNA\nalpha: 0.2\nalpha: 0.4\n"))
    assert result["status"] == "partial"
    assert [row["value"] for row in result["value"]["models"][0]["parameters"]] == [.2, .4]
    assert any(row["code"] == "raxml_parameter_repeated" for row in result["diagnostics"])


def test_exact_locations_keep_utf8_and_crlf_offsets():
    data = ("# α note\r\n" + _log("Final ML Optimization Likelihood: -3.2500\n").decode()).encode()
    result = _parse(data)
    row = result["value"]["observations"][0]
    location = row["location"]
    assert row["raw_token"] == "-3.2500"
    assert data[location["byte_start_0based"]:location["byte_end_0based_exclusive"]] == b"Final ML Optimization Likelihood: -3.2500\n"


def test_command_text_is_data_and_parser_needs_no_io(monkeypatch):
    data = _log("Final ML Optimization Likelihood: -2\n", command="raxml -s 'input one.phy' -n '$(touch /invalid)' -f b")
    artifact = _artifact(data)
    expected = native.parse_raxml_run_log(data, artifact=artifact, dialect="raxml_8")

    def forbidden(*args, **kwargs):
        raise AssertionError("parser performed I/O or execution")

    with monkeypatch.context() as patch:
        patch.setattr("builtins.open", forbidden)
        patch.setattr(Path, "open", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        actual = native.parse_raxml_run_log(data, artifact=artifact, dialect="raxml_8")
    assert actual == expected
    command = actual["value"]["commands"][0]
    assert command["argv"] == ["raxml", "-s", "input one.phy", "-n", "$(touch /invalid)", "-f", "b"]
    assert command["role"] == "support_mapping"


def test_missing_command_does_not_swallow_a_measurement():
    data = b"This is RAxML version 8.2.9 released by source.\nRAxML was called as follows:\nFinal ML Optimization Likelihood: -4\n"
    result = _parse(data)
    assert result["value"]["commands"] == []
    assert result["value"]["observations"][0]["value"] == -4


def test_two_commands_remain_unassociated_instead_of_selecting_latest():
    data = _log("RAxML was called as follows:\nraxml -s different.phy -n different -f I\nFinal ML Optimization Likelihood: -4\n")
    result = _parse(data)
    assert result["status"] == "partial"
    assert len(result["value"]["commands"]) == 2
    assert any(row["code"] == "raxml_multiple_invocations_unassociated" for row in result["diagnostics"])


def test_broken_partition_header_cannot_attach_to_previous_partition():
    data = _log("Partition: 0\nName: one\nDataType: DNA\n"
        "Partition: broken\nName: other\nAlignment Patterns: 30\n")
    result = _parse(data)
    assert result["status"] == "partial"
    assert len(result["value"]["models"]) == 1
    assert result["value"]["models"][0]["partition_name"] == "one"
    assert result["value"]["observations"] == []
    assert {row["code"] for row in result["diagnostics"]} >= {
        "raxml_partition_syntax_invalid", "raxml_partition_header_unassociated"}


def test_malformed_model_parameter_stays_raw_and_does_not_become_a_valid_zero():
    result = _parse(_log("Model Parameters of Partition 0, Name: one, Type of Data: DNA\nalpha:\nTree-Length: nan\n"))
    assert result["status"] == "partial"
    assert result["value"]["models"][0]["parameters"] == []
    assert {row["code"] for row in result["diagnostics"]} >= {
        "raxml_parameter_syntax_invalid", "raxml_numeric_token_invalid"}


@pytest.mark.parametrize("body,token", [
    ("Alignment has -1 distinct alignment patterns\n", "-1"),
    ("Proportion of gaps and completely undetermined characters in this alignment: 101%\n", "101")])
def test_impossible_native_counts_and_percentages_remain_failed_with_original_tokens(body, token):
    result = _parse(_log(body))
    assert result["status"] == "partial"
    row = result["value"]["observations"][0]
    assert (row["value"], row["state"], row["raw_token"]) == (None, "failed", token)
