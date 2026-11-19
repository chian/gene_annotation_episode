"""The Episode type refuses every class that is not exactly the ten episode files' members, one case each.

Each case is a real episode package on disk (``episode_variant``): a copy of a kept test episode changed in the one
way the case names, and imported. The refusal is raised by the import of its ``episode.py``.
"""
import pytest

from episode_runtime import BindingRegistry, EpisodeBinding

from .fact_collection.fact_extraction.episode import FactExtraction

CHILD, PARENT = 'fact_collection/fact_extraction', 'fact_collection'
CREDIT_LINE = '    credit = credit_file.credit\n'
CREDIT_DEF = ('def credit(summary, records):\n    if summary[\'fact_ref\'] is not None:\n        return 1.0\n'
              '    return len(summary[\'read\']) / len(summary[\'source_refs\'])\n')
CREDIT_FIELD = "    'credit': Field('number', \"The Episode's credit when its controller stopped it\"),\n"
FINDING_FIELD = "    'finding': Field('record', 'What the extraction found', form=FINDING_FORM),\n"
DECIDE = 'def decide(summary, feedback, ctx):'
TOOLS = "TOOLS = {'extract_field': extract_field}"


def refused(make, match, path=CHILD, **changes):
    edits = {name.replace('__', '/') + '.py': value for name, value in changes.items() if isinstance(value, list)}
    add = {name.replace('__', '/') + '.py': value for name, value in changes.items() if isinstance(value, str)}
    with pytest.raises(TypeError, match=match):
        make(path, edits, add)


def test_an_unchanged_copy_is_a_valid_episode(episode_variant):
    module = episode_variant(CHILD)
    assert module.FactExtraction.binding_path == CHILD
    assert module.FactExtraction is not FactExtraction
    assert issubclass(module.FactExtraction, EpisodeBinding)


def test_a_missing_extra_or_overriding_member(episode_variant):
    refused(episode_variant, 'episode_lacks_members:.*credit', episode=[(CREDIT_LINE, '')])
    refused(episode_variant, 'episode_members_outside_the_episode_files:.*helper',
            episode=[(CREDIT_LINE, CREDIT_LINE + '    helper = goal_file.GOAL\n')])
    refused(episode_variant, 'episode_overrides_system_members:.*build_episode',
            episode=[(CREDIT_LINE, CREDIT_LINE + '    build_episode = task_file.decide\n')])
    refused(episode_variant, 'episode_without_children_has_child_members:.*read_from_child',
            episode=[(CREDIT_LINE, CREDIT_LINE + '    read_from_child = task_file.decide\n')])
    refused(episode_variant, 'episode_with_children_lacks_members:.*read_from_child', path=PARENT,
            episode=[('    read_from_child = from_child_file.read_from_child\n', '')])


def test_an_episode_cannot_be_inherited_from_or_take_another_base_or_a_metaclass(episode_variant):
    with pytest.raises(TypeError, match='episode_must_inherit_only_from_EpisodeBinding'):
        type('Derived', (FactExtraction,), {})
    refused(episode_variant, 'episode_must_inherit_only_from_EpisodeBinding',
            episode=[('class FactExtraction(EpisodeBinding):', 'class FactExtraction(EpisodeBinding, dict):')])
    refused(episode_variant, 'episode_must_not_have_a_metaclass:.*Meta',
            episode=[('class FactExtraction(EpisodeBinding):',
                      'class Meta(type):\n    pass\n\n\nclass FactExtraction(EpisodeBinding, metaclass=Meta):')])
    refused(episode_variant, 'flag|keyword',
            episode=[('class FactExtraction(EpisodeBinding):', 'class FactExtraction(EpisodeBinding, flag=1):')])


@pytest.mark.parametrize('hook', ['    def __init__(self):\n        pass\n', '    __slots__ = ()\n',
                                  '    def __getattr__(self, name):\n        return None\n',
                                  '    @classmethod\n    def __init_subclass__(cls, **kw):\n        pass\n',
                                  '    __helper__ = 1\n', '    goal: str\n'])
def test_python_hooks_and_other_dunders_are_refused(episode_variant, hook):
    refused(episode_variant, 'episode_defines_python_hooks', episode=[(CREDIT_LINE, CREDIT_LINE + hook)])


