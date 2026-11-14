"""Root model connection ownership; importing this module starts no transport."""
import asyncio
import json
from pathlib import Path
import tomllib
from .model_session import (ModelRole, _SessionConnection,
    _ORIGINAL_SESSION_COMPLETE, _ORIGINAL_SESSION_PRESENTATION)
from .provider_errors import ModelCallError
from .provider_configuration import default_config_path

class ModelConnection:
    """Call-scoped provider ownership with original session synchronization.

    Retire the actual owned transport after each call. The existing lock protects
    mutable session state; it is not workflow-wide process admission.
    """
    session_type = _SessionConnection

    def __init__(self, config, directory, cwd, *, image_resolver=None):
        self.config, self.directory, self.cwd = config, Path(directory), Path(cwd)
        self.roles = {name: ModelRole(**config[name]) for name in ("FAST", "REASONING")}
        self.routing = config["routing"]
        self.directory.mkdir(parents=True, exist_ok=False)
        (self.directory / "configuration.json").write_text(json.dumps(config, indent=2))
        self.workers = {}
        self.session_index = 0
        self.retirement_index = 0
        self.maximum_active_workers = 0
        self.image_resolver = image_resolver
        self.worker_lock=asyncio.Lock()

    @property
    def sessions(self):
        return {key: value for worker in self.workers.values() for key, value in worker.sessions.items()}

    def has_session(self, episode_id, role):
        return (episode_id, role) in self.workers

    def conversation_key(self, episode_id, role):
        worker = self.workers.get((episode_id, role))
        return None if worker is None else worker.conversation_key(episode_id, role)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exception):
        for episode_id in tuple(dict.fromkeys(key[0] for key in self.workers)):
            await self.release(episode_id, force=bool(exception and exception[0] is not None and
                issubclass(exception[0], (KeyboardInterrupt, asyncio.CancelledError))))

    async def complete(self, episode_id, role, instructions, context, output_schema):
        async with self.worker_lock:
            return await self._complete_serial(episode_id,role,instructions,context,output_schema)

    async def complete_with_presentation(self, episode_id, role, instructions, context,
                                         output_schema, *, prompt_renderer, declared_presenter):
        """Carry the episode's selected presentation owners through this transport."""
        async with self.worker_lock:
            return await self._complete_serial(episode_id, role, instructions, context,
                output_schema, prompt_renderer=prompt_renderer,
                declared_presenter=declared_presenter)

    async def _complete_serial(self, episode_id, role, instructions, context, output_schema,
                               *, prompt_renderer=None, declared_presenter=None):
        key = (episode_id, role)
        for previous in tuple(dict.fromkeys(k[0] for k in self.workers)):
            await self.release(previous)
        self.session_index += 1
        worker = self.session_type(self.config,
            self.directory / f"session-{self.session_index:04}", self.cwd,
            image_resolver=self.image_resolver)
        await worker.__aenter__()
        self.workers[key] = worker
        self.maximum_active_workers = max(self.maximum_active_workers, len(self.workers))
        try:
            if prompt_renderer is None:
                return await worker.complete(episode_id, role, instructions, context, output_schema)
            return await worker.complete(episode_id, role, instructions, context, output_schema,
                prompt_renderer=prompt_renderer, declared_presenter=declared_presenter)
        except (KeyboardInterrupt, asyncio.CancelledError):
            await self.release(episode_id, force=True)
            raise
        finally:
            await self.release(episode_id)

    async def release(self, episode_id, *, force=False):
        for key in [key for key in self.workers if key[0] == episode_id]:
            worker = self.workers.pop(key)
            pid = worker.process.pid
            await worker.__aexit__(asyncio.CancelledError if force else None, None, None)
            worker.sessions.clear()
            worker.compaction_epochs.clear()
            worker.scientific_prompt_states.clear()
            worker.pending.clear()
            self.retirement_index += 1
            target = self.directory / "retired-sessions"
            target.mkdir(exist_ok=True)
            (target / f"retired-{self.retirement_index:05}.json").write_text(json.dumps({
                "episode_id": episode_id, "role": key[1], "provider_process": pid,
                "provider_exit_code": worker.process.returncode,
                "local_session_removed": True, "remaining_active_workers": len(self.workers),
                "maximum_active_workers": self.maximum_active_workers,
            }, indent=2))

    async def catalog(self):
        async with self.worker_lock:
            for previous in tuple(dict.fromkeys(k[0] for k in self.workers)):
                await self.release(previous)
            async with _SessionConnection(self.config, self.directory / "catalog", self.cwd) as worker:
                return await worker.catalog()


_ORIGINAL_MODEL_COMPLETE = ModelConnection.complete
_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION = ModelConnection.complete_with_presentation
_ORIGINAL_MODEL_COMPLETE_SERIAL = ModelConnection._complete_serial
_ORIGINAL_MODEL_INSTANCE_DICT = ModelConnection.__dict__['__dict__']
_ORIGINAL_MODEL_SESSION_TYPE = ModelConnection.session_type


def load_config(path=None):
    if path is None:
        path = default_config_path()
    return tomllib.loads(Path(path).read_text())["models"]
