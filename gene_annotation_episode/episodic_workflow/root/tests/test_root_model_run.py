"""The real model chooses the root's next axis.

The root's own request (``decide``) is asked of the real model through the standard ``ModelProvider`` over the
packaged ``[models]`` configuration, as ``episode_runtime/tests/test_model_run.py`` does for the test episodes.
``action`` turns the answer into the commission of one of the nine heads, ``msg_to_child`` builds that commission,
and the head's own assignment form and ``read_from_parent`` take it.

What this test does not do: run the heads. A run of the root through the runner (``link``, ``run``, ``resume``)
builds the nine heads and every episode below them, and ``link`` requires the continuation settings and a service
factory for every episode of those nine subtrees. The run's caller supplies them, and no such composition exists in
the repository yet. The test therefore makes the root's decision with the real model and stops at the commission.

Selected only with ``-m model_run`` (see ``pyproject.toml``); it needs the owner's Codex sign-in.
"""
import asyncio

import pytest

from episode_runtime import ChildCall
from gene_annotation_episode.model_provider import ModelProvider, load_config

from ..episode import RootAnnotation
from .test_root_episode import AXES, GIVEN, commission, context, head, opened, returned

FLAT = {'experimental_activity_evidence': 4.0, 'sequence_homology_evidence': 0.5}


@pytest.mark.model_run
def test_the_model_chooses_an_axis_that_can_still_earn_and_the_root_commissions_its_head(tmp_path):
    """Two axes were commissioned three times each and their credit did not move; seven axes were never
    commissioned. One more credit on any of the seven adds more annotation credit than one more on either of the
    two. The model is shown only those numbers and answers with an axis name."""
    view = opened()
    for _ in range(3):
        for slot, credit in FLAT.items():
            view = returned(view, slot, credit)
    summary = RootAnnotation.internal_summary(view)
    request = RootAnnotation.decide(summary, None, context(view))
    shown = {axis['axis']: axis for axis in request.context['axes']}
    assert all(shown[slot]['returned_credits'] == [credit] * 3 for slot, credit in FLAT.items())

    calls = tmp_path / 'model_calls'
    provider = ModelProvider(load_config(), calls, tmp_path)
    response = asyncio.run(provider.complete(view.episode_ref.episode_id, request.role, request.instructions,
                                             dict(request.context), request.output_schema))
    assert len(list(calls.glob('call-*'))) == 1
    assert set(response) == {'axis'} and response['axis'] in AXES
    assert response['axis'] not in FLAT
    assert (shown[response['axis']]['annotation_gain_of_one_credit']
            > max(shown[slot]['annotation_gain_of_one_credit'] for slot in FLAT))

    call = RootAnnotation.action(response, summary, None, context(view))
    assert isinstance(call, ChildCall) and call.slot == response['axis']
    _, _, message = commission(view, call.slot)
    own = head(call.slot, 'messages.read_from_parent')
    admitted = own.ASSIGNMENT_FORM.admit(message.assignment, 'commission:' + call.slot)
    assert set(own.ASSIGNMENT_FORM.record_refs(admitted)) == GIVEN
    parent_input = own.read_from_parent(admitted, dict(message.message))
    assert parent_input['selection']['evidence_axis']['option_id'] == AXES[call.slot][1]
    head(call.slot, 'messages.final_to_parent').RETURN_FORM.select(message.selection)
