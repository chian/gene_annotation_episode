"""Saved article replay and synthetic XML; no biological truth/model tests."""
from pathlib import Path
import hashlib
import json
import pytest
from xml.etree import ElementTree as ET

from gene_annotation_episode.acquisition import SourceSnapshot, article_details
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


class SavedArticle:
    def __init__(self, body, *, pmcid='PMC12608037'):
        self.body, self.calls, self.pmcid = body, 0, pmcid

    def literature_read(self, pmcid):
        self.calls += 1
        assert pmcid == self.pmcid
        return SourceSnapshot("europepmc", "https://example.invalid/explicit-source-replay",
            {"pmcid": pmcid}, "2026-10-20T02:15:00+00:00", self.body,
            "application/xml", {"representation": "explicit_saved_or_synthetic_fixture_no_network"})


def test_saved_primary_original_heading_is_readable_and_anchorable(tmp_path):
    fixture = Path(__file__).parent / 'fixtures/PMC8874281.xml'
    body = fixture.read_bytes()
    provenance = json.loads(fixture.with_suffix('.provenance.json').read_text())
    assert len(body) == provenance['bytes']
    assert hashlib.sha256(body).hexdigest() == provenance['sha256']
    heading = 'Yeast Growth and Complementation'
    assert heading in ["".join(n.itertext()) for n in ET.fromstring(body).findall(".//sec/title")]
    with Store(tmp_path) as store:
        initial = store.create_problem(raw_sequence="MKWAA", molecule="protein")
        clients = SavedArticle(body, pmcid='PMC8874281')
        tools = ToolRegistry(store, clients=clients)
        imported = tools.execute("public.literature.read", {"pmcid": "PMC8874281"}, operation_key="saved-primary")
        assert imported["status"] == "completed", imported
        result = imported["result"]
        source = store.get(result["source_ref"])
        assert store.get_artifact(source["artifact_ref"]) == body
        assert heading not in store.get_artifact(source["text_ref"]).decode()
        assert result["text_representation"] == "ordered_paragraph_projection"
        query = {**result["original_read_query"], "offset": body.index(heading.encode()), "limit": len(heading.encode())}
        selected = tools.execute("source.read", query)["result"]
        assert selected["text"] == heading and selected["representation"] == "original"
        assert selected["artifact_ref"] == source["artifact_ref"]
        anchor = {key: selected[key] for key in ("source_ref", "artifact_ref", "start", "end")}
        anchor["quote"] = selected["text"]
        context = store.put("context", {"context_type": "processing", "name": heading,
            "source_ref": source["id"], "attributes": [], "related_refs": [], "anchor": anchor}, origin="extracted")
        assert context["anchor"] == anchor
        default = tools.execute("source.read", {"source_ref": source["id"], "limit": 100})["result"]
        assert default["representation"] == "text" and default["artifact_ref"] == source["text_ref"]
        assert tools.execute("public.literature.read", {"pmcid": "PMC8874281"}, operation_key="saved-primary") == imported
        assert clients.calls == 1 and store.problem() == initial and project_credit(store).credit == 0


def test_original_table_paging_preserves_bytes_without_complete_hydration(tmp_path, monkeypatch):
    # Separate synthetic fixture isolates byte paging of table content omitted
    # from the paragraph projection.
    body = ("<article><body><sec><title>Controls</title><p>synthetic paragraph</p>"
            "<table-wrap><table><tr><td>medium_control_α</td><td>5</td></tr></table></table-wrap>"
            "</sec></body></article>").encode()
    with Store(tmp_path) as store:
        initial = store.create_problem(raw_sequence="MKWAA", molecule="protein")
        tools = ToolRegistry(store, clients=SavedArticle(body))
        imported = tools.execute("public.literature.read", {"pmcid": "PMC12608037"})
        source = store.get(imported["result"]["source_ref"])
        assert b"medium_control" not in store.get_artifact(source["text_ref"])
        def no_hydration(*args, **kwargs):
            raise AssertionError("bounded reading hydrated a complete artifact")
        monkeypatch.setattr(store, "get_artifact", no_hydration)
        query = {"source_ref": source["id"], "representation": "original", "limit": 31}
        chunks = []
        while query is not None:
            result = tools.execute("source.read", query)
            assert result["status"] == "completed", result
            page = result["result"]
            assert page["artifact_ref"] == source["artifact_ref"] and page["representation"] == "original"
            assert page["end"] - page["start"] <= 31
            chunks.append(page["text"])
            query = page["next_query"]
        assert "".join(chunks).encode() == body
        assert store.problem() == initial and project_credit(store).credit == 0


