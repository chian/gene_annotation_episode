"""Actual selected SciPy ITC fit, using the sole physical forward authority.

This is an in-process numerical call record, not an installed execution profile,
host software/manifest authentication, receipt grant, or recovery launcher.
"""
from copy import deepcopy
import hashlib
import inspect
import math
from numbers import Real
from pathlib import Path
import sys
import warnings

from . import bivariate_covariance, itc_binding_contracts, itc_binding_measurements
from .itc_binding_contracts import (
    FIT_OBSERVATION_VERSION, PARAMETERS, digest, validate_itc_binding_sheet,
    validate_itc_binding_fit_selection, validate_itc_binding_fit_observation, itc_binding_covariance_metadata,
)
from .itc_binding_measurements import predict_itc_binding_heats, _prepare_fit_inputs


def _observed(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("itc_binding_native_scalar_not_numeric")
    value = float(value)
    if math.isnan(value): return dict(state="nan", value=None)
    if math.isinf(value): return dict(state="positive_infinity" if value > 0 else "negative_infinity", value=None)
    return dict(state="finite", value=value)


def _file(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _entered(error, code):
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code is code: return True
        traceback = traceback.tb_next
    return False


def fit_itc_binding_measurements(sheet, *, selection):
    """Attempt exactly this selected fit; never choose settings or retry it.

    Fewer residuals than parameters are permitted by selected bounded TRF.
    Finite pseudoinverse covariance does not establish identifiability. Native
    NaN/inf covariance entries retain their scalar classifications in JSON.
    """
    sheet = validate_itc_binding_sheet(sheet)
    selection = validate_itc_binding_fit_selection(selection)
    observation = dict(version=FIT_OBSERVATION_VERSION, supplied_sha256=digest(sheet["supplied"]),
        selection=selection, call_state="not_started", call_count=0, software=None,
        effective_arguments=None, prepared_data=None, native_parameters=None,
        native_covariance=None, covariance_metadata=itc_binding_covariance_metadata(selection["weighting"]),
        warnings=[], qualifications=[], failure=None)
    stage, function, caught = "input", None, []
    try:
        prepared = _prepare_fit_inputs(sheet, selection=selection)
        observation.update(prepared_data=prepared["data"], qualifications=prepared["qualifications"])
        stage = "software"
        import numpy
        import scipy
        from scipy.optimize import curve_fit
        function = curve_fit
        observation["software"] = dict(authority="observed_in_process_not_host_commission",
            python_executable=sys.executable, python_version=sys.version,
            scipy_version=scipy.__version__, numpy_version=numpy.__version__,
            callable=dict(module=function.__module__, qualname=function.__qualname__,
                file=_file(inspect.getsourcefile(function))),
            implementation_files=[_file(module.__file__) for module in
                (itc_binding_contracts, itc_binding_measurements, bivariate_covariance, sys.modules[__name__])])
        solver, weights = selection["solver"], selection["weighting"]
        kwargs = dict(p0=[float(selection["initial_parameters"][name]) for name in PARAMETERS],
            bounds=(list(prepared["lower_bounds"]), list(prepared["upper_bounds"])), sigma=deepcopy(prepared["data"]["sigma_joule"]),
            absolute_sigma=weights["absolute_sigma"], method=solver["method"], jac=solver["jacobian"],
            **{key: deepcopy(solver[key]) for key in ("ftol", "xtol", "gtol", "max_nfev", "x_scale", "diff_step")})
        observation["effective_arguments"] = deepcopy({key: value for key, value in kwargs.items() if key != "bounds"})
        observation["effective_arguments"].update(lower_bounds=[_observed(value) for value in prepared["lower_bounds"]],
            upper_bounds=[_observed(value) for value in prepared["upper_bounds"]])
        ids = prepared["data"]["injection_ids"]

        def forward(indices, kd, n, delta_h):
            prediction = predict_itc_binding_heats(sheet, parameters=dict(kd=float(kd), n=float(n), delta_h=float(delta_h)))
            rows = {row["injection_id"]: row for row in prediction["history"] or []}
            values = []
            for index in indices:
                cell = rows[ids[int(index)]]["predicted_heat"]
                if cell["state"] != "present": raise ValueError("itc_binding_forward_unavailable:" + cell["reason"])
                values.append(cell["value"])
            return numpy.asarray(values, dtype=float)

        stage = "fit"
        observation.update(call_state="uncertain", call_count=None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parameters, covariance = function(forward, numpy.arange(len(ids), dtype=float),
                numpy.asarray(prepared["data"]["heats_joule"], dtype=float), **kwargs)
        observation.update(call_state="returned", call_count=1)
        stage = "serialization"
        observation["native_parameters"] = [_observed(value) for value in parameters]
        observation["native_covariance"] = [[_observed(value) for value in row] for row in covariance]
    except Exception as error:
        if stage == "fit":
            entered = function is not None and _entered(error, getattr(function, "__code__", None))
            observation.update(call_state="raised" if entered else "uncertain", call_count=1 if entered else None)
        observation["failure"] = dict(stage=stage, code="selected_" + stage + "_failed",
            exception_type=type(error).__module__ + "." + type(error).__name__, message=str(error))
    finally:
        observation["warnings"] = [dict(category=item.category.__module__ + "." + item.category.__name__, message=str(item.message)) for item in caught]
    return validate_itc_binding_fit_observation(observation)