def test_a_member_must_be_a_module_level_function_of_its_own_file(episode_variant):
    borrow = 'from episode_runtime.tests.fact_collection import credit as other_file\n'
    own_file = 'episode_member_must_be_defined_in_its_own_file:.*credit'
    # another episode's function, assigned in episode.py
    refused(episode_variant, own_file, episode=[
        ('"""The fact extraction episode."""\n', '"""The fact extraction episode."""\n' + borrow),
        (CREDIT_LINE, '    credit = other_file.credit\n')])
    # another episode's function imported into this episode's credit.py
    refused(episode_variant, own_file, credit=[
        (CREDIT_DEF, 'from episode_runtime.tests.fact_collection.credit import credit\n')])
    # the same code rebuilt here with this file's module name written onto it
    refused(episode_variant, own_file, credit=[(CREDIT_DEF, (
        'import types\n\nfrom episode_runtime.tests.fact_collection.credit import credit as other\n\n'
        'credit = types.FunctionType(other.__code__, other.__globals__, \'credit\')\ncredit.__module__ = __name__\n'))])
    # a function built by a factory, with captured state
    refused(episode_variant, own_file, credit=[(CREDIT_DEF, (
        'def make():\n    calls = []\n\n    def credit(summary, records):\n        calls.append(1)\n'
        '        return 0.0\n    return credit\n\n\ncredit = make()\n'))])
    # a tool of another episode's task.py
    refused(episode_variant, 'episode_member_must_be_defined_in_its_own_file:.*tool.confirm_fact', task=[
        (TOOLS, 'from episode_runtime.tests.fact_collection.task import confirm_fact\n'
                "TOOLS = {'confirm_fact': confirm_fact}")])


def test_a_member_with_the_wrong_parameters_is_refused(episode_variant):
    refused(episode_variant, 'episode_member_parameters_must_be:.*decide:summary,feedback,ctx',
            task=[(DECIDE, 'def decide(summary, feedback):')])
    refused(episode_variant, 'episode_member_parameters_must_be:.*decide',
            task=[(DECIDE, 'def decide(summary, feedback, ctx=None):')])
    refused(episode_variant, 'episode_member_parameters_must_be:.*action:response,summary,records,ctx',
            task=[('def action(response, summary, records, ctx):', 'def action(response, summary, records):')])
    refused(episode_variant, 'episode_member_parameters_must_be:.*credit:summary,records',
            credit=[('def credit(summary, records):', 'def credit(summary, records, extra):')])


def test_a_member_that_is_not_a_plain_synchronous_function_is_refused(episode_variant):
    refused(episode_variant, 'episode_member_must_be_a_plain_function:.*credit', credit=[(CREDIT_DEF, (
        'from functools import partial\n\n\ndef scored(extra, summary, records):\n    return 0.0\n\n\n'
        'credit = partial(scored, None)\n'))])
    refused(episode_variant, 'episode_member_must_be_a_plain_function:.*decide',
            episode=[('    decide = task_file.decide\n', '    decide = len\n')])
    refused(episode_variant, 'episode_member_must_not_be_async:.*decide', task=[(DECIDE, 'async ' + DECIDE)])
    refused(episode_variant, 'episode_member_must_not_be_async:.*action',
            task=[('def action(response, summary, records, ctx):',
                   'async def action(response, summary, records, ctx):')])
    refused(episode_variant, 'episode_member_must_not_be_a_generator:.*internal_summary',
            messages__internal_summary=[('    return summary\n', '    yield summary\n')])


def test_tools_are_plain_functions_of_arguments_and_ctx_and_may_be_async(episode_variant):
    refused(episode_variant, 'episode_member_must_be_a_plain_function:.*tool.extract_field', task=[
        (TOOLS, 'class Tool:\n    def __call__(self, arguments, ctx):\n        return {}\n\n\n'
                "TOOLS = {'extract_field': Tool()}")])
    refused(episode_variant, 'episode_member_parameters_must_be:.*tool.extract_field:arguments,ctx',
            task=[('def extract_field(arguments, ctx):', 'def extract_field(arguments):')])
    refused(episode_variant, 'episode_tools_must_map_tool_names_to_functions',
            task=[(TOOLS, "TOOLS = {'bad name': extract_field}")])
    refused(episode_variant, 'episode_member_must_not_be_a_generator:.*tool.extract_field',
            task=[("        return {'source_ref': arguments['source_ref'], 'found': False}\n",
                   "        yield {'source_ref': arguments['source_ref'], 'found': False}\n")])
    module = episode_variant(CHILD, {'task.py': [('def extract_field(arguments, ctx):',
                                                   'async def extract_field(arguments, ctx):')]})
    assert sorted(module.FactExtraction.tools) == ['extract_field']


