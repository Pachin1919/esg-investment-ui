# ESG Investing Strategy – ESG Exposure Engine

A research‑grade toolkit that (A) **quantifies firms' ESG / climate exposure**, (B) **models how
regulations, news and other shocks diffuse to firms**, and (C) **turns that into investment
strategies**. Everything is built to follow published papers so results can be compared with the
literature; the paper each module implements is listed next to it.

Full product plan (Swedish): [`brain/PLAN.md`](brain/PLAN.md). Table contracts: [`brain/teknik/kodstruktur/Datamodell.md`](brain/teknik/kodstruktur/Datamodell.md). All other documentation lives in the Obsidian vault [`brain/`](brain/Home.md): one note per pipeline part under [`brain/teknik/pipeline/`](brain/teknik/pipeline/Pipeline%20–%20översikt.md), plus `scope/` (markets and selection: Hong Kong, China, Taiwan, Macau), `analys/` (how greenness and sentiment are measured, including the global dictionaries) and session notes.

```
 A. Measurement            B. Shocks & diffusion              C. Investing
 ───────────────           ────────────────────               ─────────────
 carbon (GHGRP/SEC)   ──►  shock catalogue                ──► tilt / hedge / long-short
 greenness (PST)      ──►  firm network (supply chain,    ──► factor backtests (FF5+MOM+GMB)
 talk / walk (LLM)    ──►    banks, owners, geography)    ──► Fama–MacBeth robustness matrix
 attention / news     ──►  diffusion models (SIR, cascade,──► scenario ΔV distributions
                             Hawkes, I/O pass-through)
```

---

## Project status

| Area | Status | Where |
|---|---|---|
| Repo scaffold, data model, tests, lint | ✅ done | `src/esgx/schema.py`, `tests/` |
| S&P 500 universe, prices, Ken French factors | ✅ done | `src/esgx/ingest/{universe,prices,factors}.py` |
| SEC XBRL revenue & book equity (2009–) | ✅ done | `src/esgx/ingest/sec_facts.py` |
| EPA GHGRP scope‑1 → parent company → ticker (141/503 firms; 97 % of Utilities, 86 % of Energy) | ✅ done | `src/esgx/ingest/ghgrp.py` |
| Carbon level / intensity / change with 18‑month publication lag | ✅ done | `src/esgx/measures/carbon.py` |
| Greenness `g = −(10 − E)·w/100` with across/within‑industry split, carbon‑intensity proxy provider | ✅ done | `src/esgx/measures/greenness.py` |
| Green‑minus‑brown factor (sorted VW/EW, regression‑based), alphas on FF5+MOM, HML/UMD check | ✅ done | `src/esgx/factors/gmb.py`, `timeseries.py` |
| Carbon premium via lagged Fama–MacBeth, robustness matrix | ✅ done | `src/esgx/factors/famamacbeth.py` |
| EDGAR documents: 10‑K / 10‑Q sections, 8‑K press releases, climate‑passage filter | ✅ done | `src/esgx/ingest/edgar_text.py` |
| LLM talk / walk rubric (structured output, hard‑data cross‑check, cache, dry‑run) | ✅ done, first real run on XOM 10‑K 2022–2025 (talk ≈ 5.3, walk ≈ 1.7) | `src/esgx/measures/talkwalk.py` |
| Greenness from the walk score (`E_score` = walk, `E_weight` = industry aggregate intensity): one objective number for both the greenwashing flag and the return tests; run for 1,960 Taiwan firms | ✅ branch `feature/streaming-ingest` | `src/esgx/measures/greenness.py` (`scores_from_walk`) |
| Deterministic talk / walk / greenwashing without an LLM: walk from registry emissions (intensity level, intensity trend, emission trend), talk from green‑word intensity in the full 10‑K, both as 0–10 percentiles within industry‑year, gap = talk − walk | ✅ code + tests; branch `feature/deterministic-talk-walk` | `src/esgx/measures/{walk_hard,talk_dict,greenwash}.py`, `scripts/score_deterministic.py` |
| Gap variants (within industry‑year z‑gap, residual gap, top‑quintile‑talk × bottom‑tercile‑walk flag) and predictive validation (next‑year GHGRP on walk and talk, Chen 2025 eq. 1) | 🔧 code + tests; needs ≥ 20 scored firm‑years to run | `src/esgx/measures/{standardize,gap,validation}.py`, `scripts/gap_variants.py` |
| Dictionary text measures (keyword share, sentiment window, forward vs realised, vocabulary similarity, glossiness = cosine gate → sentiment) | ✅ done | `src/esgx/measures/text_measures.py` |
| Own greenness score = weighted pillars in provider `(e_score, e_weight)` form | ✅ done | `src/esgx/measures/custom_score.py` |
| **Hong Kong universe** (HSI): constituents, `.HK` prices, Ken French Asia‑Pacific ex Japan factors, yfinance fundamentals | ✅ done | `src/esgx/ingest/{universe_hk,prices,factors,fundamentals_yf}.py` |
| HKEXnews ESG / annual report PDFs with page text | ✅ done | `src/esgx/ingest/hkexnews.py` |
| Scope 1 / 2 extraction from HKEX reports via LLM (page + verbatim quote, assurance flag, confidence) | ✅ done, pilot: 5 firms → 30 firm‑years 2018–2025, ~USD 0.07 per report | `src/esgx/ingest/emissions_hk.py`, `scripts/ingest_hk.py` |
| Climate news index (GDELT), firm betas to climate/policy news | ⏳ next | `src/esgx/factors/` |
| Point‑in‑time universe (survivorship), EU ETS ingest, real E‑score adapters (MSCI/Sustainalytics) | ⏳ planned | `src/esgx/ingest/` |
| Shock catalogue, event studies, firm network, diffusion models, Monte‑Carlo ΔV | ⏳ planned (phase 3) | `src/esgx/{events,network,diffusion,scenario}/` |
| Dashboard: FastAPI API + React/TypeScript/Vite UI (overview, talk/walk, greenness, GMB, firm pages, how-it-works), `make dev` | ✅ done | `src/esgx/api/`, `app/frontend/`, `Makefile` |
| Agentic pipeline: `pipeline/agents/<id>/` (7 agents, allowed tools, READMEs), `pipeline/tools/` (26 tools), orchestrator with dry-run / cache-only / live modes, reviewer agent, designer page with agents catalogue, saved configs, CLI runner | ✅ done | `pipeline/`, `src/esgx/agents/`, `scripts/run_pipeline.py`, `configs/pipeline/` |
| LLM provider layer: Kimi K3 (Moonshot) as primary model, Claude as second rater, one `parse()` for both; source finders for reports (exchange archive), about page and news (GDELT + LLM labelling) | 🔧 built, first live test: reports found for 3 HK firms, about page 1 of 3, news search returns mostly passing mentions | `src/esgx/llm.py`, `src/esgx/ingest/{sources,web_pages,news_gdelt}.py`, `pipeline/agents/find_*`, `scripts/find_sources.py` |
| Portfolio strategies, backtester, scenario builder UI | ⏳ planned (phase 4) | `src/esgx/portfolio/`, `app/` |

