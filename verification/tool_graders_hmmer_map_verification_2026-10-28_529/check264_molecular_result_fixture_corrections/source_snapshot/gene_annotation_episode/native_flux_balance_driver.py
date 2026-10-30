"""One original selected FBA invocation and an immutable eight-role bundle.

This source-derived adapter is deliberately distinct from Biomni's lossy log
wrapper. It has no process launcher, retry, resource chooser or episode loop.
"""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import importlib.metadata
import io
import logging
import os
from pathlib import Path
import sys
import warnings

from .execution_contracts import canonical, digest
from .flux_balance_contracts import normalize_fba_solver_status
from .native_flux_balance_contracts import (OWNER_FILENAME, STARTED_FILENAME, SOLVE_ENTERED_FILENAME, ENVIRONMENT_FILENAME,
    flux_balance_environment, require, validate_flux_balance_run_plan, validate_flux_balance_software)
from .native_flux_balance_storage import (confined_file, directory, file_pin, immutable_bytes, immutable_json,
    read_bytes, read_json, retain_input)
from . import native_flux_balance_cobra_glpk as capture


def _now():
    return datetime.now(timezone.utc).isoformat()


def _verify_software(software, *, native_loaded=False):
    software = validate_flux_balance_software(software)
    require(str(Path(sys.executable).resolve()) == software["python"]["path"] and sys.version == software["python_version"],
            "fba_interpreter_mismatch")
    pins = [software["python"], *software["implementation_files"], *software["runtime_files"], *software["solver_runtime_files"]]
    by_path = {row["path"]: row for row in pins}
    for row in pins:
        require(file_pin(row["path"]) == row, "fba_software_file_changed")
    distributions = []
    for row in software["distributions"]:
        version = importlib.metadata.version(row["name"])
        require(version == row["version"], "fba_distribution_version_changed")
        distributions.append({"name": row["name"], "version": version})
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).is_file():
            require(str(Path(filename).resolve()) in by_path, "fba_unbound_import:" + str(filename))
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith("/") and "x" in fields[1]:
            require(str(Path(fields[5]).resolve()) in by_path, "fba_unbound_native_library:" + fields[5])
    if native_loaded:
        import cobra
        import optlang.glpk_interface
        import swiglpk
        require(swiglpk.glp_version() == "5.0" and cobra.Configuration().solver is optlang.glpk_interface,
                "fba_solver_interface_mismatch")
    return distributions


@contextmanager
def _diagnostic_capture(diagnostics):
    stream = io.StringIO()
    class Handler(logging.Handler):
        def emit(self, record):
            diagnostics["logging"].append({"stage": diagnostics["stage"], "logger_name": record.name,
                "level_number": record.levelno, "level_name": record.levelname, "message": record.getMessage(),
                "pathname": record.pathname or None, "lineno": record.lineno if record.lineno >= 0 else None})
            stream.write(self.format(record) + "\n")
    handler = Handler()
    root, previous_level = logging.getLogger(), logging.getLogger().level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    with warnings.catch_warnings(), redirect_stdout(stream), redirect_stderr(stream):
        warnings.simplefilter("always")
        def showwarning(message, category, filename, lineno, file=None, line=None):
            diagnostics["warnings"].append({"stage": diagnostics["stage"], "category_module": category.__module__,
                "category_name": category.__name__, "message": str(message), "filename": filename,
                "lineno": lineno if lineno >= 0 else None})
            stream.write(warnings.formatwarning(message, category, filename, lineno, line))
        warnings.showwarning = showwarning
        try:
            yield stream
        finally:
            root.removeHandler(handler)
            root.setLevel(previous_level)


def _solver_record(solution, configuration):
    # Reuse the one existing native-string interpretation, without duplicating
    # scientific calculations or a second parser/scoring policy.
    raw_status = solution["optlang_status"] if solution else None
    result = {"interface": None, "name": None, "version": None, "cobra_version": None, "optlang_version": None,
        "raw_status": raw_status, "status": normalize_fba_solver_status(raw_status),
        **{key: capture.number(role="manifest", pointer="/actual_solver/" + key, missing_reason="not_executed")
           for key in ("feasibility_tolerance", "optimality_tolerance", "integrality_tolerance")},
        "raw_parameters_file": None, "diagnostic_file": None, "alternate_optimum_claim": "not_assessed", "alternate_claim_source": None}
    if configuration:
        result.update(interface=configuration["interface"], name="GLPK", version=configuration["glpk_version"],
                      cobra_version=configuration["cobra_version"], optlang_version=configuration["optlang_version"])
        for field in ("feasibility_tolerance", "optimality_tolerance", "integrality_tolerance"):
            result[field] = deepcopy(configuration[field])
    return result


