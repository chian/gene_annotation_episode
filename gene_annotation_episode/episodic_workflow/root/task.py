"""The task of the root: each unit is one commission of one evidence-axis head, or the making of the claims of one
candidate annotation. The model chooses the step.

The child slots are named by the axis roles. Each is bound to the binding path of the head in its axis folder
(``root/a101/sequence_homology_evidence``, ``root/a105/experimental_activity_evidence``). The annotation credit is
over nine axes (``credit.AXIS_WEIGHTS``); ``CHILD_SLOTS`` holds the heads the root is linked with today, and an axis
whose head is not linked stands at credit 0 (see the comment at ``CHILD_SLOTS``). It never ends its own Episode; its
yield controller does.

Annotations generate claims (the owner, 2026-11-23). The sequence-homology head finds the candidate annotations and
scores them. What a candidate annotation says the protein does is checked by other heads, and for that the annotation
is first turned into claims: "the protein binds, catalyzes or transports this molecule". The tool ``make_claims`` does
that for one annotation, once, by a set workflow (``episode_support/tools/annotation_claims/claim_generation.py``:
find what the public record states, one model call reads it and writes the claims, only looked-up molecules are kept);
the root sees the claims and nothing of the process. A claim is then handed to a head that can check its kind
(``CLAIM_CHECKERS``), and what that head finds is that head's score of the annotation the claim was made from: both
heads score the same annotation, on one line of the root's scoring sheet. One claim may go to several heads.

The steps (``choices``, ``resume_action``). A step is offered only when there is something new for it (the owner,
2026-11-23: "it's not at all reasonable to expect new results under the same controller and purely deterministic
tools"). Every head is ended by its own yield estimator, which is that head's verdict that nothing more is worth doing
with what it holds; a head that returned and left no job running ran fully, and commissioning it again on the same
input asks the same question again. So the model is offered: a commission of the sequence-homology head before its
first return, while it has a job outstanding, and (once it takes the root's grouping of its candidates) when that
grouping has changed since it was last sent: a changed grouping is new input, the head rescores under it; and a commission of a claim-checking head on a claim while that head
was not commissioned on that claim or has a job outstanding. The model answers with the number of one of them.

Making the claims of an annotation is no decision: it is a set path that is always taken, once, for every candidate
annotation ("you find all the info, you reason about it and add anything else to the list. that's it. done"). So it is
not offered to the model: an annotation on the sheet whose claims were not made yet is work the root has started and
must finish, and the root owes the unit that makes them (``resume_action``, due at once: the system takes it without
asking the model, and the forecast gate does not refuse it). A head that left a job outstanding is owed its return
too, not due: the model may take other steps worth their cost first, and the return is taken when nothing else is.

The root's controller is the forecast yield controller (``yield_estimator.py``): the system adds to what the model is
shown the forecast of every offered action (``action_forecasts``), refuses a chosen step whose forecast is not worth
its cost, and ends the episode when no offered step is worth its cost and no work is owed.

What the model is shown is controlled data only: the annotation credit, the root's scoring sheet (every candidate
annotation the heads scored, with its merged score and each axis's row), the claims made, the steps it may take, and
for each axis its credit, the credit at each of its returns (the trend of an axis's credit says whether it is still
productive), how often it was commissioned, the numbers and flags of its latest finding and how many job records its
head left outstanding.

A head that ended its turn with a job outstanding. A head may launch a job that outlives its turn. When only that
job is outstanding its own controller ends it, and it returns the job's records. The root does not wait: the model
sees ``outstanding_jobs`` for that axis, works on other steps, and returns to the axis by commissioning it again.
Every commission of an axis passes back the records its head returned earlier (``messages/msg_to_child.py``), the
job records among them.

The selection each head is commissioned with (its evidence-axis option, thought pattern and tools, in that head's
own selection form) is the root's setting ``settings['axis_selections'][slot]``: the references name entries of the
run's frozen libraries by their digests, which only the run's caller has. ``action`` puts it into the commission."""
from episode_runtime import ChildCall, ModelRequest, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.tools.annotation_claims.claim_generation import (
    TOOL_NAME as MAKE_CLAIMS, generate_claims)

from .credit import AXIS_WEIGHTS, K, annotation_credit
from .messages.internal_summary import annotation_key, identity_of

