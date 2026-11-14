"""This private task's captured provider callable and declared-presentation transport."""
class LiteratureProviderCompletion:
    def decision_completion(self):
        provider = self.workflow.provider
        complete = provider.complete

        async def complete_private_decision(episode_id, role, instructions, context, schema):
            from types import MethodType as _PresentationMethodType
            from inspect import getattr_static as _presentation_getattr_static
            if (type(complete) is _PresentationMethodType
                    and complete.__self__ is provider
                    and type(type(provider)) is type):
                from gene_annotation_episode.episodic_workflow.root.providers import (
                    _ORIGINAL_MODEL_COMPLETE as _ROOT_MODEL_COMPLETE,
                    _ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION as _ROOT_MODEL_PRESENTATION,
                    _ORIGINAL_MODEL_COMPLETE_SERIAL as _ROOT_MODEL_SERIAL,
                    _ORIGINAL_MODEL_INSTANCE_DICT as _ROOT_MODEL_DICT,
                    _ORIGINAL_MODEL_SESSION_TYPE as _ROOT_MODEL_SESSION,
                    _ORIGINAL_SESSION_COMPLETE as _ROOT_SESSION_COMPLETE,
                    _ORIGINAL_SESSION_PRESENTATION as _ROOT_SESSION_PRESENTATION)
                if (complete.__func__ is _ROOT_MODEL_COMPLETE
                        and issubclass(type(provider), _ROOT_MODEL_DICT.__objclass__)):
                    root_instance_items = dict.items(_ROOT_MODEL_DICT.__get__(provider))
                    if all(type(key) is str and key not in ('complete_with_presentation', '_complete_serial', 'session_type')
                            for key, value in root_instance_items):
                        if (_presentation_getattr_static(type(provider), '__getattribute__', None) is object.__getattribute__
                                and _presentation_getattr_static(type(provider), 'complete_with_presentation', None) is _ROOT_MODEL_PRESENTATION
                                and _presentation_getattr_static(type(provider), '_complete_serial', None) is _ROOT_MODEL_SERIAL
                                and _presentation_getattr_static(type(provider), 'session_type', None) is _ROOT_MODEL_SESSION
                                and _presentation_getattr_static(_ROOT_MODEL_SESSION, 'complete', None) is _ROOT_SESSION_COMPLETE
                                and _presentation_getattr_static(_ROOT_MODEL_SESSION, '_presentation', None) is _ROOT_SESSION_PRESENTATION):
                            binding = self.workflow.specialist(self)
                            if binding is not None:
                                return await _PresentationMethodType(_ROOT_MODEL_PRESENTATION, provider)(episode_id, role, instructions, context, schema,
                                    prompt_renderer=binding.decision_prompt_renderer,
                                    declared_presenter=None)
            return await complete(episode_id, role, instructions, context, schema)

        return complete_private_decision
