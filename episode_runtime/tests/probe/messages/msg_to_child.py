"""The commissions: a nested plan for the slot that commissions this episode's own kind; for the extraction
slots the field, the prediction made when commissioning and the selection the plan names."""
from episode_runtime import ChildMessage


def msg_to_child(slot, arguments, summary):
    if slot == 'nested':
        return ChildMessage(objective='Carry out the nested plan',
                            message={key: arguments[key] for key in ('plan', 'controller', 'credit')
                                     if key in arguments},
                            assignment={'subject_refs': summary['subject_refs'],
                                        'input_refs': summary['input_refs'], 'held_refs': summary['held_refs']},
                            selection=tuple(arguments.get('select', ())))
    return ChildMessage(objective='Extract ' + arguments['field'] + ' for the ' + slot + ' slot',
                        message={'field': arguments['field'], 'prediction': arguments.get('prediction')},
                        assignment={'source_refs': arguments.get('source_refs', summary['subject_refs']),
                                    'field': arguments['field']},
                        selection=tuple(arguments.get('select', ())))
