"""Native-source replays/fixtures and an explicitly opted-in bounded live lookup."""
import pytest

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.chemistry import rhea_equation


@pytest.mark.parametrize('arrow,direction',[('=','undefined'),('=>','left_to_right'),('<=','right_to_left'),('<=>','bidirectional')])
def test_synthetic_equation_direction_and_symbolic_coefficient_are_not_physiology(arrow,direction):
    # Synthetic markup exercises the notation parser, not a claim that the
    # current JSON search exposes directional-quartet entries.
    html=('<span class="participant"><span class="stoichiometry">n+1</span>'
          '<a data-molid="rhea-comp:7">a carrier+</a><span class="location">(out)</span></span>'
          ' '+arrow.replace('<','&lt;').replace('>','&gt;')+' '
          '<span class="participant"><span class="stoichiometry"> </span>'
          '<a data-molid="chebi:15377">H<sub>2</sub>O</a></span>')
    actual_arrow,actual_direction,parts=rhea_equation(html)
    assert (actual_arrow,actual_direction)==(arrow,direction)
    assert parts[0]['coefficient_expression']=='n+1' and parts[0]['source_name']=='a carrier+'
    assert parts[0]['source_location']=='(out)' and parts[0]['side']=='left'
    assert parts[1]['source_name']=='H2O' and parts[1]['side']=='right'
    assert parts[1]['coefficient_basis']=='implicit_unit_rhea_notation'


@pytest.mark.parametrize('limit', [True, False, 0, -1, None, 1.5])
def test_rhea_response_byte_limit_requires_positive_integer(limit):
    with pytest.raises(ValueError, match='invalid_rhea_response_byte_limit'):
        PublicClients(ncbi_email=None, rhea_response_byte_limit=limit)


@pytest.mark.parametrize('body,limit,expected,failure', [
    (b'abcd', 4, b'abcd', None), (b'abcd', 3, b'abc', 'provider_response_byte_limit'),
    (b'abc', 8, b'abc', 'provider_body_capture_failed')])
def test_existing_unencoded_bounded_reader_keeps_original_metadata_contract(body, limit, expected, failure):
    import io
    response = io.BytesIO(body)
    response.headers = {'Content-Length': '4'}
    raw, metadata, actual_failure = PublicClients._read_bounded_response(response, limit)
    assert raw == expected and actual_failure == failure
    expected_metadata = {'body_complete': failure is None, 'response_byte_limit': limit,
        'observed_body_bytes': len(body), 'retained_body_bytes': len(expected), 'declared_body_bytes': 4}
    if failure is not None:
        expected_metadata['body_capture_failure'] = failure
    if failure == 'provider_body_capture_failed':
        expected_metadata['body_capture_error'] = 'IncompleteRead'
    assert metadata == expected_metadata


@pytest.mark.parametrize('limit', [True, False, 0, -1, None, 1.5])
def test_chebi_response_byte_limit_requires_positive_integer(limit):
    with pytest.raises(ValueError, match='invalid_chebi_response_byte_limit'):
        PublicClients(ncbi_email=None, chebi_response_byte_limit=limit)
