"""The task of the root: each unit is one commission of one head (feature calling, the organism identification head or
an evidence-axis head). The model chooses the step.

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
is settled a certain amount"; ``credit.ceiling`` is then 0 for an axis head). The annotation heads are commissioned on the
root's scope.

Annotations generate claims (the owner, 2026-11-23). The sequence-homology head finds the candidate annotations and
scores them. What a candidate annotation says the protein does is checked by other heads, and for that the annotation
is first turned into claims: "the protein binds, catalyzes or transports this molecule". The root makes no claims:
that is not one of its decisions (the owner, 2026-11-26: "claims are supposed to be made in their respective arms and
passed up to root"). The head that finds an annotation makes its claims and returns them; the root attaches each to
the line of the annotation it was made from, by code. A claim is then handed to a head that can check its kind
(``CLAIM_CHECKERS``), and what that head finds is that head's score of the annotation the claim was made from: both
heads score the same annotation, on one line of the root's scoring sheet. One claim may go to several heads.

The steps (``choices``). Every head is offered at every decision; the model decides which and how often. A head that
left a job outstanding is owed its return (``resume_action``, not due).

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
from episode_runtime import ChildCall, ModelRequest

from .credit import (AXIS_WEIGHTS, FEATURE_CREDIT_SCALE, FEATURE_FINDER, K, ORGANISM_FINDER, ORGANISM_WEIGHT,
                     root_credit)

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
TAKES_ORGANISM = ('sequence_homology_evidence',)
# The kinds of claim each linked head can check, read from that head's own claim contract (A105:
# ``literature_row_contract.CLAIM_PREDICATES``). A claim is offered to every head that lists its predicate.
CLAIM_CHECKERS = {
    'experimental_activity_evidence': ('binds', 'catalyzes', 'transports'),
}

# The heads that take the root's grouping of their candidates in their commission (``candidate_groups``) and return
# their candidates rescored under it (``docs/plan/designs/a102_regrouping.md``). A head is listed here when its own
# side is built; a head not listed is sent none and its candidates are read as found. The sequence-homology head is not
# listed: it joins its own candidate names (the owner, 2026-11-26: "join this automatically and not use the root to
# decide").
TAKES_GROUPING = ()

INSTRUCTIONS = """You direct the annotation of one sequence. Nothing about it is known beforehand: not what kind of sequence it is, not what it holds. The aim is to find what features it holds (what type of thing lies where on it, and on which strand), what each is, and from which organism, and how well the evidence supports each.

Each step you take one of the `choices`, by its number. They are options, not a sequence of stages: take the one you expect to raise the credit most for its cost.
- `feature_calling`: its episode finds the features of the sequence. It searches sequence databases and runs gene and RNA finders, and gives the candidate feature calls of the sequence (type, positions, strand), each with its score and the calls that compete with it for the same letters, the claims that wait for a call, and the genetic code its gene calls are read under. Its searches also keep taxon claims: the organisms of their hits, which add to the candidate taxa of `organism` by themselves.
- `organism_identification`: its episode classifies the sequence with the tools that can take it and gives the candidate taxa it is from. What it and the taxon claims together say is passed to the sequence homology episode when that is commissioned.
- `sequence_homology_evidence`: its episode searches sequence databases with the sequence, finds candidate annotations and scores each from sequence.
- `experimental_activity_evidence` on one claim: its episode searches the literature for experiments that test that claim. It takes hours. What it finds is its score of the annotation the claim was made from.

Claims are not yours to make: the sequence homology episode makes them for the two leading annotations it finds for a product, turning what each says the product does into claims an experiment could check ("binds", "catalyzes" or "transports" a named molecule), and returns them. An annotation that states no function gives no claims.

The scoring sheet has two levels. `feature_calls` is the level above: for each sequence (`target_ref`) its candidate feature calls, the highest `score` first, each with its type (`kind`), `strand` (. when the call names none), positions (`segments`, and `start` and `end`: zero-based, the end not included), `versions` (every position called for it, each with its support), `score` (the weighted support of the tests at its calls, at the claims that sit in it and at every call it lies within by type), `claim_count` (the claims that sit in it) and `rivals` (the calls that compete with it for letters: their place `rank` in the list and the facts of the letters shared; a rival is a competitor, not a verdict). With them: `rival_rank` (the place of the leading rival of the first), `test_count`, `waiting_claims` (stretches a search says lie inside a feature of a type, which no call includes yet: type, strand, positions, which end they claim, support) and `held_readings` (the genetic code the gene calls are read under: the code `held`, the one best supported, and the support of each code tested). A feature call with no annotation is a line of the sheet with its own score.