def test_failed_xml_projection_retains_source_and_replays_partial_outcome(tmp_path):
    body = b"<article><body><p>synthetic malformed source"
    clients = SavedArticle(body)
    with Store(tmp_path) as store:
        initial = store.create_problem(raw_sequence="MKWAA", molecule="protein")
        tools = ToolRegistry(store, clients=clients)
        args = {"pmcid": "PMC12608037"}
        first = tools.execute("public.literature.read", args, operation_key="bad-projection")
        assert first["status"] == "partial", first
        assert first["feedback"]["code"] == "literature_xml_parse_failed"
        retained = [store.get(ref) for ref in first["record_refs"]]
        assert len(retained) == 1 and retained[0]["record_type"] == "source"
        original = retained[0]
        assert original["text_ref"] is None and store.get_artifact(original["artifact_ref"]) == body
        assert tools.execute("public.literature.read", args, operation_key="bad-projection") == first
        assert clients.calls == 1 and store.problem() == initial and not store.list("observation")
    with Store(tmp_path) as reopened:
        result = ToolRegistry(reopened).execute("source.read", {"source_ref": original["id"], "representation": "original"})
        assert result["status"] == "completed" and result["result"]["text"].encode() == body
        assert project_credit(reopened).credit == 0


def test_primary_publication_ids_ignore_citations_subarticles_and_representation_aliases():
    body = b'''<article xmlns="urn:synthetic-jats"><front><article-meta>
      <article-id pub-id-type="pmcid">PMC12608037</article-id>
      <article-id pub-id-type="pmid">12345678</article-id>
      <article-id pub-id-type="doi">https://doi.org/10.1234/SYNTHETIC</article-id>
      <article-id pub-id-type="doi">10.1234/synthetic</article-id>
    </article-meta></front><body><p>Explicit synthetic paragraph.</p></body>
    <back><ref-list><ref><article-id pub-id-type="doi">10.9999/cited</article-id></ref></ref-list></back>
    <sub-article><front><article-meta><article-id pub-id-type="doi">10.9999/other</article-id></article-meta></front></sub-article>
    </article>'''
    result = article_details(body)
    assert result['publication_identifiers'] == [
        {'namespace': 'doi', 'value': '10.1234/synthetic'},
        {'namespace': 'pmcid', 'value': 'PMC12608037'},
        {'namespace': 'pmid', 'value': '12345678'}]
    assert result['metadata_issues'] == []
    assert result['sections'] == [{'paragraph_index': 0, 'text': 'Explicit synthetic paragraph.'}]
    # A citation in a document with no primary metadata is not its identity.
    assert article_details(b'<article><back><article-id pub-id-type="pmcid">PMC9</article-id></back></article>')['publication_identifiers'] == []


def test_reacquisition_keeps_publication_identity_without_creating_scientific_credit(tmp_path):
    body = b'''<article><front><article-meta>
      <article-id pub-id-type="pmc">12608037</article-id>
      <article-id pub-id-type="doi">10.1234/synthetic</article-id>
    </article-meta></front><body><p>synthetic source</p></body></article>'''
    with Store(tmp_path) as store:
        initial = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        clients = SavedArticle(body)
        tools = ToolRegistry(store, clients=clients)
        first = tools.execute('public.literature.read', {'pmcid': 'PMC12608037'}, operation_key='first')
        clients.body = body.replace(b'<body>', b'\n<body>')
        second = tools.execute('public.literature.read', {'pmcid': 'PMC12608037'}, operation_key='second')
        one, two = [store.get(result['result']['source_ref']) for result in (first, second)]
        assert one['id'] != two['id'] and one['artifact_ref'] != two['artifact_ref']
        assert one['publication_identifiers'] == two['publication_identifiers'] == [
            {'namespace': 'doi', 'value': '10.1234/synthetic'},
            {'namespace': 'pmcid', 'value': 'PMC12608037'}]
        assert first['result']['metadata_issues'] == second['result']['metadata_issues'] == []
        assert clients.calls == 2
        assert store.problem() == initial and project_credit(store).credit == 0
        assert not store.list('assessment') and not store.list('annotation')
        assert tools.execute('public.literature.read', {'pmcid': 'PMC12608037'}, operation_key='first') == first
        assert clients.calls == 2


