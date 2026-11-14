from .literature_binding_interaction_model_declarations import MODEL_COMPONENTS

FORMULAS = dict(zip(MODEL_COMPONENTS, ("c' C c; c=(-1,1,1,-1)", "sqrt(c' C c)", "e * abs(e) / (2 * V)", "tanh(S / 2)")))

COMPONENTS = MODEL_COMPONENTS
FORMULA_CODES = {name: "binding_interaction_model_" + name + "_v1" for name in COMPONENTS}
FORMULA_MEANINGS = {FORMULA_CODES[name]: FORMULAS[name] for name in COMPONENTS}
VIEW = "binding_interaction_log_model_components"

