"""Own provider outer methods remain real; only declared transport ports vary."""
from copy import deepcopy
from types import MethodType

from .. import providers


def observed_session_model(config, directory, cwd, session_type, calls):
    """Keep construction, locking, forwarding, release and presentation actual."""
    workers = []

    class ObservedSession(session_type):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            workers.append(self)

        async def complete(self, episode_id, role, instructions, context, schema, **kwargs):
            calls.append(('private' if kwargs.get('prompt_renderer') is not None else 'original',
                deepcopy(context), deepcopy(schema)))
            return await super().complete(episode_id, role, instructions, context, schema, **kwargs)

    provider = providers.ModelConnection(config, directory, cwd)
    provider.session_type = ObservedSession
    return provider, workers


def controlled_serial_model(config, directory, cwd, callback):
    """Original outer complete/hook + lock; callback is the explicit serial port."""
    provider = providers.ModelConnection(config, directory, cwd)

    async def serial(self, *args, **kwargs):
        return await callback(*args, **kwargs)

    provider._complete_serial = MethodType(serial, provider)
    return provider


def controlled_config():
    """Only for serial-port tests that never create a provider session/process."""
    return {'connection': {'command': ['forbidden-controlled-a104-provider-dispatch']},
        'FAST': {'model': 'controlled', 'reasoning_effort': 'low'},
        'REASONING': {'model': 'controlled', 'reasoning_effort': 'low'}, 'routing': {}}
