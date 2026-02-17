# Spin Lab

**Educational Slot Machine Simulator & Next-Token Probability Research Lab**

Built on Frappe Framework | AI Agent Orchestrated | Canvas Visualized

---

## What Is This?

Spin Lab is an educational simulator that models slot-machine-style random event
generators to study probability distributions, gambler's fallacy, and the
behavior of sequences under pure randomness.

It draws a direct analogy to how Large Language Models (LLMs) predict the
next token: each spin is a sample from a fixed probability distribution,
and the goal is to observe, compile, and understand how those samples
behave over time.

**This is NOT a gambling application.** There is no real money, no deposits,
no withdrawals, and no way to profit. Credits are virtual points used
exclusively for research and education.

---

## Core Analogy: Slots as Next-Token Sampling

| LLM Concept | Spin Lab Equivalent |
|---|---|
| Vocabulary | Set of reel symbols (fruits, 7s, stars, bars) |
| Token probability distribution | Reel mapping + pay table (fixed per theme) |
| Sampling one token | One spin (sample from the distribution) |
| Temperature / top-k | Volatility profile of the theme |
| Sequence of tokens | Sequence of spin outcomes |
| Perplexity / loss | Deviation of empirical vs theoretical RTP |
| Training data | Simulated spin history (millions of samples) |

---

## Key Research Questions

1. How does the empirical next-event distribution converge to the
   theoretical one as the number of spins increases?
2. How do rare events (e.g., triple 7s) cluster vs spread, and how
   does that compare to what probability theory predicts?
3. Does changing the stake (bet size) affect outcome probabilities?
   (Answer: no, but the simulator proves it empirically.)
4. How do different "gambler strategies" (naive/advised/rational)
   compare in loss trajectories under identical RNG?
5. What is the statistical behavior of aggregate results:
   binomial for event counts, Gaussian for long-run totals (CLT)?

---

## Architecture Overview

```
+----------------------------------------------------------+
|                    ORCHESTRATOR AGENT                     |
|  Routes tasks, enforces policies, validates phase gates   |
+----+----------+----------+-----------+---------+---------+
     |          |          |           |         |
+----v---+ +----v---+ +----v----+ +---v----+ +--v-------+
| Domain | | RNG &  | |Strategy | |Analytics| | Coach &  |
| Policy | |Scoring | |Behavior | | & Heat | | Safety   |
| Agent  | | Agent  | | Agent   | | Agent  | | Agents   |
+--------+ +--------+ +---------+ +--------+ +----------+

+----------------------------------------------------------+
|              FRAPPE BACKEND (Python)                      |
|  DocTypes: SlotTheme, SlotSpin, SlotSimulationRun        |
|  APIs: spin_once(), simulate(), get_event_heat()         |
|  Realtime: frappe.publish_realtime() via Socket.IO       |
+----------------------------------------------------------+

+----------------------------------------------------------+
|              CANVAS FRONTEND (JS)                         |
|  Reel animation (fruits/7s/stars/bars themes)            |
|  Heat-band overlay (freeze-blue-yellow-green-red-black)  |
|  Analytics dashboard (histograms, bankroll paths)        |
+----------------------------------------------------------+
```

---

## Themes / Configurations

| Theme | Symbols | Volatility | Description |
|---|---|---|---|
| Classic Fruits | Cherry, Lemon, Plum, Orange, Grape | Low | Frequent small wins |
| Lucky Sevens | 7, 77, 777, Bar, Bell | High | Rare large payouts |
| Stars & Bars | Star, Bell, Single BAR, Double BAR, Triple BAR | Extreme | Very rare, very large payouts |

Each theme uses the same pure RNG engine; only the pay table and symbol
mapping differ, which controls expected return (RTP) and variance.

---

## Scoring Profiles

The RNG is always pure and independent. The "house edge" is controlled
entirely by the scoring rule (pay table), not by the randomness:

| Profile | RTP | Purpose |
|---|---|---|
| `casino_edge` | ~95% | Shows how house edge works over time |
| `fair` | 100% | Zero-sum game for studying pure variance |
| `player_edge` | ~105% | Demonstrates what happens when scoring favors the player |

---

## Heat Bands (Next-Event Probability Visualization)

Each possible event gets a color based on its true probability:

| Probability Range | Band Label | Color |
|---|---|---|
| 0 - 0.1% | Frozen | White / very light blue |
| 0.1 - 1% | Cold | Blue |
| 1 - 5% | Cool | Yellow |
| 5 - 20% | Warm | Green |
| 20 - 50% | Hot | Orange / Red |
| > 50% | Max | Black |

Additionally, each event gets a **deviation label** comparing empirical
frequency to theoretical probability in a sliding window:
- "As expected" (within normal variance)
- "Currently above expectation" (looks hot)
- "Currently below expectation" (looks cold)

These labels are **descriptive of history, not predictive of the next spin**.

---

## Gambler Strategy Simulation

Three bot strategies run under identical RNG to study fallacy behavior:

| Strategy | Behavior | Purpose |
|---|---|---|
| Naive | Raises stake after losses (chasing) | Demonstrates gambler's fallacy |
| Advised | Follows Coach Agent: keep stake minimal | Shows loss-limiting via education |
| Rational | Flat stake, treats spins as independent | Baseline comparison |

All strategies receive the **same outcome sequence**; only stakes differ.
This proves empirically that no strategy changes the underlying probabilities.

---

## Tech Stack

- **Backend:** Frappe Framework (Python 3.11+)
- **Frontend:** HTML5 Canvas (vanilla JS or PixiJS)
- **Realtime:** Frappe Socket.IO (publish_realtime)
- **AI Agents:** Raven-style agent orchestration
- **Database:** MariaDB (via Frappe ORM)

---

## Project Phases

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full 6-phase plan with
agent specs, prompts, test plans, and close-phase reports.

| Phase | Name | Focus |
|---|---|---|
| 1 | Domain & Policy Design | Entities, constraints, educational framing |
| 2 | RNG & Outcome Engine | Pure random engine + pluggable scoring profiles |
| 3 | Strategy & Gambler Fallacy | Naive/Advised/Rational bot strategies |
| 4 | Analytics & Heat Bands | EventHeat, probability visualization, CLT demos |
| 5 | Coach & Safety Agents | Educational guidance, responsible-use guardrails |
| 6 | Orchestrator Validation | End-to-end integration, final acceptance |

---

## Quick Start (Development)

```bash
# Clone
git clone https://github.com/rogerboy38/spin_lab.git
cd spin_lab

# Install as Frappe app (inside a bench)
bench get-app ./spin_lab
bench --site your.site install-app spin_lab
bench migrate

# Run a test spin from bench console
bench --site your.site console
>>> from spin_lab.api.slot_engine import spin_once
>>> result = spin_once(theme="Classic Fruits", stake_points=1.0)
>>> print(result)
```

---

## Educational Disclaimer

This software is an educational research tool for studying probability,
randomness, and the gambler's fallacy. It is not intended for real-money
gambling, and no feature in this project facilitates or encourages
gambling with real currency.

All credits are virtual points with no monetary value.

If you or someone you know has a gambling problem, please contact the
National Problem Gambling Helpline: 1-800-522-4700.

---

## License

See [LICENSE](LICENSE) file.
