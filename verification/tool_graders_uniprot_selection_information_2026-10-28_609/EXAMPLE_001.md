# Concrete lookup and small selection example

This is the existing typed lookup syntax when `results` is a permitted child
and the contract-information profile is actually bound. It is not an execution
action and does not acquire a UniProt record:

```json
{
  "response": {
    "response_type": "request_context",
    "lookup": {
      "view": "composition_information",
      "operation": "episode.return_contract",
      "arguments": {
        "role": "results",
        "source": "uniprot_selected_returns"
      }
    }
  }
}
```

The returned information is rendered using `TEMPLATE_001.md` under the parent's
unchanged recurring TASK and current STEERING. A concise rendering of what the
following form asks for is:

> Assigned UniProtKB page. Select every row with exact primary accession
> P0AAW1. Return its published observed sequence length in amino acids and
> residues 10 through 19, using zero-based `[9,19)`. Request no page fields,
> whole source, or full sequence artifact. An absent accession or unavailable
> sequence remains a qualified return. This example makes no claim that the
> record or ten residues were acquired.

The parent can put this closed form's JSON encoding in the already declared
`schema_json` field of its chosen child action. The example's selection is
literal source data from `selection()` in
`tests/test_uniprot_compact_selection.py`, including all required empty lists
and false grants. `chosen_information` is a parent-chosen field name. This is
a response-construction example, not model-facing stored context:

```json
{
  "type": "object",
  "properties": {
    "chosen_information": {
      "$ref": "episode-fact:uniprot_selected_returns",
      "x-uniprot-selection": {
        "version": "uniprot_return_selection_v1",
        "pages": [{
          "publication": {"mode": "assigned_page"},
          "page_fields": [],
          "records": [{
            "record": {"mode": "primary_accession", "accession": "P0AAW1"},
            "grant_sequence_artifact": false,
            "fields": [
              {"kind": "integer", "field": "observed_sequence_length"},
              {"kind": "sequence_window", "start": 9, "end": 19}
            ]
          }],
          "grant_source": false
        }]
      }
    }
  },
  "required": ["chosen_information"],
  "additionalProperties": false
}
```

No complete child action is fabricated: its goal, scope, assignment, purpose
and interpretation fields must come from the actual parent decision. The
existing response envelope and return validation remain authoritative. The
expanded selected-return schema and custody witnesses are not supplied to the
model. This is a design example; application validation was not run in task609.
