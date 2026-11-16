"""Labelled synthetic material allocations; no model or external measurements."""
from copy import deepcopy

import pytest

from gene_annotation_episode.state import Store


def source_fixture(store, label):
    artifact = store.artifact('Labelled synthetic fixture: '+label)
    return store.put('source', {'provider': 'synthetic_fixture', 'accession': label,
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'fixture', 'retrieved_at': None}, origin='external')


