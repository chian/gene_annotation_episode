"""Credit: modest measured improvement of the time/resource model.

credit = commission.credit.model_scale x (Q(current model) - Q(model at entry))
         + the validation contributions of the predictions this Episode made

Q is the prediction quality on the commission's fixed validation cases. It is None when the current model was
trained on cases outside the commission history, and the gain is then zero. The values come from the tool
units' outcomes (a tool read them from the HPC ledger and returned them in ``credit_inputs``); credit has no
services. Actual job credit is not counted here. The credit is signed and unbounded; repeated polling adds none."""


def model_quality_improvement(inputs):
    entry, current = inputs['entry_quality'], inputs['current_quality']
    return current - entry if entry is not None and current is not None else 0.0


def credit(summary, records):
    inputs = summary['credit_inputs']
    if inputs is None:
        return 0.0
    return inputs['model_scale'] * model_quality_improvement(inputs) + inputs['prospective_validation_credit']
