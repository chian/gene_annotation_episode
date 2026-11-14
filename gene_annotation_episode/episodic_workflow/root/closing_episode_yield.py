"""Recorded closing yield from the original controller state."""
from .received_episode_yield import _BAND

def closing_yield(record):
    """Copy the actual final band, without refitting or expanding audit archives."""
    from .numerical import NumericBand, SignedNumericBand, YieldState
    state = getattr(record, 'controller_state', None)
    if not isinstance(state, YieldState):
        return None
    band = state.estimate.expected_next_gain
    if not isinstance(band, (NumericBand, SignedNumericBand)):
        return None
    return {'completed_actions': record.units_consumed, 'expected_next_gain': {field: getattr(band, field) for field in _BAND['properties']}, 'continuation_cost': state.decision.continuation_cost, 'stop_requested': state.decision.stop}
