# Research Report: Accumulative / Persistent-State Win Mechanics

**Gap analysis for Spin Lab** — what the lab does NOT yet simulate, why it
matters, and the exact math to implement it. (Deep-research synthesis,
June 2026. Sources at bottom.)

## The gap

Every mechanic in Spin Lab today — classic reels, 4096 ways, Megaways,
expanding/sticky/walking wilds, both-ways, free spins — is **memoryless
between paid spins**: RTP is a single number, every spin is a fresh draw.
Real machines also use **persistent-state ("accumulative") mechanics**
where value builds across spins, making RTP a *function of machine state*:
`RTP(state)`, not `RTP`.

This is the one lesson the lab cannot currently teach — and it is a big
one, because it is where *advantage play* lives and where the distinction
between real and illusory "due-ness" becomes precise.

## 1. Progressive jackpots (the canonical accumulative win)

Every bet B feeds a shared meter: `meter += c * B` (c ~ 1-3.5%). The meter
seeds at S after each hit. Player EV per unit bet at meter level J:

    RTP(J) = f + p * J / B          (f = fixed-win return, p = hit prob.)

Break-even meter level:  J* = B * (1 - f) / p

Worked example (Wizard of Odds, IGT Megabucks): f = 78.44%,
p = 1/49,836,032, B = $3 → J* ≈ $32.2M nominal (≈ $75.5M after
annuity + tax). Published RTP quotes the AVERAGE hit level — so a
progressive above its average meter is strictly better than its sticker
RTP, and the hit probability NEVER changes with the meter (Class III:
the meter being high does not make the jackpot "due"; it only makes it
bigger). That is the educational crown jewel here.

Regulator-style decomposition (Megabucks): fixed wins 78.44% + seed 6.69%
+ meter 3.49% = 88.62% RTP; the jackpot pool is paid for by a REDUCTION
in base-game pays — "the jackpot is not on top of the game."

Must-hit-by variant: trigger drawn uniform in [seed, max]; EV rises
monotonically toward `max`; break-even target points:
short-term `j = m(1-f)/(1-f+r)`, long-term `j = m(1-f-r)/(1-f+r)`.

## 2. Accumulating multipliers (bonus-scoped state)

- Gates of Olympus model: multiplier orbs ADD to a global multiplier that
  never resets during free spins: `M += sum(orbs)`; wins pay `win * M`.
- BTG model: `M += 1` per cascade reaction, unbounded.
- Without a max-win cap the feature EV diverges (fat tail); the industry
  cap (5,000x-100,000x) truncates the distribution: `win = min(win, cap*bet)`.
  Educational demo: sweep the cap and watch simulated RTP climb — high
  RTP can be mostly a microscopic probability of an enormous win.

## 3. Collection / banked-state machines (true machine memory)

Piggy Bankin' (WMS) archetype: 510 virtual coins, one "lucky coin"; play
deposits coins; probability of bonus per qualifying spin = k/N_remaining.
RTP(N) rises without bound as N falls — Lund (1999) put break-even around
40 coins remaining. The same physical machine is a bad bet freshly reset
and a +EV bet late. This is the basis of the slot advantage-play
literature: the posted RTP is the average over states; an AP player
cherry-picks high states. A "near miss" on a collection meter is REAL
information (next qualifying spin will trigger), unlike a symbol
near-miss, which is pure display.

## 4. Hold-and-spin / cash pots (Lightning Link)

6+ coins trigger; coins lock; 3-respin counter resets on every new coin.
Absorbing Markov chain over states (filled k, counter r), N=15 positions:

    from (k, r):  P(no coin) = q^(N-k)  -> (k, r-1);  (k, 0) absorbing
                  P(j coins) = C(N-k, j) p^j q^(N-k-j) -> (k+j, 3)

Expected collection solved exactly via the fundamental matrix (45
transient states) or the lru_cache recursion in the research notes. The
counter reset creates superlinear EV growth in locked coins — the
mathematical reason the feature "feels" like momentum.

## 5. What this teaches that memoryless mechanics cannot

1. RTP as a function of state, not a constant.
2. Advantage play: simulate (a) always-play vs (b) play-only-above-threshold
   on a banked machine — long-run outcomes differ dramatically.
3. Class III progressives are never "due" — meters raise the prize, not the
   probability. (Contrast with banked state, where due-ness is real.)
4. Jackpot contribution comes out of base pays (RTP decomposition).
5. Max-win caps: truncation of fat tails, and what "96% RTP" means when a
   chunk of it is a 1-in-millions event.

## Implementation roadmap for Spin Lab

| Priority | Mechanic | State scope | New pieces |
|---|---|---|---|
| 1 | Progressive meter | machine-level, persists | `Progressive Meter` DocType (value, seed, c, p); contribution on every video_spin; RTP(J) readout + break-even line on page |
| 2 | Must-hit-by meter | machine-level | trigger threshold redraw on reset; EV-vs-meter chart |
| 3 | Hold-and-spin | within-feature | coin grid + respin counter; exact Markov EV in tests |
| 4 | Accumulating FS multiplier | within-bonus | `M += orbs` in free spins; max-win cap slider |
| 5 | Banked collection meter | machine-level | coins_remaining per theme; RTP(N) table; AP threshold demo |

Frappe fits the machine-level state naturally: a `Progressive Meter` /
`Machine State` DocType is shared by all players of a site — exactly like
a real linked progressive.

## Sources

Wizard of Odds: Megabucks analysis; Mystery (must-hit-by) jackpots;
progressive strategy. Wizard of Vegas: break-even threads. Know Your
Slots: Piggy Bankin' AP; Lightning Link mechanics (Aristocrat-confirmed).
Lund, *Robbing the One-Armed Bandits* (1999). Galaxy of Slots / Flush:
Gates of Olympus multiplier rules. Michigan Admin Code R 432.1841 (WAP
regulation). Wikipedia/Brilliant: absorbing Markov chains.
