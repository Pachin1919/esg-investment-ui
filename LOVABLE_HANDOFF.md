# Continue the Green Street UI demo

This is an existing React + TypeScript + Vite frontend. Preserve its functionality when refining the design. The app has two distinct compositions, selectable with the top switch or `?v=blue` / `?v=green`.

The product name is **Green Street**. Keep the front-page slogan exactly as provided: **we make your wallet and the streets green**.

## Design direction

- Clarity blue: white and pale blue, compact portfolio analysis workspace, sidebar, bubble chart, contextual insights, holdings table.
- Sage green: white and pale sage, welcoming investor experience, top navigation, allocation ring, company stories, holdings table.
- Keep the light theme, calm typography, clear data hierarchy and restrained animation. Blue remains the primary candidate for the analytical workspace.
- Visual references: MioTech for environmental language and spacing, Schwab for accessible explanations, Webull for portfolio/table/detail relationships. Do not copy brand assets or claim reference animations were reproduced.

## Preserve these behaviours

Search and sorting; company detail dialog; Escape and focus restoration; independent allocation draft; strict 100% validation; clearing stale comparison after changes; empty/error/loading recovery; downloadable demo JSON; responsive layouts; reduced motion.

All companies and numbers are fictional. Missing score is unavailable, not zero. E_score, E_weight and allocation must remain separate. Carbon/Walk/Talk are illustrative, not a validated computation. The app must not invent expected returns, optimisation, source documents or a full ESG rating.

## Components to change together

`src/App.tsx`: BlueOverview, GreenOverview, HoldingTable, CompanyDetail, Explore, Method.
`src/data.ts`: frontend fixture model and capability flags.
`src/styles.css`: themes, responsive layouts and animation slots.

Do not add authentication, trading, payment, a database, live market integrations or an AI provider as part of visual refinement. Backend response contracts are still unsettled. Keep fixtures isolated and plan a future adapter for actual API data.

Run `npm ci` and `npm run build`. Review both layouts on desktop and mobile. Keep navigation, data and validation working after visual changes.

## Workflow

This local demo has not been imported into or linked with Lovable. For continued work, establish the actual project/repository connection first, then alternate editing between Lovable and Codex. A handoff file alone does not enable GitHub synchronisation.
