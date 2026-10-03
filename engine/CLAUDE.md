# CLAUDE.md – instruktioner för Claude Code i detta repo

Läs detta först i varje session. Det ersätter inte `README.md` (status, backlog, litteratur) eller
`brain/PLAN.md` (produktplan), men säger hur arbetet ska bedrivas.

## Vad projektet är
ESG Exposure Engine i tre lager: (A) mäta bolags ESG/klimatexponering, (B) modellera hur regleringar,
nyheter och andra chocker sprids till bolag, (C) omsätta det i investeringsstrategier. Allt ska följa
publicerade papper så resultat kan jämföras med litteraturen. Vilket papper varje modul bygger på står i
README:s litteraturkarta; nya moduler ska läggas till där.

**Scope:** primärt bolag i Hongkong, Kina, Taiwan och Macau som påverkar investerare i Hongkong och är exponerade mot
ESG‑faktorer. S&P 500 är referens för replikering, inte mål. Se `brain/scope/Scope – översikt.md`.

## Språk
- Svar till användaren: svenska.
- Kod, kommentarer, docstrings, commit‑meddelanden, `README.md`: engelska.
- `brain/` (inklusive `brain/PLAN.md`): svenska.

## Sessionsprotokoll (Obsidian‑vaulten i `brain/`)
Vaulten är användarens "second brain". Varje session ska lämna spår där, utan att användaren behöver be om det.

**Vid sessionsstart**
1. Kör `date "+%Y-%m-%d %H:%M %Z"` och notera starttiden.
2. Läs `brain/Home.md` och den senaste anteckningen i `brain/sessions/` för att ta upp tråden (öppna frågor, nästa steg).
3. Skapa `brain/sessions/YYYY-MM-DD Session N – kort titel.md` från `brain/templates/Session.md`. N = nästa löpnummer för dagen. Fyll i `date`, `start`, `timezone`, `project`.

**Under sessionen**
- Skriv beslut löpande som `- [beslut] vad och varför`.
- Skriv öppna frågor som `- [ ] fråga` så de blir sökbara tasks.
- Lägg till commit‑hashar i frontmatter `commits` när commits görs.

**Vid sessionsslut** (när användaren avslutar, säger tack/hejdå, eller ber om en sammanfattning)
1. Kör `date` igen och fyll i `end`.
2. Fyll i sammanfattning, tidslinje med klockslag, resultat (tabeller, filer), öppna frågor, nästa steg.
3. Begrepp som använts i mer än en session får en not i rätt del av vaulten (`brain/analys/` eller `brain/teknik/`) med frontmatter `tags`, `source` (papper), `code` (fil). Länka med `[[wikilinks]]`.
4. Uppdatera `brain/Home.md` med länken till sessionen och eventuella nya koncept.
5. Uppdatera statusmatrisen i `README.md` och statusavsnittet i `brain/PLAN.md` om status ändrats.
6. Uppdatera noterna i `brain/teknik/pipeline/` för de pipeline‑delar som ändrats under sessionen.
7. Committa och pusha (`git push`), och spegla sedan vaulten med `make brain-push`. Vaulten ska alltid ligga på GitHub,
   både i projektrepot och i det fristående repot ESG-Investing-Brain.

Om användaren avslutar abrupt utan sluttid: fyll i `end` med tiden för sista tool‑anropet och skriv det i noten.

## Dokumentation (alla md‑filer bor i vaulten)
- All dokumentation skrivs som md‑noter i `brain/`. Inga md‑filer i `docs/`, `pipeline/`, `src/` eller andra kodmappar.
  Undantag: `README.md` och `CLAUDE.md` i roten (GitHub och Claude Code kräver dem där) och genererade rapporter i `outputs/`.
- Vaulten har fyra delar:
  - `brain/scope/` – vad analysen omfattar: Hongkong, Kina, Taiwan och Macau, bolag som påverkar investerare i Hongkong
    och är exponerade mot ESG‑faktorer.
  - `brain/analys/` – hur analysen går till: `greenness/` (objektiva siffror → score), `sentiment/` (ordlistor i
    `sentiment/ordlistor/`, glossiness, talk/walk), `avkastning/` (GMB, robusthet, diffusion).
  - `brain/teknik/` – `kodstruktur/` (var koden bor, datamodell) och `pipeline/` (hur den körs).
  - `brain/sessions/` (sessionsnoter), `brain/templates/`, `brain/PLAN.md` (produktplan).
- `brain/teknik/pipeline/` beskriver hur pipelinen fungerar, en not per del: `Pipeline – översikt.md` (karta), orkestrerare, spec,
  körlägen, API, `agents/Agent <id>.md` (en per agent) och `tools/Tool <modul>.md` (en per tool‑modul).
- Ny eller ändrad agent, tool‑modul eller annan pipeline‑del → skapa eller uppdatera dess not i samma commit (mall
  `brain/templates/Pipeline-del.md`) och länka den från översikten. Noten ska stämma med koden: in, ut, parametrar, tools,
  kända begränsningar som `- [ ]`.
- Ny eller ändrad mätning → not i `brain/analys/` (mall `brain/templates/Analys-del.md`). Ändrad ordlista i
  `text_measures.py` → uppdatera dess not i `brain/analys/sentiment/ordlistor/` (mall `Ordlista.md`) i samma commit.

## Arbetssätt
- **Papper först.** Innan en ny mätning, faktor eller modell implementeras: identifiera vilket papper i
  arkivet (`README.md`, litteraturkartan) som definierar metoden, replikera dess specifikation, och avvik
  först därefter. Skriv källan i modulens docstring.
