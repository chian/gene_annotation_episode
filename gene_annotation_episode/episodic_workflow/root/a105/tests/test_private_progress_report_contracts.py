"""Transport recognizes exact private progress reports without owning progress."""
from copy import deepcopy
from importlib import import_module

import pytest

from .test_private_literature_bindings import binding
from gene_annotation_episode.episodic_workflow.root.a105.communication import (
    ReportBoundaryError, validate_closed_schema)
from gene_annotation_episode.episodic_workflow.root.a105.domain import obj


@pytest.mark.parametrize('schema_name', ['lead_return_schema', 'screening_schema'])
def test_transport_accepts_only_original_private_progress_report(binding, schema_name):
    module = import_module(type(binding).__module__.rsplit('.', 1)[0] + '.credit')
    schema = obj({'answers': getattr(module, schema_name)()})
    assert validate_closed_schema(schema) == schema
    altered = deepcopy(schema)
    altered['properties']['answers']['items']['properties']['annotation_support'] = {'const': 'invented_support'}
    with pytest.raises(ReportBoundaryError, match='literature task fact schema must match'):
        validate_closed_schema(altered)
