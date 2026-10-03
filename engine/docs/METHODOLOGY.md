# Methodology: the papers behind the ESG Exposure Engine

Every number the product produces traces to published research. This document lists the
concepts we use, the paper each comes from, and the part of the product where it lives —
the E-scoring pipeline, the green factor, or the stock-recommendation engine.

| Paper | Concept | Part of the product |
|---|---|---|
| Pástor, Stambaugh & Taylor (2022, JFE) | Greenness `g`, GMB factor, across/within decomposition | E-scoring; green factor; portfolio exposures |
| Bolton & Kacperczyk (2021, JFE) | Carbon premium: emissions level *and* growth are priced | Walk score; return tests |
| Crosignani, Osambela & Pritsker (2025) | Emission *intensity* as the priced characteristic | Walk score |
| Fama & MacBeth (1973); Newey & West (1987) | Two-pass cross-sectional pricing; HAC standard errors | Return tests; validation tables |
| Fama & French (2015); Carhart (1997) | FF5 + momentum risk model | Risk model; stock recommendations |
| Jegadeesh & Titman (1993) | 12–2 momentum, skipping the most recent month | Local factor construction (Taiwan) |
| Merton (1980) | Sample mean returns are unusable; factor-based `mu` | Stock recommendations |
| Engle, Giglio, Kelly, Lee & Stroebel (2020, RFS) | Climate-news hedging; climate vocabulary similarity | Talk score; news channel |
| Loughran & McDonald (2011, JF) | Finance-specific sentiment dictionary | Talk score (glossiness) |
| Giannetti et al. (2023) | Greenwashing = talk *given* walk; glossy-talk measure | Greenwashing detection |
| Gourier & Mathurin (2025) | LLM prompt discipline; salience | All AI agents (extraction, scoring, screening) |
| Liang, Sun & Teo (2022); Chen (2022, 2025) | Words-vs-actions gap; talk/walk rubric dimensions | Talk/walk scoring; greenwashing detection |
| Berg, Koelbel & Rigobon (2022, RFS) | ESG ratings diverge (56% measurement, 38% scope, 6% weight) | Motivation for the deterministic design |
| Bellon & Boualam | Tilting beats divestment | Stock recommendations (long-only tilt) |

---

## 1. Measurement: talk, walk, greenness

### Greenness à la Pástor–Stambaugh–Taylor (2022, "Dissecting Green Returns", JFE)

**Paper.** PST construct a greenness measure `g = −(10 − E_score)·E_weight/100`, where
E_score (0–10) is the firm's environmental score and E_weight (0–100) is how material the
environmental pillar is for the firm's *industry* (at MSCI, an expert judgment: Exxon ≈ 48,
Best Buy ≈ 11). The weight stops a mediocre oil company and a mediocre retailer from looking
equally green. PST decompose `g` into an across-industry part and a within-industry part —
and find almost all of the green outperformance sits in the across component.

**In the product — the E-scoring step.** Our greenness score implements the formula and the
decomposition directly. Because we have no MSCI license, both inputs are computed from
data: the E_score **is our deterministic walk score** (the firm's emission-intensity
percentile within its industry and year), so one objective number feeds the greenwashing
flag, the greenness score, the green factor and the return tests. The E_weight is the
industry's aggregate emission intensity, percentile-ranked across industries each year —
a data-driven stand-in for MSCI's expert judgment. First Taiwan run: 1,960 companies
scored, from Cement (weight 50) down to Electronic Products Distribution (6).

### Walk from hard data — Bolton & Kacperczyk (2021, JFE) and Crosignani, Osambela & Pritsker (2025)

**Papers.** Bolton–Kacperczyk show that both the *level* and the *growth* of carbon
emissions carry a return premium — so a walk measure must track level and trends.
Crosignani et al. show the priced characteristic is emission *intensity* (tCO2e / revenue),
and model it as a random walk — one-year changes are mostly noise.

**In the product — the walk score.** What a firm demonstrably *does*, measured on registry
and self-reported emissions with audited financials: the headline walk score is the firm's
emission-intensity percentile within industry × year (0–10). The level and growth trends
are computed and reported separately — per Crosignani they are noisy — but never blended
into the headline number, because no paper blends them. Firms without hard data get **no**
walk score rather than a favourable one. Additional pillars (water, waste, renewable
share) follow the same percentile design.

