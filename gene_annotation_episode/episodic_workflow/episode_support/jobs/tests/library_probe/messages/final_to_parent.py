"""Always returned: the Episode's credit, the finding (how much of the plan was carried out) and every record its
plan steps wrote, in custody."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'plan_steps': Field('integer', 'Steps of the commissioned plan'),
    'steps_done': Field('integer', 'Plan steps carried out'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'How much of the plan was carried out', form=FINDING_FORM),
    'record_refs': Field('record_refs', 'Every record its plan steps wrote'),
})


def final_to_parent(summary, completion, selection):
    outcomes = summary['outcomes'][:summary['steps']]
    written = list(dict.fromkeys(ref for outcome in outcomes for ref in outcome['produced']))
    return {'credit': completion['credit'],
            'finding': {'plan_steps': len(summary['plan']), 'steps_done': summary['steps']},
            'record_refs': written}
