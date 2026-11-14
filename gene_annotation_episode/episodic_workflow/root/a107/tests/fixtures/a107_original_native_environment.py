def _environment(value):
    require(type(value) is dict and all(type(k) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k)
        and type(v) is str and "\0" not in v for k, v in value.items()), "invalid_native_environment")
    require(all(value.get(k) == "1" for k in ("PYTHONNOUSERSITE", "PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE",
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")), "invalid_native_environment")
    for name in ("PYTHONHOME", "TMP", "TEMP", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR"):
        path_value(value.get(name), absolute=True)
