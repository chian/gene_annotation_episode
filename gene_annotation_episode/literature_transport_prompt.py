"""Source interpretation instructions, separate from transport numerical cells."""

TRANSPORT_TASK = """Determine whether the test and reference substrate conditions belong to the same fitted kinetic curve as the reported Km. Establish the actual molecule or construct, analyte, preparation, experimental system and measured endpoint. Keep whole-cell uptake separate from reconstituted transport and accumulated tracer separate from initial flux. A common paper, protein name, substrate name or equal numerical value does not establish a shared kinetic curve.

Select source-supported substrate concentrations and an actually received saved apparent-Km measurement. Preserve the source conditions and the scope of the fitted curve. Assign a common curve context only when the source supports that relationship; preserve different or unknown contexts rather than borrowing a fit from another preparation. A literal source quotation establishes custody, not the scientific truth of that assignment. Inspect neighboring context or complementary evidence when it can resolve the relationship.

Identify the owners of covariance rows and columns and what each reported spread means. Untyped plus-minus spread is not known sampling variance, and a shared Km is one uncertain quantity used by both conditions. Preserve biological versus technical repetition, correlated inputs, missing covariance and source disagreements. Leave parsing, unit conversion and response arithmetic to the selected deterministic operation.

A substrate-response correction is conditional on the common-curve model. Its response is test substrate saturation divided by reference substrate saturation. It supplies an operand for an appropriate source-effect correction; it is not a reliability grade, evidence of isolated molecular transport, annotation probability or target-transfer weight. Retain usable native quantities when the comparison or uncertainty is unavailable. Do not invent missing inputs or add an extra reliability multiplier for a correction already applied. Return only the parent's requested numerical components and their necessary scientific qualifications."""

__all__ = ["TRANSPORT_TASK"]
