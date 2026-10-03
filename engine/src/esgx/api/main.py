"""FastAPI app serving the measurement layer to the dashboard in `app/frontend`.

Run locally:  make api            (uvicorn on port 8000, reload on)
Frontend:     make web            (Vite on port 8001, proxies /api to 8000)
Docs:         http://localhost:8000/docs

Mirrors the Dentio pattern (FastAPI service + Vite SPA, Makefile-driven, separate ports)
without the parts this project does not need (auth, database, cloud).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from esgx.api.pipeline_routes import router as pipeline_router
from esgx.api.store import DataStore, records

app = FastAPI(title="ESG Exposure Engine API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001", "http://[::1]:8001"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_store = DataStore()
app.include_router(pipeline_router)


def get_store() -> DataStore:
    return _store


Store = Annotated[DataStore, Depends(get_store)]


@app.get("/api/health")
def health(store: Store) -> dict:
    return {"status": "ok", "datasets": store.datasets()}


@app.get("/api/firms")
def firms(store: Store) -> list[dict]:
    return records(store.firms())


@app.get("/api/firms/{firm_id}")
def firm(firm_id: str, store: Store) -> dict:
    firms = store.firms()
    row = firms[firms["firm_id"] == firm_id]
    if row.empty:
        raise HTTPException(404, f"unknown firm {firm_id}")
    em = store.emissions()
    gr = store.greenness()
    tw = store.talkwalk_firm_year()
    docs = store.talkwalk_documents()
    return {
        **records(row)[0],
        "emissions": records(em[em["firm_id"] == firm_id].sort_values("year")) if not em.empty else [],
        "greenness": records(gr[gr["firm_id"] == firm_id].sort_values(["provider", "year"])) if not gr.empty else [],
        "talkwalk": records(tw[tw["firm_id"] == firm_id].sort_values("year")) if not tw.empty else [],
        "documents": records(docs[docs["firm_id"] == firm_id].sort_values("filing_date")) if not docs.empty else [],
    }


@app.get("/api/talkwalk/firm-years")
def talkwalk_firm_years(store: Store) -> list[dict]:
    df = store.talkwalk_firm_year()
    return records(df.sort_values(["firm_id", "year"])) if not df.empty else []


@app.get("/api/talkwalk/documents")
def talkwalk_documents(store: Store, firm_id: str | None = None) -> list[dict]:
    df = store.talkwalk_documents()
    if df.empty:
        return []
    if firm_id:
        df = df[df["firm_id"] == firm_id]
    return records(df.sort_values(["firm_id", "filing_date", "section"]))


@app.get("/api/greenness")
def greenness(
    store: Store,
    year: int | None = None,
    provider: str | None = None,
) -> dict:
    df = store.greenness()
    if df.empty:
        return {"years": [], "providers": [], "year": None, "provider": None, "firms": [], "sectors": []}
    years = sorted(int(y) for y in df["year"].unique())
    providers = sorted(df["provider"].unique())
    year = year or years[-1]
    provider = provider or providers[0]
    sel = df[(df["year"] == year) & (df["provider"] == provider)]
    firms = store.firms()[["firm_id", "name", "sector"]]
    sel = sel.merge(firms, on="firm_id", how="left").sort_values("g")
    sectors = (
        sel.groupby("sector", dropna=True)
        .agg(g=("g", "mean"), g_across=("g_across", "mean"), n=("firm_id", "count"))
        .reset_index()
        .sort_values("g")
    )
    return {
        "years": years,
        "providers": providers,
        "year": year,
        "provider": provider,
        "firms": records(sel, ["firm_id", "name", "sector", "e_score", "e_weight", "g", "g_across", "g_within"]),
        "sectors": records(sectors),
    }


@app.get("/api/gmb")
def gmb(store: Store) -> dict:
    df = store.gmb()
    if df.empty:
        return {"months": [], "summary": {}}
    summary = {}
    for c in ("gmb", "gmb_ew", "gmb_within"):
        if c in df:
            s = df[c].dropna()
            summary[c] = {
                "mean_bps": float(s.mean() * 1e4),
                "t_stat": float(s.mean() / s.std() * (len(s) ** 0.5)) if len(s) > 1 and s.std() > 0 else None,
                "n_months": len(s),
            }
    return {"months": records(df), "summary": summary}


@app.get("/api/emissions/{firm_id}")
def emissions(firm_id: str, store: Store) -> list[dict]:
    em = store.emissions()
    return records(em[em["firm_id"] == firm_id].sort_values("year")) if not em.empty else []


@app.get("/api/search")
def search(store: Store, q: str = Query(min_length=1), limit: int = 20) -> list[dict]:
    firms = store.firms()
    if firms.empty:
        return []
    ql = q.lower()
    hit = firms["firm_id"].str.lower().str.contains(ql, regex=False) | firms["name"].str.lower().str.contains(ql, regex=False)
    return records(firms[hit].head(limit), ["firm_id", "name", "sector", "has_talkwalk", "has_emissions"])
