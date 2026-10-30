"""Exercise native global warnings after poly-A tables and zero-base inputs."""
import run_native_examples_001 as runner

runner.OUT = runner.ROOT / 'native_examples_003'
runner.CASES = {
    'warning_poly_a': (['-a', 'AGATCG', '--poly-a'], ['CCCCAGATCGAAAA'] * 20, None),
    'warning_paired_poly_a': (['-a', 'AGATCG', '-A', 'AGATCG', '--poly-a'],
                              ['CCCCAGATCGAAAA'] * 20, ['TTTTAGATCGAAAA'] * 20),
    'zero_bases': ([], ['', ''], None),
}

if __name__ == '__main__':
    runner.main()
