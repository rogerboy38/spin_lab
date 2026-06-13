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


class TestThemeFromConfig(unittest.TestCase):
    def test_config_round_trip_matches_builtin(self):
        from spin_lab.engine.video_slot import deep_sea_config, theme_from_config
        t = theme_from_config(deep_sea_config())
        a, b = analytic_rtp(t), analytic_rtp(DEEP_SEA)
        self.assertAlmostEqual(a["total_rtp"], b["total_rtp"], places=12)
        self.assertEqual(t.strips, DEEP_SEA.strips)


class TestClassicVideoThemes(unittest.TestCase):
    def test_four_themes_exist_and_hit_targets(self):
        from spin_lab.engine.video_slot import (VIDEO_THEMES, base_total_rtp,
                                                 video_profile_scale)
        self.assertEqual(len(VIDEO_THEMES), 8)
        for name, t in VIDEO_THEMES.items():
            base = base_total_rtp(t)  # exact, or MC-calibrated for expanding themes
            for profile, target in SCORING_PROFILES.items():
                self.assertAlmostEqual(
                    base * video_profile_scale(t, profile), target, places=9,
                    msg=f"{name}/{profile}")

    def test_classic_video_simulation_converges(self):
        res = video_simulate("Lucky Sevens 4096", 100_000, "fair", seed=3)
        self.assertAlmostEqual(res["empirical_rtp"], 1.0, delta=0.25)  # very high volatility


class TestExpandingWilds(unittest.TestCase):
    def _nova(self):
        from spin_lab.engine.video_slot import VIDEO_THEMES
        return VIDEO_THEMES["Star Nova 4096"]

    def test_expansion_covers_reel_and_locks(self):
        from spin_lab.engine.video_slot import apply_expanding_wilds
        t = self._nova()
        grid = [["PURPLE"] * 4 for _ in range(6)]
        grid[2][1] = "STAR"          # wild on eligible reel 3 (idx 2)
        grid[0][0] = "STAR"          # reel 1 is NOT eligible
        newly = apply_expanding_wilds(t, grid, set())
        self.assertEqual(newly, {2})
        self.assertEqual(grid[2], ["STAR"] * 4)       # full wild reel
        self.assertNotEqual(grid[0], ["STAR"] * 4)    # reel 1 untouched

    def test_no_expansion_when_disabled(self):
        from spin_lab.engine.video_slot import apply_expanding_wilds
        grid = [["TEN"] * 4 for _ in range(6)]
        grid[2][0] = "WILD"
        self.assertEqual(apply_expanding_wilds(DEEP_SEA, grid, set()), set())

    def test_respin_chain_bounded(self):
        from spin_lab.engine.video_slot import video_spin as vspin
        t = self._nova()
        rng = make_rng(2024)
        for _ in range(300):
            res = vspin(t, 1.0, "fair", rng=rng)
            self.assertLessEqual(res["respins_used"], t.max_respins)
            self.assertLessEqual(len(res["locked_reels"]), len(t.expanding_reels))
            # locked reels in the final grid must be fully wild
            for r in res["locked_reels"]:
                self.assertEqual(res["grid"][r], [t.wild] * 4)

    def test_mc_calibrated_profile_hits_target(self):
        res = video_simulate("Star Nova 4096", 60_000, "fair", seed=4242)
        self.assertAlmostEqual(res["empirical_rtp"], 1.0, delta=0.08)
        self.assertGreater(res["respin_rate"], 0.2)   # signature feature fires often

    def test_plain_themes_unaffected(self):
        res = video_simulate(DEEP_SEA, 30_000, "fair", seed=7)
        self.assertEqual(res["respin_rate"], 0)


