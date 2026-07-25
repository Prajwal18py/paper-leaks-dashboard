# India Exam Paper Leaks — Dashboard

An interactive EDA dashboard on documented Indian exam/question-paper leak incidents (2004–2026), built entirely with **Python (pandas)** for the analysis and vanilla **HTML/CSS/JS + Chart.js** for the front end — no frameworks, no build step.

**[Live demo →](#)** *(https://paper-leaks-dashboard-nu.vercel.app/)*


<img width="1887" height="1078" alt="Image" src="https://github.com/user-attachments/assets/35850173-080f-4f96-bcaf-ecbe8ad9350f" />

<img width="1891" height="1078" alt="Image" src="https://github.com/user-attachments/assets/6c7568aa-9a81-4d02-9257-2c1c922ce9a6" />

<img width="1905" height="1078" alt="Image" src="https://github.com/user-attachments/assets/433a32a1-55b2-4a42-b728-470b11b2f119" />

---

## What's in it

- **Interactive chart** — group incidents by Period, State, Body Type, Exam Type, Year, or Leak Status, with combinable filter chips (Period / Body Type / Leak Status / Confidence) and a live "Showing X of Y" counter
- **Table view** — same data as proportional inline bar-charts in a sortable table, with totals
- **Choropleth map of India** — incidents shaded by state, built from real GIS boundary data, hover/tap for exact counts
- **Accountability gap** — arrests vs. convictions, state vs. central bodies
- **Institutional response** — how often exams get cancelled vs. retested vs. just investigated
- **Leak mechanism mining** — OMR/marks manipulation, impersonation, print-press leaks, WhatsApp, in-hall device leaks, insider leaks — pulled from free-text case notes
- **Repeat offenders** — conducting bodies ranked by incident count, with name variants merged
- **Biggest incidents** — top cases ranked by aspirants affected
- **Sourcing** — which outlets cover these stories, with outlet name normalization
- **Methodology box** — plain-language definitions of Confirmed/Alleged/Denied/Suspected, confidence tiers, and arrests vs. convictions
- **Bottom-line takeaways** + a data-quality caveat section (reporting bias, missingness, unit inconsistency)

Every number on the page is computed live from the CSV — nothing is hardcoded.

---

## Tech stack

| Layer | Tool |
|---|---|
| Data processing | Python 3, pandas |
| Map geometry | GIS boundary data, simplified with Shapely, projected to SVG |
| Charts | [Chart.js](https://www.chartjs.org/) (CDN) |
| Front end | Plain HTML/CSS/JS — no React, no build step |
| Fonts | Special Elite, IBM Plex Sans, Courier Prime, Caveat (Google Fonts) |

---

## Project structure

```
.
├── Dashboard.html          # the finished, self-contained dashboard (open this)
├── generate_dashboard.py   # reads the CSV, computes stats, writes Dashboard.html
├── india_paths.json        # simplified India state boundary data used by the map
└── paper_leaks.csv         # source dataset (110+ incidents, 2004–2026)
```

`Dashboard.html` is fully self-contained — the map data is baked into it at generation time, so you only need `india_paths.json` if you're *regenerating* the dashboard, not just viewing it.

---

## Running it locally

```bash
git clone https://github.com/Prajwal18py/paper-leaks-dashboard.git
cd paper-leaks-dashboard
```

Just want to view it? Open `Dashboard.html` directly in a browser, or use VS Code's Live Server extension.

Want to regenerate it (e.g. after updating the CSV)?

```bash
pip install pandas shapely --break-system-packages
python3 generate_dashboard.py paper_leaks.csv Dashboard.html
```

---

## Hosting it live

Enable GitHub Pages on this repo (Settings → Pages → Source: `main` branch), then your dashboard is live at:

```
https://prajwal18py.github.io/paper-leaks-dashboard/Dashboard.html
```

---

## Data & methodology

- **Confirmed** — acknowledged by the conducting body, an investigating agency, or a court, or backed by multiple independent reports.
- **Alleged** — credibly reported by press/aspirants but not officially acknowledged.
- **Denied** — the conducting body has publicly denied the leak despite reports.
- **Suspected** — pattern-based inference (abnormal scores, pre-exam viral content) without confirmation.
- **Confidence** (High/Medium/Low) reflects how solid the sourcing is per incident, not how serious the leak was.

Read the full caveat and methodology sections inside the dashboard itself before citing any numbers — the dataset is a record of *reported* incidents, not a complete census, and pre-2012 rows are subject to real reporting/digitisation bias.

---

## License

MIT — use, fork, and adapt freely. Attribution appreciated but not required.
