# HealthResearchDatabase.com

HealthResearchDatabase.com is a GitHub Pages-ready consumer health-research product backed by automatically refreshed public data from PubMed/NCBI and ClinicalTrials.gov.

The site has two layers:

1. **Consumer layer** — a shareable Healthspan Habits Score, friend challenges, research-question discovery, and a Research Pulse designed for organic social traffic.
2. **Evidence layer** — topic indexes, publication/trial records, downloadable datasets, and a transparent methodology page.

## Consumer features

- **Healthspan Habits Score** at `/healthspan/`
  - 10-question, 0–100 habit-alignment score.
  - Runs entirely in the browser; no account or backend is required.
  - No email gate before the result.
  - Stores the visitor's previous score locally in their browser.
  - Clearly presented as a lifestyle-habit index, **not** biological age, a diagnosis, a medical-risk model, or a lifespan prediction.
- **Friend challenges**
  - Challenge URLs carry only the challenger's score, never questionnaire answers.
  - A visitor can compare their result against the challenger or against their own prior result.
- **Shareable score cards**
  - Static score landing pages exist for every score from 0–100 at `/score/<score>/`.
  - Each score page has score-specific Open Graph metadata and a 1200×630 social preview image.
  - Result sharing supports native share, Facebook, X, Pinterest, email, copy link, and local PNG export.
- **Research Pulse** at `/latest/`
  - Highlights newly indexed research with filters for reviews and randomized trials.
- **Research search**
  - Searches the generated study/trial metadata in-browser.

A global percentile leaderboard is intentionally **not** included in this static GitHub Pages version. It would require a server-side data store and enough real participant data to produce defensible rankings.

## What the research index covers

- Sauna & heat therapy
- Infrared sauna
- Cold-water immersion
- Contrast therapy
- Photobiomodulation / red light
- Floatation therapy
- Massage therapy
- Sleep & passive heating
- Exercise recovery

The API queries live in `data/topics.json`.

## Research-quality safeguards

The database uses two layers of topic matching:

1. The PubMed or ClinicalTrials.gov search query selects candidate records.
2. A conservative metadata post-filter requires the topic intervention to appear in high-signal metadata such as the title, keywords, MeSH terms, conditions, or intervention fields.

This is deliberately precision-first. It reduces false positives caused by generic terms such as `cold exposure` or `far infrared` that can refer to unrelated research.

The site does **not** infer treatment efficacy from study counts. Labels such as **Research depth** describe the amount and design diversity of indexed research only; they are not clinical recommendations, GRADE ratings, risk-of-bias assessments, or evidence-of-benefit scores.

## Automatic research updates

`.github/workflows/update-research.yml` runs every Monday and Thursday and can also be run manually. It:

1. Searches PubMed through NCBI E-utilities.
2. Retrieves publication metadata and publication types.
3. Searches ClinicalTrials.gov API v2.
4. Applies the topic metadata precision filter.
5. Deduplicates records that match multiple topics.
6. Regenerates topic, study, and trial pages.
7. Rebuilds JSON/CSV datasets and `sitemap.xml`.
8. Commits refreshed data to the repository.
9. Deploys the refreshed static site to GitHub Pages.

No paid API is required.

### Optional GitHub secrets

Under **Settings → Secrets and variables → Actions** you may add:

- `NCBI_API_KEY` — optional free NCBI API key. Without it, the updater stays below the unauthenticated E-utilities request rate.
- `NCBI_EMAIL` — optional contact email sent with NCBI E-utilities requests.

The site works without either secret.

## First deployment — important

The packaged repository intentionally contains the static starter datasets rather than a copied snapshot of the live generated database. The interface handles that state without displaying misleading zero counts, but the research updater should be run immediately after the upload.

1. Upload **all files** to the repository root, including the hidden `.github` directory.
2. Go to **Settings → Pages** and set **Source → GitHub Actions**.
3. Confirm the custom domain is `healthresearchdatabase.com`.
4. Go to **Actions → Update research database and deploy → Run workflow**.
5. Let that workflow complete. It will fetch current PubMed and ClinicalTrials.gov records, regenerate the research pages/data, commit them, and deploy the populated site.
6. Open the homepage, one topic page, `/latest/`, and `/healthspan/` to confirm the deployment.
7. Enable **Enforce HTTPS** after GitHub validates the custom domain and certificate if it is not already enabled.

Do **not** skip step 4 on the first upload; otherwise the consumer experience will work, but research counts will remain in the pending-refresh state until the scheduled updater runs.

## Scoring methodology

The Healthspan Habits Score is documented publicly at `/methodology/#habits-score`.

It is intentionally simple and transparent:

- 10 behavioral questions.
- Maximum of 10 points per question.
- Equal weighting for readability and auditability, not because every behavior has the same health effect size.
- No questionnaire answers are uploaded by the static site.
- Previous results are stored locally in the visitor's browser.
- Challenge links expose the score only.

## Data policy

The site intentionally does **not** republish full PubMed abstracts or article text. It stores bibliographic metadata, publication types, indexing terms, source identifiers, and links to primary-source records.

## Local generation

To regenerate static research pages using the data already in `data/`:

```bash
python scripts/update_research.py --generate-only
```

To perform a live research refresh locally:

```bash
python scripts/update_research.py
```

The optional developer helper below regenerates the 0–100 social score pages and images:

```bash
python scripts/generate_score_pages.py
```

That helper uses Pillow. Pillow is **not** required by the production updater or GitHub Pages deployment; the generated score pages/images are already included in the repository.

## Custom domain

The included `CNAME` contains:

```text
healthresearchdatabase.com
```
