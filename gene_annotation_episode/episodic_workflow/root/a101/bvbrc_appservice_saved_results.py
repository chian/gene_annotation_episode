"""Authenticate the latest matching saved result and its numerical contents.

This performs the existing complete publication read for the chosen result,
including its required acquisition dependencies. It then checks the exact saved
content bindings directly. It does not authenticate every older scientific
projection merely to locate the latest one, nor recursively authenticate the
same publication again for each of its two content objects. Nothing is cached
across calls and no scientific calculation, execution or selection occurs.
"""
from .communication import plain
from .execution_contracts import canonical


def read_latest_adapter_result(publications, context, *, adapter_ids):
    """Return (body, sheet, components), or None for no matching owned result.

The numerical order is supplied by the API binding's actual operation indexes.
A corrupt newest matching publication raises; it is never silently replaced by
an older result. A newer partial result remains newer than an older completed
one. Every call reauthenticates the current source and original ownership.
"""
    if (type(adapter_ids) is not tuple or not adapter_ids or
            any(type(v) is not str or not v for v in adapter_ids) or
            len(adapter_ids) != len(set(adapter_ids))):
        raise ValueError('appservice_saved_result_adapter_selection_invalid')
    publications.host.custody.authenticate(context, allow_unsaved=True)
    if context.role != 'results':
        return None
    outcomes = list(publications.api._own_outcomes(context))
    seen = set()
    for _, outcome in reversed(outcomes):
        for reference in reversed((outcome.get('result') or {}).get('result_record_refs', [])):
            if reference in seen:
                continue
            seen.add(reference)
            body = publications.read(reference, context.scope, episode_id=context.episode_id)
            saved = body['publication']['adapter_result']
            if saved is None or saved['adapter_id'] not in adapter_ids:
                continue
            if (body['run_id'] != context.run_id or body['episode_id'] != context.episode_id or
                    canonical(body['scope']) != canonical(plain(context.scope)) or
                    canonical(body['assignment']) != canonical(plain(context.assignment))):
                raise ValueError('appservice_saved_result_owner_conflict')
            origin = body['publication']['origin']
            stamp = body['publication_inputs']['current_snapshot']['retrieved_at']
            contents = [None if saved[name + '_content'] is None else publications._content(
                saved[name + '_content'], origin, name, stamp) for name in ('sheet', 'components')]
            return body, *contents
    return None


__all__ = ['read_latest_adapter_result']
