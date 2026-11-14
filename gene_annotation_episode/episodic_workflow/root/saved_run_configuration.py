"""Saved run configuration and original numerical continuation settings."""
from __future__ import annotations
from collections.abc import Mapping
import json
from pathlib import Path
import tomllib
import uuid
from .boundary_validation import parse_json_object
from .episode_journal import WorkflowError
from .task_values import _plain, _digest
from .workflow_values import _annotation_child_roles

def _recorded_annotation_child_roles(settings):
    if 'annotation_child_roles' not in settings:
        return None
    value = settings['annotation_child_roles']
    if not isinstance(value, list):
        raise ValueError('invalid_recorded_annotation_child_roles')
    return _annotation_child_roles(tuple(value))


def _has_explicit_model_configuration(configuration):
    return "models" in configuration or any(key in configuration for key in
        ("FAST", "REASONING", "connection", "routing"))


def _effective_models(provider_config=None):
    from .provider_configuration import default_config_path
    defaults = tomllib.loads(default_config_path().read_text())
    supplied = {} if provider_config is None else _plain(provider_config)
    if not isinstance(supplied, Mapping):
        raise TypeError("provider_config must be a mapping")
    models = supplied.get("models", supplied) if _has_explicit_model_configuration(supplied) else defaults["models"]
    for role in ("FAST", "REASONING"):
        if not isinstance(models.get(role), Mapping) or set(models[role]) != {"model", "reasoning_effort"}:
            raise ValueError(f"{role} must declare model and reasoning_effort")
    return _plain(models)


def _effective_configuration(provider_config=None, controller_settings=None):
    """Choose defaults once at the caller boundary, before an Episode exists."""
    from .provider_configuration import default_config_path
    defaults = tomllib.loads(default_config_path().read_text())
    supplied = {} if provider_config is None else _plain(provider_config)
    models = _effective_models(provider_config)
    controller = dict(defaults["controller"])
    controller.update(supplied.get("controller", {}))
    if controller_settings is not None:
        controller.update(controller_settings)
    unknown = set(controller) - {"cost", "window_size", "subsample_size", "uncertainty_alpha"}
    if unknown:
        raise ValueError(f"unknown controller settings: {sorted(unknown)}")
    from .numerical import YieldParameters
    YieldParameters(**{key: value for key, value in controller.items() if key != "cost"})
    cost = controller["cost"]
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not 0 <= cost < float("inf"):
        raise ValueError("continuation cost must be finite and nonnegative")
    return _plain(models), controller


def _credit_binding_from_settings(settings):
    """Expose the recorded score meaning without projecting state again."""
    versions = settings["binding_versions"]["credit"]
    binding = {"projector": settings["bindings"]["credit"], "versions": _plain(versions),
               "scope_source": "context.scope"}
    result = {**binding, "kind": "custom",
        "meaning": "Bound projector; its recorded definition declares the score, axes and denominator."}
    definition = settings.get("binding_definitions", {}).get("credit")
    if definition is not None:
        result["definition"] = _plain(definition)
    return result


def _run_location(store, run_dir, resume):
    if run_dir is None and resume:
        exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_runs'").fetchone()
        row = (store.db.execute("SELECT settings FROM runtime_runs ORDER BY started_at DESC,run_id DESC LIMIT 1").fetchone()
               if exists else None)
        if row is None:
            raise WorkflowError("no saved run exists to resume")
        run_dir = json.loads(row[0])["directory"]
    directory = Path(run_dir) if run_dir is not None else Path.cwd() / "runs" / uuid.uuid4().hex
    directory = directory.expanduser().resolve()
    marker = directory / "run.json"
    if resume:
        if not marker.is_file():
            raise WorkflowError("resume requires an existing run.json")
        manifest = parse_json_object(marker.read_text())
        return directory, manifest["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    if marker.exists():
        raise WorkflowError("run directory already contains a run; use resume")
    return directory, "run_" + uuid.uuid4().hex


def controller_from_settings(settings):
    """Restore the configured default controller without selecting new values."""
    from .numerical import YieldController
    control = settings.get('controller')
    if control is None:
        raise WorkflowError('original_caller_controller_factory_required')
    def factory(path, initial_credit):
        return YieldController(_digest(path), initial_credit, control['cost'],
            {key: value for key, value in control.items() if key != 'cost'})
    return factory


