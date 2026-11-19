"""A104 private sequence normalization for captured masking inputs."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import ContractError

MOLECULES = ["dna", "rna", "protein", "unspecified"]

@dataclass(frozen=True)
class SequenceRecord:
    name: str
    sequence: str
    description: str = ""
    occurrence: int = 0
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def parse_sequences(data: str | bytes, *, format: str = "raw", molecule: str = "unspecified", name: str = "input") -> list[SequenceRecord]:
    if molecule not in MOLECULES or format not in {"auto", "fasta", "raw"}:
        raise ContractError("unsupported_input_declaration")
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError("input_not_utf8") from exc
    if format == "auto":
        if not data.lstrip().startswith(">"):
            raise ContractError("sequence_representation_unrecognized")
        format = "fasta"
    alphabet = {"dna": set("ACGTRYSWKMBDHVN"), "rna": set("ACGURYSWKMBDHVN"),
                "protein": set("ABCDEFGHIKLMNPQRSTVWXYZJUO*")}.get(molecule)
    records = []
    seen: dict[str, int] = {}

    def append(header: str, sequence: str) -> None:
        fields = header.strip().split(maxsplit=1)
        if not fields:
            raise ContractError("empty_sequence_identifier")
        sequence = "".join(sequence.split()).upper()
        if not sequence:
            raise ContractError("empty_sequence")
        if not sequence.isascii() or any(not char.isprintable() for char in sequence):
            raise ContractError("unrepresentable_sequence_symbol")
        occurrence = seen.get(fields[0], 0)
        seen[fields[0]] = occurrence + 1
        issues = []
        if alphabet is not None and not set(sequence) <= alphabet:
            issues.append("unexpected_symbol_for_declared_molecule")
        if molecule == "protein" and "*" in sequence[:-1]:
            issues.append("internal_protein_stop_symbol")
        if occurrence:
            issues.append("duplicate_source_identifier")
        records.append(SequenceRecord(fields[0], sequence, fields[1] if len(fields) > 1 else "", occurrence, tuple(issues)))

    if format == "raw":
        append(name, data)
    else:
        header, sequence = None, []
        for line in data.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    append(header, "".join(sequence))
                header, sequence = line[1:], []
            elif header is None:
                raise ContractError("sequence_before_fasta_header")
            else:
                sequence.append(line)
        if header is not None:
            append(header, "".join(sequence))
    if not records:
        raise ContractError("empty_input")
    return records


