import { useMethod, usePipelineDefault } from '@/core/queries';
import { Card, ErrorBox, Loading } from '@/shared/ui';
import { LayerDiagram } from './LayerDiagram';
import { Steps } from './Steps';
import { Chips, Collapsible } from './Collapsible';

export function MethodPage() {
  const m = useMethod();
  const p = usePipelineDefault();
  if (m.isError) return <ErrorBox error={m.error} />;
  if (m.isLoading || p.isLoading || !m.data || !p.data) return <Loading />;
  const d = m.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">How it works</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink2">
          The engine has three layers: measure firms' climate exposure, model how shocks diffuse to
          firms, and turn that into strategies. What runs today is the measurement layer. Every
          number below is read from the code, not typed into this page: rubric version{' '}
          <code>{d.rubric_version}</code>, model <code>{d.model}</code>.
        </p>
      </div>
      <Card title="Three layers" subtitle="Layer A is built; B and C are planned (see README)">
        <LayerDiagram />
      </Card>
      <Steps stages={p.data.stages} d={d} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card
          title="The scorer's system prompt"
          subtitle={`Fixed and versioned (${d.rubric_version}). Changing it bumps the version and invalidates the cache on purpose.`}
        >
          <Collapsible label="Show prompt">
            <pre className="whitespace-pre-wrap rounded-md bg-page p-3 text-xs leading-relaxed text-ink2">
              {d.system_prompt}
            </pre>
          </Collapsible>
          <p className="mt-2 text-xs text-ink2">
            Every call also receives a HARD DATA block (GHGRP scope 1 for the last four years,
            revenue, scope-1 change) so claims are checked against facts. Output is forced into a
            schema: eleven 0–10 sub-scores, up to ten commitments, quotes, a two-sentence summary.
            Each response is cached on filing, section, rubric version, model and prompt variant.
          </p>
        </Card>
        <Card title="Cost model" subtitle={d.cost.basis}>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-ink2">Per scored section</dt>
            <dd className="tabular">{d.cost.usd_per_section.toFixed(2)} USD</dd>
            <dt className="text-ink2">Per reviewer memo</dt>
            <dd className="tabular">{d.cost.usd_per_review.toFixed(2)} USD</dd>
            <dt className="text-ink2">Sections per 10-K</dt>
            <dd className="tabular">3–4</dd>
            <dt className="text-ink2">One firm, four years of 10-K</dt>
            <dd className="tabular">
              ≈ {(d.cost.usd_per_section * 12 + d.cost.usd_per_review * 4).toFixed(2)} USD
            </dd>
          </dl>
          <p className="mt-3 text-xs text-ink2">
            Runs above 20 USD ask for confirmation. Dry-run and cache-only modes cost nothing.
            Dry-run numbers are never reported as results.
          </p>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Greenness and the GMB factor" subtitle="Pástor, Stambaugh & Taylor (2022)">
          <p className="font-mono text-sm">{d.greenness.formula}</p>
          <ul className="mt-2 space-y-1 text-sm text-ink2">
            <li>
              <b className="text-ink">E score</b>: {d.greenness.e_score}.
            </li>
            <li>
              <b className="text-ink">E weight</b>: {d.greenness.e_weight} (range{' '}
              {d.greenness.e_weight_range.join('–')}).
            </li>
            <li>
              <b className="text-ink">Timing</b>: emissions of year t are used from July t+1 (
              {d.sample.emissions_lag_months}-month lag). Sample {d.sample.start_year}–
              {d.sample.end_year}.
            </li>
            <li>
              <b className="text-ink">GMB sorted</b>: {d.gmb.sorted}.
            </li>
            <li>
              <b className="text-ink">GMB regression</b>: {d.gmb.regression}.
            </li>
            <li>
              <b className="text-ink">Own score</b>: pillars combined as{' '}
              {Object.entries(d.custom_score_weights)
                .map(([k, v]) => `${k} ${v}`)
                .join(', ')}
              ; gap enters negatively.
            </li>
          </ul>
        </Card>
        <Card
          title="Dictionary measures"
          subtitle="No API. Complement, never replace, the hard data (feedback effect: firms write for machine readers)"
        >
          <ul className="space-y-1 text-sm text-ink2">
            <li>
              <b className="text-ink">Keyword share</b>: environment terms / non-stopwords,
              non-directional list (Giannetti et al.).
            </li>
            <li>
              <b className="text-ink">Sentiment</b>: Loughran–McDonald net sentiment in ±10 words
              around each environment term.
            </li>
            <li>
              <b className="text-ink">Forward vs realised</b>: share of hits near forward-looking
              terms vs near realised-action terms.
            </li>
            <li>
              <b className="text-ink">Climate similarity</b>: cosine similarity to the climate
              vocabulary (Engle et al.).
            </li>
            <li>
              <b className="text-ink">Glossiness</b>: cosine gate → sentiment on the retained
              segments; climate share × positive tone. A talk measure only.
            </li>
          </ul>
          <Collapsible label={`Environment terms (${d.env_terms.length})`}>
            <Chips items={d.env_terms} />
          </Collapsible>
          <Collapsible label={`Forward-looking terms (${d.forward_terms.length})`}>
            <Chips items={d.forward_terms} />
          </Collapsible>
          <Collapsible label={`Realised-action terms (${d.realised_terms.length})`}>
            <Chips items={d.realised_terms} />
          </Collapsible>
          <Collapsible label={`Climate passage filter terms (${d.climate_terms.length})`}>
            <Chips items={d.climate_terms} />
          </Collapsible>
        </Card>
      </div>

      <Card title="Rules that never change" subtitle="From CLAUDE.md and the literature">
        <ul className="grid gap-2 text-sm text-ink2 md:grid-cols-2">
          <li>
            <b className="text-ink">Talk and walk are reported separately</b>, plus the gap. Never
            one blended number.
          </li>
          <li>
            <b className="text-ink">Hard data is the anchor.</b> Text measures complement emissions
            and financials, never replace them.
          </li>
          <li>
            <b className="text-ink">No look-ahead.</b> Emissions of year t from July t+1; betas from
            windows ending t−1.
          </li>
          <li>
            <b className="text-ink">Paper first.</b> Each module replicates a published
            specification before deviating.
          </li>
          <li>
            <b className="text-ink">Robustness matrix is standard</b>: level vs intensity,
            with/without super-emitters, VW vs EW, several providers.
          </li>
          <li>
            <b className="text-ink">Providers share one shape</b>: (firm, year, provider, e_score,
            e_weight), so downstream code never changes.
          </li>
        </ul>
      </Card>
    </div>
  );
}
