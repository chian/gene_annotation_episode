"""Additional actual producer branches; preserves the first run and receipts."""
import run_native_examples_001 as runner

runner.OUT = runner.ROOT / 'native_examples_002'
runner.CASES = {
    'indel_beyond_nominal': (['-a', 'AGATCGGAAG', '-e', '0.1'], ['TTTTAGATCGAAG', 'TTTTAGATCGGAAG'], None),
    'linked_zero_back': (['-a', 'link=ACGTAC...AGATCG'], ['ACGTACGGGG', 'ACGTACCCCC'], None),
    'anywhere_zero_back': (['-b', 'ACGTAC'], ['ACGTACGGGG', 'ACGTACCCCC'], None),
    'linked_anchored': (['-a', '^ACGTAC...AGATCG$'], ['ACGTACGGGGAGATCG', 'ACGTACCCCCAGATCG'], None),
    'noninternal': (['-a', 'AGATCGX'], ['CCCCAGATCG', 'GGGGAGATCGAAAA'], None),
    'casava': (['--discard-casava'], ['CCCCCC', 'GGGGGG'], None),
    'expected_errors': (['--max-ee', '0.00001'], ['CCCCCC', 'GGGGGG'], None),
}

original_fastq = runner.fastq


def fastq(path, seqs):
    if path.parent.name != 'casava':
        return original_fastq(path, seqs)
    path.write_text(''.join(f'@synthetic_{i} 1:{"Y" if i == 0 else "N"}:0:AAA\n{s}\n+\n{"I" * len(s)}\n'
                            for i, s in enumerate(seqs)))


runner.fastq = fastq
if __name__ == '__main__':
    runner.main()