`annotations` is the level below: every candidate annotation scored so far, the highest `score` first. Each sits on one feature call, shown as its `feature_call` (the `kind`, `strand`, `start`, `end` and `score` of that feature call). Each has its `vocabulary` and its `name` or `identifier`, its `score`, and `rows`: the score each axis gives it, on that axis's own scale (negative when that axis's evidence says the annotation does not hold). The annotation's score is (prod_i (1 + k * s_i) ** w_i - 1) * ((1 + k * s_o) ** w_o - 1) * s_f: the product over the axis scores s_i, with 0 for an axis that has not scored it, multiplied by the factor of the score s_o of the organism the annotation is reported with, multiplied by the score s_f of the feature call it sits on, so an annotation on a feature call of score zero scores zero. An annotation supported on several axes scores more than the same support on one, and an axis that speaks against it discounts the rest; the organism only scales what the axes give, so an annotation the axes give zero stays at zero, and with no organism every annotation scores zero. That organism is the leading candidate taxon of `organism`; the annotation shows it as `organism_taxon_id` and `organism_score` (absent, with s_o counted 0 and the score 0, when no candidate taxon is held), and `organism_weight` is w_o. The first is the best annotation as the evidence stands.

`genome_annotation` is the annotation of the whole sequence as it stands: every feature call with its `term`, the feature call's score * (1 + `annotation_score`) * `agreement` * `part_coherence`, where `annotation` is the one of its two leading annotations, or none, that gives the highest term, `annotation_score` the axes' score of that annotation alone and `agreement` how far the organisms of the hits behind it are of the family of the leading candidate taxon. Of rival feature calls the one of the higher term is `chosen`; the other shows the feature record it `lost_to`. Its `score` is `organism_factor` * `set_coherence` * the sum of the chosen terms; `part_coherence` and `set_coherence` are 1 for now. The steps earn the `credit`, not this score.

`organism` shows the organism identification episode's `credit`, `commissions` and `gain_of_one_credit`, and which organism the sequence is from: the `candidates` taxa, the leading one first, each with its taxon id, name, rank code, lineage and score (the support on its own lineage, so a vaguer call such as a family supports every finer candidate inside it), the `placement` (the leading candidate, its leading rival and the deepest taxon the two share), `test_count` (the classifications and claim sheets held) and `waiting_claims` (taxon claims of the searches that no candidate is or lies inside: the claimed taxon and its lineage, its bit and support, the candidate it is consistent with, why it waits, what it earned and the source of its claim sheet). The candidates are scored from the classifications of the organism identification episode and the taxon claims of feature calling's searches together: a claim adds to the candidates it lies inside and never opens one.

`claims` lists the claims made: the annotation each was made from, what it says, and for each episode that can check it how often it was commissioned on it.

The `credit` is v_o * (1 + s * v_f * prod_i (1 + k * v_i) ** w_i): v_o is the credit of the organism identification episode, v_f feature calling's credit with its scale s (`feature_credit_scale`), and v_i the axis credits; `k` and the `weight` w_i of each axis are given. The organism multiplies everything: until the organism identification episode has credit the credit is 0 and no other step can raise it, so no other step is worth its cost then. With an organism and nothing else the credit is v_o. Feature calling then multiplies it, and until feature calling has credit no annotation episode can raise it: an annotation sits on a feature. Progress on one axis alone raises the credit linearly; the same progress spread over several axes raises it more. `gain_of_one_credit` is what one more unit of credit of that episode would add now. The scores say which feature and which annotation the evidence favours; the credit says how productive the work was. They are separate.

`feature_calling` shows: `credit`; `credit_after_each_return`; `commissions`; `outstanding_jobs`; and `gain_of_one_credit`. `axes` shows for each axis: `credit`; `credit_after_each_return`; `commissions`; `finding` (the numbers and flags of its latest finding); `outstanding_jobs` (how many jobs its episode left running); and `gain_of_one_credit`. A job that is still running is not evidence: take other steps and return to that axis later.

`action_forecasts` gives, for each kind of step offered, what steps of that kind have earned before (`forecast_gain`), how long they took (`expected_seconds`) and whether one is worth its cost now (`worth`). A step that is not worth its cost is refused.