def test_names_and_paths_are_checked_at_definition(episode_variant):
    refused(episode_variant, 'episode_binding_path_must_be_lowercase_segments',
            goal=[("BINDING_PATH = 'fact_collection/fact_extraction'", "BINDING_PATH = 'Bad Path'")])
    refused(episode_variant, 'episode_binding_path_must_end_its_package_path:.*fact_collection/elsewhere',
            goal=[("BINDING_PATH = 'fact_collection/fact_extraction'", "BINDING_PATH = 'fact_collection/elsewhere'")])
    refused(episode_variant, 'episode_child_slots_must_map_slot_names_to_binding_paths', path=PARENT,
            task=[("CHILD_SLOTS = {'extraction': 'fact_collection/fact_extraction'}",
                   "CHILD_SLOTS = {'Bad Slot': 'fact_collection/fact_extraction'}")])
    refused(episode_variant, 'episode_child_slots_must_map_slot_names_to_binding_paths', path=PARENT,
            task=[("CHILD_SLOTS = {'extraction': 'fact_collection/fact_extraction'}",
                   "CHILD_SLOTS = {'extraction': 7}")])
    refused(episode_variant, 'episode_services_must_be_a_tuple_of_distinct_service_names',
            task=[('SERVICES = ()', "SERVICES = ('a', 'a')")])
    refused(episode_variant, 'episode_services_must_be_a_tuple_of_distinct_service_names',
            task=[('SERVICES = ()', "SERVICES = ['a']")])
    refused(episode_variant, 'episode_goal_must_be_text',
            goal=[("GOAL = 'Extract the commissioned field from the records passed for it'", "GOAL = '  '")])
    refused(episode_variant, 'episode_assignment_form_must_be_a_RecordForm',
            episode=[('    assignment_form = from_parent_file.ASSIGNMENT_FORM\n',
                      '    assignment_form = {}\n')])


def test_every_return_form_declares_credit_and_finding_as_required_fields(episode_variant):
    """Credit and finding are always returned: the class definition refuses a ``return_form`` that lacks one of
    them, offers one only as a selectable field, or declares a credit that is not a number. The content form of
    ``finding`` is the episode's own."""
    from .fact_collection.episode import FactCollection
    from .probe.episode import Probe
    for episode_class in (FactExtraction, FactCollection, Probe):
        fields = episode_class.return_form.fields
        assert fields['credit'].required and fields['credit'].type == 'number' and fields['finding'].required
    assert FactExtraction.return_form.fields['finding'].form is not Probe.return_form.fields['finding'].form
    refused(episode_variant, 'episode_return_form_must_require:FactExtraction:credit',
            messages__final_to_parent=[(CREDIT_FIELD, '')])
    refused(episode_variant, 'episode_return_form_must_require:FactExtraction:finding',
            messages__final_to_parent=[(FINDING_FIELD, '')])
    refused(episode_variant, 'episode_return_form_must_require:FactExtraction:credit,finding',
            messages__final_to_parent=[(CREDIT_FIELD, ''), (FINDING_FIELD, '')])
    refused(episode_variant, 'episode_return_form_must_require:FactExtraction:credit', messages__final_to_parent=[
        (CREDIT_FIELD, "    'credit': Field('number', 'Selectable credit', required=False),\n")])
    refused(episode_variant, 'episode_return_form_must_require:FactExtraction:finding', messages__final_to_parent=[
        (FINDING_FIELD, "    'finding': Field('record', 'Selectable finding', required=False),\n")])
    refused(episode_variant, 'episode_return_form_credit_must_be_a_number:FactExtraction',
            messages__final_to_parent=[(CREDIT_FIELD, "    'credit': Field('text', 'Credit as text'),\n")])
    # The finding may have any declared form: here plain text.
    module = episode_variant(CHILD, {'messages/final_to_parent.py': [
        (FINDING_FIELD, "    'finding': Field('text', 'What the extraction found, in words'),\n")]})
    assert module.FactExtraction.return_form.fields['finding'].type == 'text'


