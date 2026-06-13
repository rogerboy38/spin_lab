# The Betting-System Debunker — research & feature notes

A new teaching tool on the roulette page (**🧪 Systems Lab** button). It runs thousands
of simulated sessions on the real wheel and shows, live, that no staking system beats a
negative-expectation game. This note records the research behind it.

## The one fact everything rests on

Every spin is independent — the ball has no memory. On an even-money bet:

- **European (single zero):** win 18/37 ≈ 48.65%, house edge **1/37 = 2.70%**
- **American (00):** win 18/38 ≈ 47.37%, house edge **2/38 = 5.26%**

Because outcomes are independent, the expected value of a *sequence* of bets is just the
sum of the expected value of each bet (linearity of expectation). Every unit wagered
returns −2.70% (EU) or −5.26% (US) **no matter how you size or sequence the bets**. A
progression is just a weighted sum of negative numbers — still negative. Billingsley,
*Probability and Measure*: "No betting system can convert a subfair game into a profitable
enterprise."

## The systems, and why each fails

- **Martingale** — double after every loss, reset on a win. A win recovers the run +1
  unit, but stakes blow up geometrically (1,2,4,8,16…), so a finite bankroll and the table
  maximum cap the recovery. A 63-unit bankroll busts after 6 straight losses.
- **Grand Martingale** — double *and add a unit*; bigger wins, faster ruin.
- **D'Alembert** — +1 unit after a loss, −1 after a win; assumes wins and losses "balance,"
  which is the gambler's fallacy — losses are actually more frequent.
- **Fibonacci** — stakes follow 1,1,2,3,5,8…; slower escalation, same negative-progression
  flaw.
- **Labouchère** — cross off two numbers on a win, append one on a loss; a losing run
  lengthens the list and inflates the stake without bound.
- **Paroli** (reverse Martingale) — double after *wins* for a 3-win streak; can't exploit
  "hot hands" because spins are independent. Many small losses, rare modest wins.

## What the simulator demonstrates

For each system it reports, over thousands of sessions: % that ended up, % busted (ruin),
% down-but-alive, average turnover, and the punchline —

> **expected loss = house edge × total wagered ≈ actual average loss.**

Verified (American wheel, base 5, bankroll 500, 100 spins/session, 40k sessions):

| System | ended up | busted | turnover | edge×turnover | actual loss |
|---|---|---|---|---|---|
| Flat | 26% | 0% | 500 | 26.3 | 26.7 |
| Martingale | 44% | 56% | 1149 | 60.5 | 62.4 |
| D'Alembert | 45% | 39% | 2358 | 124 | 126 |
| Fibonacci | 68% | 28% | 1116 | 59 | 59 |
| Labouchère | 25% | 74% | 2987 | 157 | 158 |
| Paroli | 30% | 0% | 834 | 44 | 44 |

The ratio actual/expected ≈ 1.00 every time. Notice the trap: Martingale and Fibonacci
*usually* show a profit — which is exactly why they feel like they work — but the rare red
crashes erase all the small wins and more. Bet sizing changes only the **shape of the risk
(volatility)**, never the average. Table limits + a finite bankroll turn Martingale's
"guaranteed win" into guaranteed eventual ruin.

## Why this framing (the research)

The most evidence-backed anti-gambling interventions are "unmask the trick" devices:
Dixon/Harrigan's work on Losses Disguised as Wins (a short explanatory animation measurably
corrected players' win-overestimates, *International Gambling Studies* 2017), and
gambler's-ruin / strategy-debunk Monte-Carlo demos. Reality-check and limit-setting prompts
help but modestly. So rather than lecture, the Systems Lab lets the student run the "system"
themselves and watch the math win — the same approach the literature supports.

## Selected sources

- Wikipedia — Martingale (betting system); Labouchère system
- Wizard of Odds — "The Truth about Betting Systems" (1B+ trial simulations converge to the edge)
- Billingsley, *Probability and Measure*; Epstein, *The Theory of Gambling and Statistical Logic*
- Dixon, Harrigan et al. 2010 (LDW arousal); Graydon/Dixon 2017 (educational animation)
- Schüll, *Addiction by Design* (time-on-device)
