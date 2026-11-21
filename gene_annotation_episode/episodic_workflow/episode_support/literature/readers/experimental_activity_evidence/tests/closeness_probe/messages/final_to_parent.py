"""Always returned: the Episode's credit, the finding (how many pairs were measured) and every record the pairs wrote."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'plan_steps': Field('integer', 'Pairs of the commissioned plan'),
    'steps_done': Field('integer', 'Pairs measured'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'How much of the plan was carried out', form=FINDING_FORM),
    'record_refs': Field('record_refs', 'Every record its pairs wrote'),
})


def final_to_parent(summary, completion, selection):
    outcomes = summary['outcomes'][:summary['steps']]
    written = list(dict.fromkeys(ref for outcome in outcomes for ref in outcome['produced']))
    return {'credit': completion['credit'],
            'finding': {'plan_steps': len(summary['plan']), 'steps_done': summary['steps']},
            'record_refs': written}