- **Robusthetsmatris är standard**, inte tillval: nivå vs intensitet, laggad specifikation, med/utan super
  emitters (vår definition: GICS Utilities + Energy; Crosignani m.fl. använder NAICS 2211, Bolton–Kacperczyk olja/gas +
  utilities + transport; ange alltid vilken), VW vs EW, flera providers, matchade vs hela universumet, alfa med och utan
  GMB. Se `brain/analys/avkastning/Robusthetsmatris.md`.
- **Talk och walk rapporteras alltid separat** plus gap. Aldrig ett enda blandat tal.
- **Hårddata är ankare.** Textbaserade mått får aldrig ersätta utsläpps‑ och finansdata, bara komplettera
  (feedback‑effekten: bolag skriver för maskinläsare).
- **Timing.** Utsläpp år t används från juli t+1 (18 månaders lagg). Betas från fönster som slutar t−1.
  Ingen look‑ahead.
- **Datamodell.** Alla tabeller följer `src/esgx/schema.py` och valideras med `schema.validate` vid
  modulgränser. Nya tabeller läggs till där och i `brain/teknik/kodstruktur/Datamodell.md`.
- **Providers.** Alla ESG‑källor exponeras i formen `(firm_id, year, provider, e_score, e_weight)` så
  nedströms kod (greenness, GMB, Fama–MacBeth) är oförändrad.

## Kod och verktyg
- **Små filer.** Varje fil ska vara så liten som möjligt och helst under 200 rader (kod, tester, frontend).
  Växer en fil förbi det: dela upp efter ansvar (en modul per begrepp, en komponent per fil) i stället för
  att lägga till. Gäller nya filer strikt; befintliga filer över gränsen delas när de ändå ändras.
- Python 3.12 i `.venv`, hanterad med `uv`. Installera: `uv pip install --python .venv/bin/python -e ".[dev,api]"`.
- Kör alltid `.venv/bin/pytest -q` och `.venv/bin/ruff check src tests scripts pipeline kimi-agents` innan commit. Båda ska vara gröna.
  Frontend: `cd app/frontend && npm run type-check && npm run lint`.
- **Kimi‑agenter.** `kimi-agents/kimi_agents/` (en modul per agent med fast `SYSTEM_PROMPT`, Kimi K3 via `client.kimi_parse`,
  nyckel `MOONSHOT_API_KEY`). Fristående från `pipeline/` tills vidare. Not: `brain/teknik/Kimi-agenter.md`.
- **Agentisk pipeline.** `pipeline/agents/<id>/` (en mapp per agent: `agent.py` med `AGENT`) och
  `pipeline/tools/` (Python‑funktioner registrerade med `@tool`, kind/cost). En agent får bara de tools som står i
  dess definition. Orkestreraren i `src/esgx/agents/pipeline.py` kör dem i specens ordning. Nya steg = ny agentmapp +
  ev. nya tools, aldrig logik i orkestreraren.
- Lägg tester i `tests/` för varje ny mätning eller faktor, minst ett riktningstest på syntetisk data.
- Rådata, LLM‑cache och outputs är git‑ignorerade (`data/raw/`, `data/processed/`, `outputs/`). Committa aldrig data.
- Tunga nedladdningar körs i bakgrunden med logg till `outputs/ingest_*.log`; ingest‑funktioner cachar till parquet och tar `refresh=True`.
- SEC kräver User‑Agent (`ESGX_SEC_USER_AGENT`) och max 10 anrop/s. EPA Envirofacts pagineras 10 000 rader.

## LLM‑scoring (`src/esgx/measures/talkwalk.py`)
- Primär modell `kimi-k3` (Moonshot, `MOONSHOT_API_KEY`) via `esgx.llm.parse` med pydantic‑schema (structured output,
  strömmat svar). `claude-*` (`ANTHROPIC_API_KEY`) finns kvar som andra bedömare. Poäng från olika modeller blandas aldrig:
  modellnamnet ingår i cache‑nyckeln och sparas i `usage_model`. Se `brain/teknik/pipeline/LLM-leverantörer.md`.
- Källor: `find_reports` (börsarkiv, ingen LLM), `find_about_page` och `find_news` (LLM). Om oss‑sidor och nyheter är
  bara talk och kräver datum; blockerade sajter kringgås inte.
- Systemprompten är fast och versionerad (`RUBRIC_VERSION`). Ändra rubriken → bumpa versionen → cachen
  invalideras avsiktligt. Skriv i sessionsnoten vad som ändrades och varför.
- Promptdisciplin: citera ordagrant, "do not infer, invent or speculate", exkludera riskdiskussion och lobbying,
  Chens implementation‑regel för walk.
- Utan API‑nyckel: `--dry-run` (heuristik, bara för att testa pipelinen). Rapportera aldrig dry‑run‑siffror som resultat.
- Innan större körningar: uppskatta tokens och kostnad, och fråga användaren om körningen kostar mer än ~20 USD.

## Git
- Remote `brain` (github.com/erikjin12345/ESG-Investing-Brain, privat) är en envägsspegel av `brain/` via
  `git subtree push` (`make brain-push`). Redigera alltid noterna i `brain/` här, aldrig direkt i spegelrepot.
- Branch `main`, remote `origin` (github.com/erikjin12345/ESG-Investing-Strategy).
- Committa i logiska steg med beskrivande meddelanden; avsluta med
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Pusha efter varje avslutat steg och alltid vid sessionsslut.

## Kursarkivet
Källmaterialet är `~/Downloads/Archive.zip` (SSE‑kurser: Climate Finance, Behavioral Finance,
Digitalization in Finance). Det ligger inte i repot (upphovsrätt). Vid behov: packa upp till scratchpad,
extrahera text med `pdftotext` och det pptx‑skript som användes i session 1, referera pappren i README.