def test_the_class_must_be_the_only_one_of_its_episode_file(episode_variant):
    text = (episode_variant(CHILD).__file__)
    source = open(text).read()
    with pytest.raises(TypeError, match='episode_must_be_defined_in_its_episode_file'):
        episode_variant(CHILD, add={'elsewhere.py': source}, module='elsewhere')
    twin = source.split('class FactExtraction(EpisodeBinding):')[1]
    refused(episode_variant, 'episode_file_defines_two_episodes:.*FactExtraction,Twin',
            episode=[('    final_to_parent = final_file.final_to_parent\n',
                      '    final_to_parent = final_file.final_to_parent\n\n\nclass Twin(EpisodeBinding):' + twin)])


def test_the_class_keeps_unchangeable_copies_of_its_tools_and_slots(episode_variant):
    module = episode_variant(PARENT)
    episode_class, task_file = module.FactCollection, module.task_file
    with pytest.raises(TypeError):
        episode_class.tools['later'] = len
    with pytest.raises(TypeError):
        episode_class.child_slots['other'] = CHILD
    task_file.TOOLS['later'] = len                      # the file's mapping is not the class's
    task_file.CHILD_SLOTS['other'] = CHILD
    assert sorted(episode_class.tools) == ['confirm_fact']
    assert dict(episode_class.child_slots) == {'extraction': CHILD}


def test_the_registry_refuses_an_instance_with_attributes_of_its_own(episode_variant):
    binding = episode_variant(CHILD).FactExtraction()
    assert BindingRegistry([binding]).paths == (CHILD,)
    binding.tools = {}
    with pytest.raises(TypeError, match='binding_instance_has_attributes_of_its_own:FactExtraction:tools'):
        BindingRegistry([binding])


def test_a_second_class_of_the_same_name_in_one_episode_file_is_refused(episode_variant):
    body = open(episode_variant(CHILD).__file__).read().split('class FactExtraction(EpisodeBinding):')[1]
    refused(episode_variant, 'episode_file_defines_two_episodes:.*FactExtraction,FactExtraction',
            episode=[('    final_to_parent = final_file.final_to_parent\n',
                      '    final_to_parent = final_file.final_to_parent\n\n\nFirst = FactExtraction\n\n\n'
                      'class FactExtraction(EpisodeBinding):' + body)])


def test_a_lambda_member_is_refused(episode_variant):
    refused(episode_variant, 'episode_member_must_be_a_plain_function:.*credit',
            credit=[(CREDIT_DEF, 'credit = lambda summary, records: 0.0\n')])


def test_the_registry_accepts_only_a_class_its_definition_checked(episode_variant):
    """A class given ``EpisodeBinding`` as its base after its definition was never checked."""
    module = episode_variant(CHILD, add={'loose.py': (
        'from episode_runtime import EpisodeBinding\n\n\nclass Base:\n    pass\n\n\nclass Loose(Base):\n'
        "    binding_path = 'anything'\n    child_slots = {}\n    tools = {}\n    services = ()\n\n\n"
        'Loose.__bases__ = (EpisodeBinding,)\n')}, module='loose')
    assert isinstance(module.Loose(), EpisodeBinding)
    with pytest.raises(TypeError, match='episode_class_was_not_checked_at_its_definition:Loose'):
        BindingRegistry([module.Loose()])


def test_the_registry_refuses_a_class_changed_after_its_definition(episode_variant):
    replaced = episode_variant(CHILD).FactExtraction
    replaced.credit = len
    with pytest.raises(TypeError, match='episode_class_changed_after_its_definition:FactExtraction:credit'):
        BindingRegistry([replaced()])
    added = episode_variant(CHILD).FactExtraction
    added.helper = 1
    with pytest.raises(TypeError, match='episode_class_changed_after_its_definition:FactExtraction:helper'):
        BindingRegistry([added()])
    removed = episode_variant(CHILD).FactExtraction
    del removed.services
    with pytest.raises(TypeError, match='episode_class_changed_after_its_definition:FactExtraction:services'):
        BindingRegistry([removed()])
