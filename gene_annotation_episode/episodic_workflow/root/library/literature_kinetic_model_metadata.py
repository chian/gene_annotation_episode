from .literature_kinetic_formula_declarations import COMPONENTS as ALL_COMPONENTS, FORMULAS

COMPONENTS = ALL_COMPONENTS[5:]
FORMULA_CODES = {name: "kinetic_model_" + name + "_v1" for name in COMPONENTS}
FORMULA_MEANINGS = {FORMULA_CODES[name]: FORMULAS[name] for name in COMPONENTS}
VIEW = "kinetic_log_model_components"
