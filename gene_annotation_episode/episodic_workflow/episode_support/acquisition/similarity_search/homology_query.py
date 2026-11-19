"""Protein search operands, independent of original annotation-target identity.

Reference queries are evidence subjects for a target investigation. Receipt
authorization belongs to the commissioning resource binding; this validator
checks molecular type and scope without turning a reference into a target.
"""


def protein_query(store,scope,query_ref,*,error_code):
    store.validate_scope(scope)
    query=store.get(query_ref)
    rooted=bool(store.roots(query_ref))
    eligible=(store.scope_covers(store.coverage(query_ref),scope) if rooted else
        query['record_type']=='reference' and bool(store.reference_subset([query_ref],scope)))
    if store.subject_unit(query_ref)!='aa' or not query.get('sequence_ref') or not eligible:
        raise ValueError(error_code)
    return query
