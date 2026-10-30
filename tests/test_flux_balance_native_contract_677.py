"""Bounded interface evidence only; no production FBA implementation.

Select individual tests through bounded529. The provisioning test installs only
into its own attempt/installed directory and never imports the new distributions.
"""

import email
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


def _attempt():
    import pytest

    selected_attempt = os.environ.get("HMMER529_ATTEMPT")
    if not selected_attempt or not Path(selected_attempt).name.endswith("677"):
        pytest.skip("Select this verification explicitly through bounded529 in a 677 attempt")
    path = Path(selected_attempt)
    request = json.loads((path / "selected_request.json").read_text())
    if len(request["tests"]) != 1 or "test_flux_balance_native_contract_677.py::" not in request["tests"][0]:
        pytest.skip("Select one specific 677 verification function; no implicit downloads or solve")
    assert request["policy"] == {
        "memory_bytes": 21474836480,
        "scratch_bytes": 4294967296,
        "wall_seconds": None,
    }
    assert request["swap_bytes"] == 0
    return path


def _save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def _pin(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": path.stat().st_size}


def test_provision_exact_cobra_glpk_distribution():
    attempt = _attempt()
    baseline = attempt / "dependencies"
    constraints = []
    baseline_names = set()
    for info in sorted(baseline.glob("*.dist-info/METADATA")):
        metadata = email.message_from_bytes(info.read_bytes())
        name = metadata["Name"]
        if name == "gene-annotation-episode":
            continue
        constraints.append(name + "==" + metadata["Version"])
        baseline_names.add(name.lower().replace("_", "-"))
    constraint_file = attempt / "baseline_constraints.txt"
    constraint_file.write_text("\n".join(constraints) + "\n")
    wheels = attempt / "wheelhouse"
    wheels.mkdir()
    command = [sys.executable, "-B", "-m", "pip", "download",
               "--disable-pip-version-check", "--no-cache-dir", "--only-binary=:all:",
               "--index-url", "https://pypi.org/simple", "--dest", str(wheels),
               "--constraint", str(constraint_file),
               "cobra==0.32.1", "optlang==1.9.1", "swiglpk==5.0.13"]
    with (attempt / "provision_stdout.txt").open("w") as out, \
            (attempt / "provision_stderr.txt").open("w") as err:
        result = subprocess.run(command, stdout=out, stderr=err, check=False)
    _save(attempt / "provision_download.json", {"argv": command, "returncode": result.returncode})
    assert result.returncode == 0, (attempt / "provision_stderr.txt").read_text()
    rows, additions = [], []
    for wheel in sorted(wheels.glob("*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            info = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
            metadata = email.message_from_bytes(archive.read(info))
        name = metadata["Name"].lower().replace("_", "-")
        rows.append({**_pin(wheel), "name": metadata["Name"], "version": metadata["Version"],
                     "requires_dist": metadata.get_all("Requires-Dist", [])})
        if name not in baseline_names:
            additions.append(str(wheel))
    _save(attempt / "resolved_wheels.json", rows)
    installed = attempt / "installed"
    shutil.copytree(baseline, installed, dirs_exist_ok=True)
    installed.chmod(0o755)
    command = [sys.executable, "-B", "-m", "pip", "install", "--disable-pip-version-check",
               "--no-cache-dir", "--no-index", "--no-deps", "--no-compile",
               "--target", str(installed), *additions]
    with (attempt / "install_stdout.txt").open("w") as out, \
            (attempt / "install_stderr.txt").open("w") as err:
        result = subprocess.run(command, stdout=out, stderr=err, check=False)
    _save(attempt / "provision_install.json", {"argv": command, "returncode": result.returncode})
    assert result.returncode == 0, (attempt / "install_stderr.txt").read_text()
    _save(attempt / "provision_summary.json", {
        "selected": {"cobra": "0.32.1", "optlang": "1.9.1", "swiglpk": "5.0.13"},
        "baseline": "bounded529/check005/dependencies (frozen copy in this attempt)",
        "scientific_imported": False, "solve_calls": 0,
        "additional_wheel_count": len(additions), "combined_dependency_root": str(installed),
    })


def test_install_retained_pinned_wheels():
    """Repair only the failed writable staging root; reuse downloaded bytes."""
    attempt = _attempt()
    source = Path(os.environ["HMMER_NATIVE_ORACLE_FBA677_WHEELS"])
    pins = json.loads(source.with_name("resolved_wheels.json").read_text())
    baseline_names = set()
    for info in (attempt / "dependencies").glob("*.dist-info/METADATA"):
        metadata = email.message_from_bytes(info.read_bytes())
        baseline_names.add(metadata["Name"].lower().replace("_", "-"))
    additions = []
    for row in pins:
        wheel = source / Path(row["path"]).name
        assert _pin(wheel)["sha256"] == row["sha256"]
        assert wheel.stat().st_size == row["size_bytes"]
        if row["name"].lower().replace("_", "-") not in baseline_names:
            additions.append(str(wheel))
    installed = attempt / "installed"
    shutil.copytree(attempt / "dependencies", installed, dirs_exist_ok=True)
    installed.chmod(0o755)
    command = [sys.executable, "-B", "-m", "pip", "install", "--disable-pip-version-check",
               "--no-cache-dir", "--no-index", "--no-deps", "--no-compile",
               "--target", str(installed), *additions]
    with (attempt / "install_stdout.txt").open("w") as out, \
            (attempt / "install_stderr.txt").open("w") as err:
        result = subprocess.run(command, stdout=out, stderr=err, check=False)
    _save(attempt / "provision_install.json", {"argv": command, "returncode": result.returncode})
    assert result.returncode == 0, (attempt / "install_stderr.txt").read_text()
    _save(attempt / "provision_summary.json", {
        "selected": {"cobra": "0.32.1", "optlang": "1.9.1", "swiglpk": "5.0.13"},
        "baseline": "bounded529/check005/dependencies (frozen copy in this attempt)",
        "scientific_imported": False, "solve_calls": 0,
        "additional_wheel_count": len(additions), "combined_dependency_root": str(installed),
        "source_wheels": str(source), "prior_pins": pins,
    })


def test_one_original_tiny_native_solve(monkeypatch):
    """One selected effective fixture, full native retention, no calculator."""
    attempt = _attempt()
    import importlib.metadata
    import io
    import logging
    import math
    import socket
    import traceback
    import warnings

    def no_network(*args, **kwargs):
        raise AssertionError("The supplied-input FBA probe must not acquire a model")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    import cobra
    import libsbml
    import optlang.glpk_interface as glpk_interface
    import pandas as pd
    import swiglpk as glp
    from optlang.expression_parsing import parse_optimization_expression

    cobra.Configuration().solver = "glpk"
    assert importlib.metadata.version("cobra") == "0.32.1"
    assert importlib.metadata.version("optlang") == "1.9.1"
    assert importlib.metadata.version("swiglpk") == "5.0.13"
    root = attempt / "probe"
    root.mkdir()
    input_path = Path(os.environ["HMMER_NATIVE_ORACLE_FBA677_MODEL"])
    raw = input_path.read_bytes()
    (root / "original.xml").write_bytes(raw)

    def scalar(value):
        if value is None:
            return {"value": None, "state": "missing", "native_token": None, "float_hex": None}
        number = float(value)
        return {"value": number if math.isfinite(number) else None,
                "state": "finite" if math.isfinite(number) else "nonfinite",
                "native_token": repr(number), "float_hex": number.hex()}

    def expression(obj, variables):
        offset, coefficients, quadratic = parse_optimization_expression(obj, linear=False)
        return {"expression": str(obj.expression), "is_linear": bool(obj.is_Linear),
                "offset": scalar(offset), "terms": [
                    {"variable_position": variables.index(var), "variable_name": var.name,
                     "coefficient": scalar(coef)} for var, coef in coefficients.items()],
                "quadratic_term_count": len(quadratic)}

    def problem_snapshot(model):
        model.solver.update()
        variables = list(model.solver.variables)
        return {"optlang_json": model.solver.to_json(),
                "variables": [{"position": i, "name": var.name, "type": var.type,
                               "lower": scalar(var.lb), "upper": scalar(var.ub)}
                              for i, var in enumerate(variables)],
                "constraints": [{"position": i, "name": row.name,
                                 "lower": scalar(row.lb), "upper": scalar(row.ub),
                                 "indicator_variable": None if row.indicator_variable is None else row.indicator_variable.name,
                                 "active_when": row.active_when,
                                 **expression(row, variables)}
                                for i, row in enumerate(model.solver.constraints)],
                "objective": {"direction": model.objective.direction,
                              **expression(model.objective, variables)},
                "reaction_variables": [{"reaction_position": i, "reaction_id": rxn.id,
                                        "forward_position": variables.index(rxn.forward_variable),
                                        "forward_name": rxn.forward_variable.name,
                                        "reverse_position": variables.index(rxn.reverse_variable),
                                        "reverse_name": rxn.reverse_variable.name}
                                       for i, rxn in enumerate(model.reactions)]}

    def model_snapshot(model):
        return {"cobra_json": json.loads(cobra.io.to_json(model, sort=False)),
                "sbml_metadata": getattr(model, "_sbml", None),
                "compartments": list(model.compartments.items()),
                "all_compartment_descriptions": model._compartments,
                "genes": [{"id": gene.id, "name": gene.name, "annotation": gene.annotation,
                           "notes": gene.notes} for gene in model.genes],
                "reactions": [{"id": rxn.id, "gpr": rxn.gene_reaction_rule,
                               "gene_ids_in_model_order": [gene.id for gene in model.genes if gene in rxn.genes],
                               "stoichiometry": [{"metabolite_id": met.id, "coefficient": scalar(coef)}
                                                 for met, coef in rxn.metabolites.items()]}
                              for rxn in model.reactions]}

    def control_values(control):
        values = {}
        for name in dir(control):
            if name.startswith("_") or name in {"this", "thisown"}:
                continue
            value = getattr(control, name)
            if isinstance(value, (int, float, bool, str)) or value is None:
                values[name] = value
        return values

    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(logging.Formatter("%(name)s %(levelname)s %(message)s"))
    logger = logging.getLogger()
    original_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    native_passes = []
    original_simplex = glpk_interface.glp_simplex

    def recorded_simplex(problem, control):
        row = {"routine": "glp_simplex", "parameters": control_values(control)}
        native_passes.append(row)
        code = original_simplex(problem, control)
        row.update(return_code=code, raw_status=glp.glp_get_status(problem),
                   primal_status=glp.glp_get_prim_stat(problem), dual_status=glp.glp_get_dual_stat(problem))
        return code

    monkeypatch.setattr(glpk_interface, "glp_simplex", recorded_simplex)
    with warnings.catch_warnings(record=True) as observed_warnings:
        warnings.simplefilter("always")
        try:
            model = cobra.io.read_sbml_model(io.StringIO(raw.decode("utf-8")))
            _save(root / "original_loaded_model.json", model_snapshot(model))
            _save(root / "original_problem.json", problem_snapshot(model))
            doc = libsbml.readSBMLFromString(raw.decode("utf-8"))
            _save(root / "libsbml_read_errors.json", [{"id": doc.getError(i).getErrorId(),
                  "severity": doc.getError(i).getSeverityAsString(), "message": doc.getError(i).getMessage()}
                 for i in range(doc.getNumErrors())])
            json_text = cobra.io.to_json(model, sort=False)
            (root / "original_export.json").write_text(json_text)
            json_loaded = cobra.io.load_json_model(io.StringIO(json_text))
            _save(root / "json_loaded_problem_without_solve.json", problem_snapshot(json_loaded))
            model.reactions.IN.bounds = (-10.0, 8.0)
            model.constraints.A_c.ub = 1.0
            model.constraints.A_c.lb = 1.0
            net_cap = model.problem.Constraint(model.reactions.AB.flux_expression +
                model.reactions.OUT.flux_expression + 2, ub=14, name="net_cap")
            split_cap = model.problem.Constraint(model.reactions.IN.forward_variable +
                model.reactions.IN.reverse_variable, ub=9, name="split_cap")
            aux = model.problem.Variable("aux", lb=0, ub=None, type="continuous")
            aux_link = model.problem.Constraint(aux - model.reactions.OUT.flux_expression,
                lb=0, ub=0, name="aux_link")
            model.add_cons_vars([net_cap, split_cap, aux, aux_link])
            model.objective = model.problem.Objective(model.objective.expression + 1.5, direction="min")
            _save(root / "effective_model.json", model_snapshot(model))
            _save(root / "effective_problem.json", problem_snapshot(model))
            (root / "effective_problem.lp").write_text(model.solver.to_lp())
            code = glp.glp_write_prob(model.solver.problem, 0, str(root / "effective_problem.glpk"))
            assert code == 0
            cobra.io.write_sbml_model(model, str(root / "effective_export.xml"), units=False)
            config = model.solver.configuration
            _save(root / "configuration.json", {
                "interface": model.solver.interface.__name__, "glpk_version": glp.glp_version(),
                "libsbml_version": libsbml.getLibSBMLDottedVersion(), "model_tolerance": model.tolerance,
                "configuration": {"presolve": config.presolve, "verbosity": config.verbosity, "timeout": config.timeout},
                "public_tolerances": {name: getattr(config.tolerances, name) for name in dir(config.tolerances)},
                "simplex_control": control_values(config._smcp), "integer_control": control_values(config._iocp),
                "distributions": {name: importlib.metadata.version(name) for name in
                    ("cobra", "optlang", "swiglpk", "python-libsbml", "numpy", "pandas", "sympy")}})
            # This sentinel forbids a second solve even if later capture/assertions fail.
            _save(root / "solve_started.json", {"model_optimize_calls": 1, "input": _pin(root / "original.xml")})
            solution = model.optimize()
            _save(root / "solution.json", {
                "status": solution.status, "objective": scalar(solution.objective_value),
                "fluxes": [{"reaction_id": key, "value": scalar(value)} for key, value in solution.fluxes.items()],
                "reduced_costs": [{"reaction_id": key, "value": scalar(value)} for key, value in solution.reduced_costs.items()],
                "shadow_prices": [{"metabolite_id": key, "value": scalar(value)} for key, value in solution.shadow_prices.items()]})
            _save(root / "native_solution.json", {
                "optlang_status": model.solver.status, "glpk_status": glp.glp_get_status(model.solver.problem),
                "glpk_primal_status": glp.glp_get_prim_stat(model.solver.problem),
                "glpk_dual_status": glp.glp_get_dual_stat(model.solver.problem),
                "native_objective": scalar(glp.glp_get_obj_val(model.solver.problem)),
                "glpk_objective_constant": scalar(glp.glp_get_obj_coef(model.solver.problem, 0)),
                "optlang_objective_offset": scalar(model.solver._objective_offset),
                "variables": [{"position": i, "name": var.name, "primal": scalar(var.primal), "dual": scalar(var.dual)}
                              for i, var in enumerate(model.solver.variables)],
                "constraints": [{"position": i, "name": row.name, "primal": scalar(row.primal), "dual": scalar(row.dual)}
                                for i, row in enumerate(model.solver.constraints)],
                "native_passes": native_passes})
            pd.DataFrame({"reaction_id": [rxn.id for rxn in model.reactions],
                          "reaction_name": [rxn.name for rxn in model.reactions],
                          "flux": [solution.fluxes[rxn.id] for rxn in model.reactions],
                          "lower_bound": [rxn.lower_bound for rxn in model.reactions],
                          "upper_bound": [rxn.upper_bound for rxn in model.reactions]}).to_csv(root / "flux.csv", index=False)
            _save(root / "probe_summary.json", {"model_optimize_calls": 1, "native_glpk_passes": len(native_passes),
                 "original_direction": "min", "json_loaded_direction": json_loaded.objective.direction,
                 "effective_direction": model.objective.direction, "status": solution.status,
                 "objective": float(solution.objective_value), "fluxes": {k: float(v) for k, v in solution.fluxes.items()},
                 "aux_primal": float(aux.primal), "annotation_or_episode_verified": False})
            assert solution.status == "optimal"
            assert solution.objective_value == -2.75
            assert dict(solution.fluxes) == {"IN": 7.0, "AB": 6.0, "OUT": 6.0}
            assert aux.primal == 6.0
            assert json_loaded.objective.direction == "max"
        except Exception:
            (root / "exception.txt").write_text(traceback.format_exc())
            raise
        finally:
            _save(root / "warnings.json", [{"category": item.category.__name__, "message": str(item.message),
                  "filename": item.filename, "lineno": item.lineno} for item in observed_warnings])
            (root / "native_logging.txt").write_text(log_buffer.getvalue())
            _save(root / "native_passes.json", native_passes)
            logger.removeHandler(handler)
            logger.setLevel(original_level)