class TestV3Features(unittest.TestCase):
    def _theme(self, name):
        from spin_lab.engine.video_slot import VIDEO_THEMES
        return VIDEO_THEMES[name]

    def test_both_ways_full_run_pays_once(self):
        from spin_lab.engine.video_slot import evaluate_ways_both
        t = self._theme("Outlaw Trail 4096")
        g = [["TEN", "JACK", "QUEEN", "KING"]] * 6
        _, wins = evaluate_ways_both(t, g)
        self.assertEqual(len([w for w in wins if w["symbol"] == "TEN"]), 1)

    def test_both_ways_non_overlapping_pay_twice(self):
        from spin_lab.engine.video_slot import evaluate_ways_both
        t = self._theme("Outlaw Trail 4096")
        g = [["TEN"] * 4] * 3 + [["JACK"] * 4] * 3   # TEN reels 1-3, JACK reels 4-6
        _, wins = evaluate_ways_both(t, g)
        symbols = sorted((w["symbol"], w.get("direction", "L2R")) for w in wins)
        self.assertIn(("TEN", "L2R"), symbols)
        self.assertIn(("JACK", "R2L"), symbols)

    def test_megaways_heights_and_ways(self):
        from spin_lab.engine.video_slot import grid_ways, spin_grid_megaways
        t = self._theme("Mega Vines")
        rng = make_rng(5)
        seen = set()
        for _ in range(500):
            g = spin_grid_megaways(t, rng)
            for col in g:
                self.assertTrue(2 <= len(col) <= 7)
                seen.add(len(col))
            self.assertTrue(64 <= grid_ways(g) <= 117_649)
        self.assertEqual(seen, {2, 3, 4, 5, 6, 7})

    def test_walking_wilds_respin_and_bound(self):
        from spin_lab.engine.video_slot import WALK_CAP, video_spin as vspin
        t = self._theme("Beanstalk Walk 4096")
        rng = make_rng(77)
        saw_walk = False
        for _ in range(200):
            res = vspin(t, 1.0, "fair", rng=rng)
            self.assertLessEqual(res["respins_used"], WALK_CAP)
            if res["respins_used"]:
                saw_walk = True
        self.assertTrue(saw_walk)

    def test_sticky_wilds_reported_in_fs(self):
        res = video_simulate("Outlaw Trail 4096", 30_000, "fair", seed=8)
        self.assertGreater(res["fs_trigger_rate"], 0)   # free spins happened (sticky path ran)

    def test_v3_themes_hit_targets(self):
        from spin_lab.engine.video_slot import base_total_rtp, video_profile_scale
        for name in ("Outlaw Trail 4096", "Beanstalk Walk 4096", "Mega Vines"):
            t = self._theme(name)
            base = base_total_rtp(t)
            for profile, target in SCORING_PROFILES.items():
                self.assertAlmostEqual(base * video_profile_scale(t, profile), target,
                                       places=9, msg=f"{name}/{profile}")


class TestProgressiveMath(unittest.TestCase):
    def test_break_even_and_rtp(self):
        from spin_lab.engine.progressive_math import break_even_meter, rtp_at
        # fair base, c=2%, p=1/200k -> J* = 4000; RTP at J* must be exactly 1
        j = break_even_meter(1.0, 0.02, 1 / 200_000)
        self.assertAlmostEqual(j, 4000.0, places=6)
        self.assertAlmostEqual(rtp_at(1.0, 0.02, 1 / 200_000, j), 1.0, places=9)
        # casino_edge base needs a bigger meter
        self.assertGreater(break_even_meter(0.95, 0.02, 1 / 200_000), j)

    def test_average_jackpot_equals_breakeven_for_fair(self):
        from spin_lab.engine.progressive_math import average_jackpot, break_even_meter
        # for base=1.0: J* = c/p and avg = seed + c/p -> avg > J* by seed
        c, p, seed = 0.015, 1 / 200_000, 1000.0
        self.assertAlmostEqual(average_jackpot(seed, c, p) - seed,
                               break_even_meter(1.0, c, p), places=6)

    def test_mhb_trigger_in_range(self):
        from spin_lab.engine.progressive_math import draw_mhb_trigger, mhb_expected_hit
        rng = make_rng(3)
        for _ in range(200):
            t = draw_mhb_trigger(5000, 10000, rng)
            self.assertTrue(5000 <= t <= 10000)
        self.assertEqual(mhb_expected_hit(5000, 10000), 7500.0)


