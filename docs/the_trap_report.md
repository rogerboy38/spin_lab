# The Trap: How Variable RTP Hooks and Harvests a Crowd
### An educational note — demonstrated by Spin Lab and the Gambler's Ruin Lab

---

## 1. The parable of the wild boars

There is an old parable about how to catch a herd of wild boars (*jabalíes*)
that no one can trap by force.

> You do not chase them. You leave food in a clearing, every day, for free.
> The boars are wary at first, but the food is real and the risk seems low,
> so they come. More come. Word spreads through the herd. Once they feed
> there daily, you quietly build one wall. The boars notice but the food is
> still there, so they keep eating. The next day, another wall. Then another.
> The herd grows fat and comfortable inside three walls and a single open
> gate. They no longer remember the open field. One day, while they are
> eating, you close the gate. The whole herd is caught at once.

Each step felt safe to the boar. No single day's wall looked like a trap.
The trap was the **sequence**, not any one moment in it. By the time the
gate closes, leaving is no longer a habit the herd has — and the door is
shut anyway.

This note is about the same structure applied to gambling, and how Spin Lab
lets you watch every stage of it happen in numbers.

---

## 2. The casino lifecycle: acquire → retain → extract

A commercial gambling operation has three economic phases. They map onto the
parable one-to-one.

**Phase 1 — The free food (acquisition).**
A new venue or app needs a crowd. So it runs *loss leaders*: welcome bonuses,
deposit matches, free spins, "loosest slots in town" launch promotions,
comped drinks, points, and jackpots seeded high. During this window the
*effective* return to the player can genuinely exceed 100% — the house is
paying to fill the room, exactly as the farmer pays in corn. The gambler's
early experience is a real win, and that memory is the hook.

**Phase 2 — The walls (retention).**
Once a base of regulars exists, the promotions normalize and the math
tightens back toward, or below, the legal floor for that jurisdiction. The
regulars barely notice: the lights, sounds, near-misses and **Losses
Disguised as Wins** keep the room *feeling* generous even as the payout
drops. The walls go up while everyone is still eating.

**Phase 3 — The closed gate (extraction).**
Now the house simply runs its edge. Every spin is a small, certain transfer
from the crowd to the operator. The gambler's bankroll performs a random
walk with a downward drift, and the mathematics of **Gambler's Ruin**
guarantees the ending: with a finite bankroll and any house edge, continued
play ends in ruin with probability approaching one. The gate is closed. The
herd is harvested.

---

## 3. What is documented vs. what is the model

To keep this honest, separate the verified facts from the illustrative model.

**Documented and verifiable:**
- **RTP is configurable.** Modern server-based and online slots ship with
  multiple certified RTP settings; operators select one within the lab-tested
  range. The same game can legally run at, say, 96% in one market and 88% in
  another.
- **Jurisdictions set very different floors.** US states mandate a *certified
  minimum* RTP — Nevada **75%**, New Jersey **83%** — while actual averages
  run ~92–95%. Mexico's framework sets **no mandated payout floor**, so
  effective RTP can sit at **85% or lower**.
- **Promotions are real +EV loss leaders.** Welcome bonuses, free spins and
  match deposits are acquisition spending; they are designed to be unwound by
  later normal-RTP play.
- **Loss Disguised as a Win is a measured phenomenon** (Dixon, Harrigan et
  al.): multi-line and ways games celebrate sub-stake "wins," so the room
  feels like winning while bankrolls fall.
- **Gambler's Ruin is a theorem**, not an opinion: in a fair game the chance
  of reaching a goal before ruin is exactly bankroll ÷ goal; any edge bends
  that downward, and unbounded play tends to ruin.

**The model / parable (illustration, not a claim about any specific venue):**
- The precise "open at 110%, then secretly drop it once the crowd is locked
  in" sequence is a *teaching model* of the incentive structure, not an
  alleged operating procedure of a named casino. What is true is that every
  ingredient of that sequence — adjustable RTP, promotional looseness, and a
  retained audience — exists and points the same direction. The model shows
  where those incentives lead when followed to their conclusion.

---

## 4. How Spin Lab demonstrates each stage

Spin Lab is a pure-math sandbox (virtual points only) that makes every phase
of the trap visible and runnable.

