# How Professional Gaming Machines Really Work
### A teaching companion to Spin Lab — what's behind the real glass

Spin Lab mirrors the real architecture: an outcome decided server-side by
an RNG + math model, then merely *presented* on a canvas. This note
explains how the commercial industry actually builds and certifies that —
so students can see that our lab is a faithful (virtual, harm-free) model
of the genuine thing.

---

## 1. The RNG never sleeps

Real machines run a **pseudo-random number generator (PRNG)** —
overwhelmingly the **Mersenne Twister (MT19937)**, period 2^19937−1 —
seeded from a hardware entropy source (thermal/electrical noise). The
critical fact: it is **free-running**. It cycles thousands of values per
second even when the machine sits idle (Nevada historically required
~100 cycles/sec for unpredictability). When you press Spin, the machine
grabs whatever value the generator holds *at that millisecond*. A fraction
of a second earlier or later = a completely different result. You are not
"timing" anything — that is the whole design.

**Spin Lab parallel:** our `engine/rng.py` is a seedable PRNG; the spin's
outcome is fixed the instant the API is called, before any animation.

## 2. Virtual reels — the trick that hides the odds

The reels you see (≈22 physical stops) are a **presentation layer**. The
real probabilities live in a **virtual reel / weighting table** (Telnaes
patent, 1984 — the foundation of the modern industry). The PRNG output is
mapped through a big lookup table: a jackpot symbol might occupy 1 of 256
virtual stops while looking identical on the strip. Cheap symbols get many
virtual stops, rare ones get few. The visible reel can't betray the odds.

**Spin Lab parallel:** our strip + window model and weighted reel counts
do exactly this; the heat-band table even *exposes* the hidden true
probability the real machine hides.

## 3. Who decides the outcome — the legal fork

| Model | Where the outcome is decided | Each spin independent? |
|---|---|---|
| **Class III** (Vegas/NJ) | inside the machine's RNG | yes |
| **Class II** (tribal bingo) | a central **bingo** server; reels just *act out* a bingo result | no — shared draw |
| **Central determination / VLT** | a finite **pool** of pre-made outcomes (like scratch tickets) | no — drawn from a pool |
| **Online (RGS)** | the provider's **remote server** | yes |

This distinction is the most important thing students rarely know: a
machine that *looks* like a slot may legally be a **bingo terminal** (Class
II) whose spinning reels are pure theatre translating a bingo pull — that's
how slot-looking machines appear on tribal floors without a state compact.
A VLT may draw from a finite pool, so its payout is *mathematically exact*,
not just a long-run average.

## 4. Inside the box: trusted vs non-trusted code

Historically the game lived on an **EPROM chip** with a CRC signature;
changing a game meant physically swapping the chip, and regulators could
verify the CRC at any time. Modern machines are hardened industrial PCs
running **signed game packages**, split into:

- **Trusted / critical** (full certification): RNG, math engine, pay
  tables, reel-strip weighting, financial meters.
- **Non-trusted** (skin only): art, audio, UI. Can change without full
  re-certification.

Every build carries a **SHA-256 hash**; the running code is checked against
the lab-approved hash, and a single changed bit fails the integrity check.

**Spin Lab parallel:** our **pure engine** (the math, fully unit-tested) is
the "trusted" layer; the **canvas/CSS** is the "non-trusted" skin — exactly
the same separation.

## 5. The par sheet → certified binary pipeline

Every game starts as a confidential **par sheet**: virtual stops per reel,
symbol map, pay table, hit frequencies, theoretical RTP, volatility index.
From it the math model, reel strips and the certified binary are built.
Casinos generally never see par sheets — only regulators and test labs do.

**Spin Lab parallel:** our `analytic_rtp()` + Monte-Carlo calibration *is*
a par-sheet calculation, and the Video Slot Theme DocType is an editable,
visible par sheet.

## 6. Server-based floors & remote RTP changes

