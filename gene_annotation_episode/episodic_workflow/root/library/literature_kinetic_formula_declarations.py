COMPONENTS = (
    "numerator_parameter", "denominator_parameter", "parameter_difference",
    "parameter_ratio", "log_parameter_contrast", "log_contrast_variance",
    "log_contrast_standard_uncertainty", "source_profile_log_ratio", "source_signed_index",
)
FORMULAS = {
    "numerator_parameter": "source_numerator_parameter",
    "denominator_parameter": "source_denominator_parameter",
    "parameter_difference": "numerator_parameter-denominator_parameter",
    "parameter_ratio": "numerator_parameter/denominator_parameter",
    "log_parameter_contrast": "ln(numerator_parameter)-ln(denominator_parameter)",
    "log_contrast_variance": "Cnn+Cdd-2*Cnd",
    "log_contrast_standard_uncertainty": "sqrt(Cnn+Cdd-2*Cnd)",
    "source_profile_log_ratio": "e*abs(e)/(2*V)",
    "source_signed_index": "tanh(source_profile_log_ratio/2)",
}