class TestGamblersRuin(unittest.TestCase):
    def test_fair_formula(self):
        from spin_lab.engine.ruin import fair_ruin_probability, biased_ruin_probability
        self.assertAlmostEqual(fair_ruin_probability(10, 20), 0.5)
        self.assertAlmostEqual(fair_ruin_probability(30, 100), 0.3)
        # biased reduces to fair at p=0.5
        self.assertAlmostEqual(biased_ruin_probability(10, 20, 0.5),
                               fair_ruin_probability(10, 20), places=9)
        # house edge (p<0.5) lowers goal probability
        self.assertLess(biased_ruin_probability(10, 20, 0.45), 0.5)

    def test_edge_orders_outcomes(self):
        from spin_lab.engine.ruin import simulate_ruin
        edge = simulate_ruin("Classic Fruits", 50, 100, "casino_edge",
                             sessions=800, seed=3)
        plus = simulate_ruin("Classic Fruits", 50, 100, "player_edge",
                             sessions=800, seed=3)
        # player edge must reach the goal more often than house edge
        self.assertGreater(plus["p_reach_goal"], edge["p_reach_goal"])
        # every session ends (no leftover probability mass beyond rounding)
        for r in (edge, plus):
            self.assertAlmostEqual(
                r["p_reach_goal"] + r["p_ruin"] + r["p_timeout"], 1.0, places=2)

    def test_ruin_certain_with_big_goal_small_bank(self):
        from spin_lab.engine.ruin import simulate_ruin
        r = simulate_ruin("Classic Fruits", 5, 500, "casino_edge",
                          sessions=600, seed=1)
        self.assertGreater(r["p_ruin"], 0.9)   # tiny bank, huge goal, edge -> doom


class TestProfilesEditable(unittest.TestCase):
    def test_engine_defaults_present(self):
        # the pure engine keeps all six defaults regardless of DB
        from spin_lab.engine.themes import SCORING_PROFILES
        for k in ("nevada_min", "loose_85", "tight_90", "casino_edge", "fair", "player_edge"):
            self.assertIn(k, SCORING_PROFILES)


class TestLoteria(unittest.TestCase):
    def test_rtp_converges_to_target(self):
        from spin_lab.engine.loteria import simulate
        for target in (1.20, 1.10, 0.95):
            r = simulate(120_000, target_rtp=target, seed=5)
            self.assertAlmostEqual(r["empirical_rtp"], target, delta=0.03)

    def test_free_food_is_net_positive_at_120(self):
        from spin_lab.engine.loteria import simulate
        r = simulate(50_000, target_rtp=1.20, seed=9)
        self.assertGreater(r["final_net"], 0)   # the bait: player ends UP in this stage

    def test_config_has_16_cards(self):
        from spin_lab.engine.loteria import config
        self.assertEqual(len(config()["cards"]), 16)
        self.assertEqual(len(config()["tiers"]), 4)


class TestRoulette(unittest.TestCase):
    def test_wheel_and_colors(self):
        from spin_lab.engine.roulette import WHEEL, color, POCKETS
        self.assertEqual(POCKETS, 37)
        self.assertEqual(len(WHEEL), 37)
        self.assertEqual(set(WHEEL), set(range(37)))
        self.assertEqual(color(0), "green")
        self.assertEqual(color(1), "red")
        self.assertEqual(color(2), "black")

    def test_payouts_and_settle(self):
        from spin_lab.engine.roulette import settle
        bets = [{"kind": "straight", "target": 17, "amount": 1},
                {"kind": "black", "amount": 1}, {"kind": "dozen", "target": 2, "amount": 1}]
        r = settle(bets, 17)   # 17 is BLACK, in dozen 2 (13-24)
        self.assertEqual(r[0]["won"], 36)
        self.assertEqual(r[1]["won"], 2)
        self.assertEqual(r[2]["won"], 3)

    def test_zero_kills_outside(self):
        from spin_lab.engine.roulette import settle
        bets = [{"kind": "red", "amount": 1}, {"kind": "even", "amount": 1},
                {"kind": "straight", "target": 0, "amount": 1}]
        r = settle(bets, 0)
        self.assertEqual(r[0]["won"], 0)   # red loses on 0
        self.assertEqual(r[1]["won"], 0)   # even loses on 0
        self.assertEqual(r[2]["won"], 36)  # straight-up 0 wins

    def test_rtp_converges_to_36_37(self):
        from spin_lab.engine.roulette import spin, settle, theoretical_rtp
        from spin_lab.engine.rng import make_rng
        rng = make_rng(11)
        staked = paid = 0.0
        for _ in range(200_000):
            n = spin(rng)
            staked += 1
            paid += settle([{"kind": "red", "amount": 1}], n)[0]["won"]
        self.assertAlmostEqual(paid / staked, theoretical_rtp(), delta=0.01)