# Slot (the axis role) -> the binding path of the axis head in its axis folder: the heads the root is linked with.
# The owner, 2026-11-23: link A101 to A105 through a real root and run it from start to finish ("modify the root episode
# to make this now work"). A run links every binding its child slots name, so a head is listed here once it runs on the
# system. On 2026-11-23 the heads of A103, A104, A106, A107, A108 and A110 do not load (they lack ``offered_actions`` and
# ``ceiling``); A102's head loads and is not linked yet. Each is one line here, with its commission in
# ``messages/msg_to_child.py`` (already written), when its head is brought in:
#     'structural_homology_evidence', 'gene_context_evidence', 'evolutionary_history_evidence', 'perturbation_evidence',
#     'partner_presence_evidence', 'sample_context_evidence', 'biochemical_feasibility_evidence'
CHILD_SLOTS = {
    'sequence_homology_evidence': 'sequence_homology_evidence',                # A101, root/a101
    'experimental_activity_evidence': 'experimental_activity_evidence',        # A105, root/a105
}
SERVICES = ()
# The head that finds the candidate annotations: it is commissioned on the subject, not on a claim.
ANNOTATION_FINDER = 'sequence_homology_evidence'
# The kinds of claim each linked head can check, read from that head's own claim contract (A105:
# ``literature_row_contract.CLAIM_PREDICATES``). A claim is offered to every head that lists its predicate.
CLAIM_CHECKERS = {
    'experimental_activity_evidence': ('binds', 'catalyzes', 'transports'),
}

# The heads that take the root's grouping of their candidates in their commission (``candidate_groups``) and return
# their candidates rescored under it (``docs/plan/designs/a102_regrouping.md``). A head is listed here when its own
# side is built; a head not listed is sent none and its candidates are read as found.
TAKES_GROUPING = ('sequence_homology_evidence',)

INSTRUCTIONS = """You direct the annotation of one protein. The aim is to find its best annotation and how well the evidence supports it.

Each step you take one of the `choices`, by its number:
- `sequence_homology_evidence`: its episode searches sequence databases, finds candidate annotations for the protein and scores each from sequence.
- `experimental_activity_evidence` on one claim: its episode searches the literature for experiments that test that claim. It takes hours. What it finds is its score of the annotation the claim was made from.

Claims are made for you: for every candidate annotation found, what it says the protein does is turned into claims an experiment could check ("binds", "catalyzes" or "transports" a named molecule). An annotation that states no function gives no claims.

`annotations` is the scoring sheet: every candidate annotation scored so far, the highest `score` first. Each has its `vocabulary` and its `name` or `identifier`, its `score`, and `rows`: the score each axis gives it, on that axis's own scale (negative when that axis's evidence says the annotation does not hold). The annotation's score is prod_i (1 + k * s_i) ** w_i - 1 over the axis scores s_i, with 0 for an axis that has not scored it: an annotation supported on several axes scores more than the same support on one, and an axis that speaks against it discounts the rest. The first is the best annotation as the evidence stands.

`claims` lists the claims made: the annotation each was made from, what it says, and for each episode that can check it how often it was commissioned on it.

The annotation credit is prod_i (1 + k * v_i) ** w_i - 1 over the axis credits v_i; `k` and the `weight` w_i of each axis are given. Progress on one axis alone raises it linearly. The same progress spread over several axes raises it more. `annotation_gain_of_one_credit` is what one more unit of credit on that axis would add now. The scores say which annotation the evidence favours; the credit says how productive the work was. They are separate.

`axes` shows for each axis: `credit`; `credit_after_each_return`; `commissions`; `finding` (the numbers and flags of its latest finding); and `outstanding_jobs` (how many jobs its episode left running). A job that is still running is not evidence: take other steps and return to that axis later.

`action_forecasts` gives, for each kind of step offered, what steps of that kind have earned before (`forecast_gain`), how long they took (`expected_seconds`) and whether one is worth its cost now (`worth`). A step that is not worth its cost is refused.

Only steps that have something new to run on are offered: an episode that has returned without a job outstanding did everything worth doing with what it held, so it is not offered again on the same input.

Spend the expensive steps where they tell the leading annotations apart: a claim that the leading annotation makes and its rival does not is worth more than one both make. Choose the step you expect to raise the annotation credit most. You cannot end this episode: its controller ends it when no step is worth its cost."""


def axis_view(slot, summary, credits, current):
    """What the model is shown of one axis: numbers and flags only."""
    axis = summary['axes'][slot]
    return {'axis': slot, 'weight': AXIS_WEIGHTS[slot], 'credit': axis['credit'],
            'credit_after_each_return': axis['credit_after_each_return'],
            'commissions': len(axis['credit_after_each_return']),
            'finding': axis['finding'], 'outstanding_jobs': axis['outstanding_jobs'],
            'annotation_gain_of_one_credit':
                annotation_credit({**credits, slot: credits[slot] + 1.0}) - current}


def claim_view(claim, summary):
    """What the model is shown of one claim: the annotation it was made from, what it says, and how often each head that
    can check it was commissioned on it."""
    return {'annotation': claim['annotation'], 'predicate': claim['predicate'], 'partner': claim['partner'],
            'partner_kind': claim['partner_kind'],
            'commissions': {slot: summary['axes'][slot]['claim_commissions'].get(claim['claim_ref'], 0)
                            for slot, predicates in CLAIM_CHECKERS.items() if claim['predicate'] in predicates}}