On modern floors, certified game packages (and **pre-certified RTP
settings** like 88% / 92% / 95%) can be **downloaded remotely** to
cabinets. An operator can switch a machine's RTP — but only among
**already-certified options**, and every change is logged with a timestamp
to the Casino Management System. No compliant system lets an operator type
in an arbitrary RTP.

**Spin Lab parallel:** the Scoring Profile DocType + RTP dropdown is this
exact idea — pick a certified configuration; the whole game rescales.

## 7. How the machine talks to the casino

- **SAS (Slot Accounting System)** — IGT's serial protocol (19.2 kbps),
  the universal standard; the casino host polls each machine for coin-in,
  coin-out, jackpots, door events. SAS also runs **TITO** (ticket-in /
  ticket-out) — the barcoded slips that replaced coins.
- **G2S (Game to System)** — the modern TCP/IP successor: bidirectional,
  100 Mbps, multi-host, supports downloadable games, cashless wallets and
  responsible-gaming limits.

All of it feeds the **Casino Management System**: real-time floor
monitoring, theoretical-vs-actual hold, player tracking, progressive
management, regulatory reporting.

## 8. Certification — who proves it's fair

Before a machine runs, an **independent test lab** (GLI, BMM, iTech Labs)
reviews it against standards: **GLI-11** (land-based devices), **GLI-19**
(online), **GLI-21** (client-server). They:

- read the **source code** of the RNG, mapping function, pay tables, meters;
- run the RNG through statistical batteries — **NIST SP 800-22** and
  **Diehard** (monobit, runs, spectral, entropy, etc.) at ~99% confidence;
- verify RTP by reviewing the pay table against the strips **and** by
  **simulating billions of spins** to confirm convergence;
- check minimum-RTP floors per jurisdiction;
- **field-audit**: pull a machine, read its firmware hash, compare to the
  approved hash — any mismatch = immediate suspension.

**Spin Lab parallel:** our 54 unit tests are a miniature of this — chi-square
RNG uniformity, RTP convergence, math correctness — run offline against the
pure engine.

## 9. Online slots: the browser is just a screen

In every regulated online slot, **the outcome is decided on the server
before any reel moves.** The browser cannot be trusted (the player controls
it), so the HTML5 client only sends "spin" and animates whatever the
**Remote Gaming Server (RGS)** returns. The 2–4 seconds of spinning is
deliberate suspense over an already-fixed result.

The supply chain splits three ways: the **provider/studio** (NetEnt,
Pragmatic…) builds and hosts the game math on its RGS; the **aggregator**
wires many providers to many operators and moves the wallet; the
**operator** (the brand you see) holds the license, manages accounts and
picks which certified RTP to offer — and never touches game logic.

A single online spin:
press Spin → HTTPS to RGS → RGS validates session & debits wallet → RGS
RNG fixes the reel stops → pay table → credit wallet → immutable log →
result returned → **browser animates the predetermined stops.**

**Spin Lab parallel:** this is *precisely* our architecture — `frappe.call`
→ whitelisted API → pure engine fixes the outcome → JSON back → canvas
animates. We built, in miniature, a real RGS.

---

## The one-sentence takeaway for students

A modern slot — physical or online — is **a certified math model behind a
cosmetic animation**: an RNG fixes the result the instant you commit, a
weighting table hides the true odds, independent labs verify the payout,
and the spinning you watch is theatre over a decision already made. Spin
Lab is the same machine with the curtain removed.

---

## Sources
GLI standards (GLI-11/19/21) — gaminglabs.com · Telnaes virtual-reel patent
US 4,448,419 · Class II vs III (IGRA / NIGC) · Server-Based Gaming
(Wikipedia; Nevada GCB; GLI-21) · SAS & G2S protocol references (CDC
Gaming; Gaming Standards Association) · NIST SP 800-22 & Diehard RNG test
suites · Remote Gaming Server architecture guides (CrustLab; Reelsoft).
Full URL list in the research thread.
