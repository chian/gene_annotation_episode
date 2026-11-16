"""Saved article replay and synthetic XML; no biological truth/model tests."""
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot, article_details
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


class SavedArticle:
    def __init__(self, body, *, pmcid='PMC12608037'):
        self.body, self.calls, self.pmcid = body, 0, pmcid

    def literature_read(self, pmcid):
        self.calls += 1
        assert pmcid == self.pmcid
        return SourceSnapshot("europepmc", "https://example.invalid/explicit-source-replay",
            {"pmcid": pmcid}, "2026-10-20T02:15:00+00:00", self.body,
            "application/xml", {"representation": "explicit_saved_or_synthetic_fixture_no_network"})


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