def has_something_new(slot, summary, claim_ref=None):
    """Whether a commission of ``slot`` (on ``claim_ref`` for a claim-checking head) has something new to run on: the
    head has not run on this input yet, it left a job running at its latest return, or (a head that takes the root's
    grouping of its candidates) the grouping the root holds now differs from the one it was last sent."""
    axis = summary['axes'][slot]
    ran = bool(axis['credit_after_each_return']) if claim_ref is None else claim_ref in axis['claim_commissions']
    regrouped = slot in TAKES_GROUPING and claim_ref is None and summary['groups'][slot] != axis['groups_sent']
    return not ran or axis['outstanding_jobs'] > 0 or regrouped


def choices(summary):
    """The steps the model is offered now, in a fixed order (see the module text). Each is the action the system takes
    for it and what the model is shown of it."""
    offered = []
    if has_something_new(ANNOTATION_FINDER, summary):
        offered.append({'action': ANNOTATION_FINDER})
    for claim in summary['claims']:
        for slot, predicates in CLAIM_CHECKERS.items():
            if claim['predicate'] in predicates and has_something_new(slot, summary, claim['claim_ref']):
                offered.append({'action': slot, 'claim_ref': claim['claim_ref'], **claim_view(claim, summary)})
    return [{'choice': number, **step} for number, step in enumerate(offered)]


def annotations_without_claims(summary):
    """The annotations on the sheet whose claims were not made yet, in the order of the sheet."""
    return [identity_of(annotation) for annotation in summary['annotations']
            if annotation_key(annotation) not in summary['claims_made']]


def resume_action(summary, records, ctx):
    """The unit this episode owes (``method_loop.episode_type``, step 3): the making of the claims of the first
    annotation on the sheet that has none yet, due at once; else the return to a head that left a job running, not due
    (the model may take other steps worth their cost first); else ``None``."""
    waiting = annotations_without_claims(summary)
    if waiting:
        (subject,) = summary['scope']['subject_refs']
        return {'action_type': MAKE_CLAIMS, 'due': True,
                'arguments': {'annotation': waiting[0], 'subject_ref': subject,
                              'rivals': [identity_of(annotation) for annotation in summary['annotations']
                                         if identity_of(annotation) != waiting[0]]}}
    if summary['axes'][ANNOTATION_FINDER]['outstanding_jobs'] > 0:
        return {'action_type': ANNOTATION_FINDER, 'due': False,
                'arguments': {'selection': ctx.settings['axis_selections'][ANNOTATION_FINDER],
                              'candidate_groups': summary['groups'][ANNOTATION_FINDER]}}
    return None


def decide(summary, feedback, ctx):
    """Ask the model which step to take next."""
    credits = {slot: summary['axes'][slot]['credit'] for slot in AXIS_WEIGHTS}
    current = annotation_credit(credits)
    offered = choices(summary)
    context = {'annotation_credit': current, 'k': K,
               'annotations': summary['annotations'],
               'claims': [claim_view(claim, summary) for claim in summary['claims']],
               'axes': [axis_view(slot, summary, credits, current) for slot in CHILD_SLOTS],
               'commissions': summary['commissions'],
               'choices': [{name: value for name, value in step.items() if name != 'claim_ref'} for step in offered],
               'feedback': feedback}
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['choice'],
              'properties': {'choice': {'type': 'integer', 'enum': [step['choice'] for step in offered]}}}
    return ModelRequest('REASONING', INSTRUCTIONS, context, schema)


def offered_actions(summary, ctx):
    """The action types this decision offers: the actions of ``choices(summary)``, each once, and ``make_claims`` while
    an annotation's claims are owed."""
    return list(dict.fromkeys([step['action'] for step in choices(summary)]
                              + ([MAKE_CLAIMS] if annotations_without_claims(summary) else [])))


def action(response, summary, records, ctx):
    """The step the model chose: the commission of a head with the selection the root's settings give that axis (and,
    for a head that checks claims, the claim)."""
    step = choices(summary)[response['choice']]
    arguments = {'selection': ctx.settings['axis_selections'][step['action']]}
    if step['action'] != ANNOTATION_FINDER:
        arguments['claim_ref'] = step['claim_ref']
    elif step['action'] in TAKES_GROUPING:
        arguments['candidate_groups'] = summary['groups'][step['action']]
    return ChildCall(step['action'], arguments)


async def make_claims(arguments, ctx):
    """The claims of one candidate annotation, by the set workflow of ``claim_generation.generate_claims``."""
    return await generate_claims(ctx.store, ctx.model, ctx.operation_key, annotation=arguments['annotation'],
                                 rivals=arguments['rivals'], subject_ref=arguments['subject_ref'])


TOOLS = {MAKE_CLAIMS: make_claims}
