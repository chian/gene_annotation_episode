"""The commissions: for an extraction slot the field and the sources."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective='Extract ' + arguments['field'] + ' for the ' + slot + ' slot',
                        message={'field': arguments['field'], 'prediction': arguments.get('prediction')},
                        assignment={'source_refs': arguments.get('source_refs', summary['subject_refs']),
                                    'field': arguments['field']},
                        selection=tuple(arguments.get('select', ())))
