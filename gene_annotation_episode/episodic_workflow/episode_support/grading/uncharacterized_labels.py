"""Labels of ignorance: the names databases give a protein whose function is not known.

The owner, 2026-11-23: "hypothetical protein ... is a label of ignorance, not a label of positive knowledge". A database
hit that carries such a label says that proteins like the target exist and that nobody has characterized them. It is
no candidate for what the target is: it names no annotation, earns no credit and is told apart from nothing. It is
counted, so that "many matches are uncharacterized" stays visible (what a conserved protein of unknown function may
still tell, for instance the functions the organisms that carry it all lack a gene for, is a separate investigation
that starts from that count).

``UNCHARACTERIZED_LABELS`` is a fixed list: the standard wordings of the sequence databases for "function unknown". A
name is such a label when it IS one of them (case, British spelling and spacing apart). A name that says more (a
family, a domain, a locus: "DUF2497 domain-containing protein") is not: it states something about the protein."""

UNCHARACTERIZED_LABELS = (
    'hypothetical protein',
    'conserved hypothetical protein',
    'uncharacterized protein',
    'putative uncharacterized protein',
    'protein of unknown function',
)


def is_uncharacterized_label(name):
    """Whether ``name`` is one of ``UNCHARACTERIZED_LABELS`` (case, 'uncharacterised' and spacing apart)."""
    return ' '.join(name.casefold().replace('uncharacterised', 'uncharacterized').split()) in UNCHARACTERIZED_LABELS