def _csv(model, solution, payload):
    import pandas as pd
    require(solution is not None and payload["point_state"] == "basic_solution", "primal_not_established")
    identifiers = [r.id for r in model.reactions]
    require(solution.fluxes.index.is_unique and len(solution.fluxes) == len(identifiers)
            and set(solution.fluxes.index) == set(identifiers), "flux_identity_conflict")
    require(all(row["flux"]["state"] == "present" for row in payload["reaction_values"]), "flux_missing")
    frame = pd.DataFrame({"reaction_id": identifiers, "reaction_name": [r.name for r in model.reactions],
        "flux": [solution.fluxes[r.id] for r in model.reactions], "lower_bound": [r.lower_bound for r in model.reactions],
        "upper_bound": [r.upper_bound for r in model.reactions]})
    return frame.to_csv(index=False).encode("utf-8")


def _replay(plan, paths):
    require(paths["manifest"].is_file(), "fba_original_attempt_already_started")
    manifest = read_json(paths["manifest"])
    require(manifest.get("sealed") is True and manifest.get("attempt") == plan["identity"], "fba_original_attempt_mismatch")
    require(manifest.get("software_sha256") == digest(plan["requested_job"]["native_flux_balance"]["software"]), "fba_original_attempt_mismatch")
    if plan["version"] == "flux_balance_run_plan_v2":
        observation = read_json(confined_file(plan["attempt_directory"], ENVIRONMENT_FILENAME))
        expected = plan["environment_binding"]["realized_environment"]
        require(type(observation) is dict and set(observation) == {
            "version", "plan_sha256", "expected_environment", "observed_environment"}
            and observation["version"] == "flux_balance_environment_observation_v1"
            and observation["plan_sha256"] == digest(plan) and observation["expected_environment"] == expected,
            "fba_environment_observation_mismatch")
        require(read_json(confined_file(plan["attempt_directory"], STARTED_FILENAME)).get(
            "environment_observation_sha256") == digest(observation), "fba_environment_observation_mismatch")
        actual = observation["observed_environment"]
        require(type(actual) is dict and set(actual) == set(expected)
            and all(v is None or type(v) is str for v in actual.values()), "fba_environment_observation_mismatch")
    declarations = {r["role"]: r for r in plan["outputs"] if r["role"] != "manifest"}
    require(set(r["role"] for r in manifest["files"]) == set(declarations), "fba_output_role_mismatch")
    for row in manifest["files"]:
        declaration = declarations[row["role"]]
        require(all(row[k] == declaration[k] for k in ("role", "relative_path", "format")), "fba_output_role_mismatch")
        if row["identity"] is not None:
            pin = file_pin(paths[row["role"]])
            require({k: pin[k] for k in ("sha256", "size_bytes")} == row["identity"], "artifact_identity_conflict")
        else:
            require(not paths[row["role"]].exists(), "artifact_identity_conflict")
    return manifest


