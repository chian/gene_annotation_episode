"""What the plan did. Always returned: the Episode's credit (the system hands it in ``completion``) and the
finding (how much of the plan was carried out). Also what the loop's view said at the end and the sheet rows its
tool units wrote (returned in custody); when selected, how the Episode ended and the closing values its ``close``
units wrote."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'plan_steps': Field('integer', 'Steps of the commissioned plan'),
    'steps_done': Field('integer', 'Plan steps carried out'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'How much of the plan was carried out', form=FINDING_FORM),
    'n': Field('integer', 'Plan steps carried out'),
    'n_updates': Field('integer', 'Child updates in the view'),
    'n_reports': Field('integer', 'Child reports in the view'),
    'subject_names': Field('list', 'Names read from the held subject records'),
    'slots': Field('list', 'The slot of each child unit'),
    'produced': Field('list', 'The records each tool unit of the plan produced'),
    'row_refs': Field('record_refs', 'The sheet rows its tool units wrote'),
    'completion': Field('record', 'How the Episode ended, as the system says it', required=False),
    'closing': Field('list', 'The closing values its close units wrote, in order', required=False),
})


def final_to_parent(summary, completion, selection):
    outcomes = summary['outcomes'][:summary['steps']]
    tools = [outcome for outcome in outcomes if outcome['kind'] == 'tool']
    rows = [ref for outcome in tools for ref in outcome['produced'] if ref.startswith('row_')]
    result = {'credit': completion['credit'],
              'finding': {'plan_steps': len(summary['plan']), 'steps_done': summary['steps']},
              'n': summary['steps'], 'n_updates': summary['n_updates'], 'n_reports': summary['n_reports'],
              'subject_names': summary['subject_names'],
              'slots': [outcome['slot'] for outcome in outcomes if outcome['kind'] == 'child'],
              'produced': [outcome['produced'] for outcome in tools], 'row_refs': list(dict.fromkeys(rows))}
    if 'completion' in selection:
        result['completion'] = completion
    if 'closing' in selection:
        result['closing'] = [outcome['outcome']['closing'] for outcome in tools if outcome['tool'] == 'close']
    return result
