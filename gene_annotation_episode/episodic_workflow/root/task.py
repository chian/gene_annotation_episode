"""The task of the root: each unit is one commission of one head (feature calling, the organism identification head or
an evidence-axis head), or the making of the claims of one candidate annotation. The model chooses the step.

The root is given one bare sequence: a string. Nothing here looks at what kind of sequence it is (the owner,
2026-11-25: "root just takes in a sequence. there should be no hard coding about type of sequence. it's just a
string"): only a tool knows what it can take, and a head whose tools take nothing of the sequence finds nothing.

The child slots are named by the heads' roles. Each is bound to the binding path of its head, whose folder sits directly
under the root (``root/feature_calling``, ``root/organism_identification``, ``root/sequence_homology_evidence``,
``root/experimental_activity_evidence``). The root's credit (``credit.py``) is feature calling's credit as the base,
multiplied by the factor of the nine axis credits (``credit.AXIS_WEIGHTS``); ``CHILD_SLOTS`` holds the heads the root
is linked with today, and an axis whose head is not linked stands at credit 0 (see the comment at ``CHILD_SLOTS``). It
never ends its own Episode; its yield controller does.

Feature calling (``FEATURE_FINDER``) says which features the sequence holds: per sequence its candidate feature calls
(type, positions, strand, a score each, the calls that compete for the same letters), the claims that wait for a call,
and the genetic code its gene calls are read under. Its searches also keep taxon claims, which the root's scoring sheet
of candidate taxa reads with the organism head's classifications (``messages/internal_summary.organism_table``). Its
credit is the base of the root's credit: until it is credited, no annotation head can raise the root's credit (the
owner, 2026-11-25: the annotation "is a multiplier of that that cannot gain anything until feature type scoring/credit
is settled a certain amount"; ``credit.ceiling`` is then 0 for an axis head). Tying the annotations to the feature calls
they sit on is not built yet (part B of the root link): the annotation heads are commissioned on the root's scope.

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
input asks the same question again. So the model is offered: a commission of feature calling before its first return
and while it has a job outstanding (it leaves none: it does not end while a search of its own is running); a commission
of the sequence-homology head before its first return, while it has a job outstanding, and (once it takes the root's
grouping of its candidates) when that grouping has changed since it was last sent: a changed grouping is new input, the
head rescores under it; and a commission of a claim-checking head on a claim while that head was not commissioned on
that claim or has a job outstanding. These are options, not a sequence: no order among them is coded. The model
answers with the number of one of them.

Making the claims of an annotation is no decision: it is a set path that is always taken, once, for every candidate
annotation ("you find all the info, you reason about it and add anything else to the list. that's it. done"). So it is
not offered to the model: an annotation on the sheet whose claims were not made yet is work the root has started and
must finish, and the root owes the unit that makes them (``resume_action``, due at once: the system takes it without
asking the model, and the forecast gate does not refuse it). A head that left a job outstanding is owed its return
too, not due: the model may take other steps worth their cost first, and the return is taken when nothing else is.

The root's controller is the forecast yield controller (``yield_estimator.py``): the system adds to what the model is
shown the forecast of every offered action (``action_forecasts``), refuses a chosen step whose forecast is not worth
its cost, and ends the episode when no offered step is worth its cost and no work is owed.

What the model is shown is controlled data only: the root's credit; feature calling's credit, the credit at each of its
returns, how often it was commissioned, how many jobs it left outstanding and what one more unit of its credit would add;
the root's scoring sheet in its two levels (the feature calls of each sequence with their scores, the claims that wait
for a call and the genetic code held; and every candidate annotation the heads scored, with its merged score and each
axis's row); the organism (the candidate taxa of the root's scoring sheet, the placement, the number of tests and the
taxon claims that wait); the claims made; the steps it may take; and for each axis its credit, the credit at each of its
returns (the trend of an axis's credit says whether it is still productive), how often it was commissioned, the numbers
and flags of its latest finding, how many job records its head left outstanding and what one more unit of its credit
would add.

A head that ended its turn with a job outstanding. A head may launch a job that outlives its turn. When only that
job is outstanding its own controller ends it, and it returns the job's records. The root does not wait: the model
sees ``outstanding_jobs`` for that axis, works on other steps, and returns to the axis by commissioning it again.
Every commission of an axis passes back the records its head returned earlier (``messages/msg_to_child.py``), the
job records among them.

The selection each axis head is commissioned with (its evidence-axis option, thought pattern and tools, in that head's
own selection form) is the root's setting ``settings['axis_selections'][slot]``: the references name entries of the
run's frozen libraries by their digests, which only the run's caller has. ``action`` puts it into the commission.
Feature calling and the organism identification head take no selection: their assignment is the root's scope."""
from episode_runtime import ChildCall, ModelRequest, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.tools.annotation_claims.claim_generation import (
    TOOL_NAME as MAKE_CLAIMS, generate_claims)

