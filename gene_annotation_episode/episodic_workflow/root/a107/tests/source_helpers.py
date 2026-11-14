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