### Greenwashing = talk *given* walk — Giannetti et al. (2023), Liang–Sun–Teo (2022), Chen (2025)

**Papers.** The literature defines greenwashing not as "talks green" but as *talk in excess
of what the firm's actions explain*: Giannetti et al. compare disclosure to lending
behaviour, Liang et al. compare PRI signatories' words to their holdings.

**In the product — greenwashing detection.** Implemented two ways. The gap measure: talk
minus walk on standardized 0–10 scores, normalized within industry and year (Giannetti's
per-year normalization, PST's within-industry demeaning). The excess-talk measure: a
regression of green-claim intensity on emissions level, emissions trend, report length and
industry × year effects — the residual is how much *more* a firm talks than its numbers
justify. Whether excess talk is cheap talk is then tested, not assumed: excess talk
followed by falling emissions is credible signalling; otherwise it is greenwashing. That
predictive test ships with the product's validation output.

### Climate vocabulary and glossy talk — Engle et al. (2020, RFS), Loughran–McDonald (2011, JF)

**Papers.** Engle, Giglio, Kelly, Lee & Stroebel hedge climate-change news using a climate
vocabulary and cosine similarity. Loughran–McDonald built the standard finance sentiment
dictionary (generic dictionaries misclassify financial text).

**In the product — the talk score and news channel.** The deterministic talk side measures
how much and how glossy a firm's climate language is: claim-word intensity from curated
dictionaries, cosine similarity to the Engle et al. climate vocabulary, and a two-step
glossiness measure (climate-relevance gate, then Loughran–McDonald sentiment around
environment terms). The same climate vocabulary drives the news search that feeds the
news-based talk channel.

---

## 2. The green factor and return tests

### The GMB factor — Pástor–Stambaugh–Taylor (2022)

**Paper.** PST build the green-minus-brown factor two ways: sorted portfolios (green
tercile minus brown tercile, value-weighted, monthly) and a cross-sectional regression of
market-adjusted excess returns on `g` (the return of a characteristic-mimicking portfolio).

**In the product — the green factor.** Both constructions are implemented. Our regression
version additionally controls for size, momentum and industry in each monthly
cross-section: the green slope is then the return of a portfolio that is *neutral to those
risk factors* — the isolated green premium, not a sector bet. Market betas use a trailing
60-month window shifted one month back, so nothing looks ahead. Following PST's own
interpretation, we report the realized green outperformance as driven by climate-concern
shocks, while the ex-ante expected premium on green assets is *negative* — green assets
are hedges, and investors accept lower expected returns for them.

### The carbon premium — Fama & MacBeth (1973), Newey & West (1987), Bolton & Kacperczyk (2021)

**Paper.** Fama–MacBeth: run a cross-sectional regression each period, then average the
slope time series; a slope is the return of a zero-cost characteristic-mimicking portfolio.
Newey–West: heteroskedasticity- and autocorrelation-consistent standard errors on that
average. Bolton–Kacperczyk apply it to emissions with the *lagged* specification
(year t−1 emissions, year t returns); contemporaneous monthly specs are biased toward zero.

**In the product — the return tests and validation tables.** The carbon-premium estimator
follows the lagged annual design with Newey–West t-statistics, and every return series
(the green factor, any portfolio) is evaluated against FF5 + momentum with the same HAC
standard errors. These tables are part of the product's output, not an internal check.

### The risk model — Fama & French (2015), Carhart (1997), Jegadeesh & Titman (1993), Merton (1980)

**Papers.** FF5 plus momentum is the standard empirical risk model; momentum is the prior
12–2 month return, skipping the most recent month. Merton (1980): mean returns are
estimated far too noisily to use as optimizer inputs.

**In the product — the risk model behind exposures and recommendations.** Hong Kong stocks
are risk-adjusted with Ken French's published Asia Pacific ex Japan FF5 + momentum series;
for Taiwan, where no published set exists, we construct the factors locally with the same
recipes (value-weighted market, median-split size, 30/70 book-to-market, 12–2 momentum).
Expected returns and the covariance matrix used by the stock-recommendation engine are
always factor-based — never sample averages.

---

## 3. Stock recommendations

- **Green exposures**: each stock's returns are regressed on FF5 + momentum + the green
  factor, giving its `b_gmb` — how it *behaves* when green outperforms. A stock can be
  brown (negative `g`) yet have positive `b_gmb`; the recommendation engine uses the
  greenness characteristic for tilting and the exposure for risk. Positive `b_gmb` means
  the stock hedges climate-concern shocks (PST).
- **Tilt beats divestment** (Bellon–Boualam): the default recommendation is a long-only
  tilt — overweight green, underweight brown relative to the current portfolio.
  Underweighting brown against the benchmark is economically a benchmark-relative short,
  without short-selling frictions. The GMB factor itself remains the long-short
  measurement and hedging instrument.
- **Optimization with a conscience for turnover**: target weights maximize expected return
  minus risk-aversion × variance plus a green-preference term, subject to a linear
  penalty on trading away from the user's current holdings — so no-change is the default
  and every recommended trade must earn its cost. Risk preference (1–5) maps to risk
  aversion, green preference (1–5) to the green term.

---

## 4. How the AI is allowed to touch any of this — Gourier & Mathurin (2025)

**Paper.** Gourier & Mathurin's discipline for LLM text work: the model chooses only from
what is supplied; it must not infer, invent or speculate.

**In the product — every AI agent.** Each model task is scoped, structured and auditable:

- **Emissions extraction**: scope 1/2 figures are read out of HKEX report PDFs with page
  numbers and verbatim quotes, so every number can be traced back to the document.
- **Talk/walk rubric scoring**: a fixed, versioned rubric (0–10 sub-scores following the
  Chen / Giannetti / Liang / Gourier-Mathurin literature), with the firm's hard data passed
  in so the model checks claims against facts. Every call is cached by rubric version,
  model and prompt variant — re-runs are free and comparable.
- **Preference screening**: the investor's free-text preferences are translated into a
  filter choosing only from the universe's *actual* sectors, industries and countries;
  the parsed interpretation is shown before any trade is proposed. The model proposes,
  the code disposes.
- **Two-model design**: Kimi K3 is the primary model, Claude the second rater; the model
  identity is part of every cache key so raters never mix.

The design rule: **AI where judgment is needed, math where it is not.** Downstream of a
score, everything — factors, exposures, optimization — is deterministic and reproducible.

---

## 5. Cross-cutting rigour

- **No look-ahead**: emissions become effective only after an 18-month publication lag;
  all betas are shifted one month back; book-to-market follows the same lag rule as the
  greenness panel.
- **Deterministic first**: the whole universe gets deterministic talk/walk/greenwashing
  scores with no LLM at all; the LLM measures layer on top, versioned and cached.
- **Validation as a product output**: carbon-premium tables, robustness with and without
  super-emitter industries, and the predictive test on excess talk are part of what the
  engine produces — not an afterthought.

## References

- Pástor, Ľ., Stambaugh, R. F., & Taylor, L. A. (2022). Dissecting green returns. *Journal of Financial Economics*.
- Bolton, P., & Kacperczyk, M. (2021). Do investors care about carbon risk? *Journal of Financial Economics*.
- Crosignani, M., Osambela, E., & Pritsker, M. (2025). Working paper on emission intensity pricing.
- Fama, E. F., & MacBeth, J. D. (1973). Risk, return, and equilibrium: Empirical tests. *Journal of Political Economy*.
- Fama, E. F., & French, K. R. (2015). A five-factor asset pricing model. *Journal of Financial Economics*.
- Carhart, M. M. (1997). On persistence in mutual fund performance. *Journal of Finance*.
- Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling losers. *Journal of Finance*.
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*.
- Merton, R. C. (1980). On estimating the expected return on the market. *Journal of Financial Economics*.
- Engle, R. F., Giglio, S., Kelly, B., Lee, H., & Stroebel, J. (2020). Hedging climate change news. *Review of Financial Studies*.
- Loughran, T., & McDonald, B. (2011). When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks. *Journal of Finance*.
- Berg, F., Koelbel, J. F., & Rigobon, R. (2022). Aggregate confusion: The divergence of ESG ratings. *Review of Finance*.
- Giannetti, M., et al. (2023). Working paper on glossy talk vs lending behaviour.
- Gourier, G., & Mathurin, T. (2025). Working paper on LLM-based text classification for sustainable finance.
- Liang, H., Sun, L., & Teo, M. (2022). Working paper on PRI signatories' words vs holdings.
- Chen (2022, 2025). Talk/walk greenwashing measures (see the talk/walk scoring rubric).