from .credit import AXIS_WEIGHTS, FEATURE_CREDIT_SCALE, FEATURE_FINDER, K, root_credit
from .messages.internal_summary import ORGANISM_WEIGHT, annotation_key, identity_of

# Slot (the head's role) -> the binding path of the head, the folder of that name under the root: the heads the root is
# linked with. Feature calling (``FEATURE_FINDER``, named in ``credit.py`` because its credit is the base of the root's)
# was linked on 2026-11-25; its own subtree (``feature_calling/bvbrc_blast``) is linked with it.
# The owner, 2026-11-23: link A101 to A105 through a real root and run it from start to finish ("modify the root episode
# to make this now work"). A run links every binding its child slots name, so a head is listed here once it runs on the
# system. On 2026-11-23 the heads of A103, A104, A106, A107, A108 and A110 do not load (they lack ``offered_actions`` and
# ``ceiling``); A102's head loads and is not linked yet. Each is one line here, with its commission in
# ``messages/msg_to_child.py`` (already written), when its head is brought in:
#     'structural_homology_evidence', 'gene_context_evidence', 'evolutionary_history_evidence', 'perturbation_evidence',
#     'partner_presence_evidence', 'sample_context_evidence', 'biochemical_feasibility_evidence'
CHILD_SLOTS = {
    'feature_calling': 'feature_calling',                                      # not an evidence axis: the credit's base
    'organism_identification': 'organism_identification',                      # not an evidence axis
    'sequence_homology_evidence': 'sequence_homology_evidence',                # A101
    'experimental_activity_evidence': 'experimental_activity_evidence',        # A105
}
SERVICES = ()
# The head that finds the candidate annotations: it is commissioned on the subject, not on a claim.
ANNOTATION_FINDER = 'sequence_homology_evidence'
# The head that says which organism the subject is from. It is commissioned on the root's own scope, as every head is:
# its commission is a unit the root owes once, at the start, whatever the subject (its tools check what they can take;
# ``resume_action``). It is no evidence axis and earns no credit of the root's; the root computes the scoring sheet of
# candidate taxa from the records it returns and the taxon claims feature calling keeps
# (``internal_summary.organism_table``); what that sheet holds is passed down to the heads that take it
# (``TAKES_ORGANISM``) and to the claim maker, and the score of its leading candidate is a factor of every candidate
# annotation's score (``internal_summary.annotation_score``). The owner,
# 2026-11-24: "add organismal taxa ID potential candidates as a new head from root"; "a way to pass this info on taxa
# candidates to the root who can pass whatever info it decides down to the other children".
ORGANISM_FINDER = 'organism_identification'
TAKES_ORGANISM = ('sequence_homology_evidence',)
# The kinds of claim each linked head can check, read from that head's own claim contract (A105:
# ``literature_row_contract.CLAIM_PREDICATES``). A claim is offered to every head that lists its predicate.
CLAIM_CHECKERS = {
    'experimental_activity_evidence': ('binds', 'catalyzes', 'transports'),
}

# The heads that take the root's grouping of their candidates in their commission (``candidate_groups``) and return
# their candidates rescored under it (``docs/plan/designs/a102_regrouping.md``). A head is listed here when its own
# side is built; a head not listed is sent none and its candidates are read as found.
TAKES_GROUPING = ('sequence_homology_evidence',)