def run_flux_balance_native(plan):
    plan = validate_flux_balance_run_plan(plan)
    job, owner = plan["requested_job"]["native_flux_balance"], plan["identity"]
    attempt = directory(plan["attempt_directory"], create=True)
    paths = {row["role"]: confined_file(attempt, row["relative_path"], create_parents=True) for row in plan["outputs"]}
    owner_path, started = attempt / OWNER_FILENAME, attempt / STARTED_FILENAME
    if owner_path.exists():
        require(read_json(owner_path) == plan, "fba_original_attempt_mismatch")
    else:
        immutable_json(owner_path, plan)
    if started.exists():
        require(read_json(started)["plan_sha256"] == digest(plan), "fba_original_attempt_mismatch")
        return _replay(plan, paths)
    require(not any(path.exists() for path in paths.values()), "fba_original_attempt_unsealed")
    expected_environment = flux_balance_environment(job["software"], attempt_directory=str(attempt),
        lifecycle_directory=str(Path(owner["execution_id"]).parent))
    observed_environment = {k: os.environ.get(k) for k in expected_environment}
    start_record = {"plan_sha256": digest(plan), "started_at": _now()}
    if plan["version"] == "flux_balance_run_plan_v2":
        observation = {
            "version": "flux_balance_environment_observation_v1", "plan_sha256": digest(plan),
            "expected_environment": expected_environment, "observed_environment": observed_environment}
        start_record["environment_observation_sha256"] = digest(observation)
    immutable_json(started, start_record)
    if plan["version"] == "flux_balance_run_plan_v2":
        immutable_json(confined_file(attempt, ENVIRONMENT_FILENAME), observation)
    statuses = {role: "absent" for role in paths}
    diagnostics = {"warnings": [], "logging": [], "exceptions": [], "stage": "selection"}
    problems, distributions, model, solution, solution_payload = [], [], None, None, None
    model_payload = {"version": "cobra_model_capture_v1", "loaded_original": None, "effective": None,
        "input_profile": job["model_input"]["format"], "loader": {"name": "read_sbml_model" if job["model_input"]["format"] == "sbml" else "load_json_model",
            "cobra_version": "0.32.1", "number_type": "float64", "id_replacement": "cobra_F_REPLACE" if job["model_input"]["format"] == "sbml" else "none"},
        "source_to_loaded_ids": [], "source_feature_audit": [], "source_audit": None, "issues": []}
    problem_payload = {"version": "cobra_glpk_problem_capture_v1", "loaded_original": None, "effective": None,
                       "configuration_before_solve": None, "issues": []}
    application = capture._request_application(job)
    calls, events, problem_sha, outcome, context = 0, [], None, "not_executed", None
    def write(role, value, *, raw=False):
        try:
            (immutable_bytes if raw else immutable_json)(paths[role], value)
            statuses[role] = "present"
            return True
        except Exception as error:
            diagnostics["exceptions"].append(capture.exception(error, "capture", "write/" + role))
            problems.append(capture.issue("artifact_missing", "capture", "/" + role))
            statuses[role] = "incompatible" if paths[role].exists() else "absent"
            return False
    with _diagnostic_capture(diagnostics) as log:
        try:
            require(write("selected_request", {"version": "flux_balance_selected_request_v1", "attempt": owner,
                "requested_job": plan["requested_job"]}), "artifact_missing")
            require(observed_environment == expected_environment if plan["version"] == "flux_balance_run_plan_v2"
                    else all(os.environ.get(k) == v for k, v in expected_environment.items()), "fba_runtime_environment_mismatch")
            for leaf in ("tmp", "cache", "cache/pip"):
                directory(attempt / leaf, create=True)
            distributions = _verify_software(job["software"])
            original_pin = retain_input(job["model_input"]["file"]["path"], paths["original_model"], max_bytes=plan["policy"]["scratch_bytes"])
            statuses["original_model"] = "present"
            if original_pin != {k: job["model_input"]["file"][k] for k in ("sha256", "size_bytes")}:
                statuses["original_model"] = "incompatible"
                raise ValueError("model_identity_conflict")
            diagnostics["stage"] = "load"
            raw = read_bytes(paths["original_model"])
            context = capture._load_model(paths["original_model"], profile=job["model_input"]["format"], raw=raw,
                                          scratch_directory=attempt / "tmp", diagnostics=diagnostics)
            model_payload["source_audit"] = context["source_audit"]
            model_payload["source_feature_audit"] = context["source_information"]["features"]
            model = capture._load_audited_model(paths["original_model"], context)
            model.solver.update()
            model_payload["source_to_loaded_ids"] = context["source_information"]["joins"]
            model_payload["source_feature_audit"] = context["source_information"]["features"]
            model_payload["loaded_original"] = capture.capture_cobra_glpk_model(model, phase="loaded_original", source_audit=context["source_audit"])
            problem_payload["loaded_original"] = capture.capture_cobra_glpk_problem(model, phase="loaded_original")
            diagnostics["stage"] = "apply"
            applied = capture._apply_request(model, job, application, diagnostics)
            model.solver.update()
            model_payload["effective"] = capture.capture_cobra_glpk_model(model, phase="effective", source_audit=context["source_audit"])
            problem_payload["effective"] = capture.capture_cobra_glpk_problem(model, phase="effective")
            problem_payload["configuration_before_solve"] = capture.capture_cobra_glpk_configuration(model, role="effective_problem", pointer="/configuration_before_solve")
            confirmed = capture._confirm_application(application, model_payload, problem_payload)
            require(write("effective_model", model_payload) and write("effective_problem", problem_payload), "artifact_missing")
            problem_sha = file_pin(paths["effective_problem"])["sha256"]
            if applied and confirmed:
                diagnostics["stage"] = "solve"
                with capture._observe_native_passes(model, problem_sha) as events:
                    immutable_json(attempt / SOLVE_ENTERED_FILENAME, {"attempt": owner, "effective_problem_sha256": problem_sha,
                        "model_optimize_call_count": 1, "entered_at": _now()})
                    calls = 1
                    solution = model.optimize()
                outcome = "completed"
            else:
                outcome = "failed"
        except Exception as error:
            diagnostics["exceptions"].append(capture.exception(error, diagnostics["stage"], "selected_native_invocation"))
            raw_code = str(error).split(":", 1)[0]
            code = raw_code if raw_code in capture.flux_balance_schema("Issue")["properties"]["code"]["enum"] else {
                "selection": "binding_unavailable", "load": "model_load_failed", "apply": "constraint_rejected", "solve": "solver_exception"}.get(diagnostics["stage"], "artifact_missing")
            problems.append(capture.issue(code, diagnostics["stage"], "/selected_native_invocation"))
            outcome = "partial" if calls else "failed"
        finally:
            diagnostics["stage"] = "capture"
            if model is not None:
                try:
                    solution_payload = capture.capture_cobra_glpk_solution(model, solution, optimize_call_count=calls,
                                                                          native_passes=events, diagnostics=diagnostics)
                    if not write("solution", solution_payload):
                        outcome = "partial" if calls else "failed"
                except Exception as error:
                    diagnostics["exceptions"].append(capture.exception(error, "capture", "solution_capture"))
                    problems.append(capture.issue("artifact_missing", "capture", "/solution"))
                    outcome = "partial" if calls else "failed"
            for role, payload in (("effective_model", model_payload), ("effective_problem", problem_payload)):
                if statuses[role] == "absent" and (context is not None or payload.get("loaded_original") is not None):
                    write(role, payload)
            if statuses["effective_problem"] == "present":
                problem_sha = file_pin(paths["effective_problem"])["sha256"]
            if solution is not None and solution_payload is not None and solution_payload["point_state"] == "basic_solution":
                try:
                    if not write("flux_csv", _csv(model, solution, solution_payload), raw=True):
                        outcome = "partial"
                except Exception as error:
                    diagnostics["exceptions"].append(capture.exception(error, "capture", "flux_csv"))
                    problems.append(capture.issue("flux_missing", "capture", "/flux_csv"))
                    outcome = "partial"
            try:
                distributions = _verify_software(job["software"], native_loaded=model is not None)
            except Exception as error:
                diagnostics["exceptions"].append(capture.exception(error, "capture", "software_after"))
                problems.append(capture.issue("binding_unavailable", "capture", "/software"))
                if application["request_realization"] == "exact":
                    application["request_realization"] = "unknown"
                outcome = "partial" if calls else "failed"
            log.write(canonical({"diagnostics": diagnostics, "solve_call_count": calls, "execution_outcome": outcome}) + "\n")
    if not write("native_log", log.getvalue().encode("utf-8"), raw=True):
        outcome = "partial" if calls else "failed"
    files = []
    for declaration in plan["outputs"]:
        role = declaration["role"]
        if role == "manifest":
            continue
        identity = None
        if paths[role].is_file():
            pin = file_pin(paths[role])
            identity = {k: pin[k] for k in ("sha256", "size_bytes")}
        files.append({**declaration, "state": statuses[role], "identity": identity})
    configuration = solution_payload["configuration_after_solve"] if solution_payload else problem_payload["configuration_before_solve"]
    manifest = {"version": "flux_balance_native_manifest_v1", "sealed": True, "attempt": owner,
        "software_sha256": digest(job["software"]), "model_identity": {k: job["model_input"]["file"][k] for k in ("sha256", "size_bytes")},
        "actual_distributions": distributions, "actual_solver": _solver_record(solution_payload, configuration),
        "source_function_sha256": job["source_function_sha256"], "effective_problem_sha256": problem_sha,
        "files": files, "solve_call_count": calls, "execution_outcome": outcome,
        "request_realization": application["request_realization"], "request_application": application,
        "issues": problems + deepcopy(application["issues"])}
    immutable_json(paths["manifest"], manifest)
    return manifest


def execute_flux_balance_plan(plan):
    manifest = run_flux_balance_native(plan)
    return 0 if manifest["execution_outcome"] == "completed" else 2


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    try:
        require(len(arguments) == 1 and Path(arguments[0]).is_absolute(), "one_absolute_fba_run_plan_required")
        return execute_flux_balance_plan(read_json(arguments[0]))
    except (ValueError, OSError, MemoryError) as error:
        print(canonical({"stage": "fba_driver_failed", "exception_class": type(error).__name__, "code": str(error)}), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
