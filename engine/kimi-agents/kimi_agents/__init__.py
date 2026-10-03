"""Kimi agents: small, self-contained agents that find where a firm's text lives.

Each agent is one module with a fixed system prompt (where it uses the model) and a `run` function
that returns rows of the `sources` table (see `sources.py`). The model is Kimi K3 (Moonshot AI) through
`client.kimi_parse`. Scope: firms listed in Hong Kong (incl. mainland China and Macau firms listed
there). Kept outside `pipeline/` for now so the main talk/walk pipeline is untouched.

  reports     annual, interim, quarterly and ESG reports from the HKEXnews archive (no model)
  about_page  the firm's own description of itself on its website (model picks the link)
  news        news articles about the firm and ESG from GDELT (model labels the headlines)
"""

MODEL = "kimi-k3"
