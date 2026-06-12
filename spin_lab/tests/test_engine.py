"""Standalone engine tests - no Frappe site required.

Run with:  python -m unittest discover spin_lab/tests
"""

import math
import unittest

from spin_lab.engine.heat import band_for, deviation_label, event_heat
from spin_lab.engine.rng import make_rng, spin_reels
from spin_lab.engine.slot_engine import simulate, spin_once
from spin_lab.engine.strategies import compare_strategies
from spin_lab.engine.themes import (
    DEFAULT_THEMES,
    SCORING_PROFILES,
    base_payout,
    event_probability,
    match_combination,
    profile_scale,
    theoretical_rtp,
)

FRUITS = DEFAULT_THEMES["Classic Fruits"]
SEVENS = DEFAULT_THEMES["Lucky Sevens"]


class TestPayTable(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(match_combination(("GRAPE", "GRAPE", "GRAPE"), "GRAPE|GRAPE|GRAPE"))

    def test_wildcard_excludes_literal(self):
        # CHERRY|CHERRY|* must not fire on triple cherry (specific rule covers it)
        self.assertFalse(match_combination(("CHERRY", "CHERRY", "CHERRY"), "CHERRY|CHERRY|*"))
        self.assertTrue(match_combination(("CHERRY", "CHERRY", "LEMON"), "CHERRY|CHERRY|*"))

    def test_most_specific_rule_wins(self):
        triple = base_payout(FRUITS, ("CHERRY", "CHERRY", "CHERRY"))
        double = base_payout(FRUITS, ("CHERRY", "CHERRY", "LEMON"))
        self.assertEqual(triple, 6.0)
        self.assertEqual(double, 2.0)


class TestRNGUniformity(unittest.TestCase):
    def test_chi_square_uniform_over_stops(self):
        """Symbol frequencies on one reel must match weights (chi-square)."""
        rng = make_rng(42)
        n = 200_000
        counts = {s.symbol: 0 for s in FRUITS.symbols}
        for _ in range(n):
            counts[spin_reels(FRUITS, rng)[0]] += 1
        chi2 = sum(
            (counts[s.symbol] - n * FRUITS.symbol_probability(s.symbol)) ** 2
            / (n * FRUITS.symbol_probability(s.symbol))
            for s in FRUITS.symbols
        )
        # df=4, p=0.001 critical value ~ 18.47
        self.assertLess(chi2, 18.47)

    def test_independence_from_stake(self):
        """Same seed => same reels regardless of stake."""
        r1 = spin_once(FRUITS, stake_points=0.01, rng=make_rng(7)).reels
        r2 = spin_once(FRUITS, stake_points=100.0, rng=make_rng(7)).reels
        self.assertEqual(r1, r2)


class TestRTP(unittest.TestCase):
    def test_profiles_hit_target_rtp_analytically(self):
        for theme in DEFAULT_THEMES.values():
            base = theoretical_rtp(theme)
            for profile, target in SCORING_PROFILES.items():
                self.assertAlmostEqual(base * profile_scale(theme, profile), target, places=9)

    def test_empirical_rtp_converges(self):
        res = simulate(FRUITS, n_spins=300_000, profile="fair", seed=123)
        # 3-sigma tolerance, generous for low-volatility theme
        self.assertAlmostEqual(res["empirical_rtp"], 1.0, delta=0.05)

    def test_casino_edge_below_fair(self):
        a = simulate(SEVENS, 100_000, "casino_edge", seed=5)
        b = simulate(SEVENS, 100_000, "fair", seed=5)
        self.assertLess(a["total_paid"], b["total_paid"])
        # identical seed => identical outcome counts (RNG untouched by profile)
        self.assertEqual(a["outcome_counts"], b["outcome_counts"])


class TestStrategies(unittest.TestCase):
    def test_identical_outcomes_different_stakes(self):
        res = compare_strategies(FRUITS, 50_000, "fair", seed=99)
        s = res["strategies"]
        # flat-stake strategies (rational, advised) see the same outcome
        # sequence, so their stake-weighted RTP equals the mean multiplier
        mean_mult = res["shared_outcomes"]["mean_multiplier"]
        self.assertAlmostEqual(s["rational"]["empirical_rtp"], mean_mult, places=4)
        self.assertAlmostEqual(s["advised"]["empirical_rtp"], mean_mult, places=4)
        # naive varies stake, so its stake-WEIGHTED rtp may differ - but the
        # underlying outcomes are shared, which hit_rate documents
        self.assertGreater(res["shared_outcomes"]["hit_rate"], 0)

    def test_naive_stakes_more(self):
        res = compare_strategies(FRUITS, 50_000, "casino_edge", seed=99)
        s = res["strategies"]
        self.assertGreater(s["naive"]["total_staked"], s["rational"]["total_staked"])
        self.assertGreater(s["rational"]["total_staked"], s["advised"]["total_staked"])

    def test_naive_loses_more_under_house_edge(self):
        res = compare_strategies(SEVENS, 100_000, "casino_edge", seed=7)
        s = res["strategies"]
        self.assertLess(s["naive"]["final_bankroll"], s["advised"]["final_bankroll"])


class TestHeat(unittest.TestCase):
    def test_band_mapping(self):
        self.assertEqual(band_for(0.0005)[0], "Frozen")
        self.assertEqual(band_for(0.005)[0], "Cold")
        self.assertEqual(band_for(0.03)[0], "Cool")
        self.assertEqual(band_for(0.1)[0], "Warm")
        self.assertEqual(band_for(0.3)[0], "Hot")
        self.assertEqual(band_for(0.7)[0], "Max")

    def test_triple_seven_is_rare(self):
        p = event_probability(SEVENS, "SEVEN|SEVEN|SEVEN")
        self.assertAlmostEqual(p, (4 / 40) ** 3, places=9)  # exactly 0.001
        # 0.001 sits on the Frozen/Cold boundary -> Cold (bands are [lo, hi))
        self.assertEqual(event_heat(SEVENS, "SEVEN|SEVEN|SEVEN")["band_label"], "Cold")
        # triple diamond (0.05^3) is genuinely Frozen
        self.assertEqual(event_heat(SEVENS, "DIAMOND|DIAMOND|DIAMOND")["band_label"], "Frozen")

    def test_deviation_labels(self):
        # exactly expected
        self.assertEqual(deviation_label(0.1, 100, 1000), "as expected")
        # way above expectation
        self.assertIn("above expectation", deviation_label(0.1, 200, 1000))
        # way below
        self.assertIn("below expectation", deviation_label(0.1, 20, 1000))

    def test_probabilities_sum_sanity(self):
        for theme in DEFAULT_THEMES.values():
            total_p = sum(event_probability(theme, c) for c in theme.pay_table)
            self.assertLessEqual(total_p, 1.0)
            self.assertGreater(total_p, 0.0)


if __name__ == "__main__":
    unittest.main()