Spend the expensive steps where they tell the leading annotations apart: a claim that the leading annotation makes and its rival does not is worth more than one both make. Choose the step you expect to raise the credit most. You cannot end this episode: its controller ends it when no step is worth its cost."""


def axis_view(slot, summary, feature_credit, credits, organism_credit, current):
    """What the model is shown of one axis: numbers and flags only."""
    axis = summary['axes'][slot]
    return {'axis': slot, 'weight': AXIS_WEIGHTS[slot], 'credit': axis['credit'],
            'credit_after_each_return': axis['credit_after_each_return'],
            'commissions': len(axis['credit_after_each_return']),
            'finding': axis['finding'], 'outstanding_jobs': axis['outstanding_jobs'],
            'gain_of_one_credit': root_credit(feature_credit, {**credits, slot: credits[slot] + 1.0},
                                              organism_credit) - current}


def feature_view(summary, credits, organism_credit, current):
    """What the model is shown of feature calling: numbers only."""
    features = summary['features']
    return {'credit': features['credit'], 'credit_after_each_return': features['credit_after_each_return'],
            'commissions': len(features['credit_after_each_return']), 'outstanding_jobs': features['outstanding_jobs'],
            'gain_of_one_credit': root_credit(features['credit'] + 1.0, credits, organism_credit) - current}


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


def choices(summary):
    """The steps the model is offered, at every decision: a commission of each head, and of each claim-checking head on
    each claim it can check. Listed in a fixed order so that a number names the same step for the model and for
    ``action``; the list is not an order of work. What to take and how often is the model's decision."""
    offered = [{'action': FEATURE_FINDER}, {'action': ORGANISM_FINDER}, {'action': ANNOTATION_FINDER}]
    offered.extend({'action': slot, 'claim_ref': claim['claim_ref'], **claim_view(claim, summary)}
                   for claim in summary['claims'] for slot, predicates in CLAIM_CHECKERS.items()
                   if claim['predicate'] in predicates)
    return [{'choice': number, **step} for number, step in enumerate(offered)]


def resume_action(summary, records, ctx):
    """The unit this episode owes (``method_loop.episode_type``, step 3): the return to a head that left a job running,
    not due (the model may take other steps worth their cost first); else ``None``."""
    if summary['axes'][ANNOTATION_FINDER]['outstanding_jobs'] > 0:
        return {'action_type': ANNOTATION_FINDER, 'due': False,
                'arguments': {'selection': ctx.settings['axis_selections'][ANNOTATION_FINDER],
                              'organism_candidates': summary['organism']['passed_down']}}
    return None


def decide(summary, feedback, ctx):
    """Ask the model which step to take next."""
    feature_credit, organism_credit = summary['features']['credit'], summary['organism']['credit']
    credits = {slot: summary['axes'][slot]['credit'] for slot in AXIS_WEIGHTS}
    current = root_credit(feature_credit, credits, organism_credit)
    offered = choices(summary)
    context = {'credit': current, 'feature_credit_scale': FEATURE_CREDIT_SCALE, 'k': K,
               'organism_weight': ORGANISM_WEIGHT,
               'feature_calling': feature_view(summary, credits, organism_credit, current),
               'feature_calls': feature_calls_view(summary),
               'annotations': summary['annotations'],
               'genome_annotation': summary['genome_annotation'],
               'claims': [claim_view(claim, summary) for claim in summary['claims']],
               'axes': [axis_view(slot, summary, feature_credit, credits, organism_credit, current)
                        for slot in CHILD_SLOTS if slot in AXIS_WEIGHTS],
               'commissions': summary['commissions'],
               'organism': {**{name: summary['organism'][name]
                               for name in ('credit', 'commissions', 'candidates', 'placement', 'test_count',
                                            'waiting_claims')},
                            'gain_of_one_credit': root_credit(feature_credit, credits, organism_credit + 1.0) - current},
               'choices': [{name: value for name, value in step.items() if name != 'claim_ref'} for step in offered],
               'feedback': feedback}
    schema = {'type': 'object', 'additionalProperties': False, 'required': ['choice'],
              'properties': {'choice': {'type': 'integer', 'enum': [step['choice'] for step in offered]}}}
    return ModelRequest('REASONING', INSTRUCTIONS, context, schema)


def offered_actions(summary, ctx):
    """The action types this decision offers: the actions of ``choices(summary)``, each once."""
    return list(dict.fromkeys(step['action'] for step in choices(summary)))


def action(response, summary, records, ctx):
    """The step the model chose: the commission of feature calling or of the organism identification head (on the root's
    scope: no arguments), or of an axis head with the selection the root's settings give that axis (and, for a head that
    checks claims, the claim)."""
    step = choices(summary)[response['choice']]
    if step['action'] in (FEATURE_FINDER, ORGANISM_FINDER):
        return ChildCall(step['action'], {})
    arguments = {'selection': ctx.settings['axis_selections'][step['action']]}
    if step['action'] != ANNOTATION_FINDER:
        arguments['claim_ref'] = step['claim_ref']
    elif step['action'] in TAKES_GROUPING:
        arguments['candidate_groups'] = summary['groups'][step['action']]
    if step['action'] in TAKES_ORGANISM:
        arguments['organism_candidates'] = summary['organism']['passed_down']
    return ChildCall(step['action'], arguments)


TOOLS = {}
