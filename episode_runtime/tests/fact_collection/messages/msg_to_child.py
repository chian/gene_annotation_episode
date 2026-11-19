"""The extraction commission: the field, every record this episode names for the child, and the optional
return fields it selects."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective='Extract the value of field ' + arguments['field'],
                        message={'field': arguments['field']},
                        assignment={'source_refs': list(summary['subject_refs']) + list(summary['context_refs']),
                                    'field': arguments['field']},
                        selection=('field',))