INSTRUCTIONS = """You direct the annotation of one sequence. Nothing about it is known beforehand: not what kind of sequence it is, not what it holds. The aim is to find what features it holds (what type of thing lies where on it, and on which strand), what each is, and from which organism, and how well the evidence supports each.

Each step you take one of the `choices`, by its number. They are options, not a sequence of stages: take the one you expect to raise the credit most for its cost.
- `feature_calling`: its episode finds the features of the sequence. It searches sequence databases and runs gene and RNA finders, and gives the candidate feature calls of the sequence (type, positions, strand), each with its score and the calls that compete with it for the same letters, the claims that wait for a call, and the genetic code its gene calls are read under. Its searches also keep taxon claims: the organisms of their hits, which add to the candidate taxa of `organism` by themselves.
- `sequence_homology_evidence`: its episode searches sequence databases with the sequence, finds candidate annotations and scores each from sequence.
- `experimental_activity_evidence` on one claim: its episode searches the literature for experiments that test that claim. It takes hours. What it finds is its score of the annotation the claim was made from.

Two things are done for you, not chosen. The organism identification episode is run at the start: it classifies the sequence with the tools that can take it, and what the classifications and the taxon claims together say is passed to the sequence homology episode and to the making of the claims. Claims are made for you: for every candidate annotation found, what it says the product of the sequence does is turned into claims an experiment could check ("binds", "catalyzes" or "transports" a named molecule). An annotation that states no function gives no claims.

The scoring sheet has two levels. `feature_calls` is the level above: for each sequence (`target_ref`) its candidate feature calls, the highest `score` first, each with its type (`kind`), `strand` (. when the call names none), positions (`segments`, and `start` and `end`: zero-based, the end not included), `versions` (every position called for it, each with its support), `score` (the weighted support of the tests at its calls, at the claims that sit in it and at every call it lies within by type), `claim_count` (the claims that sit in it) and `rivals` (the calls that compete with it for letters: their place `rank` in the list and the facts of the letters shared; a rival is a competitor, not a verdict). With them: `rival_rank` (the place of the leading rival of the first), `test_count`, `waiting_claims` (stretches a search says lie inside a feature of a type, which no call includes yet: type, strand, positions, which end they claim, support) and `held_readings` (the genetic code the gene calls are read under: the code `held`, the one best supported, and the support of each code tested). A feature call with no annotation is a line of the sheet with its own score.

`annotations` is the level below: every candidate annotation scored so far, the highest `score` first. An annotation is not yet tied to the feature call it sits on: it is scored as the annotation episodes give it. Each has its `vocabulary` and its `name` or `identifier`, its `score`, and `rows`: the score each axis gives it, on that axis's own scale (negative when that axis's evidence says the annotation does not hold). The annotation's score is (prod_i (1 + k * s_i) ** w_i - 1) * (1 + k * s_o) ** w_o: the product over the axis scores s_i, with 0 for an axis that has not scored it, multiplied by the factor of the score s_o of the organism the annotation is reported with. An annotation supported on several axes scores more than the same support on one, and an axis that speaks against it discounts the rest; the organism only scales what the axes give, so an annotation the axes give zero stays at zero. That organism is the leading candidate taxon of `organism`; the annotation shows it as `organism_taxon_id` and `organism_score` (absent, with s_o counted 0 and the factor 1, when no candidate taxon is held), and `organism_weight` is w_o. The first is the best annotation as the evidence stands.

`organism` shows which organism the sequence is from: the `candidates` taxa, the leading one first, each with its taxon id, name, rank code, lineage and score (the support on its own lineage, so a vaguer call such as a family supports every finer candidate inside it), the `placement` (the leading candidate, its leading rival and the deepest taxon the two share), `test_count` (the classifications and claim sheets held) and `waiting_claims` (taxon claims of the searches that no candidate is or lies inside: the claimed taxon and its lineage, its bit and support, the candidate it is consistent with, why it waits, what it earned and the source of its claim sheet). The candidates are scored from the classifications of the organism identification episode and the taxon claims of feature calling's searches together: a claim adds to the candidates it lies inside and never opens one.

`claims` lists the claims made: the annotation each was made from, what it says, and for each episode that can check it how often it was commissioned on it.

The `credit` is s * v_f * prod_i (1 + k * v_i) ** w_i: feature calling's credit v_f, times its scale s (`feature_credit_scale`), is the base, and the axis credits v_i multiply it; `k` and the `weight` w_i of each axis are given. Until feature calling has credit the credit is 0, and no annotation episode can raise it: an annotation sits on a feature, and gains nothing before the features are found, so a commission of an annotation episode is not worth its cost then. With feature calling credited and no axis credit the credit is s * v_f. Progress on one axis alone then raises it linearly; the same progress spread over several axes raises it more. `gain_of_one_credit` is what one more unit of credit of that episode would add now. The scores say which feature and which annotation the evidence favours; the credit says how productive the work was. They are separate.

`feature_calling` shows: `credit`; `credit_after_each_return`; `commissions`; `outstanding_jobs`; and `gain_of_one_credit`. `axes` shows for each axis: `credit`; `credit_after_each_return`; `commissions`; `finding` (the numbers and flags of its latest finding); `outstanding_jobs` (how many jobs its episode left running); and `gain_of_one_credit`. A job that is still running is not evidence: take other steps and return to that axis later.

`action_forecasts` gives, for each kind of step offered, what steps of that kind have earned before (`forecast_gain`), how long they took (`expected_seconds`) and whether one is worth its cost now (`worth`). A step that is not worth its cost is refused.

Only steps that have something new to run on are offered: an episode that has returned without a job outstanding did everything worth doing with what it held, so it is not offered again on the same input.

Spend the expensive steps where they tell the leading annotations apart: a claim that the leading annotation makes and its rival does not is worth more than one both make. Choose the step you expect to raise the credit most. You cannot end this episode: its controller ends it when no step is worth its cost."""


