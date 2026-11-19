"""The task of the root: each unit is one commission of one evidence-axis head. The model chooses the axis.

The nine child slots are named by the axis roles. Each is bound to the binding path of the head in its axis
folder (``root/a101/sequence_homology_evidence`` ... ``root/a110/biochemical_feasibility_evidence``). The root has
no tools: everything it does is a commission. It never ends its own Episode; its yield controller does.

What the model is shown is controlled data only: the annotation credit, and for each axis its credit, the credit
at each of its returns (the trend of an axis's credit says whether it is still productive), how often it was
commissioned, the numbers and flags of its latest finding and how many job records its head left outstanding.
The answer is one of the nine axis names.

A head that ended its turn with a job outstanding. A head may launch a job that outlives its turn. When only that
job is outstanding its own controller ends it, and it returns the job's records. The root does not wait: the model
sees ``outstanding_jobs`` for that axis, works on other axes, and returns to the axis by commissioning it again.
Every commission of an axis passes back the records its head returned earlier (``messages/msg_to_child.py``), the
job records among them.

The selection each head is commissioned with (its evidence-axis option, thought pattern and tools, in that head's
own selection form) is the root's setting ``settings['axis_selections'][slot]``: the references name entries of the
run's frozen libraries by their digests, which only the run's caller has. ``action`` puts it into the commission."""
from episode_runtime import ChildCall, ModelRequest, Rejected

from .credit import AXIS_WEIGHTS, K, annotation_credit

# Slot (the axis role) -> the binding path of the axis head in its axis folder.
CHILD_SLOTS = {
    'sequence_homology_evidence': 'sequence_homology_evidence',                # A101, root/a101
    'structural_homology_evidence': 'structural_homology_evidence',            # A102, root/a102
    'gene_context_evidence': 'gene_context_evidence',                          # A103, root/a103
    'evolutionary_history_evidence': 'evolutionary_history_evidence',          # A104, root/a104
    'experimental_activity_evidence': 'experimental_activity_evidence',        # A105, root/a105
    'perturbation_evidence': 'perturbation_evidence',                          # A106, root/a106
    'partner_presence_evidence': 'partner_presence_evidence',                  # A107, root/a107
    'sample_context_evidence': 'sample_context_evidence',                      # A108, root/a108
    'biochemical_feasibility_evidence': 'biochemical_feasibility_evidence',    # A110, root/a110
}
TOOLS = {}
SERVICES = ()

INSTRUCTIONS = """You direct the annotation of one subject. Its proposed annotation is evaluated on nine evidence axes, and each axis is investigated by its own episode. At each step you commission exactly one axis: its episode investigates further, holding the records it returned before, and returns its axis credit.

The annotation credit is prod_i (1 + k * v_i) ** w_i - 1 over the nine axis credits v_i; `k` and the `weight` w_i of each axis are given. Progress on one axis alone raises it linearly. The same progress spread over several axes raises it more, because credit on one axis multiplies what the other axes have earned. `annotation_gain_of_one_credit` is what one more unit of credit on that axis would add to the annotation credit now.

`axes` shows for each axis: `credit` (what its episode returned at its latest return; 0 before its first return); `returned_credits` (the credit at each of its returns, in order: an axis whose credit has stopped rising has stopped being productive); `commissions` (how often you commissioned it); `finding` (the numbers and flags of its latest finding); and `outstanding_jobs` (how many job records its episode left outstanding when it ended its turn). `commissions` lists your earlier commissions in order.

A job that is still running is not evidence. Do not spend commissions waiting for it: commission other axes and return to that axis later. Every commission of an axis passes its records back to its episode, so the episode can check the job and take its results.

Choose the axis whose next commission you expect to raise the annotation credit most, and answer with that axis. You cannot end this episode: its controller ends it when further commissions stop earning credit."""

OUTPUT_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['axis'],
                 'properties': {'axis': {'type': 'string', 'enum': list(CHILD_SLOTS)}}}


def axis_view(slot, summary, credits, current):
    """What the model is shown of one axis: numbers and flags only."""
    axis = summary['axes'][slot]
    return {'axis': slot, 'weight': AXIS_WEIGHTS[slot], 'credit': axis['credit'],
            'returned_credits': axis['returned_credits'], 'commissions': len(axis['returned_credits']),
            'finding': axis['finding'], 'outstanding_jobs': len(axis['outstanding_job_refs']),
            'annotation_gain_of_one_credit':
                annotation_credit({**credits, slot: credits[slot] + 1.0}) - current}


def decide(summary, feedback, ctx):
    """Ask the model which axis head to commission next."""
    credits = {slot: summary['axes'][slot]['credit'] for slot in CHILD_SLOTS}
    current = annotation_credit(credits)
    context = {'annotation_credit': current, 'k': K,
               'axes': [axis_view(slot, summary, credits, current) for slot in CHILD_SLOTS],
               'commissions': summary['commissions'], 'feedback': feedback}
    return ModelRequest('REASONING', INSTRUCTIONS, context, OUTPUT_SCHEMA)


def action(response, summary, records, ctx):
    """The commission of the axis the model named, with the selection the root's settings give that axis."""
    slot = response['axis']
    if slot not in CHILD_SLOTS:
        raise Rejected({'rejected': 'axis_is_not_one_of_the_nine'})
    return ChildCall(slot, {'selection': ctx.settings['axis_selections'][slot]})
