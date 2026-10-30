"""Pure display of the A110 scientific meanings actually received by this episode."""
from collections.abc import Mapping


def render_meanings(parts, content, records, *, section, table):
    models = content.get("model_definitions")
    resources = content.get("resource_definitions")
    if not isinstance(models, (tuple, list)) or not isinstance(resources, (tuple, list)):
        return False
    records = records or {}
    def label(reference):
        if reference is None:
            return "unknown"
        record = records.get(reference)
        if not isinstance(record, Mapping):
            return "meaning unavailable in the received scientific records"
        return record.get("label", record.get("name", "unknown"))
    names, alternative_number = {}, 0
    for row in models:
        if row["role"] == "claim":
            name = "Claim"
        else:
            alternative_number += 1
            name = "Alternative " + str(alternative_number)
        names[row["model_ref"]] = name
    if models:
        section(parts, "Reaction models and predictions", table(
            ("Model", "Source-supported definition", "Reaction", "Function relationship",
             "Prediction", "Unit", "Prediction basis", "Prediction evidence"),
            ((names[row["model_ref"]], label(row["model_ref"]) if row.get("definition_reported") else "unknown",
              label(row.get("reaction_ref")), label(row.get("function_relation_ref")), row.get("prediction"),
              row.get("unit"), row.get("prediction_basis"), label(row.get("prediction_evidence_ref")))
             for row in models)))
        section(parts, "Reaction comparison membership", table(
            ("Reduction", "Compared alternative models"), [(content.get("comparison_reduction"),
              ", ".join(names.get(ref, "unknown model") for ref in content.get("comparison_member_refs", ()))
              or "none declared")]))
    demand = content.get("demand_definition")
    if isinstance(demand, Mapping):
        section(parts, "Reaction resource demand", table(
            ("Demand", "Source-supported definition", "Output or process", "Biological setting", "Compartment",
             "Period", "Value", "Unit", "Demand basis", "Demand evidence"),
            [("Demand", label(demand["demand_ref"]) if demand.get("definition_reported") else "unknown",
              label(demand.get("process_ref")), label(demand.get("biological_setting_ref")),
              label(demand.get("compartment_ref")), label(demand.get("period_ref")), demand.get("value"),
              demand.get("unit"), demand.get("demand_basis"), label(demand.get("evidence_ref")))]))
    if resources:
        resource_names = {row["resource_ref"]: "Resource " + str(index + 1)
                          for index, row in enumerate(resources)}
        section(parts, "Reaction resource constraints", table(
            ("Resource", "Source-supported definition", "Substance", "Property", "Biological setting",
             "Compartment", "Period", "Supply basis", "Coefficient", "Coefficient role", "Output/demand",
             "Coefficient basis", "Supply evidence", "Coefficient evidence"),
            ((resource_names[row["resource_ref"]], label(row["resource_ref"]) if row.get("definition_reported") else "unknown",
              label(row.get("entity_ref")), label(row.get("property_ref")), label(row.get("biological_setting_ref")),
              label(row.get("compartment_ref")), label(row.get("period_ref")), row.get("supply_basis"),
              row.get("coefficient"), row.get("coefficient_role"),
              "Demand" if isinstance(demand, Mapping) and row.get("coefficient_demand_ref") == demand["demand_ref"] else "unknown",
              row.get("coefficient_basis"), label(row.get("supply_evidence_ref")),
              label(row.get("coefficient_evidence_ref"))) for row in resources)))
        section(parts, "Nominal capacity limiting resources", ", ".join(resource_names.get(ref, "unknown resource")
            for ref in content.get("nominal_limiting_resource_refs", ())) or "not established")
    return True