def axis_view(slot, summary, feature_credit, credits, current):
    """What the model is shown of one axis: numbers and flags only."""
    axis = summary['axes'][slot]
    return {'axis': slot, 'weight': AXIS_WEIGHTS[slot], 'credit': axis['credit'],
            'credit_after_each_return': axis['credit_after_each_return'],
            'commissions': len(axis['credit_after_each_return']),
            'finding': axis['finding'], 'outstanding_jobs': axis['outstanding_jobs'],
            'gain_of_one_credit': root_credit(feature_credit, {**credits, slot: credits[slot] + 1.0}) - current}


def feature_view(summary, credits, current):
    """What the model is shown of feature calling: numbers only."""
    features = summary['features']
    return {'credit': features['credit'], 'credit_after_each_return': features['credit_after_each_return'],
            'commissions': len(features['credit_after_each_return']), 'outstanding_jobs': features['outstanding_jobs'],
            'gain_of_one_credit': root_credit(features['credit'] + 1.0, credits) - current}


def feature_calls_view(summary):
    """The level above of the root's scoring sheet as the model is shown it: per sequence, the feature calls and the
    waiting claims without their record references, and the genetic code held without the sequence repeated."""
    return [{'target_ref': target['target_ref'],
             'features': [{name: value for name, value in row.items() if name != 'feature_refs'}
                          for row in target['features']],
             **({'rival_rank': target['rival_rank']} if 'rival_rank' in target else {}),
             'test_count': target['test_count'],
             'waiting_claims': [{name: value for name, value in row.items() if name != 'feature_refs'}
                                for row in target['waiting_claims']],
             'held_readings': [{name: value for name, value in row.items() if name != 'target_ref'}
                               for row in target['held_readings']]}
            for target in summary['feature_calls']]


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
    head = summary['features'] if slot == FEATURE_FINDER else summary['axes'][slot]
    ran = bool(head['credit_after_each_return']) if claim_ref is None else claim_ref in head['claim_commissions']
    regrouped = slot in TAKES_GROUPING and claim_ref is None and summary['groups'][slot] != head['groups_sent']
    return not ran or head['outstanding_jobs'] > 0 or regrouped


def choices(summary):
    """The steps the model is offered now, listed in a fixed order so that a number names the same step for the model
    and for ``action`` (the list is not an order of work: see the module text). Each is the action the system takes for
    it and what the model is shown of it."""
    offered = []
    if has_something_new(FEATURE_FINDER, summary):
        offered.append({'action': FEATURE_FINDER})
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


def organism_owed(summary):
    """Whether the commission of the organism identification head is owed: the head has not been commissioned yet.
    Whatever the subject: its tools check what they can take."""
    return summary['organism']['commissions'] == 0


def organism_of_claims(summary):
    """The organism the claim maker is told: the leading candidate taxon (id, name, rank code, score), or ``None`` when
    there is none."""
    leaders = [row for row in summary['organism']['passed_down'] if row['role'] == 'leader']
    return leaders[0] if leaders else None