def test_invalid_conflicting_or_mismatched_metadata_does_not_discard_article(tmp_path):
    body = b'''<article><front><article-meta>
      <article-id pub-id-type="doi">invalid DOI</article-id>
      <article-id pub-id-type="pmcid">PMC2</article-id>
      <article-id pub-id-type="pmcid">PMC3</article-id>
    </article-meta></front><body><p>synthetic retained paragraph</p></body></article>'''
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        result = ToolRegistry(store, clients=SavedArticle(body)).execute(
            'public.literature.read', {'pmcid': 'PMC12608037'})
        assert result['status'] == 'completed'
        payload = result['result']
        assert {issue['code'] for issue in payload['metadata_issues']} == {
            'invalid_publication_identifier', 'conflicting_publication_identifiers',
            'requested_publication_identifier_mismatch'}
        source = store.get(payload['source_ref'])
        assert source['accession'] == 'PMC12608037'
        assert source['publication_identifiers'] == [
            {'namespace': 'pmcid', 'value': 'PMC2'}, {'namespace': 'pmcid', 'value': 'PMC3'}]
        assert store.get_artifact(source['artifact_ref']) == body
        assert store.get_artifact(source['text_ref']) == b'synthetic retained paragraph'
        assert project_credit(store).credit == 0


@pytest.mark.parametrize('header', [
    '<front><article-meta><article-id pub-id-type="pmcid">PMC2</article-id></article-meta>'
    '<article-meta><article-id pub-id-type="pmcid">PMC3</article-id></article-meta></front>',
    '<front><article-meta><article-id pub-id-type="pmcid">PMC2</article-id></article-meta></front>'
    '<front><article-meta><article-id pub-id-type="pmcid">PMC3</article-id></article-meta></front>',
])
def test_multiple_primary_headers_do_not_silently_choose_an_identity(tmp_path, header):
    body = ('<article>'+header+'<body><p>synthetic retained text</p></body></article>').encode()
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        outcome = ToolRegistry(store, clients=SavedArticle(body)).execute(
            'public.literature.read', {'pmcid': 'PMC12608037'})
        assert outcome['status'] == 'completed'
        result = outcome['result']
        assert result['publication_identifiers'] == []
        assert result['metadata_issues'][0]['code'] == 'ambiguous_primary_article_metadata'
        source = store.get(result['source_ref'])
        assert 'publication_identifiers' not in source
        assert store.get_artifact(source['artifact_ref']) == body
        assert store.get_artifact(source['text_ref']) == b'synthetic retained text'


def test_oversized_numeric_metadata_cannot_prevent_article_retention(tmp_path):
    body = ('<article><front><article-meta><article-id pub-id-type="pmc">'
            +'1'*5000+'</article-id></article-meta></front>'
            '<body><p>synthetic retained text</p></body></article>').encode()
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        outcome = ToolRegistry(store, clients=SavedArticle(body)).execute(
            'public.literature.read', {'pmcid': 'PMC12608037'})
        assert outcome['status'] == 'completed'
        result = outcome['result']
        assert result['publication_identifiers'] == []
        assert result['metadata_issues'] == [{'code': 'invalid_publication_identifier',
            'namespace': 'pmcid', 'metadata_child_index': 0}]
        source = store.get(result['source_ref'])
        assert store.get_artifact(source['artifact_ref']) == body
        assert store.get_artifact(source['text_ref']) == b'synthetic retained text'
