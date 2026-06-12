"""Tests for the 4096-ways video slot engine."""

import unittest

from spin_lab.engine.rng import make_rng
from spin_lab.engine.themes import SCORING_PROFILES
from spin_lab.engine.video_slot import (
    DEEP_SEA,
    ROWS,
    TOTAL_WAYS,
    analytic_rtp,
    count_scatters,
    evaluate_ways,
    spin_grid,
    video_profile_scale,
    video_simulate,
    video_spin,
)


def grid_of(*columns):
    return [list(c) for c in columns]


class TestWaysEvaluation(unittest.TestCase):
    def test_total_ways_constant(self):
        self.assertEqual(TOTAL_WAYS, 4**6)

    def test_simple_three_match(self):
        g = grid_of(
            ["KRAKEN", "TEN", "TEN", "TEN"],
            ["KRAKEN", "JACK", "JACK", "JACK"],
            ["KRAKEN", "QUEEN", "QUEEN", "QUEEN"],
            ["KING", "KING", "KING", "ACE"],   # breaks the KRAKEN run
            ["ACE", "ACE", "CRAB", "CRAB"],
            ["CRAB", "SHARK", "SHARK", "OCTOPUS"],
        )
        total, wins = evaluate_ways(DEEP_SEA, g)
        kraken = next(w for w in wins if w["symbol"] == "KRAKEN")
        self.assertEqual(kraken["count"], 3)
        self.assertEqual(kraken["ways"], 1 * 1 * 1)
        self.assertEqual(kraken["pay"], DEEP_SEA.pay_table["KRAKEN"][3])

    def test_ways_multiply_per_reel_counts(self):
        g = grid_of(
            ["ACE", "ACE", "TEN", "TEN"],      # 2 aces
            ["ACE", "ACE", "ACE", "JACK"],     # 3 aces
            ["ACE", "QUEEN", "QUEEN", "QUEEN"],# 1 ace
            ["KING", "KING", "KING", "KING"],  # run ends
            ["TEN", "JACK", "QUEEN", "KING"],
            ["TEN", "JACK", "QUEEN", "KING"],
        )
        _, wins = evaluate_ways(DEEP_SEA, g)
        ace = next(w for w in wins if w["symbol"] == "ACE")
        self.assertEqual(ace["ways"], 2 * 3 * 1)

    def test_wild_substitutes_and_counts(self):
        g = grid_of(
            ["ACE", "TEN", "TEN", "TEN"],
            ["WILD", "JACK", "JACK", "JACK"],   # wild counts as ACE
            ["ACE", "WILD", "QUEEN", "QUEEN"],  # 1 ace + 1 wild = 2
            ["KING", "KING", "KING", "KING"],
            ["TEN", "JACK", "QUEEN", "KING"],
            ["TEN", "JACK", "QUEEN", "KING"],
        )
        _, wins = evaluate_ways(DEEP_SEA, g)
        ace = next(w for w in wins if w["symbol"] == "ACE")
        self.assertEqual(ace["count"], 3)
        self.assertEqual(ace["ways"], 1 * 1 * 2)

    def test_only_highest_match_pays(self):
        g = grid_of(*[["TEN", "JACK", "QUEEN", "KING"]] * 6)  # TEN on all 6 reels
        _, wins = evaluate_ways(DEEP_SEA, g)
        ten = next(w for w in wins if w["symbol"] == "TEN")
        self.assertEqual(ten["count"], 6)   # pays 6-match only, not 3/4/5 too
        self.assertEqual(len([w for w in wins if w["symbol"] == "TEN"]), 1)

    def test_no_pay_without_reel1(self):
        g = grid_of(
            ["TEN", "TEN", "TEN", "TEN"],       # no KRAKEN on reel 1
            ["KRAKEN", "KRAKEN", "KRAKEN", "KRAKEN"],
            ["KRAKEN", "KRAKEN", "KRAKEN", "KRAKEN"],
            ["KRAKEN", "KRAKEN", "KRAKEN", "KRAKEN"],
            ["JACK", "JACK", "JACK", "JACK"],
            ["JACK", "JACK", "JACK", "JACK"],
        )
        _, wins = evaluate_ways(DEEP_SEA, g)
        self.assertFalse(any(w["symbol"] == "KRAKEN" for w in wins))


class TestStripModel(unittest.TestCase):
    def test_window_height(self):
        g = spin_grid(DEEP_SEA, make_rng(1))
        self.assertEqual(len(g), 6)
        self.assertTrue(all(len(col) == ROWS for col in g))

    def test_scatter_spacing_prevents_multi_scatter_windows(self):
        """At most one scatter visible per reel window (strip spacing rule)."""
        for strip in DEEP_SEA.strips:
            n = len(strip)
            for stop in range(n):
                window = [strip[(stop + r) % n] for r in range(ROWS)]
                self.assertLessEqual(window.count("PEARL"), 1)

    def test_no_wild_on_reel_1(self):
        self.assertNotIn("WILD", DEEP_SEA.strips[0])


class TestRTP(unittest.TestCase):
    def test_profiles_hit_target_analytically(self):
        r = analytic_rtp(DEEP_SEA)
        for profile, target in SCORING_PROFILES.items():
            scaled = r["total_rtp"] * video_profile_scale(DEEP_SEA, profile)
            self.assertAlmostEqual(scaled, target, places=9)

    def test_simulation_converges_to_analytic_decomposition(self):
        res = video_simulate(DEEP_SEA, 150_000, "fair", seed=42)
        r = analytic_rtp(DEEP_SEA)
        scale = video_profile_scale(DEEP_SEA, "fair")
        d = res["rtp_decomposition"]
        self.assertAlmostEqual(d["base_ways"], r["base_ways_rtp"] * scale, delta=0.04)
        self.assertAlmostEqual(d["scatter"], r["scatter_rtp"] * scale, delta=0.02)
        self.assertAlmostEqual(res["empirical_rtp"], 1.0, delta=0.12)  # high volatility

    def test_fs_trigger_rate_matches_analytic(self):
        res = video_simulate(DEEP_SEA, 150_000, "fair", seed=7)
        p = analytic_rtp(DEEP_SEA)["p_free_spin_trigger"]
        self.assertAlmostEqual(res["fs_trigger_rate"], p, delta=0.002)

    def test_retrigger_expectation_formula(self):
        # E[spins] = n_avg / (1 - R) must exceed n_avg and stay finite
        r = analytic_rtp(DEEP_SEA)
        self.assertGreater(r["expected_free_spins_per_trigger"], 8.0)
        self.assertLess(r["expected_free_spins_per_trigger"], 30.0)


class TestSpin(unittest.TestCase):
    def test_spin_structure_and_determinism(self):
        a = video_spin(DEEP_SEA, 1.0, "fair", rng=make_rng(5))
        b = video_spin(DEEP_SEA, 1.0, "fair", rng=make_rng(5))
        self.assertEqual(a["grid"], b["grid"])
        self.assertEqual(a["total_win"], b["total_win"])

    def test_stake_scales_win_not_outcome(self):
        a = video_spin(DEEP_SEA, 1.0, "fair", rng=make_rng(11))
        b = video_spin(DEEP_SEA, 10.0, "fair", rng=make_rng(11))
        self.assertEqual(a["grid"], b["grid"])
        self.assertAlmostEqual(b["total_win"], a["total_win"] * 10, places=4)


if __name__ == "__main__":
    unittest.main()
