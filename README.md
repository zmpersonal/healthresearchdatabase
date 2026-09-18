# HealthResearchDatabase.com

Health Research Database is a GitHub Pages-ready, continuously updated claim-to-evidence product built from public PubMed and ClinicalTrials.gov metadata.

## What the site now includes

- **HRD Claim Ledger** — living claim pages with a concise answer, Evidence Profile, Claim Fidelity analysis, Research Receipt, matched source records, trial radar and citation text.
- **HRD Research Receipts** — reproducible claim-specific counts, exact match terms, inclusion/exclusion rules, dataset date and JSON endpoints.
- **HRD Claim Fidelity** — a public framework comparing claim wording with the intervention, population, dose, duration, comparator, outcome, measurement and setting actually studied.
- **Evidence Map** — intervention/outcome counts linked to the exact claim receipt.
- **Trial Radar** — recruiting, active and near-completion studies from ClinicalTrials.gov.
- **Evidence Changes** — a visible feed of new publications and registry updates, ready to preserve future reassessments and corrections.
- **Research dashboards** — publication mix, research-over-time chart, claims and source records for every intervention.
- **Open data and API** — JSON/CSV downloads, checksums, Dataset schema, CC BY 4.0 citation guidance, claim receipt endpoints, feeds and status JSON.
- **Governance** — methodology, editorial policy, corrections, data sources, funding/conflict disclosure and indexing-error reports.
- **Healthspan Habits Test** — retained as a secondary feature, with its complete questionnaire and scoring rubric rendered in HTML.

All essential research text, counts, dates and source links are present in the initial HTML. JavaScript enhances filtering and interaction; it is not required for crawlers to read the evidence.

## Automatic updates

`.github/workflows/update-research.yml` runs every Monday and Thursday and can be triggered manually. It:

1. retrieves PubMed and ClinicalTrials.gov records;
2. applies intervention-specific precision filters and obvious non-human exclusions;
3. classifies design using PubMed publication types plus methods-language heuristics;
4. regenerates topic, claim, study and trial pages;
5. rebuilds Research Receipts, API JSON, feeds, datasets and split sitemaps;
6. commits and deploys the refreshed site.

No paid API is required.

### Optional GitHub secrets

Under **Settings → Secrets and variables → Actions**:

- `NCBI_API_KEY` — optional free NCBI key for a higher request limit.
- `NCBI_EMAIL` — optional contact email sent with NCBI E-utilities requests.

The updater works without either secret.

## First deployment

1. Upload the repository contents to the repository root, including `.github`.
2. In **Settings → Pages**, choose **GitHub Actions** as the source.
3. Confirm the custom domain is `healthresearchdatabase.com`.
4. Run **Actions → Update research database and deploy → Run workflow** once.
5. Confirm the homepage, one claim page, `/trial-radar/`, `/evidence-map/` and `/healthspan/`.
6. Enable **Enforce HTTPS** after the domain certificate is ready.

Scheduled updates continue automatically after that first run.

## Local generation

Rebuild from the bundled datasets:

```bash
python scripts/update_research.py --generate-only
```

Perform a live source refresh and rebuild:

```bash
python scripts/update_research.py
```

The production updater uses only Python's standard library.

## Important scientific boundary

Research Receipts are reproducible counts within HRD's indexed snapshot. They are not systematic reviews, efficacy scores, risk-of-bias assessments or medical recommendations. Claim Fidelity measures directness between research and claim wording; it does not grade whether an intervention works.
