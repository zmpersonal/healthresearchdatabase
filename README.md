# HealthResearchDatabase.com

A GitHub Pages-ready, automatically refreshed wellness research index using official public data from PubMed/NCBI and ClinicalTrials.gov.

## What it indexes

- Sauna & heat therapy
- Infrared sauna
- Cold-water immersion
- Contrast therapy
- Photobiomodulation / red light
- Floatation therapy
- Massage therapy
- Sleep & passive heating
- Exercise recovery

The exact API queries live in `data/topics.json`.

## Automatic updates

`.github/workflows/update-research.yml` runs every Monday and Thursday and can also be run manually. It:

1. Searches PubMed through NCBI E-utilities.
2. Retrieves publication metadata and PubMed publication types.
3. Searches ClinicalTrials.gov API v2.
4. Deduplicates records that match multiple topics.
5. Regenerates topic, study and trial pages.
6. Rebuilds JSON/CSV datasets and `sitemap.xml`.
7. Commits refreshed data to the repository.
8. Deploys the refreshed static site to GitHub Pages.

No paid API is required.

### Optional GitHub secrets

Under **Settings → Secrets and variables → Actions** you may add:

- `NCBI_API_KEY` — optional free NCBI API key. Without it the script deliberately stays below the unauthenticated E-utilities request rate.
- `NCBI_EMAIL` — optional contact email sent with NCBI E-utilities requests.

The site works without either secret.

## First deployment

1. Upload all files to the repository root, including the hidden `.github` directory.
2. Go to **Settings → Pages**.
3. Set **Source → GitHub Actions**.
4. Set the custom domain to `healthresearchdatabase.com`.
5. Point the domain DNS to GitHub Pages.
6. Go to **Actions → Update research database and deploy → Run workflow**.
7. After the workflow succeeds, the placeholder/empty starter index will be replaced by live PubMed and ClinicalTrials.gov records.
8. Enable **Enforce HTTPS** after GitHub finishes validating the custom domain and provisioning its certificate.

## Data policy

The site intentionally does **not** republish full PubMed abstracts or article text. It stores bibliographic metadata, publication types, indexing terms, source identifiers and links to the primary records.

A publication's study-design bucket is descriptive and is **not** a quality grade, clinical recommendation, GRADE assessment or risk-of-bias evaluation.

## Local generation

To regenerate static pages using the data already in `data/`:

```bash
python scripts/update_research.py --generate-only
```

To perform a live refresh locally:

```bash
python scripts/update_research.py
```

## Custom domain

The included `CNAME` contains:

```text
healthresearchdatabase.com
```
