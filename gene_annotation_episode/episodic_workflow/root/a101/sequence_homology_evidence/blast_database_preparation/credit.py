"""Credit: ``handoff_unit`` once a launch child reported a handoff, plus ``prepared_unit`` for each distinct usable
prepared-data record a results child reported (D17: only what is gained). A launch the resource refused, a product
that is not usable, a repeat of a held record and a read earn nothing. Both are read from the children's admitted
reports in the summary, which name the records this Episode then holds."""


def credit(summary, records):
    handed_off = summary['handoff_unit'] if summary['handoff_refs'] else 0.0
    return handed_off + summary['prepared_unit'] * len(summary['usable_prepared_refs'])
