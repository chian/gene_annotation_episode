"""Authenticate existing fixture quotations before selecting their byte locations."""


def verified_source_locations(store, value):
    if isinstance(value, list):
        return [verified_source_locations(store, item) for item in value]
    if not isinstance(value, dict):
        return value
    fields = set(value)
    witness = fields in (
        {'source_ref', 'representation', 'start', 'end', 'quote'},
        {'source_ref', 'artifact_ref', 'start', 'end', 'quote'},
    ) or fields == {'kind', 'source_ref', 'representation', 'start', 'end', 'quote'} and value['kind'] == 'text'
    if witness:
        source = store.get(value['source_ref'])
        artifact = value.get('artifact_ref') or source['artifact_ref' if value['representation'] == 'original' else 'text_ref']
        assert artifact in (source['artifact_ref'], source.get('text_ref'))
        actual = store.get_artifact(artifact)[value['start']:value['end']].decode('utf-8')
        assert actual == value['quote'], 'Original fixture quote must match the retained UTF-8 bytes'
        return {key: item for key, item in value.items() if key != 'quote'}
    return {key: verified_source_locations(store, item) for key, item in value.items()}
