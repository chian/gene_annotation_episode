"""Explicit version/selection schemas and pre-acquisition cross checks."""
from copy import deepcopy
import ast
from pathlib import Path

import pytest
from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_bundle_v2_contracts as c
from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_bundle_adapter_v2 as adapter
from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_bundle_adapter as old
from gene_annotation_episode.episodic_workflow.root.a101.bvbrc_appservice_adapters import bind_adapters
from gene_annotation_episode.episodic_workflow.root.a101.tests.test_bvbrc_proteome_bundle_v2_resolution import fixture,selector


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


def test_schema_detached_and_actual_static_import_closure_pinned(monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_directional_fact_contracts as facts
    assert c.DIRECTIONAL_BINDING_CODES == frozenset(facts.BINDING_CODES)
    a=c.parameters_schema_v2();a['$defs'].clear();assert c.parameters_schema_v2()['$defs']
    # Read the actual declared owners through the adapter's unchanged source
    # locator. The recording port returns the exact original bytes.
    axis = __package__.rsplit('.tests', 1)[0]
    package = Path(__file__).resolve().parents[1]
    original_read = Path.read_bytes
    declared = []
    def record_read(path):
        raw = original_read(path)
        declared.append((path.resolve(), raw))
        return raw
    with monkeypatch.context() as capture:
        capture.setattr(Path, 'read_bytes', record_read)
        actual_pin = adapter.implementation_sha256()
    assert [path.name for path, _ in declared] == list(adapter._DEPENDENCIES)
    assert len({path for path, _ in declared}) == len(declared)
    import hashlib
    expected_pin = hashlib.sha256()
    for name, (path, raw) in zip(adapter._DEPENDENCIES, declared):
        assert path.is_relative_to(package)
        assert path.read_bytes() == raw
        expected_pin.update(name.encode()+b'\0'+str(len(raw)).encode()+b'\0'+raw)
    assert actual_pin == expected_pin.hexdigest()
    declared_paths = {path for path, _ in declared}
    from importlib.util import resolve_name
    def source_path(module):
        assert module == axis or module.startswith(axis+'.')
        relative = module[len(axis):].lstrip('.').split('.') if module != axis else []
        base = package.joinpath(*relative)
        py = base.with_suffix('.py') if relative else None
        if py is not None and py.is_file():
            return py
        init = base/'__init__.py'
        return init if init.is_file() else None
    pending = [path for path, _ in declared if path.suffix == '.py']
    physical_seen = set()
    while pending:
        path = pending.pop()
        if path in physical_seen:
            continue
        physical_seen.add(path)
        relative = path.parent.relative_to(package)
        source_package = axis + ('.'+'.'.join(relative.parts) if relative.parts else '')
        for node in ast.walk(ast.parse(path.read_text())):
            targets = []
            if isinstance(node, ast.Import):
                targets.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = resolve_name('.'*node.level+(node.module or ''), source_package) if node.level else node.module or ''
                if base == axis or base.startswith(axis+'.'):
                    if node.module:
                        target = source_path(base)
                        assert target is not None, (path, node.lineno, base)
                        targets.append(base)
                        # `from package import module` can load a submodule;
                        # attributes remain in the already selected base owner.
                        if target.name == '__init__.py':
                            targets.extend(base+'.'+alias.name for alias in node.names
                                           if alias.name != '*' and source_path(base+'.'+alias.name) is not None)
                    else:
                        targets.append(base)
                        for alias in node.names:
                            if alias.name != '*':
                                target = source_path(base+'.'+alias.name)
                                assert target is not None, (path, node.lineno, alias.name)
                                targets.append(base+'.'+alias.name)
            for target in targets:
                if target == axis or target.startswith(axis+'.'):
                    destination = source_path(target)
                    assert destination is not None, (path, node.lineno, target)
                    pending.append(destination)
    for path in physical_seen-declared_paths:
        # The relocation adds exactly this package entry. Its source must be
        # byte-identical to the explicit original initializer in the roster.
        assert path == package/'library/__init__.py'
        assert package/'__init__.py' in declared_paths
        assert path.read_bytes() == (package/'__init__.py').read_bytes()
    seen = {path.name for path in physical_seen}
    assert seen<=set(adapter._DEPENDENCIES)
