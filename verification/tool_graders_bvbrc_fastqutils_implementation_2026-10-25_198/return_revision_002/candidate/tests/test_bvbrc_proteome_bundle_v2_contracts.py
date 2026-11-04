"""Explicit version/selection schemas and pre-acquisition cross checks."""
from copy import deepcopy
import ast
from pathlib import Path

import pytest
from gene_annotation_episode import bvbrc_proteome_bundle_v2_contracts as c
from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as adapter
from gene_annotation_episode import bvbrc_proteome_bundle_adapter as old
from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
from test_bvbrc_proteome_bundle_v2_resolution import fixture,selector


@pytest.mark.parametrize('mutation',[
    lambda p:p.update(extra=1),lambda p:p.update(analysis_id=' '),
    lambda p:p.update(primary_document_id='phantom'),lambda p:p.update(directional_documents=[]),
    lambda p:p['directional_documents'][0].update(source_ref='forbidden'),
    lambda p:p['directional_documents'][0].update(report_key=' '),
    lambda p:p['directional_calculation_parameters'].update(ratio_decimal_places=True),
    lambda p:p['directional_calculation_parameters'].pop('rounding'),
    lambda p:p['directional_documents'].append(deepcopy(p['directional_documents'][0])),
])
def test_closed_parameters_reject_missing_conflicting_or_ambiguous_fields(mutation):
    p=fixture()['parameters'];mutation(p)
    with pytest.raises(ValueError):c.validate_parameters_v2(p)


@pytest.mark.parametrize('mutation',[
    lambda s:s['requirements'][0].update(role='other'),
    lambda s:s['requirements'][0]['declared_format'].update(producer_source_ref='different'),
    lambda s:s['requirements'].append(deepcopy(s['requirements'][0])),
    lambda s:s.update(requirements=[]),
    lambda s:s['adapter']['parameters']['directional_documents'][0].update(document_id='unknown-target'),
])
def test_selector_cross_checks_without_store_or_future_sources(mutation):
    s=selector(fixture());assert c.validate_result_selector_v2(s)==s
    mutation(s)
    with pytest.raises(ValueError):c.validate_result_selector_v2(s)


def test_both_versions_bind_only_under_exact_selected_pin():
    pins=[dict(adapter_id=m.ADAPTER_ID,adapter_version=m.ADAPTER_VERSION,implementation_sha256=m.implementation_sha256()) for m in (old,adapter)]
    assert set(bind_adapters(pins))=={('bvbrc_proteome','1'),('bvbrc_proteome','2')}
    pins[1]['implementation_sha256']=pins[0]['implementation_sha256']
    with pytest.raises(ValueError,match='implementation_conflict'):bind_adapters(pins)


def test_schema_detached_and_actual_static_import_closure_pinned():
    from gene_annotation_episode import bvbrc_proteome_directional_fact_contracts as facts
    assert c.DIRECTIONAL_BINDING_CODES == frozenset(facts.BINDING_CODES)
    a=c.parameters_schema_v2();a['$defs'].clear();assert c.parameters_schema_v2()['$defs']
    package=Path(adapter.__file__).parent
    pending=[n for n in adapter._DEPENDENCIES if n.endswith('.py')];seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name)
        for node in ast.walk(ast.parse((package/name).read_text())):
            if isinstance(node,ast.ImportFrom) and node.level==1:
                modules=[node.module.split('.')[0]] if node.module else [i.name for i in node.names]
                pending.extend(m+'.py' for m in modules if (package/(m+'.py')).exists())
    assert seen<=set(adapter._DEPENDENCIES)
