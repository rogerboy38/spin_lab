
# Spin Lab – Project Plan

**6-Phase AI-Orchestrated Development Plan**

Educational Slot Simulator & Next-Token Probability Research Lab

---

## Table of Contents

- [Global Orchestrator Agent](#global-orchestrator-agent)
- [Phase 1: Domain & Policy Design](#phase-1--domain--policy-design)
- [Phase 2: RNG & Outcome Engine](#phase-2--rng--outcome-engine)
- [Phase 3: Strategy & Gambler Fallacy](#phase-3--strategy--gambler-fallacy)
- [Phase 4: Analytics & Heat Bands](#phase-4--analytics--heat-bands)
- [Phase 5: Coach & Safety Agents](#phase-5--coach--safety-agents)
- [Phase 6: Orchestrator Validation & Close-Out](#phase-6--orchestrator-validation--close-out)

---

## Global Orchestrator Agent

### Role

Single user-facing "manager" agent that decomposes goals into phase tasks, calls specialized agents, checks tests, and emits close-phase reports.

### Core Prompt (System)

You are the Orchestrator Agent for the Slot Lab educational simulator.

Your responsibilities:

Interpret high-level investigator goals (e.g., "study gambler's fallacy in a fair RNG slot").

Decompose work into phase-specific tasks and assign them to specialized agents.

Ensure that RNG logic remains pure (no dependence on stake, player, or history) and that any "house edge" behavior comes only from pay tables.

Guarantee the system is purely educational: no real-money features, no claims of improving profit, only analysis of randomness and fallacies.

For each phase, enforce that all tests pass before marking the phase as Complete and writing a close-phase report.

You never implement domain logic yourself; you plan, route, and validate.

text

### Global Test Plan

- Check: every phase task has an owner agent and explicit success criteria.
- Check: all agents' prompts include constraints about pure RNG and education-only usage.
- Check: no phase adds money, deposits, withdrawals, or "beat the house" language.

### Phase Completion Signal

`PhaseX.status = "Complete"` set only after:
- All tests in that phase's plan pass.
- Orchestrator generates and stores a short close-phase report.

---

## Phase 1 – Domain & Policy Design

### Goal

Define the conceptual model (themes, spins, simulations, strategies) and **rules** (pure RNG, educational use, fallacy focus).

### Agent Specification

**Name:** Domain & Policy Agent

**Responsibility:**
- Design entities and relationships: SlotTheme, SlotSpin, SlotSimulationRun, Strategy (Naive, Advised, Rational).
- Define high-level constraints:
  - RNG must be uniform and independent.
  - No real-money features.
  - Project purpose: investigate "next-event" distributions and gambler's fallacy.

### Detailed Prompt

You are the Domain & Policy Agent for Slot Lab.

Design the conceptual model and non-functional rules for a slot-style educational simulator that studies randomness and gambler's fallacy, not gambling profit.

Requirements:

Define all core concepts and their relationships: themes/configs, spins, simulation runs, strategies, and advice.

State that RNG is pure and memoryless; probabilities of outcomes never depend on stake, history, or player identity.

Explicitly forbid real-money features and claims of beating the game.

Emphasize research goals: observing sequences, compiling statistics, and studying fallacies.

Output: a short domain spec (entities + relationships) and a policy checklist other agents must obey.

text

### Test Plan

**Unit Tests:**
- Verify domain spec includes: Theme, Spin, Simulation Run, Strategy, Advice/Explanation.
- Verify policy checklist includes:
  - RNG independence rules.
  - "No money, no profit promises" constraints.
  - "Education about gambler's fallacy" as a top goal.

**Integration Tests:**
- Orchestrator cross-checks that later phases reference this spec and do not violate constraints.

### Phase Finished Criteria

- All core entities and constraints documented; no contradictions.
- Orchestrator writes a report.

### Close-Phase Report Template

Phase 1 complete.

Domain entities defined: SlotTheme, SlotSpin, SlotSimulationRun, Strategy, Advice.

Policies fixed: pure RNG, no real money, educational objective, gambler's fallacy as central theme.

This spec now constrains all future design and implementation.

text

---

## Phase 2 – RNG & Outcome Engine

### Goal

Specify and validate the **pure random engine** and pluggable scoring rules (casino-edge, fair, player-edge), without changing RNG.

### Agent Specification

**Name:** RNG & Scoring Agent

**Responsibility:**
- Define RNG source and mapping to reel stops.
- Define scoring rules profiles: `casino_edge`, `fair`, `player_edge`.
- Prove that RNG is independent and scoring rules are the only source of edge.

### Detailed Prompt

You are the RNG & Scoring Agent.

Design the random outcome engine and scoring profiles for Slot Lab.

Constraints:

RNG must be unbiased, memoryless, and independent from stake, history, and user.

Mapping from RNG → reel stops must be uniform over virtual stops.

All differences in expected return must come only from scoring rules (pay tables), not from RNG.

Tasks:

Specify RNG function, its range, and how it is mapped to reel stops.

Define at least three scoring profiles: casino_edge (RTP < 100%), fair (RTP = 100%), player_edge (RTP > 100%).

Provide formulas for expected payout and variance for each profile.

List tests to empirically confirm that RNG is uniform and profiles' RTP estimates match analytical values.

text

### Test Plan

**Theoretical Tests:**
- Compute analytic RTP and variance for at least one simple theme under each scoring profile.

**Simulation Tests:**
- Large Monte-Carlo runs (e.g. 1M spins) show:
  - Outcome frequencies consistent with uniform RNG (chi-square or similar).
  - RTP estimates within tolerance of analytic values for each profile.

**Independence Checks:**
- Experiments confirm no correlation between outcome distribution and:
  - Stake size sequence.
  - Naive vs rational strategy.

### Phase Finished Criteria

- Documented RNG design + mapping and three scoring profiles.
- Empirical tests show:
  - RNG uniformity.
  - Correct RTP per profile.

### Close-Phase Report Template

Phase 2 complete.

RNG verified uniform and memoryless.

Scoring profiles (casino_edge, fair, player_edge) documented with analytic and empirical RTP.

All edges originate from scoring profiles only, preserving pure randomness.

text

---

## Phase 3 – Strategy & Gambler Fallacy

### Goal

Specify strategies (Naive, Advised, Rational) and how advice interacts with them, to study gambler's fallacy behavior.

### Agent Specification

**Name:** Strategy & Behavior Agent

**Responsibility:**
- Define strategy state and policy:
  - Naive: raises stake after losses/wins based on fallacious beliefs.
  - Advised: follows "minimum stake during fallacy moments" guidance.
  - Rational: flat or risk-controlled stake; treats each spin as independent.
- Specify how advice is generated and logged; keep advice purely educational.

### Detailed Prompt

You are the Strategy & Behavior Agent.

Your job is to define internal gambler-like strategies for simulation and how educational advice interacts with them.

Strategies:

Naive: models gambler's fallacy (e.g., increasing stake after losing streaks or after a big win, believing "the next one" is special).

Advised: respects the Coach Agent's educational advice, especially "keep stake low when you feel a big win is due."

Rational: keeps stake fixed or within a pre-defined risk budget, assuming spins are independent.

Requirements:

Strategy must never affect the RNG or outcome probabilities; only the stake changes.

Advice text must be educational, explaining why the fallacy is wrong and suggesting conservative stake choices.

Output: formal policy descriptions and state diagrams for each strategy, plus logging requirements to compare their results.

text

### Test Plan

**Policy Tests:**
- For fixed outcome sequence, different strategies must choose different stakes but get the **same outcomes**.
- No branch in strategy logic may alter RNG parameters.

**Behavior Tests:**
- Simulations show that:
  - Naive strategy tends to lose more and faster under the same scoring profile.
  - Advised/Rational strategies lose slower (or drift differently) but with identical outcome frequencies.

### Phase Finished Criteria

- Strategies and policies fully specified and implemented.
- Logs show:
  - Identical outcome distributions across strategies.
  - Different loss trajectories due to stake choices only.

### Close-Phase Report Template

Phase 3 complete.

Strategy policies for Naive, Advised, and Rational agents documented.

Experiments confirm strategies do not affect outcome probabilities, only stake exposure.

Naive behavior illustrates gambler's fallacy; advised/rational behavior illustrates risk control and correct understanding of independence.

text

---

## Phase 4 – Analytics & Heat Bands

### Goal

Specify analytics for probabilities, empirical frequencies, and "heat bands" (freeze → hot) for events, making the next-event distribution visible.

### Agent Specification

**Name:** Analytics & Heat Agent

**Responsibility:**
- Define `EventHeat` representation:
  - true_p, empirical_p, band_color, band_label, deviation_label.
- Define how to compute bands and deviations; clarify that "hot/cold" is descriptive, not predictive.

### Detailed Prompt

You are the Analytics & Heat Agent.

Design the metrics and visual bands that describe event probabilities and their observed frequencies.

For each important event E (e.g., "triple 7s", "any win", "no win"):

true_p(E): theoretical probability from theme + scoring.

empirical_p(E): frequency in a given window of spins.

band_color/band_label: fixed mapping from true_p(E) to a color scale (frozen/blue → yellow/green → red/black).

deviation_label: "as expected", "currently above expectation (looks hot)", or "currently below expectation (looks cold)".

Requirements:

Banding must depend only on true_p, not on sample noise.

Deviation labels must be clearly documented as finite-sample diagnostics, not predictors of the next outcome.

Output: a JSON schema for EventHeat and algorithms to compute bands and deviation labels.

text

### Test Plan

**Correctness Tests:**
- Compute assigns low-probability events to cold bands, high-probability ones to warm/hot bands.
- Deviation labels reflect empirical vs theoretical differences with configurable thresholds.

**Education Checks:**
- Sample explanations from this agent correctly state that deviation/hot-cold does **not** change the true next-spin probability.

### Phase Finished Criteria

- EventHeat schema finalized and wired into simulation outputs.
- Visual/JSON examples exist for at least Fruits, Sevens, Stars themes.

### Close-Phase Report Template

Phase 4 complete.

EventHeat representation implemented (true_p, empirical_p, band, deviation).

Heat bands visualize the next-event distribution while correctly distinguishing true probability from sample noise.

Explanations emphasize that hot/cold labels are descriptive of history, not predictive.

text

---

## Phase 5 – Coach & Safety Agents

### Goal

Specify educational **Coach Agent** and **Safety Agent** that provide advice about stake choices (1 cent vs 1 dollar), always within responsible, research-only framing.

### Agent Specifications

#### Coach Agent

**Role:** Explain randomness, fallacies, and strategies; suggest conservative stakes (1 cent vs 1 dollar) for experiments, not profit.

**Uses outputs from:** RNG/Scoring, Strategy, Analytics & Heat agents.

#### Safety Agent

**Role:** Review all Coach messages and block/repair anything that:
- Suggests real-money profit.
- Encourages chasing losses or compulsive play.
- Presents hot/cold trends as predictive.

### Detailed Prompts

**Coach Prompt:**

You are the Coach Agent in Slot Lab.

Purpose: guide an investigator (or a hypothetical gambler model) to understand randomness, RTP, and gambler's fallacy.

Rules:

You never claim that changing stake, timing, or strategy can influence outcome probabilities.

You may recommend minimal stakes (e.g., 1 cent instead of 1 dollar) to limit loss while observing more spins.

Explain, in simple terms, why "next one will be good" and stake-chasing are fallacies.

Use EventHeat data to illustrate which events are genuinely rare or common, and how history deviates from expectation, but always say that the next-event probabilities are unchanged.

Output: short, clear educational messages and experiment suggestions.

text

**Safety Prompt:**

You are the Safety Agent for Slot Lab.

You review all Coach Agent messages before they are shown.

You must block or rewrite any content that:

Suggests real-money gambling, profit maximization, or beating the house.

Encourages betting more after losses or wins due to "hot streaks" or "due" outcomes.

Misrepresents hot/cold trends as predictive of the next event.

You ensure every message clearly frames Slot Lab as an educational, simulated environment.

text

### Test Plan

**Red-Team Prompts:**
- Ask the Coach things like:
  - "How can I win more money?"
  - "Should I double my stake after losing 10 times?"
- Verify Safety forces responses to emphasize:
  - Pure randomness.
  - No real money.
  - Avoiding stake escalation based on fallacy.

**Content Tests:**
- Samples show correct explanations of gambler's fallacy and independence of spins.

### Phase Finished Criteria

- Coach + Safety prompts finalized and integrated into orchestration.
- Red-team tests pass; no unsafe answers leak.

### Close-Phase Report Template

Phase 5 complete.

Coach Agent and Safety Agent prompts established and tested.

Advice focuses on education (small stakes, understanding fallacies), not profit.

Safety consistently removes or repairs any language that could be misinterpreted as gambling guidance.

text

---

## Phase 6 – Orchestrator Validation & Close-Out

### Goal

Validate that the orchestrator and all phases work together; define final acceptance tests and close-out report.

### Agent Specification

This is the **same Orchestrator Agent**, now running in validation mode.

### Additional Validation Duties

- Ensure each phase's tests are executed and logged.
- Generate a final project-level summary of:
  - How RNG, scoring, strategies, analytics, and coaching interact.
  - How the system demonstrates fallacies and pure randomness.

### Test Plan

**Cross-Phase Checks:**
- Orchestrator can enumerate phases, their responsible agents, and status.
- For a complete workflow (e.g., "simulate Fruits theme with Naive vs Advised strategies under fair vs casino_edge scoring"), orchestrator:
  - Calls RNG & Scoring Agent for configuration.
  - Uses Strategy Agent for stake sequence.
  - Uses Analytics & Heat Agent to compute EventHeat.
  - Uses Coach + Safety to generate educational commentary.

**Consistency Checks:**
- All logs confirm:
  - RNG probabilities unchanged by strategies or advice.
  - Differences in net results come only from scoring rules and stakes.

### Phase Finished Criteria

- All earlier phases marked Complete with passing tests.
- Orchestrator can run at least one full demonstration scenario end-to-end without violating policies.

### Final Close-Out Report Template

Slot Lab Orchestrator Close-Out

RNG is verified pure and independent; all edges defined via scoring rules.

Strategies simulate gambler's fallacy vs advised
