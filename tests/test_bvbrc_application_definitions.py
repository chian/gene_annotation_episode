"""Synthetic preparations against retained official definitions; no remote jobs."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import socket

import pytest

from gene_annotation_episode.bvbrc_application_definitions import (
    REQUIRED_APPLICATION_IDS, get_application_spec, prepare_application,
)
from gene_annotation_episode.bvbrc_analysis_protocol import prepare_rpc_request


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "verification/tool_graders_bvbrc_application_artifacts_2026-10-24"
OUT = {"output_path": "/synthetic@bvbrc/home/Selected folder", "output_file": "Original name"}
READ = "/synthetic@bvbrc/home/reads.fastq"
CONTIGS = "/synthetic@bvbrc/home/contigs.fasta"
GROUP = "/synthetic@bvbrc/home/genome group"
START = {"workspace": "/synthetic@bvbrc/home", "parent_id": "original-parent", "disable_preflight": 0}

# Every value is explicit test input, not an inferred service default. External
# Workspace objects, references, and file contents have not been acquired.
EXAMPLES = {
    "GenomeAssembly2": {"single_end_libs": [{"read": READ}], "recipe": "spades", "genome_size": 1000, "max_bases": 4000},
    "GenomeAnnotation": {"contigs": CONTIGS, "scientific_name": "Synthetic bacterium", "code": 11, "domain": "Bacteria"},
    "ComprehensiveGenomeAnalysis": {"input_type": "contigs", "contigs": CONTIGS, "scientific_name": "Synthetic bacterium", "code": 11, "domain": "Bacteria", "genome_size": 1000},
    "Homology": {"input_type": "dna", "input_source": "fasta_data", "input_fasta_data": ">query\nACGT\n", "db_type": "fna", "db_source": "fasta_data", "db_fasta_data": ">subject\nACGA\n", "blast_program": "blastn", "blast_max_hits": 2},
    "Variation": {"single_end_libs": [{"read": READ}], "reference_genome_id": "123.4", "mapper": "BWA-mem", "caller": "FreeBayes"},
    "TnSeq": {"reference_genome_id": "123.4", "read_files": {"condition-a": {"replicates": [{"read1": READ}]}}, "recipe": "gumbel"},
    "CodonTree": {"genome_ids": ["123.4", "123.5"], "number_of_genes": 2, "bootstraps": 10},
    "GeneTree": {"sequences": [{"type": "aligned_dna_fasta", "filename": CONTIGS}], "alphabet": "DNA", "recipe": "FastTree"},
    "CoreGenomeMLST": {"input_genome_type": "genome_group", "input_genome_group": GROUP, "analysis_type": "chewbbaca", "input_schema_selection": "explicit-selected-schema"},
    "WholeGenomeSNPAnalysis": {"input_genome_type": "genome_group", "input_genome_group": GROUP, "analysis_type": "Whole Genome SNP Analysis", "majority-threshold": 0.5, "min_mid_linkage": 10, "max_mid_linkage": 40},
    "TaxonomicClassification": {"input_type": "contigs", "contigs": CONTIGS, "algorithm": "Kraken2", "database": "Kraken2"},
    "MetagenomeBinning": {"contigs": CONTIGS, "force_local_assembly": False},
    "MetagenomicReadMapping": {"gene_set_type": "feature_group", "gene_set_feature_group": GROUP, "single_end_libs": [{"read": READ}]},
    "RNASeq": {"single_end_libs": [{"sample_id": "sample-A", "read": READ}], "reference_genome_id": "123.4", "genome_type": "bacteria", "recipe": "HTSeq-DESeq"},
    "ViralAssembly": {"single_end_lib": {"read": READ}, "strategy": "irma", "module": "FLU"},
    "GenomeAlignment": {"genome_ids": ["123.4", "123.5"], "recipe": "progressiveMauve"},
    "SARS2Assembly": {"single_end_libs": [{"read": READ}], "primers": "ARTIC", "recipe": "onecodex"},
    "MSA": {"input_type": "input_sequence", "input_status": "unaligned", "fasta_keyboard_input": ">a\nACGT\n>b\nACGA\n", "alphabet": "dna", "aligner": "Muscle"},
    "MetaCATS": {"input_type": "files", "alphabet": "na", "p_value": 0.05, "alignment_file": CONTIGS, "group_file": "/synthetic@bvbrc/home/groups.tsv"},
    "GenomeComparison": {"genome_ids": ["123.4", "123.5"], "reference_genome_index": 1},
    "ComparativeSystems": {"genome_ids": ["123.4", "123.5"]},
    "FastqUtils": {"single_end_libs": [{"read": READ}], "recipe": ["FASTQC"]},
    "InfluenzaHASubtypeConversion": {"input_source": "fasta_data", "input_fasta_data": ">q\nMKT\n", "types": "H1"},
    "SubspeciesClassification": {"input_source": "fasta_data", "input_fasta_data": ">q\nACGT\n", "virus_type": "DENGUE"},
}


def parameters(identity, **overrides):
    return {**deepcopy(OUT), **deepcopy(EXAMPLES[identity]), **overrides}


def codes(result, severity=None):
    return {x["code"] for x in result["diagnostics"] if severity is None or x["severity"] == severity}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure preparation must not use the network")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_fixed_scope_and_hashes_match_all_retained_official_sources():
    rows = json.loads((RESEARCH / "APPLICATIONS.json").read_text())["applications"]
    assert set(EXAMPLES) == set(REQUIRED_APPLICATION_IDS) == {r["required_application_id"] for r in rows}
    assert len(REQUIRED_APPLICATION_IDS) == 24
    for row in rows:
        spec = get_application_spec(row["required_application_id"])
        original = (RESEARCH / row["source_definition"]["file"]).read_bytes()
        assert Path(spec["source"]["retained_path"]).read_bytes() == original
        assert spec["source"]["content"].encode() == original
        assert sha256(original).hexdigest() == spec["source"]["sha256"] == row["source_definition"]["sha256"]
        assert spec["definition"]["id"] == spec["native_id"] == row["source_native_application_id"]
        assert spec["definition"]["parameters"] == row["declared_parameters"]
        assert spec["source"]["git_tree_sha"] == row["source_definition"]["git_tree_sha"]
        assert spec["source"]["git_blob_sha"] == row["source_definition"]["git_blob_sha"]


@pytest.mark.parametrize("identity", REQUIRED_APPLICATION_IDS)
def test_tiny_preparation_preserves_exact_operands_without_defaults(identity):
    supplied = parameters(identity)
    before = deepcopy(supplied)
    result = prepare_application(identity, supplied, START)
    assert result["status"] == "ok", result["diagnostics"]
    native = "HASubtypeNumberingConversion" if identity == "InfluenzaHASubtypeConversion" else identity
    assert result["value"] == {"required_id": identity, "native_application_id": native, "native_params": [native, before, START]}
    assert result["value"]["native_params"][1] is not supplied
    assert supplied == before
    assert "deployment_not_verified" in codes(result, "qualification")
    assert not codes(result, "error")
    assert prepare_rpc_request("AppService.start_app2", result["value"]["native_params"], request_id="synthetic-request") == {
        "version": "1.1", "method": "AppService.start_app2", "params": [native, before, START], "id": "synthetic-request",
    }


def test_only_exact_two_retained_sources_are_transformed():
    expected = {"CoreGenomeMLST": [544, 839], "WholeGenomeSNPAnalysis": [565, 983, 1208]}
    for identity in REQUIRED_APPLICATION_IDS:
        spec = get_application_spec(identity)
        if identity not in expected:
            assert spec["parse_corrections"] == []
            continue
        with pytest.raises(json.JSONDecodeError):
            json.loads(spec["source"]["content"])
        correction, = spec["parse_corrections"]
        assert correction["byte_offsets"] == expected[identity]
        raw = spec["source"]["content"].encode()
        for offset in reversed(correction["byte_offsets"]):
            assert raw[offset:offset + 1] == b","
            raw = raw[:offset] + raw[offset + 1:]
        assert json.loads(raw) == spec["definition"]
        assert sha256(raw).hexdigest() == correction["derived_sha256"]


def test_definition_duplicate_member_is_retained_and_validated_as_integer_enum():
    spec = get_application_spec("GenomeAnnotation")
    assert spec["duplicate_object_keys"] == [{"path": "$.definition.parameters[3].type", "key": "type", "values": ["enum", "int"]}]
    result = prepare_application("GenomeAnnotation", parameters("GenomeAnnotation"), {})
    assert result["status"] == "ok"
    assert "duplicate_definition_member" in codes(result, "qualification")
    for value in (2, "11", True, 11.5):
        result = prepare_application("GenomeAnnotation", parameters("GenomeAnnotation", code=value), {})
        assert result["status"] == "invalid"
    result = prepare_application("GenomeAnnotation", parameters("GenomeAnnotation", code=0), {})
    assert result["value"]["native_params"][1]["code"] == 0
    assert "native_taxonomy_lookup_selected" in codes(result)


@pytest.mark.parametrize("identity,field", [("GenomeAssembly2", "max_bases"), ("ComprehensiveGenomeAnalysis", "genome_size"), ("Variation", "reference_genome_id")])
def test_duplicate_declarations_do_not_block_values_satisfying_both(identity, field):
    spec = get_application_spec(identity)
    assert sum(x.get("id") == field for x in spec["definition"]["parameters"]) == 2
    result = prepare_application(identity, parameters(identity), {})
    assert result["status"] == "ok"
    diagnostic, = [d for d in result["diagnostics"] if d["code"] == "duplicate_parameter_declaration"]
    assert len(diagnostic["declarations"]) == 2
    if identity == "ComprehensiveGenomeAnalysis":
        assert [d["default"] for d in diagnostic["declarations"]] == [5000000, "5000000"]
    if identity == "Variation":
        p = parameters(identity)
        del p[field]
        assert prepare_application(identity, p, {})["status"] == "invalid"


@pytest.mark.parametrize("identity,field,value,code", [
    ("GenomeAssembly2", "genome_size", "1000", "expected_integer"),
    ("GenomeAssembly2", "trim", "false", "expected_boolean_or_native_zero_one"),
    ("MSA", "alphabet", "aa", "value_not_in_native_enum"),
    ("MSA", "aligner", "ClustalW", "value_not_in_native_enum"),
    ("WholeGenomeSNPAnalysis", "majority-threshold", 0.55, "value_not_in_native_enum"),
    ("SubspeciesClassification", "input_source", "id_list", "source_input_mode_not_implemented"),
    ("SubspeciesClassification", "input_source", "genome_group", "source_input_mode_not_implemented"),
    ("FastqUtils", "recipe", ["invented-step"], "unsupported_fastq_step"),
    ("Homology", "input_fasta_data", "", "selected_input_missing"),
    ("MSA", "output_path", [], "required_parameter_missing"),
    ("MSA", "output_file", "nested/output", "output_basename_required"),
])
def test_concrete_invalid_fields(identity, field, value, code):
    result = prepare_application(identity, parameters(identity, **{field: value}), {})
    assert result["status"] == "invalid"
    assert result["value"] is None
    assert code in codes(result, "error")


def test_hyphenated_name_unknown_fields_and_zero_are_preserved():
    p = parameters("WholeGenomeSNPAnalysis", **{"majority-threshold": 0.0, "majority_threshold": 0.5, "extra": {"zero": 0, "missing": None, "text": "0"}})
    result = prepare_application("WholeGenomeSNPAnalysis", p, {})
    assert result["status"] == "ok"
    assert result["value"]["native_params"][1] == p
    unknown = [d["path"] for d in result["diagnostics"] if d["code"] == "unknown_parameter_unvalidated"]
    assert set(unknown) == {"$.parameters.majority_threshold", "$.parameters.extra"}
    assert type(result["value"]["native_params"][1]["majority-threshold"]) is float


def test_nested_groups_native_arrays_and_required_sample_identity():
    bad = parameters("RNASeq", single_end_libs=[{"read": READ}])
    result = prepare_application("RNASeq", bad, {})
    assert any(d["code"] == "required_parameter_missing" and d["path"] == "$.parameters.single_end_libs[0].sample_id" for d in result["diagnostics"])
    assert result["status"] == "invalid"
    bad = parameters("GenomeAssembly2", single_end_libs={"read": READ})
    assert "expected_group_array" in codes(prepare_application("GenomeAssembly2", bad, {}))
    p = parameters("GenomeAssembly2", trim=0, normalize=True)
    result = prepare_application("GenomeAssembly2", p, {})
    assert result["status"] == "ok"
    assert type(result["value"]["native_params"][1]["trim"]) is int
    assert type(result["value"]["native_params"][1]["normalize"]) is bool


def test_gene_tree_real_descriptor_shape_and_unconsumed_controls():
    p = parameters("GeneTree", sequences=[{"type": "feature_ids", "feature_ids": ["fig|123.4.peg.1", "fig|123.4.peg.2"]}], alignment_program="mafft", bootstrap=5)
    result = prepare_application("GeneTree", p, {})
    assert result["status"] == "ok"
    assert {d["path"] for d in result["diagnostics"] if d["code"] == "source_parameter_not_consumed"} == {"$.parameters.alignment_program", "$.parameters.bootstrap"}
    p["sequences"] = ["aligned_dna_fasta"]
    assert prepare_application("GeneTree", p, {})["status"] == "invalid"


def test_tnseq_named_replicates_keep_relationships_and_diagnose_overwrite():
    p = parameters("TnSeq")
    p["read_files"]["condition-a"]["replicates"].append({"read": READ, "read1": "/another"})
    result = prepare_application("TnSeq", p, {})
    assert result["status"] == "invalid"
    assert "producer_would_overwrite_read1" in codes(result)


def test_optional_definition_requires_original_content_identity_and_provenance():
    spec = get_application_spec("MSA")
    assert prepare_application("MSA", parameters("MSA"), {}, definition=spec)["status"] == "ok"
    assert prepare_application("MSA", parameters("MSA"), {}, definition=spec["definition"])["status"] == "invalid"
    mutations = [
        lambda s: s.update(required_id="Homology"),
        lambda s: s.update(native_id="Homology"),
        lambda s: s["source"].update(sha256="0" * 64),
        lambda s: s["definition"]["parameters"].clear(),
        lambda s: s["source"].update(url="https://invented.invalid/contract"),
        lambda s: s["source"].pop("sha256"),
    ]
    for mutate in mutations:
        changed = deepcopy(spec)
        mutate(changed)
        assert prepare_application("MSA", parameters("MSA"), {}, definition=changed)["status"] == "invalid"


def test_service_definition_has_explicit_custody_qualification_and_no_guessed_repair():
    spec = get_application_spec("MSA")
    spec["source"]["kind"] = "retained_service_definition"
    result = prepare_application("MSA", parameters("MSA"), {}, definition=spec)
    assert result["status"] == "ok"
    assert "definition_custody_requires_caller_verification" in codes(result)
    spec["source"]["content"] = spec["source"]["content"].rstrip()[:-1] + ",}"
    spec["source"]["sha256"] = sha256(spec["source"]["content"].encode()).hexdigest()
    result = prepare_application("MSA", parameters("MSA"), {}, definition=spec)
    assert result["status"] == "invalid"
    assert "invalid_definition_json" in codes(result)


def test_different_service_definition_does_not_inherit_stale_producer_semantics():
    # Deliberately synthetic catalogue definition; no claim this was deployed.
    spec = get_application_spec("SubspeciesClassification")
    spec["definition"]["parameters"].append({"id": "input_id_list", "type": "array", "required": 0})
    spec["source"]["kind"] = "retained_service_definition"
    spec["source"]["content"] = json.dumps(spec["definition"])
    spec["source"]["sha256"] = sha256(spec["source"]["content"].encode()).hexdigest()
    p = parameters("SubspeciesClassification", input_source="id_list", input_id_list=["query-A"])
    result = prepare_application("SubspeciesClassification", p, {}, definition=spec)
    assert result["status"] == "ok"
    assert "producer_binding_unverified_for_definition" in codes(result, "qualification")
    assert "source_input_mode_not_implemented" not in codes(result)


def test_explicit_null_and_cga_empty_read_records_have_specific_meanings():
    p = parameters("GenomeAssembly2", min_contig_cov=None)
    result = prepare_application("GenomeAssembly2", p, {})
    assert result["status"] == "invalid"
    assert "expected_finite_number" in codes(result)
    p = parameters("MSA", fasta_files=None)
    result = prepare_application("MSA", p, {})
    assert result["status"] == "ok"
    assert "explicit_null_preserved" in codes(result)
    p = parameters("ComprehensiveGenomeAnalysis", input_type="reads", single_end_libs=[{}])
    result = prepare_application("ComprehensiveGenomeAnalysis", p, {})
    assert result["status"] == "invalid"
    assert "read_input_required" in codes(result)
    p = parameters("ComprehensiveGenomeAnalysis", input_type="genbank", genbank_file="/synthetic@bvbrc/home/genome.gbk")
    result = prepare_application("ComprehensiveGenomeAnalysis", p, {})
    assert result["status"] == "ok"
    assert "source_mode_implementation_unverified" in codes(result, "qualification")


def test_start_parameters_use_shared_native_validator_and_no_defaults():
    start = {"workspace": "/user/home", "parent_id": "42", "base_url": "https://example.invalid", "user_metadata": "original text", "disable_preflight": 0, "user_override": "explicit-user", "constraint": "explicit-selection"}
    result = prepare_application("MSA", parameters("MSA"), start)
    assert result["status"] == "ok", result["diagnostics"]
    assert result["value"]["native_params"][2] == start
    for invalid in ({"disable_preflight": True}, {"workspace": 4}, {"memory": "1G"}):
        result = prepare_application("MSA", parameters("MSA"), invalid)
        assert result["status"] == "invalid"
        assert any(d["path"].startswith("$.start_parameters") for d in result["diagnostics"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), (1, 2), {1: "value"}])
def test_non_json_unknown_values_never_escape_preparation(value):
    result = prepare_application("MSA", parameters("MSA", extra=value), {})
    assert result["status"] == "invalid"


def test_fresh_specs_and_unknown_required_id():
    first = get_application_spec("MSA")
    first["definition"]["parameters"].clear()
    assert get_application_spec("MSA")["definition"]["parameters"]
    for identity in ("MinHash", "PrimerDesign", "Docking", "HASubtypeNumberingConversion", None):
        with pytest.raises(ValueError):
            get_application_spec(identity)
        assert prepare_application(identity, {}, {})["status"] == "invalid"
