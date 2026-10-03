"""EU ETS verified emissions (installation level) – placeholder for phase 1.

The EU Transaction Log has no stable JSON API; the practical route is the
bulk CSV export from the European Environment Agency ("EU ETS data viewer")
or the `euets.info` mirror. Both need account/operator → issuer matching similar
to `ghgrp.match_to_universe`. Not implemented in phase 0 (US universe only).
"""

from __future__ import annotations

import pandas as pd


def load_euets(*args, **kwargs) -> pd.DataFrame:
    raise NotImplementedError("EU ETS ingest is scheduled for phase 1 (see brain/PLAN.md).")
