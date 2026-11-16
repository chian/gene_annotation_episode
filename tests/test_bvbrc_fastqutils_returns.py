"""Saved numerical projection and reversible communication, without host custody.

Actual executor custody/Workflow tests are separate. These synthetic envelopes
cannot prove transport, original commissioning or service deployment.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import uuid

import pytest

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode.episodic_workflow.root.bvbrc_appservice_publication import RESULT_VERSION
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_returns import FACT_SOURCES, fastqutils_fact_sources, parent_form_schema, project_fastqutils_return_facts
from gene_annotation_episode.execution_contracts import canonical, digest

spec = importlib.util.spec_from_file_location('fastq_return_fixtures',
    Path(__file__).resolve().parents[1] / 'gene_annotation_episode/episodic_workflow/root/tests/fixtures/bvbrc_fastqutils/bundle/fixture_support.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def content(value, source=None):
    sha = digest(value)
    return {'source_ref': source or 'source_' + sha[:24], 'artifact_field': 'artifact_ref',
        'artifact_ref': 'artifact_' + sha, 'sha256': sha,
        'byte_count': len(canonical(value).encode())}


def saved_fixture(data=None, fields=None):
    if data is None:
        data, fields = f.seven_family_data()
    bundle, raw, values, parameters = data
    # C's schema-only fixture changes the path without the parallel original
    # task association. This host-contract fixture explicitly declares the
    # same synthetic path on both sides before parsing, never after saving.
    for artifact in bundle['artifacts']:
        synthetic_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'synthetic-fastqutils:' + artifact['workspace_object']['path']))
        artifact['workspace_object']['uuid'] = synthetic_uuid
        artifact['task_association']['output_path'] = artifact['workspace_object']['path']
        artifact['task_association']['output_uuid'] = synthetic_uuid
    selected = f.oracle('RESULT_SELECTOR_PRE_DOWNLOAD_002.json')
    selected.update(requested_schema=f.schema(fields), adapter={
        'adapter_id': adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION,
        'parameters': parameters})
    bundle['requested_selector_sha256'] = digest(selected)
    result = f.run(data, fields)
    sheet, components = result['sheet'], result['components']
    saved = {key: deepcopy(result[key]) for key in
        ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
    saved.update(sheet_content=content(sheet), components_content=content(components))
    source = 'source_' + digest(bundle)[:24]
    body = {'version': RESULT_VERSION, 'source_ref': source, 'reference': source, 'record_refs': [source],
        'assignment': {'selector': selected}, 'publication_inputs': {'selector': selected,
            'adapter': selected['adapter'], 'adapter_implementation_sha256': adapter.implementation_sha256()},
        'bundle': bundle, 'publication': {'bundle_content': content(bundle, source),
            'result_record_refs': [source], 'adapter_result': saved}}
    return body, sheet, components


@pytest.fixture
def retained():
    value = saved_fixture()
    projected(value)  # Adverse cases must start with a valid saved publication.
    return value


def projected(retained):
    body, sheet, components = retained
    return project_fastqutils_return_facts(body, requested_sources=FACT_SOURCES, sheet=sheet, components=components)


def test_schema_descriptors_are_isolated_and_empty_selection_is_no_work():
    before = fastqutils_fact_sources()
    changed = fastqutils_fact_sources()
    changed[FACT_SOURCES[0]]['report_schema']['items']['properties'].clear()
    assert fastqutils_fact_sources() == before
    assert project_fastqutils_return_facts(None, requested_sources=(), sheet=None, components=None) == {}
    with pytest.raises(ValueError):
        project_fastqutils_return_facts(None, requested_sources=('invented',), sheet=None, components=None)
