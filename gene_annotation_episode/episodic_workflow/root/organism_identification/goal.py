"""What this episode is for: which organism the DNA of the assigned scope is from. The goal names what this episode's own
cycle improves: the candidate taxa of the scope's sequence found by graded classification, each with its score, and how
well the leading candidates are separated. ``UNIT`` and ``RESULT`` describe one unit and the return."""

BINDING_PATH = 'organism_identification'
GOAL = ('This episode says which organism the assigned DNA is from. It improves the candidate taxa of the sequence: a taxon '
        'that a graded classification supports is a candidate, and its score is the sum of the support on its own lineage '
        '(a call at a vaguer level, such as a family, is supporting information for every finer candidate inside it, so the '
        'finest candidate the classifications agree on has the most score). A taxon and its ancestor are never rivals; '
        'rivals are calls that are not nested. The credit counts what was found and separated: a new possibility earns its '
        'score, a finer candidate under a listed one earns what it adds, and a classification earns by how differently the '
        'two leading rivals respond to it. A repeat earns nothing. A classification says what its index holds and nothing '
        'of what it does not hold. Only the yield controller ends the episode.')
UNIT = 'One selected tool: one run of one classifier on one sequence of the scope'
RESULT = ('The candidate taxa of each sequence of the scope with their scores (taxon id of the NCBI taxonomy, rank, lineage), '
          'the leading candidate, its leading rival and the deepest taxon the two share, the records this episode '
          'committed, and the credit')
