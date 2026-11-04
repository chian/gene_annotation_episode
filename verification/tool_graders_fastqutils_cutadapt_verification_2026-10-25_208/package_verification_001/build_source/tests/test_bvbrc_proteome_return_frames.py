"""Actual public return resolvers under the reviewed synchronous form frame.

The existing return fixture supplies a controlled publication envelope over real
scientific constructors. This file verifies the frame and custody boundary;
the separate host tests establish actual AppService publication.
"""
from contextvars import copy_context
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.bvbrc_proteome_returns import BVBRCProteomeReturns
from gene_annotation_episode.communication import plain, validate_form, form_with_facts, ReportBoundaryError
from gene_annotation_episode.form_reference_validation import form_reference_validation
from gene_annotation_episode.runtime import TypedReportContract
from test_bvbrc_proteome_returns import run, MEASUREMENTS, MEAN, fact_form


def prepared(run):
    args = run.example({'mean': MEAN})
    child = run.child(run.saved.root, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    schema = plain(child.request)['report_contract']['measurements']['schema']
    values = run.host.facts(child, schema)
    form = form_with_facts({}, schema, values)
    return child, schema, form


def counted(monkeypatch, owner, name):
    actual, calls = getattr(owner, name), []
    def observe(*args, **kwargs):
        calls.append((args, kwargs))
        return actual(*args, **kwargs)
    monkeypatch.setattr(owner, name, observe)
    return calls


def test_public_own_resolver_reuses_one_form_only_and_semantics_reauthenticate(run, monkeypatch):
    child, schema, form = prepared(run)
    calls = counted(monkeypatch, run.host, 'facts')
    resolve = lambda ref, ns: run.host.resolve_own(child, ref, ns)
    assert validate_form(form, schema, resolve) == form
    assert len(calls) == 1
    assert validate_form(form, schema, resolve) == form
    assert len(calls) == 2
    typed = TypedReportContract('Return requested native mean', schema, resolve,
        lambda value: run.host.validate_received_report(child, value, schema))
    assert plain(typed.admit(form, audit_identifiers=(child.episode_id,)).as_record()) == form
    assert len(calls) == 4  # One traversal snapshot plus independent semantic validation.
    altered = deepcopy(form)
    altered['f0'][0]['value']['cell']['value'] = .9
    with pytest.raises(ValueError, match='returned_facts_conflict'):
        typed.admit(altered, audit_identifiers=(child.episode_id,))
    assert len(calls) == 6


def test_public_resolvers_distinguish_owner_direction_and_changed_original_context(run, monkeypatch):
    child, schema, form = prepared(run)
    ref = form['f0'][0]['field']
    calls = counted(monkeypatch, run.host, 'facts')
    received = counted(monkeypatch, run.host, 'received_context')
    other = BVBRCProteomeReturns(run.api)
    other_calls = counted(monkeypatch, other, 'facts')
    with form_reference_validation():
        assert run.host.resolve_own(child, ref, 'bvbrc_proteome_field')
        assert run.host.resolve_own(replace(child), ref, 'bvbrc_proteome_field')
        assert other.resolve_own(child, ref, 'bvbrc_proteome_field')
        assert run.host.resolve_received(run.saved.root, ref, 'bvbrc_proteome_field') is False
        # This changed request is not the actual commissioned request. Cached
        # authority from the original context cannot authorize it.
        request = plain(child.request)
        request['report_contract']['measurements']['schema'] = fact_form()
        assert run.host.resolve_own(replace(child, request=request), ref, 'bvbrc_proteome_field') is False
        assert run.host.resolve_own(replace(child, received_record_refs=('unreceived',)),
            ref, 'bvbrc_proteome_field')
    assert len(calls) == 3 and len(other_calls) == 1 and len(received) == 1


def test_nested_frames_errors_and_copied_context_expire_with_public_resolver(run, monkeypatch):
    child, schema, form = prepared(run)
    ref = form['f0'][0]['field']
    calls = counted(monkeypatch, run.host, 'facts')
    resolve = lambda: run.host.resolve_own(child, ref, 'bvbrc_proteome_field')
    with form_reference_validation():
        assert resolve()
        copied = copy_context()
        with form_reference_validation():
            assert resolve()
        assert resolve() and len(calls) == 2
        with pytest.raises(RuntimeError):
            with form_reference_validation():
                assert resolve()
                raise RuntimeError('controlled nested failure')
        assert resolve() and len(calls) == 3
    assert copied.run(resolve) and copied.run(resolve)
    assert len(calls) == 5
    bad = deepcopy(form)
    bad['f0'][0]['field'] += 'not-original'
    with pytest.raises(ReportBoundaryError):
        validate_form(bad, schema, lambda ref, ns: run.host.resolve_own(child, ref, ns))
    assert validate_form(form, schema, lambda ref, ns: run.host.resolve_own(child, ref, ns)) == form
    assert len(calls) == 7


def test_each_source_reference_keeps_possession_check_inside_shared_frame(run, monkeypatch):
    child, _, form = prepared(run)
    source = form['f0'][0]['source_ref']
    actual = run.api.appservice.custody.possession
    rejected = False
    def possession(context, ref, **kwargs):
        if rejected and ref == source:
            raise ValueError('controlled_source_custody_revoked')
        return actual(context, ref, **kwargs)
    monkeypatch.setattr(run.api.appservice.custody, 'possession', possession)
    with form_reference_validation():
        assert run.host.resolve_own(child, source, 'execution_result')
        rejected = True
        with pytest.raises(ValueError, match='controlled_source_custody_revoked'):
            run.host.resolve_own(child, source, 'execution_result')


def test_later_validation_rejects_changed_saved_value_and_custody(run, monkeypatch):
    child, schema, form = prepared(run)
    resolver = lambda ref, ns: run.host.resolve_own(child, ref, ns)
    assert validate_form(form, schema, resolver) == form
    source = form['f0'][0]['source_ref']
    body = run.publications.bodies[source]
    body['publication']['adapter_result']['facts']['mean']['cell']['value'] = .9
    with pytest.raises(ValueError, match='saved_projection_invalid'):
        validate_form(form, schema, resolver)


def test_received_public_resolver_reuses_one_frame_and_revalidates_later_admission(run, monkeypatch):
    args = run.example({'mean': MEAN})
    scientific = run.child(run.saved.root, 'scientific_process', args[0], sources=(MEASUREMENTS,))
    child = run.child(scientific, 'results', args[0], sources=(MEASUREMENTS,))
    run.publications.add(child, args)
    form, schema, _, _ = run.admit(scientific, child)
    calls = counted(monkeypatch, run.host, 'received_context')
    resolver = lambda ref, ns: run.host.resolve_received(scientific, ref, ns)
    assert validate_form(form, schema, resolver) == form
    assert len(calls) == 1
    assert validate_form(form, schema, resolver) == form
    assert len(calls) == 2
    # A successful earlier traversal cannot authorize a later changed report.
    index = int(child.path[-1][1].removeprefix('child_'))
    run.store.db.execute('UPDATE runtime_report_attempts SET failure=? WHERE run_id=? '
        'AND parent_episode_id=? AND decision_index=?',
        ('{}', scientific.run_id, scientific.episode_id, index))
    with pytest.raises(ReportBoundaryError):
        validate_form(form, schema, resolver)
    assert len(calls) == 3


def test_failed_authentication_factory_is_not_reused_and_returned_dict_is_detached(run, monkeypatch):
    child, _, form = prepared(run)
    ref, values, calls = form['f0'][0]['field'], [], []
    actual = run.host.facts
    def observe(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise ValueError('controlled_authentication_failure')
        result = actual(*args, **kwargs)
        values.append(result)
        return result
    monkeypatch.setattr(run.host, 'facts', observe)
    with form_reference_validation():
        with pytest.raises(ValueError, match='controlled_authentication_failure'):
            run.host.resolve_own(child, ref, 'bvbrc_proteome_field')
        assert run.host.resolve_own(child, ref, 'bvbrc_proteome_field')
        values[0][MEASUREMENTS].clear()
        assert run.host.resolve_own(child, ref, 'bvbrc_proteome_field')
        assert len(calls) == 2
    assert run.host.resolve_own(child, ref, 'bvbrc_proteome_field')
    assert len(calls) == 3