First results on free data (`outputs/phase0_report.md`): value‑weighted GMB earned **44 bps/month (t = 2.8)** over 2012‑06–2020‑12 and reversed after 2021; the within‑industry component is insignificant; the carbon premium is insignificant in all four Fama–MacBeth specifications. All three patterns match Pástor–Stambaugh–Taylor (2022) and the mixed carbon‑premium literature.

---

## Quick start

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env   # then fill in ANTHROPIC_API_KEY and ESGX_SEC_USER_AGENT; .env is git-ignored and auto-loaded

# Phase 0: download data (~15 min first time), build greenness + GMB, write outputs/phase0_report.md
.venv/bin/python scripts/phase0_replicate.py

# Talk vs walk on SEC documents – dry run needs no API key, real run uses claude-opus-5
.venv/bin/python scripts/score_talkwalk.py --tickers XOM NEE --start 2023-01-01 --dry-run
.venv/bin/python scripts/score_talkwalk.py --tickers XOM NEE --forms 10-K 8-K --start 2022-01-01   # key from .env

.venv/bin/pytest && .venv/bin/ruff check src tests scripts
```

Outputs land in `outputs/`, processed tables in `data/processed/`, raw downloads and LLM
responses are cached under `data/raw/` (git‑ignored).

### Dashboard (local server)

A read-only FastAPI service over the output tables plus a React / TypeScript / Vite front end,
laid out like the Dentio stack (API on port 8000, web on 8001, Makefile-driven, ports overridable).

```bash
make install     # python deps into .venv (uv) + npm ci in app/frontend
make dev         # API http://localhost:8000 (docs at /docs) + web http://localhost:8001
make api         # or each one separately
make web
make dev PORT=8002 WEB_PORT=8003   # parallel instance
make test && make lint             # pytest + ruff + tsc + eslint
```

Pages: overview (dataset availability, KPIs), talk vs walk (pillars by year, gap, sub-scores,
dictionary measure vs LLM talk scatter, document table), greenness (sector averages, distribution,
brownest / greenest), GMB factor (cumulative and monthly), a firm page (emissions, intensity,
greenness, talk / walk, scored documents), **How it works** (the whole method with the parameters
read live from the code: rubric version, weights, prompt, term lists, formulas, cost model) and
**Pipeline** (see below). The UI computes nothing: it shows what the pipeline wrote. Rebuild the
talk / walk tables without API cost after adding dictionary columns with
`scripts/score_talkwalk.py ... --cache-only`.

### Agentic pipeline

The measurement pipeline is a chain of stages owned by agents defined under
`pipeline/agents/<id>/` (one folder per agent: `agent.py` with the definition,
allowed tools, inputs, outputs and `run`; described in words in [`brain/teknik/pipeline/`](brain/teknik/pipeline/Pipeline%20–%20översikt.md)) using Python tools registered under
`pipeline/tools/` (EDGAR, HKEXnews, EPA GHGRP, SEC XBRL, yfinance, Ken French, dictionary text
measures, LLM calls, local storage; each tagged api / scrape / compute / llm / storage and free /
network / paid). An agent gets a `ToolBox` that only exposes its own tools. Deterministic stages
(collect filings, collect hard data, preprocess, dictionary measures, aggregate) run code; agent
stages (talk / walk scorer, reviewer) are LLM agents with their own model, effort and role prompt.
The orchestrator in `src/esgx/agents/pipeline.py` only sequences them. The role prompt is appended to the versioned base rubric and creates a prompt
*variant* with its own cache key, so the base rubric never changes silently. The **Pipeline** page
lets you enable / disable stages, change agents and weights, estimate cost, run in three modes and
save the spec under `configs/pipeline/`:

- `dry_run`: no API, keyword heuristics (never report these numbers);
- `cache_only`: no API, cached LLM answers only, misses are skipped;
- `live`: real calls, refused without `ANTHROPIC_API_KEY`, confirmation above 20 USD.

Each run writes `documents.csv`, `firm_year.csv`, `memos.json` and `run.json` to
`outputs/pipeline_runs/<run-id>/`; the dashboard's main tables change only when the aggregate stage
has `publish: true`. The same orchestrator runs from the CLI:

```bash
.venv/bin/python scripts/run_pipeline.py --tickers XOM --mode cache_only
.venv/bin/python scripts/run_pipeline.py --config configs/pipeline/strict-scorer.json --tickers XOM NEE --mode live
```

---

## What is left to implement, and which papers to follow

Each item names the paper whose method should be replicated before extending it.

### Layer A – measurement
1. **Real E‑scores as providers.** Adapter for MSCI / Sustainalytics / Refinitiv in the `(e_score, e_weight)` shape; report rating divergence per Berg, Koelbel & Rigobon (2022). Keep the carbon proxy as a robustness provider.
2. **Talk / walk validation** (needs API key). Run on Energy, Utilities, Materials; test that only *walk* predicts next‑year GHGRP emissions (design from Chen 2025 eq. 1; note Chen validates on TRI toxic risk and finds no relation with carbon intensity), that ratings load on *talk* (Chen 2025, Table 7), and normalise talk/walk per industry‑year with quintile/tercile cut‑offs (Giannetti et al. 2023; Liang, Sun & Teo 2022).
3. **Climate news and attention.** WSJ‑style vocabulary index and negative‑news index from GDELT (Engle et al. 2020); Google Trends and local temperature anomalies (Choi, Gao & Jiang 2020); greenwashing salience index (Gourier & Mathurin 2025).
4. **Firm betas** to the climate‑news, policy and greenwashing indices; green factor loadings (Pástor, Stambaugh & Taylor 2021, 2022).
5. **Point‑in‑time universe and EU ETS** installation data for a European universe (Martinsson et al. 2022 for Swedish carbon‑tax firms).

### Layer B – shocks and diffusion
6. **Shock catalogue and event‑study calibration**: Paris 2015 (Bolton & Kacperczyk 2021), Texas SB13/19 (Garrett & Ivanov 2024), California cap‑and‑trade (Ivanov, Kruttli & Watugala 2024), stewardship codes / FTC Green Guides (Liang, Sun & Teo 2022).
7. **Firm network layers**: supply chain via input‑output tables (scope 3), bank lending (Kacperczyk & Peydró 2024), institutional ownership (Bolton & Kacperczyk 2021 divestment channel), geography/politics (Hong & Kostovetsky 2012; Fos, Kempf & Tsoutsoura 2025).
8. **Diffusion models**: SIR on news salience, Hawkes on ESG incidents (Gerasimova & Rohrer 2021 local‑event bias), cascade/threshold for pro/anti‑ESG law adoption across states, Bass diffusion for green technology, input‑output pass‑through for carbon prices and CBAM (Känzig 2023).
9. **Non‑linear responses**: impact elasticity of brown vs green firms (Hartzmark & Shue 2023), tilting vs divestment (Bellon & Boualam 2024), green paradox (Sinn 2008), carbon leakage exemptions (Martinsson et al. 2022).

### Layer C – investing (with ML / AI)
10. **Strategy templates**: tilt, climate‑news hedge portfolio (Engle et al. 2020, mimicking‑portfolio and quantity‑based approaches), scenario long/short, greenwashing short (Liang, Sun & Teo 2022).
11. **Backtester**: alphas with and without GMB, lagged Fama–MacBeth, always with/without super emitters and multiple providers (Crosignani, Osambela & Pritsker 2025).
12. **Machine learning for the investing layer** – follow the Digitalization‑in‑Finance papers:
    - Man + machine: use the LLM as an analyst that is combined with, not substituted for, quantitative signals; evaluate where AI beats humans (structured data, breadth) and where humans keep an edge (soft information, regime changes) – Cao, Jiang, Wang & Yang (2024).
    - Feedback effect: firms rewrite disclosures for machine readers; rotate dictionaries, weight hard data over text, and monitor machine‑readability drift – Cao, Jiang, Yang & Zhang (2023).
    - Data‑driven screening bias: ML trained on history over‑weights firms that look like past winners and under‑funds novel ones; audit our scorer for the same bias – Bonelli (2025); Lyonnet & Stern (2022).
    - Robo‑advice: use the exposure engine to diversify and de‑bias retail portfolios; measure attention and trading effects – D'Acunto, Prabhala & Rossi (2019).
    - Simple models first: logistic/OLS matches complex ML within one asset class, ML wins cross‑asset – course Lecture 5 (Goldstein, Spatt & Ye 2021 on big data in finance).
    - Alternative data as inputs: satellite, job postings (Chen 2025 green‑job postings), news – J.P. Morgan alternative‑data handbook.

### Behavioral‑finance layer (investor and manager behaviour in the models)
13. **Investor reactions to shocks**: prospect‑theory value function and probability weighting for how investors respond to climate losses (Kahneman & Tversky 1979; Tversky & Kahneman 1992); myopic loss aversion to explain flow reactions to short‑horizon ESG underperformance (Benartzi & Thaler 1995; Iqbal, Islam, List & Nguyen 2021).
14. **Time preference and commitment**: hyperbolic discounting for why long‑dated transition risks are under‑priced (Laibson 1997; O'Donoghue & Rabin 1999; Frederick, Loewenstein & O'Donoghue 2002); commitment devices as a model of net‑zero pledges (Bryan, Karlan & Nelson 2010).
15. **Experience effects and overconfidence**: managers and investors who lived through climate disasters update beliefs more (Malmendier & Nagel 2016; Alok, Kumar & Wermers 2020); CEO overconfidence in transition capex (Malmendier & Tate 2005).
16. **Salience and shrouded attributes**: greenwashing as shrouded attributes (Gabaix & Laibson 2006); salience of disasters and local‑event bias (Gerasimova & Rohrer 2021; Choi, Gao & Jiang 2020); mental accounting of "ESG sleeves" (Thaler 1985).
17. **User‑facing de‑biasing**: show distributions and long horizons, not last month (Thaler 2016; Rabin 2000 calibration theorem; Stango & Zinman 2023 for heterogeneity in behavioural traits).

---

## Literature map

Legend: ✅ implemented · 🔧 partly implemented · ⏳ to implement · 📖 conceptual input (shapes design, no code)

### Climate finance
Rows checked against the PDFs in the course archive on 2026-10-03 (session note in `brain/sessions/`).

| Paper | Use in this project | Status |
|---|---|---|
| Pástor, Stambaugh & Taylor (2022) *Dissecting Green Returns*, JFE | Greenness `g = −(10−E_score)·E_weight/100`, VW‑demeaned; GMB = VW top‑third minus bottom‑third `g` (2012‑11–2020‑12); across/within‑industry split; the HML/UMD check uses their greenness‑weighted, beta‑hedged *green factor*, not the sorted GMB; ICC greenium | ✅ (greenness, sorted GMB) · 🔧 green factor · ⏳ ICC |
| Pástor, Stambaugh & Taylor (2021) *Sustainable Investing in Equilibrium*, JFE | Two‑factor pricing (market + ESG factor), `α_n = −(d̄/a)·g_n`, climate‑beta extension; expected vs realised return wedge from taste shocks | 📖 |
| Bolton & Kacperczyk (2021) *Do Investors Care About Carbon Risk?*, JFE | Carbon premium on emission **level and growth, not intensity**; headline specs are pooled OLS with year‑month FE and firm/year clustering (Fama–MacBeth only for the premium series); divestment on scope‑1 intensity in salient industries; the 2005–15 vs 2016–17 split is confounded by Trucost sample growth | ✅ (lagged FM and OLS specs) · ⏳ divestment test |
| Crosignani, Osambela & Pritsker (2025) *Understanding the Pricing of Carbon Emissions*, NY Fed Staff Report | Annual fiscal‑year excess return on one‑year‑lagged intensity in **levels** (tCO2e/$m), year + NAICS‑2 FE, firm clustering; super emitters = **NAICS 2211 electric power only**; winsorisation sensitivity; post‑Paris concentration | ✅ (lagged annual spec) · 🔧 super‑emitter cut (we use Utilities + Energy; see robustness matrix) |
| Hong & Kacperczyk (2009) *The Price of Sin*, JFE | Norm‑constrained institutions underweight sin stocks (−18 % IO, −21 % analyst coverage) → 26–29 bps/month premium (1965–2006), 15–20 % lower M/B | 📖 |
| Krueger, Sautner & Starks (2020) *The Importance of Climate Risks for Institutional Investors*, RFS | Survey of 439 institutions; **source of the physical / regulatory / technological taxonomy**; climate risk ranked 5th overall; 50 % say regulatory risk has already materialised; engagement preferred to divestment | 📖 |
| Engle, Giglio, Kelly, Lee & Stroebel (2020) *Hedging Climate Change News*, RFS | Climate change vocabulary (74 authoritative texts) → daily WSJ tf‑idf cosine index (1984–2017), AR(1) innovations as hedge target; mimicking portfolio on E‑score‑sorted + size/value/market portfolios, OOS corr ≈ 0.2–0.3 | 🔧 (vocabulary cosine; the cosine *gate* in glossiness is our design) · ⏳ index + hedge |
| Hong, Li & Xu (2019) *Climate Risks and Market Efficiency*, J. Econometrics | **Country‑level** food‑industry portfolios (31 countries, 1985–2014) sorted on PDSI drought trends (AR(1) + linear trend, quintiles): Q5−Q1 ≈ 0.56 %/month; cross‑country Fama–MacBeth only as robustness | 📖 (FM engine is ours, not a replication) · ⏳ physical‑risk trends |
| Alok, Kumar & Wermers (2020) *Do Fund Managers Misestimate Climatic Disaster Risk?*, RFS | Salience bias as a **DiD on mutual‑fund holdings**: funds within 100 miles of SHELDUS disasters underweight disaster‑zone stocks by ≈ 0.09 pp for ≈ 4 quarters; reversal strategy earns DGTW alpha | ⏳ |
| Gerasimova & Rohrer (2022) *Not by Whom but Where*, WP | Local‑event bias: analysts whose (surname‑imputed) nationality matches the RepRisk incident country cut recommendations 0.07–0.16 more (pooled DiD, 901 events 2007–2020); "local" is nationality, not office | ⏳ |
| Choi, Gao & Jiang (2020) *Attention to Global Warming*, RFS | City‑level abnormal temperature (10‑year decomposition, 74 exchange cities, 2001–2017) → Google "global warming" attention; emission‑minus‑clean portfolio loses ≈ 48 bps in warmest‑quintile months; retail, not institutional, selling | ⏳ |
| Berg, Koelbel & Rigobon (2022) *Aggregate Confusion*, RF | ESG rating divergence (pairwise correlations 0.38–0.71) → multi‑provider robustness | 📖 · ⏳ adapters |
| Chen (2025) *Green Investors and Green Transition Efforts: Talk the Talk or Walk the Walk?*, WP | **Job‑posting measure, not text**: walk / talk = shares of a firm's Lightcast postings in O*NET green occupations, split by the task rule (occupation is talk‑relevant if < 50 % of its O*NET green tasks are implementation / governance of implementation), with an eco‑context keyword filter. Validation (eq. 1, firm + industry×time FE): walk predicts lower TRI toxic risk (RSEI) and higher Bloomberg disclosure, talk does not; **carbon intensity shows no relation for either**; talk still earns greener MSCI / Sustainalytics / Refinitiv E ratings and more ESG‑fund ownership | 📖 task rule borrowed for the rubric · 🔧 validation regression (branch `feature/gap-variants`, on GHGRP not TRI) · ⏳ job‑posting walk measure |
| Giannetti, Jasova, Loumioti & Mendicino (2023) *Glossy Green Banks*, ECB WP | Bank‑specific environmental keyword dictionary (share of words, stemmed), ±10‑word Loughran–McDonald sentiment around hits, top‑quintile "high environmental reporter" dummy; forward‑looking terms only as a robustness exclusion; **no cosine gate, no segment scoring**; result: high reporters lend 3.6 % more to brown (top‑quintile NACE GHG/VA) borrowers (AnaCredit 2014–2020) | ✅ dictionary + window sentiment · 🔧 glossiness (cosine gate + sentiment) is our combination, not in the paper · ⏳ per‑year normalisation |
| Liang, Sun & Teo (2022) *Greenwashing: Evidence from Hedge Funds*, RF | Greenwasher = PRI‑signatory hedge‑fund firm whose VW Refinitiv ESG of 13F holdings is in the bottom tercile (prior year, 1‑year lag); greenwashers underperform 7.72 %/yr (FH7 alpha); **no text component** — a commitment‑vs‑holdings definition | 🔧 bottom‑tercile cut (branch `feature/gap-variants`) · ⏳ holdings‑based flag · ⏳ short strategy |
| Gibson Brandon, Glossner, Krueger, Matos & Steffen (2022) *Do Responsible Investors Invest Responsibly?*, RF | Firm‑year consensus ESG = mean of within‑year Z‑scores across ASSET4, MSCI IVA, Sustainalytics (available providers); portfolio ESG = VW mean over year‑end FactSet holdings; PRI signatories +12 % s.d., US non‑reporting signatories −26 % s.d. | ⏳ |
| Gourier & Mathurin (2025) *A Greenwashing Index*, WP | Monthly WSJ greenwashing‑salience index (% of articles) from a two‑stage classifier (bag‑of‑words → OpenAI‑embedding SVM/RF/XGB) trained on manual + GPT‑4o‑mini / GPT‑4‑Turbo labels; prompt discipline (quote first, "do not infer, invent or speculate", exclude risk and lobbying); **cosine‑to‑climate‑dictionary only samples articles for manual labelling**, it is not a gate in the index | ✅ prompt rules · ⏳ index · (our cosine gate is our design) |
| Rozhkova (2025) *Effects of Anti‑ESG Legislation: Evidence from the Mutual Fund Industry*, WP | Staggered DiD of state anti‑boycott / anti‑ESG‑investing laws (16 states by 2024) on VW Refinitiv ESG of mutual‑fund holdings (−1.6 % / −3 to −12 %), fossil‑fuel tilt and flows (+1.1 / +2.8 %); demand‑side shock‑catalogue entry | ⏳ shock catalogue |
| Hong & Kostovetsky (2012) *Red and Blue Investing*, JFE | Fund managers' FEC donations predict under‑weighting of tobacco / guns / defense (−1.34 pp) and higher KLD scores; **an investor‑values parameter, not a geography input** | 📖 |
| Garrett & Ivanov (2024) *Gas, Guns, and Governments*, WP | Texas SB 13/19 (Sept 2021) forced exit of five **municipal‑bond** underwriters; triple‑difference on issuer reliance × Texas × post: +10.3 bp offering yield per s.d. of reliance, $300–500 m extra interest; underwriter‑relationship channel, not corporate ESG pricing | ⏳ event study (muni template) |
| Fos, Kempf & Tsoutsoura (2025) *The Political Polarization of Corporate America*, WP | Executive‑team partisan segregation from voter registration (S&P 1500, 2008–2022): dyadic matching +22 %, > 2× post‑2016; misaligned executives 2.6 pp more likely to leave; a **firm‑level attribute**, not a network layer | ⏳ |
| Chinn, Hart & Soroka (2020) *Politicization and Polarization in Climate Change News Content*, Science Communication | Dictionary actor counts (politicians vs scientists) and Wordfish partisan‑language distance in US newspaper climate coverage 1985–2017; political‑salience input to the news index | 📖 |
| Ivanov, Kruttli & Watugala (2024) *Banking on Carbon*, RFS | Cap‑and‑trade (CA 2011, Waxman–Markey 2009) → shorter maturities (−5 to −7 months), term loans → credit lines, +1.7 pp rates; **private firms only**, committed credit unchanged | ⏳ |
| Kacperczyk & Peydró (2024) *Carbon Emissions and the Bank‑Lending Channel*, WP | **SBTi‑committed** banks cut credit to prior high‑scope‑1 borrowers (−6.4 % debt per 1 s.d. log scope 1, extensive margin); borrowers' emissions unchanged, capex −4.3 %, only MSCI E "opportunities" talk rises → direct greenwashing evidence for the talk/walk gap | ⏳ |
| Nguyen, Ongena, Qi & Sila (2022) mortgage SLR premium, RF; Beyene, Falagiarda, Ongena & Scopelliti (2022) diesel car loans, SFI WP; Noth & Schüwer (2023) disasters and bank stability, JEEM | Household / bank channels: +7.5 bps on 30‑year mortgages for 6‑ft sea‑level‑rise exposure (none on 15‑year, weaker in denier areas); captive banks *subsidise* diesel after Dieselgate (−25 bps, +1–2 pp LTV), only low‑emission‑zone shocks raise independent lenders' rates (+12 bps); top‑1 % disaster exposure raises bank PD +0.15–0.29 pp | 📖 |
| Flammer (2021) *Corporate Green Bonds*, JFE; Tang & Zhang (2020) *Do Shareholders Benefit from Green Bonds?*, JCF | Green‑bond issuance as a credible signal: CAR +0.49 % (Flammer) / +1.4 % for first‑time issuers (T&Z), E‑rating up and CO2/assets −13 % (matched DiD), institutional ownership +7.9 %; **no greenium within issuer** in either paper | ⏳ phase 5 (signal, not greenium) |
| Auh, Choi, Deryugina & Park (2022) *Natural Disasters and Municipal Bonds*, WP | Physical‑shock event‑study template: county repeat‑sales bond returns around SHELDUS disasters, matched‑county benchmark; uninsured revenue bonds −51 bps over 20 weeks, zero for insured / GO | ⏳ shock catalogue |
| Baldauf, Garlappi & Yannelis (2020) *Only If You Believe In It*, RFS; Eichholtz, Kok & Quigley (2010) *Green Office Buildings*, AER; Flynn & Ojeda (2023) *Green Listings and House Prices*, WP; Clara, Cocco, Naaraayanan & Sharma (2022) *Investments that Make our Homes Greener*, WP | Real‑asset pricing of beliefs and green attributes: underwater‑home price elasticity to county believer share −0.99; **commercial office** green‑label premium +3 % rent / +16 % price; MLS green‑listing premium +18–28 % (talk‑based, age‑confounded, 5–8 % in denier counties); UK MEES standard raises retrofits but carbon gains ≈ ¼ of efficiency gains (cost‑based label → metric gaming) | 📖 |
| Hartzmark & Sussman (2019) *Do Investors Value Sustainability?*, JF; Bonnefon, Landier, Sastry & Thesmar (2025) *Moral Preferences of Investors*, JFE; Brière & Ramelli (2020) *Personal Values, Responsible Investing and Stock Allocation*, Amundi WP; Brodback, Guenster & Mezger (2019) *Altruism and Egoism in Investment Decisions*, RFE; Barber, Morse & Yasuda (2021) *Impact Investing*, JFE | Preference parameters for flow / demand modelling: rank‑driven fund flows −0.44 % / +0.30 % TNA per month for 1 / 5 globes with no alpha; value‑alignment WTP 0.61 $ per $ of externality, impact weight ≈ 0 (BDM auction); responsible option raises equity allocation +6–7 pp; conjoint weight on responsibility 48 % (survey); institutional WTP 2.5–3.7 ppts IRR for impact | 📖 |
| Martinsson, Sajtos, Strömberg & Thomann (2021) *Carbon Pricing and Firm‑Level CO2 Abatement*, WP | `ln(CO2/sales)` on lagged `ln(marginal carbon price)` with firm and year FE (Sweden 1990–2015): 1 % higher marginal tax → −3.4 % intensity; exemptions for high emitters (leakage) give the cross‑sectional variation | ⏳ shock catalogue |
| Känzig (2023) *The Unequal Economic Consequences of Carbon Pricing*, WP | Daily EUA front‑futures surprises around 114 EU ETS supply announcements (normalised by electricity price) as external instrument in a monthly euro‑area VAR 1999–2019; public shock series | ⏳ |
| Hartzmark & Shue (2024) *Counterproductive Sustainable Investing*, WP | Impact elasticity (Δ scope‑1+2 intensity per Δ cost of capital, Trucost 2002–2020): brown‑quintile firms −8 t/$m per +10 % return and +40–75 t/$m under distress, green firms ≈ 0; divestment from brown backfires | ⏳ scenario non‑linearity |
| De Simone, Naaraayanan & Sachdeva (2024) *Opening the Brown Box*, WP | India CPCB emission‑cap clusters (2009), difference‑in‑discontinuities at CEPI 70/60: coal −29 %, grid power +19.6 pp, abatement capex up, firm entry and product variety down; firm‑response menu for the regulatory shock layer | ⏳ |
| List & Momeni (2021) *When CSR Backfires*, Mgmt Sci | Moral‑licensing field experiment (MTurk, n > 3 000): employer charity raises employee shirking 20 %; behavioural parameter for "talk licenses weak walk", **not an E‑policy spillover** | 📖 |
| Hong & Shore (2023) *Corporate Social Responsibility*, Annu. Rev. Financ. Econ. | Seven‑test taxonomy of pecuniary vs non‑pecuniary CSR motives; greenium‑to‑investment consistency check (median greenium −1.19 % implies far more decarbonisation capex than observed) | 📖 |
| Edmans & Kacperczyk (2022) *Sustainable Finance*, RF; Starks (2023) *Value versus Values*, JF; Hong, Karolyi & Scheinkman (2020) *Climate Finance*, RFS; Stroebel & Wurgler (2021) *What Do You Think About Climate Finance?*, JFE | Framing: three motives for sustainable finance (E&K); value vs values (Starks); six‑theme research programme (HKS); 861‑respondent survey with a **five‑way** risk ranking — regulatory first over 5 years, physical over 30, 20:1 say markets under‑price climate risk (S&W). The three‑way taxonomy belongs to Krueger, Sautner & Starks | 📖 |

### Behavioral finance
| Paper | Planned use | Status |
|---|---|---|
| Kahneman & Tversky (1979) *Prospect Theory*, Econometrica; Tversky & Kahneman (1992) *Advances in Prospect Theory*, JRU | Investor response functions to ESG losses/gains in scenario demand modelling | ⏳ |
| Benartzi & Thaler (1995) *Myopic Loss Aversion and the Equity Premium Puzzle*, QJE; Iqbal, Islam, List & Nguyen (2021) *Myopic Loss Aversion and Investment Decisions: From the Laboratory to the Field*, NBER WP 28730 | Flow reactions to short‑horizon ESG underperformance; evaluation‑horizon parameter in the UI | ⏳ |
| Laibson (1997) *Golden Eggs and Hyperbolic Discounting*, QJE; O'Donoghue & Rabin (1999) *Doing It Now or Later*, AER; Frederick, Loewenstein & O'Donoghue (2002) *Time Discounting and Time Preference*, JEL | Under‑pricing of long‑dated transition risk; discount‑rate scenarios | ⏳ |
| Bryan, Karlan & Nelson (2010) *Commitment Devices*, Annu. Rev. Econ. | Hard vs soft commitments: unvalidated net‑zero pledge = soft, SBTi‑validated target = harder; input to the walk score | 📖 |
| Malmendier & Nagel (2016) *Learning from Inflation Experiences*, QJE | Experience‑weighted belief updating after local disasters | ⏳ |
| Malmendier & Tate (2005) *CEO Overconfidence and Corporate Investment*, JF | Option‑holding / press measures of overconfidence → investment–cash‑flow sensitivity; hypothesised analogue for transition capex and over‑promising (not in the paper) | 📖 |
| Gabaix & Laibson (2006) *Shrouded Attributes*, QJE | Greenwashing as shrouding; who gets fooled (retail vs institutional) | 📖 |
| Thaler (1985) *Mental Accounting and Consumer Choice*, Marketing Sci. | ESG "sleeves" in portfolios | 📖 |
| Barberis (2012) *A Model of Casino Gambling*, Mgmt Sci.; Rabin (2000) *Risk Aversion and Expected‑Utility Theory*, Econometrica | Probability weighting, calibration of small‑stakes risk aversion | 📖 |
| DellaVigna & Malmendier (2006) *Paying Not to Go to the Gym*, AER | Contract choice under naive beliefs (fund‑fee design analogue) | 📖 |
| Rabin (2002) *A Perspective on Psychology and Economics*, EER; Rabin (2013) *Incorporating Limited Rationality into Economics*, JEL; Thaler (2016) *Behavioral Economics: Past, Present, and Future*, AER; Mullainathan & Thaler (2000) *Behavioral Economics*; Gabaix & Laibson (2008) *The Seven Properties of Good Models*, in Caplin & Schotter (eds.), OUP; Stango & Zinman (2023) *We Are All Behavioural, More, or Less*, REStud | Modelling discipline and heterogeneity of biases across users | 📖 |

### Digitalization in finance (ML / AI for the investing layer)
| Paper | Planned use | Status |
|---|---|---|
| Cao, Jiang, Wang & Yang (2024) *From Man vs. Machine to Man + Machine*, JFE | **ML‑ensemble** "AI analyst" (random forest + gradient boosting + LSTM on fundamentals, dictionary and ML sentiment; 3‑year rolling window, t−1 cutoff), not an LLM; AI beats analysts on 54.5 % of forecasts, the hybrid 54.8 % and avoids 90.7 % of analysts' extreme errors; template for scorer‑vs‑human evaluation and for the reviewer agent | ⏳ |
| Cao, Jiang, Yang & Zhang (2023) *How to Talk when a Machine is Listening*, RFS | Feedback effect: firms with high machine readership avoid Loughran–McDonald negative / uncertainty / modal words after 2011 (−9 to −11 bp per s.d. of machine downloads, no change for Harvard lists), BERT‑negative after 2018, and raise format machine‑readability; rationale for not trusting dictionary‑only talk (dictionary rotation and drift monitoring are our design) | 🔧 (LLM over dictionaries) · ⏳ drift monitor |
| Bonelli (2025) *Data‑Driven Investors*, RFS; Lyonnet & Stern (2022) *Venture Capital (Mis)Allocation in the Age of AI*, WP | Opposite findings: data‑driven VCs (first data‑scientist hire) tilt to startups similar to past successes (Bonelli); algorithms de‑bias VC selection (Lyonnet & Stern); audit our scorer for history bias | ⏳ |
| D'Acunto, Prabhala & Rossi (2019) *The Promises and Pitfalls of Robo‑Advising*, RFS | Retail robo‑advice built on the exposure engine | ⏳ phase 5 |
| Babina, Fedyk, He & Hodson (2024) *Artificial Intelligence, Firm Growth, and Product Innovation*, JFE | Firm‑level AI investment primarily from **resumes** (Cognism), job postings (Burning Glass) secondary; skill AI‑relatedness learned from co‑occurrence with ML / NLP / CV, posting threshold 0.1; template for a job‑posting green‑hiring walk measure (Chen 2025) | 📖 |
| Chen, Wu & Yang (2019) *How Valuable Is FinTech Innovation?*, RFS | Patent‑application text filter (487‑term finance glossary) + supervised classifier + anticipation‑adjusted event‑study value; template for a green‑patent walk variable (Y02 tag replaces the classifier) | ⏳ |
| Goldstein, Jiang & Karolyi (2019) *To FinTech and Beyond*, RFS; Goldstein, Spatt & Ye (2021) big data in finance | Framing of big/alternative data | 📖 |
| Jiang, Tang, Xiao & Yao (2025) *Surviving the Fintech Disruption*, JFE (occupational fintech exposure, firm upskilling — framing only); Tang (2019) *Peer‑to‑Peer Lenders Versus Banks*, RFS | Lending‑channel analogue (Tang: P2P substitutes for bank credit to infra‑marginal borrowers, complements for small loans) for the bank network layer | 📖 |
| Otis, Clarke, Delecourt, Holtz & Koning (2025) *The Uneven Impact of Generative AI on Entrepreneurial Performance*, WP | RCT of a GPT‑4 assistant for Kenyan SMEs: heterogeneous effects by baseline performance → report scorer validity by firm size / sector | 📖 |
| Howell, Niessner & Yermack (2020) ICOs; Foley, Karlsen & Putniņš (2019) Bitcoin; Nakamoto (2008) | Out of scope for now | – |

---

## Data sources (all free)

| Data | Source | Module |
|---|---|---|
| Universe | Wikipedia S&P 500 list (current constituents; survivorship bias) | `ingest/universe.py` |
| Prices, shares outstanding | yfinance | `ingest/prices.py` |
| Factors FF5 + MOM | Ken French Data Library | `ingest/factors.py` |
| Revenue, book equity | SEC XBRL companyfacts API | `ingest/sec_facts.py` |
| Scope‑1 emissions | EPA GHGRP Envirofacts API (facilities > 25 kt/yr) | `ingest/ghgrp.py` |
| Filings and press releases | SEC EDGAR submissions + archives | `ingest/edgar_text.py` |
| LLM scoring | Anthropic API (`claude-opus-5`, structured output) | `measures/talkwalk.py` |
| HK universe | Wikipedia Hang Seng Index constituents + yfinance `.info` + HKEXnews stock map | `ingest/universe_hk.py` |
| HK factors | Ken French Asia Pacific ex Japan FF5 + MOM | `ingest/factors.py` (`region=`) |
| Taiwan universe, scope 1 / 2 / 3 with verification flag, renewable share, water, waste, monthly revenue | TWSE OpenAPI (`t187ap03_L`, `t187ap46_L_1`–`L_4`, `t187ap05_L`) | `ingest/twse_esg.py` |
| HK revenue, book equity | yfinance statements, converted to USD millions (HKD peg 7.8) | `ingest/fundamentals_yf.py` |
| HK ESG / annual reports | HKEXnews title‑search API (category "Financial Statements / ESG Information"), PDF → page text | `ingest/hkexnews.py` |
| HK scope 1 / 2 emissions | LLM extraction from the reports (HKEX Appendix C2 KPI A1.2 mandatory since FY2020) | `ingest/emissions_hk.py` |
| Planned | GDELT, Google Trends, NOAA/ECMWF, EU ETS registry, input‑output tables, 13F | – |

## Caveats
- Greenness is currently a proxy from scope‑1 intensity, not a commercial E score; unmatched firms are treated as the cleanest in their sector.
- Universe is today's S&P 500 (survivorship bias) and market caps use yfinance share histories.
- LLM talk/walk scores exist only for a pilot (XOM); dry‑run numbers are keyword heuristics for pipeline testing only.
- Hong Kong emissions come from LLM extraction of PDF reports, not a registry: each figure carries page, quote and a confidence; treat low‑confidence rows as missing. Coverage starts FY2020 (mandatory KPI A1.2).
