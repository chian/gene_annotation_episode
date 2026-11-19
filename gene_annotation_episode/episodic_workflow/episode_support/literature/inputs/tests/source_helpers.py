"""Source and literal-witness constructors used by A107 partner tests."""


def source(store, raw, *, parents=(), text=None):
    artifact = store.artifact(raw, 'application/octet-stream')
    text_ref = store.artifact(text, 'text/plain') if text is not None else None
    return store.put('source', {'provider': 'source_reaction_example', 'accession': None,
        'uri': None, 'artifact_ref': artifact, 'text_ref': text_ref, 'request_ref': None,
        'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)},
        origin='caller')


def witness(ref, raw, quote, representation='original'):
    token = quote.encode('utf-8')
    start = raw.index(token)
    return {'source_ref': ref, 'representation': representation, 'start': start,
            'end': start + len(token), 'quote': quote}


_LOCATION_FORMS = (
    {'source_ref', 'artifact_ref', 'start', 'end', 'quote'},
    {'source_ref', 'representation', 'start', 'end', 'quote'},
    {'kind', 'source_ref', 'representation', 'start', 'end', 'quote'},
)


def location_inputs(value):
    """Tool-argument form of literal witnesses: the source interval without its quotation."""
    if isinstance(value, list):
        return [location_inputs(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: location_inputs(item) for key, item in value.items()}
    if set(result) in _LOCATION_FORMS:
        del result['quote']
    return result


def source_artifacts(store, value):
    """Artifacts of every source selected anywhere in tool arguments."""
    references = set()

    def collect(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in ('source_ref', 'data_source_ref', 'metadata_source_ref') and isinstance(child, str):
                    references.add(child)
                else:
                    collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)
    collect(value)
    return {record[name] for record in map(store.get, sorted(references))
            for name in ('artifact_ref', 'text_ref') if record.get(name) is not None}