**The hook (Phase 1).** Set the scoring profile to **player_edge · 105%**
(or imagine a launch at 110%). Play, and run the Gambler's Ruin lab: your
chance of reaching a cash-out goal rises *above* the fair 50% baseline.
This is the "free food" — and it is exactly why the early experience feels
winnable.

**The walls (Phase 2).** Now switch the profile down the ladder the lab
provides — **casino_edge · 95% → tight · 90% → loose market · 85% →
Nevada min · 75%** — while watching the same machine. The reels, sounds and
**LDW counter** barely change in feel. The "Next-Event Heat Bands" prove the
symbol probabilities are identical; only the *payout scale* moved. The walls
went up silently.

**The closed gate (Phase 3).** Open the **Gambler's Ruin Lab**, set a
bankroll and a cash-out goal, and run 1,500 lives. Watch the chance of
cashing out collapse as RTP drops:

| Profile (RTP) | ~P(reach goal, B=50 G=100) | Models |
|---|---|---|
| player_edge · 105% | ~59% | the launch hook |
| fair · 100% | ~47–50% | the theorem's baseline (B/G) |
| casino_edge · 95% | ~34% | a competitive legal machine |
| tight · 90% | ~26% | a stingy but legal machine |
| loose market · 85% | ~16% | an unregulated/loose market |
| Nevada min · 75% | ~5% | the US legal floor |

The fan of trajectories tells the rest: a few green lines climb to the goal,
a growing majority of red lines crash to zero. No line is smarter than
another — they got identical odds. Only variance and the edge decided who
walked out. That red majority *is* the harvested herd.

**Why no strategy is the open gate.** The "Compare Strategies" chart runs
naive (chase losses), advised (minimum stake) and rational (flat stake)
against the *same* outcomes. Stakes differ wildly; the underlying
probabilities never move. There is no betting system inside the fence. The
only winning move is the one the boars forgot existed: **the open field —
not playing, or leaving while ahead.**

---

## 5. The mathematics that closes the gate

Three results, all demonstrated live in the lab, make the ending certain.

1. **Memorylessness.** Each spin is an independent draw. Past results never
   change the next spin's probability (the heat-band "deviation" labels prove
   this). "Due" is a feeling, not a fact. The boar's comfort is not safety.

2. **The house edge compounds.** A 5% edge is not "lose 5% once." It applies
   to *every* stake. Across a session the expected loss is 5% of the *total
   amount wagered*, which for an engaged player is many times their starting
   bankroll. Small per-spin, total over time.

3. **Gambler's Ruin.** With finite money and a negative expected value, the
   probability of eventual ruin approaches 1 the longer play continues. The
   only escape is to stop — to remember the open field before the gate shuts.

Put together: the room is engineered so that leaving feels unnecessary
(Phase 1's memory), staying feels generous (Phase 2's LDWs), and the math
quietly guarantees the outcome (Phase 3's edge). That is the trap, and it is
why "the business is only for the casino."

---

## 6. The one open door

In the parable the farmer leaves a single gate — and closes it. In real life
the gate is never welded shut: the player can walk out any day, while ahead
or at any time, and the field is always there. The entire purpose of Spin
Lab is to make that door visible again — to replace the *feeling* of a
winnable game with the *arithmetic* of a designed one, so the choice to
stay or leave is made with open eyes.

The lab is educational. It uses virtual points and pays nothing. If you or
someone you know is struggling with gambling, the door is real and help
exists — in the US, the National Problem Gambling Helpline: **1-800-522-4700**.

---

## Sources & further reading

- US state minimum RTPs (Nevada 75%, New Jersey 83%): industry summaries of
  state gaming-payout regulation.
- Mexico gaming framework (SEGOB/DGJS; no mandated payout floor; 2023/2025
  reforms): SiGMA regulatory coverage.
- Loss Disguised as a Win: Dixon, Harrigan, et al., gambling-studies
  literature on multi-line slot reinforcement.
- Gambler's Ruin: standard probability theory (absorbing random walk; P(goal)
  = bankroll ÷ goal in the fair case).
- Adjustable / server-based RTP and certification: GLI-11 gaming-device
  standards and operator RTP-configuration practice.
- The wild-boar parable: an old teaching story about incremental capture,
  retold in many forms (commonly cited in discussions of freedom and habit).
