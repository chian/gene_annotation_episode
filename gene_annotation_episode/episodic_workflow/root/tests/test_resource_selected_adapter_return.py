"""A resource child receives facts only from the adapter it selected."""

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.resource_episodes import ResourceEpisodes


class _Adapter:
    def __init__(self, resource_id, *, reject=False):
        self.resource_id = resource_id
        self.reject = reject
        self.validated = False
        self.resolved = False

    def capability(self):
        return {'resource_id': self.resource_id, 'kind': 'local',
            'availability': 'available', 'observed_at': 'fixture',
            'provenance_refs': [], 'knowledge_entry_ids': [], 'tool_names': []}

    def as_record(self):
        return {'resource_id': self.resource_id}

    def prepare_assignment(self, *args):
        raise AssertionError('no child is commissioned in this test')

    def catalog(self, *args):
        return []

    def execute(self, *args):
        raise AssertionError('no tool is selected in this test')

    def fact_sources(self, role):
        return {}

    def facts(self, context, completion_snapshot):
        return {}

    def resolve(self, context, reference, namespace):
        self.resolved = True
        if self.reject:
            raise AssertionError('unselected adapter resolved a child reference')
        return False

    def validate_report(self, context, form, schema):
        self.validated = True
        if self.reject:
            raise AssertionError('unselected adapter validated a child return')

    def credit_view(self, context, receiver_selection):
        return {'credit': 0}


class _Services:
    def capabilities(self):
        return []

    def reference_in_scope(self, reference, scope, namespace):
        return False


def test_selected_resource_child_owns_its_return_and_reference_binding():
    selected = _Adapter('selected')
    unrelated = _Adapter('unrelated', reject=True)
    binding = ResourceEpisodes(_Services(), resource_adapters=[selected, unrelated])
    context = BindingContext('run', 'child', 'launch_local', (('launch_local', 'child'),),
        {'subject_refs': []}, {'resource_selection': {'resource_id': 'selected'}}, {})
    schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    binding.validate_report(context, {}, schema)
    assert binding.resolve(context, 'unknown', None) is False
    assert selected.validated and selected.resolved
    assert not unrelated.validated and not unrelated.resolved
