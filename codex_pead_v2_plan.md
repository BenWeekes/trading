# Codex PEAD V2 Plan

## Summary

The original PEAD baseline is not good enough:

- baseline result over the 2-year monthly sweep: `-764.64`
- trades: `17`
- profitable months: `4`
- losing months: `6`

The best practical replacement found so far is:

- strategy: `quality_eps10_rev1_top2_10d`
- result: `+482.88` on a `$10,000` base over the same 2-year sweep
- trades: `8`
- win rate: `62.5%`
- profitable months: `4`
- losing months: `1`

That is materially better than the old baseline, but still only about `+2.4%/year` before costs. So PEAD V2 is an improvement, not a complete answer, and not strong enough for live deployment.

## Proposed PEAD V2 Rules

- EPS surprise `>= 10%`
- revenue surprise `>= 1%`
- revenue beat required
- regime filter on
- no momentum filter
- max gap `<= 8%`
- enter next trading day after earnings
- take top `2` candidates per scan/cohort
- hold up to `10` trading days
- stop loss `5%`
- target `10%`

Notes:

- `top 2 per scan` is better than `top 2 per month` because earnings cluster around season.
- `1%` revenue surprise is a starting threshold, not settled truth. It should be tested against higher thresholds such as `3%` and, later, scaled by company size if useful.

## What Actually Helped

The improvement came from better event selection:

- stronger EPS surprise
- revenue confirmation
- fewer trades
- faster exits

It did **not** come from deeper AI reasoning yet.

Evidence-based V1 failure pattern:

- V1 produced `18` trades, but only `7` winners and `11` losers.
- Median trade result was `-5%`, which means the typical trade hit the full stop.
- Most losses were not tiny misses. They were post-earnings reversals that stopped out quickly.
- Several losing trades had strong EPS surprise and positive revenue surprise, so revenue confirmation alone does not explain the failures.
- The baseline was too permissive: it allowed many events with similar-looking beats, but continuation was inconsistent.

So the main issue was not just “missing revenue filter.” It was:

- too many acceptable-looking events
- too little selectivity
- too much exposure to gap-and-reverse behavior after earnings

V2 helps by:

- raising the EPS threshold
- requiring revenue confirmation
- cutting the number of trades
- exiting faster

## Literature Signal

The broader research direction is consistent with this plan: PEAD tends to improve when combined with richer post-event information such as transcripts, investor response, and related news flow, not just raw EPS surprise. That supports using AI roles for interpretation and gating on top of a stricter deterministic filter, rather than treating PEAD as a pure surprise rule.

## Role Of AI

AI should help with:

- event ranking
- narrative interpretation
- risk vetoes
- entry/exit discipline
- explainability

AI should **not** be assumed to create alpha by itself.

Best next use of the roles:

- `research`: judge whether the beat is real and durable
- `risk`: veto fragile setups
- `quant_pricing`: define disciplined entry / stop / target
- `trader`: only recommend trades when the other roles align

Role disagreement policy:

- `risk` veto is binding
- `research` downgrade reduces conviction and size, but does not automatically block
- `quant_pricing` must be able to define a coherent plan or the trader should pass

## Data View

FMP is a strong core data source for:

- earnings
- historical prices
- quotes
- company news
- general news
- calendars
- economic indicators

FMP is good enough for research-driven event trading and candidate generation. It is probably not enough for elite low-latency headline trading, which is part of why expensive terminals and richer feeds exist. PEAD V2 should use FMP as the core structured data layer and combine it with AI interpretation and, later, richer sources where justified.

## Product Recommendation

Treat PEAD V2 as:

- one improved event-driven strategy
- one good test case for the multi-role system
- not the whole trading engine

Recommended path:

1. Replace the old PEAD baseline with deterministic `PEAD_V2` for paper trading.
2. Keep exits deterministic first.
3. Add role-guided gating on top of the improved filter.
4. Compare PEAD V2 against other strategies rather than assuming PEAD must become the main edge.

## Implementation Phases

### Phase 1

Make `PEAD_V2` the default PEAD candidate filter in the live system.

Success:

- fewer, higher-quality earnings candidates
- historical proxy still reproduces the better result
- paper-only rollout

### Phase 2

Add role-guided gating:

- research quality check
- risk veto
- quant pricing plan
- trader synthesis
- bounded smarter exits:
  - `research` can flag thesis-broken events
  - `risk` can adjust whether fixed stops are too tight/loose
  - `quant_pricing` can refine stop / target / hold within controlled limits

Success:

- better explanations
- fewer weak recommendations reaching approval

### Phase 3

Run historical replay comparing deterministic PEAD V2 vs role-gated PEAD V2.

Success:

- role-gated version beats deterministic V2 after reasonable assumptions

## Main Risks

- sample size is still small: `8` trades
- the variant may be partly overfit to this sample
- returns still look weak versus current Treasury yields and operating cost
- PEAD may remain too narrow to be a major standalone strategy

Before trusting V2 more broadly, it should clear:

- at least ~`30` trades in research
- robustness checks excluding the top `1-2` winners
- another out-of-sample period

## Review Questions

1. Is `quality_eps10_rev1_top2_10d` strong enough to become the new deterministic PEAD default?
2. Should PEAD V2 stay deterministic first, with roles used only for ranking and veto?
3. Should we require research and risk alignment before trader recommendation?
4. Should PEAD now be treated as one strategy module among several, rather than the core strategy?
5. What benchmark should PEAD V2 need to beat before it is worth deploying?

## Recommendation

- retire the old PEAD baseline
- adopt deterministic `PEAD_V2` for paper trading
- add role-guided gating next
- keep PEAD in the roadmap, but do not rely on it as the sole source of returns
