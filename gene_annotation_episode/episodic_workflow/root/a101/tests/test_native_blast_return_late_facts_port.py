"""Actual return constructor/late results port; authentication is controlled.

No journal, scientific publication, receipt authentication or native work is
claimed. The original real Store/Journal admission tests remain separate.
"""
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.native_blast_returns import NativeBLASTReturns, REFERENCE_SOURCE


def fixture_port():
    events = []
    context = object()
    class Results:
        def __init__(self, label):
            self.label = label
            self.accepted = True
        def applies(self, received):
            assert received is context
            events.append(('applies', self.label))
            return self.accepted
        @property
        def facts(self):
            events.append(('lookup', self.label))
            def read(received):
                assert received is context
                events.append(('facts', self.label))
                return {'execution_result_refs': [self.label], 'execution_completed': True}
            return read
    first = Results('original')
    owner = SimpleNamespace(store=SimpleNamespace(db=object()), run_id='controlled-port', native_blast_results=first)
    boundary = NativeBLASTReturns(owner)
    assert events == []  # Constructor stores the port, not its current bound reader.
    def authenticate(received):
        assert received is context
        events.append(('authenticate',))
        return received
    boundary.authenticate = authenticate
    return SimpleNamespace(events=events, context=context, Results=Results, first=first, owner=owner, boundary=boundary)


@pytest.mark.parametrize('mutation', ['method', 'results_object', 'owner_slot'])
def test_native_return_keeps_late_facts_and_original_receiver_semantics(mutation):
    s = fixture_port()
    if mutation == 'method':
        # An ordinary alternate results object may replace its method later.
        alternate = SimpleNamespace(applies=s.first.applies)
        def obsolete(context):
            pytest.fail('cached obsolete facts callback')
        alternate.facts = obsolete
        s.boundary.results = alternate
        def replaced(context):
            assert context is s.context
            s.events.append(('facts', 'replaced'))
            return {'execution_result_refs': ['replaced'], 'execution_completed': True}
        alternate.facts = replaced
        label = 'replaced'
        expected = [('authenticate',), ('applies', 'original'), ('facts', 'replaced')]
    elif mutation == 'results_object':
        s.boundary.results = s.Results('replacement')
        label = 'replacement'
        expected = [('authenticate',), ('applies', label), ('lookup', label), ('facts', label)]
    else:
        s.owner.native_blast_results = s.Results('later-owner-slot')
        label = 'original'
        expected = [('authenticate',), ('applies', label), ('lookup', label), ('facts', label)]
    result = s.boundary._own_facts(s.context, (REFERENCE_SOURCE, 'execution_completed'))
    assert result == {REFERENCE_SOURCE: [label], 'execution_completed': True}
    assert s.events == expected


@pytest.mark.parametrize('failure', ['authentication', 'applicability'])
def test_native_return_rejects_before_any_facts_descriptor_lookup(failure):
    s = fixture_port()
    sentinel = RuntimeError('original authentication error')
    if failure == 'authentication':
        def reject(context):
            assert context is s.context
            s.events.append(('authentication-error',))
            raise sentinel
        s.boundary.authenticate = reject
        with pytest.raises(RuntimeError) as caught:
            s.boundary._own_facts(s.context, (REFERENCE_SOURCE,))
        assert caught.value is sentinel
        assert s.events == [('authentication-error',)]
    else:
        s.first.accepted = False
        with pytest.raises(ValueError, match='native_blast_return_original_results_owner_required'):
            s.boundary._own_facts(s.context, (REFERENCE_SOURCE,))
        assert s.events == [('authenticate',), ('applies', 'original')]
