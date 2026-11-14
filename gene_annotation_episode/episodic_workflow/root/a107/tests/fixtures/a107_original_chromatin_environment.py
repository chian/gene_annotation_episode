"""Original predicate, fb1e4d9bac279edcae98e8f2b3324b73c1679e51.

The function body is retained as a negative control; dependencies are supplied
from the actual defining contract when the test runs. No native job executes.
"""

def _environment(value):
    value = validate_chromatin_record("Environment", value)
    require(all("\0" not in text for text in value.values()), "invalid_native_environment")
    require(all(value[key] == "1" for key in ("PYTHONNOUSERSITE", "PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE",
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")), "invalid_native_environment")
    for key in ("PYTHONHOME", "TMP", "TEMP", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR"):
        path_value(value[key], absolute=True)
    for path in value["PYTHONPATH"].split(os.pathsep):
        path_value(path, absolute=True)