def resume_action(summary, records, ctx):
    """The unit this episode owes (``method_loop.episode_type``, step 3): the commission of the organism identification
    head while it is owed, due at once (before any head that takes the organism is commissioned); else the making of the claims of the first
    annotation on the sheet that has none yet, due at once; else the return to a head that left a job running, not due
    (the model may take other steps worth their cost first); else ``None``."""
    if organism_owed(summary):
        return {'action_type': ORGANISM_FINDER, 'due': True, 'arguments': {}}
    waiting = annotations_without_claims(summary)
    if waiting:
        (subject,) = summary['scope']['subject_refs']
        return {'action_type': MAKE_CLAIMS, 'due': True,
                'arguments': {'annotation': waiting[0], 'subject_ref': subject, 'organism': organism_of_claims(summary),
                              'rivals': [identity_of(annotation) for annotation in summary['annotations']
                                         if identity_of(annotation) != waiting[0]]}}
    if summary['axes'][ANNOTATION_FINDER]['outstanding_jobs'] > 0:
        return {'action_type': ANNOTATION_FINDER, 'due': False,
                'arguments': {'selection': ctx.settings['axis_selections'][ANNOTATION_FINDER],
                              'candidate_groups': summary['groups'][ANNOTATION_FINDER],
                              'organism_candidates': summary['organism']['passed_down']}}
    return None


def decide(summary, feedback, ctx):
    """Ask the model which step to take next."""
    feature_credit = summary['features']['credit']
    credits = {slot: summary['axes'][slot]['credit'] for slot in AXIS_WEIGHTS}
    current = root_credit(feature_credit, credits)
    offered = choices(summary)
    context = {'credit': current, 'feature_credit_scale': FEATURE_CREDIT_SCALE, 'k': K,
               'organism_weight': ORGANISM_WEIGHT,
               'feature_calling': feature_view(summary, credits, current),
               'feature_calls': feature_calls_view(summary),
               'annotations': summary['annotations'],
               'claims': [claim_view(claim, summary) for claim in summary['claims']],
               'axes': [axis_view(slot, summary, feature_credit, credits, current)
                        for slot in CHILD_SLOTS if slot in AXIS_WEIGHTS],
               'commissions': summary['commissions'],
               'organism': {name: summary['organism'][name]
                            for name in ('candidates', 'placement', 'test_count', 'waiting_claims')},
               'choices': [{name: value for name, value in step.items() if name != 'claim_ref'} for step in offered],
               'feedback': feedback}
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['choice'],
              'properties': {'choice': {'type': 'integer', 'enum': [step['choice'] for step in offered]}}}
    return ModelRequest('REASONING', INSTRUCTIONS, context, schema)


def offered_actions(summary, ctx):
    """The action types this decision offers: the actions of ``choices(summary)``, each once, and ``make_claims`` while
    an annotation's claims are owed."""
    return list(dict.fromkeys([step['action'] for step in choices(summary)]
                              + ([MAKE_CLAIMS] if annotations_without_claims(summary) else [])
                              + ([ORGANISM_FINDER] if organism_owed(summary) else [])))


def action(response, summary, records, ctx):
    """The step the model chose: the commission of feature calling (on the root's scope: no arguments), or of an axis
    head with the selection the root's settings give that axis (and, for a head that checks claims, the claim)."""
    step = choices(summary)[response['choice']]
    if step['action'] == FEATURE_FINDER:
        return ChildCall(FEATURE_FINDER, {})
    arguments = {'selection': ctx.settings['axis_selections'][step['action']]}
    if step['action'] != ANNOTATION_FINDER:
        arguments['claim_ref'] = step['claim_ref']
    elif step['action'] in TAKES_GROUPING:
        arguments['candidate_groups'] = summary['groups'][step['action']]
    if step['action'] in TAKES_ORGANISM:
        arguments['organism_candidates'] = summary['organism']['passed_down']
    return ChildCall(step['action'], arguments)


async def make_claims(arguments, ctx):
    """The claims of one candidate annotation, by the set workflow of ``claim_generation.generate_claims``."""
    return await generate_claims(ctx.store, ctx.model, ctx.operation_key, annotation=arguments['annotation'],
                                 rivals=arguments['rivals'], subject_ref=arguments['subject_ref'],
                                 organism=arguments['organism'])


TOOLS = {MAKE_CLAIMS: make_claims}
