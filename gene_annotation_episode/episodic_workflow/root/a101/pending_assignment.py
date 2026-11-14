"""The parent's original commitment, separate from a child's private work."""
from collections.abc import Mapping

from .communication import plain


def original_assignment(request, decision_index):
    if request is None:
        return None
    if isinstance(request, Mapping):
        objective, message = request['goal']['objective'], request['message']
    else:
        objective, message = request.goal.objective, request.message.as_record()
    result = {'objective': plain(objective), 'scope': plain(message.get('scope')),
        'decision_index': decision_index}
    assignment = message.get('episode_assignment')
    if isinstance(assignment, Mapping):
        # These are the parent's original task inputs. Their internal field
        # names belong to the caller; task/focus variants must all survive.
        result.update({key: plain(assignment[key]) for key in
            ('context', 'constraints', 'evidence_refs') if key in assignment})
    context = assignment.get('context') if isinstance(assignment, Mapping) else None
    if isinstance(context, Mapping) and context.get('investigation_focus') is not None:
        result['investigation_focus'] = plain(context['investigation_focus'])
    return result
