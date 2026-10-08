# Green Street
Environmental portfolio analysis for retail investors — a team project.

The sections below document the initial UI prototypes. The repository now also includes the analysis engine and [integrated workspace](https://green-street-272061343685.asia-east2.run.app/app).

## Two interactive UI demos

React + TypeScript + Vite frontend with two distinct layouts:

| Version | Visual direction | Local route |
| --- | --- | --- |
| Clarity blue | White and pale blue; portfolio analysis workspace | `/?v=blue` |
| Sage green | White and pale green; guided investor experience | `/?v=green` |

**Green Street**

> we make your wallet and the streets green

### Run locally

Use Node.js 22.12+ (validated with Node.js 24).

```sh
git clone https://github.com/Pachin1919/green-street.git
cd green-street
npm ci
npm run dev
```

Open <http://127.0.0.1:4319/?v=blue> or <http://127.0.0.1:4319/?v=green>. The top switch changes versions. On Windows, `start-demo.cmd` also starts the local server. Localhost links work only on the computer running the app.

```sh
npm run build
npm run preview
```

### Implemented interactions

- Portfolio search and sorting; company details with keyboard focus restoration.
- Environmental score, industry importance, Carbon / Walk / Talk explanations.
- Independent allocation draft with 100% validation and before/after comparison.
- Empty, loading, partial-data and error states; sample JSON export.
- Responsive layouts and reduced-motion support.

All companies and metrics are fictional. Missing data remains unavailable. Allocation comparisons run locally; no live backend, expected-return forecasts, portfolio optimisation, trading or full ESG rating is provided. The research hypothesis that greenness relates to returns has not been validated by this frontend.

### Previews

**Official workspace**

![Green Street live portfolio workspace](docs/previews/official-workspace.png)

**Official website**

![Green Street official website](docs/previews/official-home.png)

Captured from the deployed application on 8 October 2026. The workspace uses a public sample portfolio; displayed return and volatility figures are model estimates.

### Project structure

```text
src/App.tsx          Two layouts, company detail and allocation flows
src/data.ts         Fictional fixtures and frontend capability definitions
src/styles.css      Colours, typography, responsive layouts and motion
docs/demo-guide.md  Detailed Chinese demo and implementation guide
```

The frontend view model is not a confirmed backend API contract. Keep a future API adapter separate from the UI. This repository is not automatically connected to Lovable.

Validation: TypeScript and production build passed; key interactions checked in a browser; both versions checked at 320, 390, 768 and 1440 px. Dependencies, build output and local browser traces are excluded from Git.
