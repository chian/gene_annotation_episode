"""Retained native parser/custody checks; no acquisition, publication or credit."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.library import infernal_search_inputs as inputs
from gene_annotation_episode.episodic_workflow.root.library.infernal_search_grader import calculate_infernal_search_scores
from gene_annotation_episode.episodic_workflow.root.library.uniprot_response_custody import (
    parse_uniprot_snapshot, uniprot_page_metadata)

FIXTURES = Path(__file__).parent / 'fixtures/tool_parser_custody/infernal'
UNIPROT = Path(__file__).parent / 'fixtures/tool_parser_custody/uniprot'


def metadata():
    seqs = []
    for block in (FIXTURES / "tiny.fa").read_text().split(">")[1:]:
        name, *lines = block.splitlines()
        sequence = "".join(lines)
        seqs.append({"name": name, "sequence": sequence, "length": len(sequence)})
    return seqs, [{"name": "tRNA5", "consensus_length": 72}, {"name": "tRNA5-hand", "consensus_length": 74}]


def artifact(name="cmsearch_fmt3", *, content=None, complete=True, table_format=None, artifact_id=None):
    if table_format is None:
        table_format = 2 if name.startswith("cmscan") and "no_hits" in name else int(name[-1]) if "fmt" in name else 3
    return {"artifact_id": artifact_id or name, "format": "infernal_tblout", "table_format": table_format,
            "complete": complete, "content": (FIXTURES / (name+".hits.tbl")).read_text() if content is None else content}


def populate(arts=None, *, program="cmsearch", supplied=True, sequence_metadata=None, model_metadata=None, **operation):
    seqs, models = metadata()
    return inputs.populate_infernal_search_sheet(arts or [artifact()],
        operation={"program": program, "native_version": "1.1.5", "settings": {}, **operation},
        sequence_metadata=sequence_metadata if sequence_metadata is not None else seqs if supplied else None,
        model_metadata=model_metadata if model_metadata is not None else models if supplied else None)


def codes(value):
    return {r["code"] for r in value["issues"]}


@pytest.mark.parametrize("program,fmt", [("cmsearch",1),("cmsearch",3),("cmscan",1),("cmscan",2),("cmscan",3)])
def test_actual_native_formats_roles_numerators_and_denominators(program, fmt):
    native = artifact(f"{program}_fmt{fmt}")
    sheet = populate([native], program=program)
    assert sheet["status"] == "available"
    assert len(sheet["hits"]) == 10
    assert sheet["artifacts"][0]["content"] == native["content"]
    assert sheet["artifacts"][0]["native_complete"] is True
    assert [h["locator"]["line"] for h in sheet["hits"]] == list(range(3, 13))
    first = sheet["hits"][0]
    assert first["sequence"]["name"] == "native_forward"
    assert first["model"]["name"] == "tRNA5"
    assert first["sequence"]["native_role"] == ("target" if program == "cmsearch" else "query")
    assert first["model"]["native_role"] == ("query" if program == "cmsearch" else "target")
    assert first["bitscore"] == 71.4
    assert first["bias_bits"] == 0
    assert first["gc_fraction"] == .5
    assert first["evalue"] == (1.9e-22 if program == "cmsearch" else 6.7e-23)
    assert all(h["inclusion"] == "?" for h in sheet["hits"])
    scores = calculate_infernal_search_scores(sheet)
    assert scores["status"] == "available"
    assert scores["hits"][0]["components"]["model_span_fraction"] == 1
    repeat = next(g for g in scores["sequence_strand_aggregates"] if g["sequence_names"] == ["native_repeat"])
    assert repeat["hit_count"] == 4
    assert repeat["union_intervals"] == [[0,72],[122,194]]
    assert repeat["union_numerator"] == 144
    assert repeat["union_denominator"] == 194
    assert repeat["union_span_fraction"] == pytest.approx(144/194)
    assert repeat["valid_geometry_count"] == 4
    assert repeat["span_sum"] == 288 and repeat["overlap_excess"] == 144
    assert len(repeat["overlap_memberships"]) == 2
    assert len(repeat["identical_interval_memberships"]) == 2


@pytest.mark.parametrize("program", ["cmsearch", "cmscan"])
def test_actual_native_no_hits_are_available_not_missing(program):
    sheet = populate([artifact(program+"_no_hits")], program=program, supplied=False)
    assert sheet["status"] == "available"
    assert sheet["hits"] == []
    scores = calculate_infernal_search_scores(sheet)
    assert scores["status"] == "available"
    assert scores["hits"] == scores["sequence_strand_aggregates"] == []


def test_missing_denominators_and_identity_preserve_native_measurements():
    sheet = populate([artifact("cmsearch_fmt1")], supplied=False)
    scores = calculate_infernal_search_scores(sheet)
    c = scores["hits"][0]["components"]
    assert c["bitscore"] == 71.4 and c["sequence_span_length"] == 72
    assert c["sequence_span_fraction"] is None and c["model_span_fraction"] is None
    assert scores["sequence_strand_aggregates"] == []
    assert len(scores["unresolved_aggregate_hit_ids"]) == 10
    assert "length_denominator_missing" in codes(sheet)


def test_unknown_settings_remain_absent_and_unknown_completion_is_not_no_hit():
    sheet = populate([artifact(content="",complete=None)], supplied=False,native_version=None)
    assert sheet["status"] == "missing"
    assert sheet["operation"]["settings"] == {}
    text = "\n".join(artifact()["content"].splitlines()[:12]) + "\n"
    partial = populate([artifact(content=text,complete=None)],native_version=None)
    assert partial["status"] == "partial"
    assert partial["artifacts"][0]["effective_complete"] is None
    assert "native_version_unknown" in codes(partial)
    assert len(partial["hits"]) == 10


def test_saved_sheet_recalculation_uses_no_native_text_parser_network_or_process(monkeypatch):
    sheet=json.loads(json.dumps(populate()))
    expected=calculate_infernal_search_scores(sheet)
    def forbidden(*args,**kwargs):
        raise AssertionError("parser/acquisition/execution forbidden during recalculation")
    monkeypatch.setattr(inputs,"populate_infernal_search_sheet",forbidden)
    monkeypatch.setattr(inputs,"_read_artifact",forbidden)
    monkeypatch.setattr(subprocess,"Popen",forbidden)
    monkeypatch.setattr(subprocess,"run",forbidden)
    monkeypatch.setattr(socket,"socket",forbidden)
    monkeypatch.setattr(Path,"read_text",forbidden)
    for art in sheet["artifacts"]:
        art["content"]="native text intentionally unavailable to calculator"
        art["rows"]=[]
    recalculated = calculate_infernal_search_scores(sheet)
    # New calculations authenticate their exact saved sheet. Editing retained
    # text changes that digest even though arithmetic uses only saved cells.
    assert recalculated["sheet_digest"] != expected["sheet_digest"]
    assert {k:v for k,v in recalculated.items() if k != "sheet_digest"} == {
        k:v for k,v in expected.items() if k != "sheet_digest"}
    included=calculate_infernal_search_scores(sheet,parameters={"hit_scope":"included"})
    assert all(g["hit_count"]==0 for g in included["sequence_strand_aggregates"])


def test_no_input_mutation_and_finite_json_validation():
    arts=[artifact()]
    before=deepcopy(arts)
    sheet=populate(arts)
    saved=deepcopy(sheet)
    calculate_infernal_search_scores(sheet)
    assert arts==before and sheet==saved
    with pytest.raises(ValueError,match="finite_json"):
        populate(arts,settings={"value":float("nan")})
def retained_uniprot_snapshot():
    """Actual retained bytes/request/transport in a labelled reader-only carrier.

    The original fixture does not retain a retrieval timestamp. The unused
    carrier field is deliberately labelled, never invented as a new retrieval.
    """
    content = (UNIPROT / 'P0AAW1.json').read_bytes()
    metadata_bytes = (UNIPROT / 'P0AAW1.transport.json').read_bytes()
    assert hashlib.sha256(content).hexdigest() == 'dc1e11907d2d7a9ea423dd90e9f6bea7393cdf21669d139b1b04e1a8647d0e3e'
    assert hashlib.sha256(metadata_bytes).hexdigest() == 'c2c89095b2d4c9662cf65535768b4720a8dc094ffa3426bb54e4d933ada1c952'
    saved = json.loads(metadata_bytes)
    return SourceSnapshot('uniprot', saved['transport']['response']['url'], saved['request'],
        'reader-fixture-only: retrieval-time-not-retained', content, 'application/json', saved['transport'])


def test_original_uniprot_custody_reads_actual_retained_record_and_page_metadata():
    snapshot = retained_uniprot_snapshot()
    before = deepcopy(snapshot)
    parsed = parse_uniprot_snapshot(snapshot, request={'operation': 'record', 'accession': 'P0AAW1'})
    record = parsed['records'][0]
    assert record['identity']['primary_accession'] == 'P0AAW1'
    assert record['identity']['accession_relation'] == 'primary'
    assert record['sequence']['observed_length_aa'] == 253
    assert record['sequence']['length_relation'] == 'agree'
    assert uniprot_page_metadata(parsed) == {
        'next_cursor': None, 'total_results': None, 'release': '2026_03',
        'release_date': '02-September-2026', 'pagination_metadata_available': True}
    assert snapshot == before


@pytest.mark.parametrize('change,error', [
    ('service', 'uniprot_response_required'),
    ('missing_request', 'request_missing_accession'),
    ('wrong_request', 'request_conflict_accession'),
    ('extra_request', 'request_invalid'),
    ('http_failure', 'http_response_not_successful'),
    ('wrong_method', 'request_method_conflict'),
    ('invalid_headers', 'headers_invalid'),
])
def test_uniprot_original_reader_rejects_changed_custody_before_projecting(change, error):
    snapshot = retained_uniprot_snapshot()
    if change == 'service':
        snapshot = replace(snapshot, service='unrelated')
    elif change == 'missing_request':
        snapshot = replace(snapshot, request={})
    elif change == 'wrong_request':
        snapshot = replace(snapshot, request={'accession': 'P75772'})
    elif change == 'extra_request':
        snapshot = replace(snapshot, request={**snapshot.request, 'unselected': True})
    else:
        transport = deepcopy(snapshot.transport)
        key, value = {'http_failure': ('status', 503), 'wrong_method': ('request_method', 'POST'),
            'invalid_headers': ('headers', [])}[change]
        transport['response'][key] = value
        snapshot = replace(snapshot, transport=transport)
    with pytest.raises(ValueError, match=error):
        parse_uniprot_snapshot(snapshot, request={'operation': 'record', 'accession': 'P0AAW1'})


def test_selected_original_infernal_fixture_bytes_match_retained_manifest():
    manifest = {row['path']: row['sha256'] for row in json.loads((FIXTURES / 'MANIFEST.json').read_bytes())}
    for path in FIXTURES.iterdir():
        if path.name in manifest:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[path.name]
    required = {'tiny.fa', 'cmsearch_fmt1.hits.tbl', 'cmsearch_fmt3.hits.tbl',
        'cmscan_fmt1.hits.tbl', 'cmscan_fmt2.hits.tbl', 'cmscan_fmt3.hits.tbl',
        'cmsearch_no_hits.hits.tbl', 'cmscan_no_hits.hits.tbl'}
    assert required <= manifest.keys()
    assert all((FIXTURES / name).is_file() for name in required)
