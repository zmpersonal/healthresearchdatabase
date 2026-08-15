#!/usr/bin/env python3
"""Refresh HealthResearchDatabase.com from PubMed and ClinicalTrials.gov.

Uses only Python's standard library. Full abstracts are intentionally not republished.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TOPICS_FILE = DATA / "topics.json"
STUDIES_FILE = DATA / "studies.json"
TRIALS_FILE = DATA / "trials.json"
STATS_FILE = DATA / "stats.json"

NCBI_KEY = os.getenv("NCBI_API_KEY", "").strip()
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "").strip()
TOOL = "healthresearchdatabase"
USER_AGENT = "HealthResearchDatabase/1.0 (+https://healthresearchdatabase.com/methodology/)"

DESIGNS = [
    ("a", "Systematic review / meta-analysis"),
    ("b", "Randomized controlled trial"),
    ("c", "Controlled / clinical trial"),
    ("d", "Observational research"),
    ("e", "Other research"),
]

INTERPRETATION = {
    "a": "This record is classified as a research synthesis because PubMed identifies it as a systematic review and/or meta-analysis. Synthesis quality still depends on the included studies and methods.",
    "b": "This record is classified as a randomized controlled trial. Randomization can strengthen causal inference, but sample size, blinding, adherence, endpoints and attrition still matter.",
    "c": "This record is classified as an interventional clinical study that PubMed does not identify as a randomized controlled trial. Design details should be checked in the source record.",
    "d": "This record is classified as observational research. Observational findings can identify associations, but confounding and selection effects may limit causal conclusions.",
    "e": "PubMed does not place this record into one of the higher-level design buckets used by this index. Check the publication types and source record before drawing conclusions.",
}

COMMERCE = {
    "sauna-heat-therapy": ("Explore home saunas", "https://inhousewellness.com/collections/saunas"),
    "infrared-sauna": ("Explore infrared saunas", "https://inhousewellness.com/collections/infrared-saunas"),
    "cold-water-immersion": ("Explore cold plunges", "https://inhousewellness.com/collections/cold-plunge"),
    "contrast-therapy": ("Explore home wellness equipment", "https://inhousewellness.com/"),
    "sleep-and-passive-heating": ("Explore home saunas", "https://inhousewellness.com/collections/saunas"),
    "exercise-recovery": ("Explore home wellness equipment", "https://inhousewellness.com/"),
}


def request_bytes(url: str, timeout: int = 35, retries: int = 3) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, application/xml;q=0.9, */*;q=0.8"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last = exc
            if i < retries - 1:
                time.sleep(1.5 * (i + 1))
    raise last


def get_json(url: str) -> dict:
    return json.loads(request_bytes(url).decode("utf-8"))


def ncbi_url(endpoint: str, params: dict) -> str:
    params = dict(params)
    params.setdefault("tool", TOOL)
    if NCBI_EMAIL:
        params.setdefault("email", NCBI_EMAIL)
    if NCBI_KEY:
        params["api_key"] = NCBI_KEY
    return f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{endpoint}?{urllib.parse.urlencode(params)}"


def text_of(el) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def extract_year(article) -> str:
    candidates = [
        article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate/Year"),
        article.find("./MedlineCitation/DateCompleted/Year"),
        article.find("./MedlineCitation/DateRevised/Year"),
    ]
    for c in candidates:
        t = text_of(c)
        if re.fullmatch(r"\d{4}", t):
            return t
    medline = text_of(article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate"))
    m = re.search(r"(19|20)\d{2}", medline)
    return m.group(0) if m else ""


def classify(pub_types: list[str], mesh: list[str]) -> tuple[str, str]:
    p = {x.lower() for x in pub_types}
    if "meta-analysis" in p or "systematic review" in p:
        return DESIGNS[0]
    if "randomized controlled trial" in p:
        return DESIGNS[1]
    clinical_terms = {"controlled clinical trial", "clinical trial", "clinical trial, phase i", "clinical trial, phase ii", "clinical trial, phase iii", "clinical trial, phase iv", "pragmatic clinical trial"}
    if p & clinical_terms:
        return DESIGNS[2]
    observational_terms = {"observational study", "comparative study", "multicenter study", "evaluation study"}
    if p & observational_terms:
        return DESIGNS[3]
    return DESIGNS[4]


def parse_pubmed_article(article, topic_slugs: list[str], topic_name_map: dict[str, str]) -> dict | None:
    citation = article.find("./MedlineCitation")
    if citation is None:
        return None
    pmid = text_of(citation.find("PMID"))
    title = text_of(citation.find("./Article/ArticleTitle"))
    if not pmid or not title:
        return None
    journal = text_of(citation.find("./Article/Journal/Title")) or text_of(citation.find("./Article/Journal/ISOAbbreviation"))
    authors = []
    for a in citation.findall("./Article/AuthorList/Author"):
        collective = text_of(a.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        last, fore = text_of(a.find("LastName")), text_of(a.find("ForeName"))
        name = " ".join(x for x in [fore, last] if x)
        if name:
            authors.append(name)
    pub_types = [text_of(x) for x in citation.findall("./Article/PublicationTypeList/PublicationType") if text_of(x)]
    mesh = [text_of(x.find("DescriptorName")) for x in citation.findall("./MeshHeadingList/MeshHeading") if text_of(x.find("DescriptorName"))]
    keywords = [text_of(x) for x in citation.findall("./KeywordList/Keyword") if text_of(x)]
    doi = ""
    for aid in article.findall("./PubmedData/ArticleIdList/ArticleId"):
        if (aid.attrib.get("IdType") or "").lower() == "doi":
            doi = text_of(aid)
            break
    design_class, design_label = classify(pub_types, mesh)
    year = extract_year(article)
    return {
        "pmid": pmid,
        "title": title,
        "authors": authors[:12],
        "journal": journal,
        "year": year,
        "doi": doi,
        "publication_types": pub_types,
        "mesh": mesh[:30],
        "keywords": keywords[:20],
        "topics": sorted(topic_slugs),
        "topic_names": [topic_name_map[s] for s in sorted(topic_slugs) if s in topic_name_map],
        "design_class": design_class,
        "design_label": design_label,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    }


def fetch_pubmed(topics: list[dict], retmax: int = 140) -> list[dict]:
    pmid_topics: dict[str, set[str]] = defaultdict(set)
    for t in topics:
        print(f"PubMed search: {t['name']}")
        url = ncbi_url("esearch.fcgi", {"db": "pubmed", "term": t["pubmed_query"], "retmode": "json", "retmax": str(retmax), "sort": "pub date"})
        try:
            payload = get_json(url)
            ids = payload.get("esearchresult", {}).get("idlist", [])
            for pmid in ids:
                pmid_topics[str(pmid)].add(t["slug"])
            time.sleep(0.12 if NCBI_KEY else 0.38)
        except Exception as exc:
            print(f"WARNING PubMed search failed for {t['slug']}: {exc}", file=sys.stderr)
    ids = list(pmid_topics)
    print(f"Unique PubMed IDs: {len(ids)}")
    topic_name_map = {t["slug"]: t["name"] for t in topics}
    records = []
    for i in range(0, len(ids), 100):
        chunk = ids[i:i+100]
        url = ncbi_url("efetch.fcgi", {"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"})
        try:
            root = ET.fromstring(request_bytes(url))
            for art in root.findall("./PubmedArticle"):
                pmid = text_of(art.find("./MedlineCitation/PMID"))
                rec = parse_pubmed_article(art, list(pmid_topics.get(pmid, [])), topic_name_map)
                if rec:
                    records.append(rec)
            time.sleep(0.12 if NCBI_KEY else 0.38)
        except Exception as exc:
            print(f"WARNING PubMed fetch chunk failed: {exc}", file=sys.stderr)
    records.sort(key=lambda r: (int(r["year"]) if str(r.get("year","")).isdigit() else 0, int(r["pmid"]) if str(r.get("pmid","")).isdigit() else 0), reverse=True)
    return records


def nested(d: dict, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def parse_trial(study: dict, slugs: set[str], name_map: dict[str, str]) -> dict | None:
    p = study.get("protocolSection", {})
    ident = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    design = p.get("designModule", {})
    cond = p.get("conditionsModule", {})
    arms = p.get("armsInterventionsModule", {})
    nct = ident.get("nctId", "")
    title = ident.get("briefTitle") or ident.get("officialTitle") or ""
    if not nct or not title:
        return None
    interventions = []
    for x in arms.get("interventions", []) or []:
        name = x.get("name")
        if name:
            interventions.append({"name": name, "type": x.get("type", "")})
    locs = []
    for x in nested(p, "contactsLocationsModule", "locations", default=[]) or []:
        parts = [x.get("facility"), x.get("city"), x.get("state"), x.get("country")]
        label = ", ".join(y for y in parts if y)
        if label:
            locs.append(label)
    return {
        "nct_id": nct,
        "title": title,
        "status": status.get("overallStatus", ""),
        "study_type": design.get("studyType", ""),
        "phases": design.get("phases", []) or [],
        "enrollment": nested(design, "enrollmentInfo", "count", default=""),
        "conditions": cond.get("conditions", []) or [],
        "interventions": interventions[:12],
        "locations": locs[:8],
        "start_date": nested(status, "startDateStruct", "date", default=""),
        "completion_date": nested(status, "completionDateStruct", "date", default=""),
        "last_update": status.get("lastUpdateSubmitDate", ""),
        "topics": sorted(slugs),
        "topic_names": [name_map[s] for s in sorted(slugs) if s in name_map],
        "url": f"https://clinicaltrials.gov/study/{nct}",
    }


def fetch_trials(topics: list[dict]) -> list[dict]:
    raw: dict[str, dict] = {}
    memberships: dict[str, set[str]] = defaultdict(set)
    name_map = {t["slug"]: t["name"] for t in topics}
    for t in topics:
        print(f"ClinicalTrials search: {t['name']}")
        params = {"query.term": t["trial_query"], "pageSize": "100", "format": "json", "countTotal": "true"}
        url = "https://clinicaltrials.gov/api/v2/studies?" + urllib.parse.urlencode(params)
        try:
            payload = get_json(url)
            for study in payload.get("studies", []) or []:
                nct = nested(study, "protocolSection", "identificationModule", "nctId", default="")
                if nct:
                    raw[nct] = study
                    memberships[nct].add(t["slug"])
            time.sleep(0.15)
        except Exception as exc:
            print(f"WARNING ClinicalTrials search failed for {t['slug']}: {exc}", file=sys.stderr)
    out=[]
    for nct, study in raw.items():
        rec=parse_trial(study,memberships[nct],name_map)
        if rec: out.append(rec)
    def trial_sort(t):
        active = t.get("status") in {"RECRUITING","NOT_YET_RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION"}
        return (1 if active else 0, t.get("last_update", ""), t.get("nct_id", ""))
    out.sort(key=trial_sort, reverse=True)
    return out


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def esc(v): return html.escape(str(v or ""), quote=True)


def shell(title: str, desc: str, canonical: str, body: str) -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{esc(canonical)}"><link rel="stylesheet" href="/assets/site.css"></head><body>
<header class="site-header"><div class="wrap header-inner"><a class="brand" href="/"><span class="brand-mark">HRD</span><span>Health Research Database<small>Evidence index · updated automatically</small></span></a><nav><a href="/latest/">Latest</a><a href="/trials/">Clinical trials</a><a href="/evidence/">Study designs</a><a href="/methodology/">Methodology</a><a class="nav-cta" href="/">Search</a></nav></div></header>
<main>{body}</main>
<footer><div class="wrap footer-grid"><div><a class="brand" href="/"><span class="brand-mark">HRD</span><span>Health Research Database</span></a><p>Research indexing and discovery. Not medical advice.</p></div><div><h4>Research</h4><a href="/latest/">Latest records</a><a href="/trials/">Clinical trials</a><a href="/evidence/">Study designs</a></div><div><h4>About</h4><a href="/methodology/">Methodology</a><a href="/data-download/">Download data</a></div></div></footer></body></html>'''


def badge(rec: dict) -> str:
    return f'<span class="badge {esc(rec.get("design_class","e"))}">{esc(rec.get("design_label","Other research"))}</span>'


def paper_row(s: dict) -> str:
    first=(s.get("authors") or [""])[0]
    return f'''<article class="paper"><div class="meta">{esc(s.get('year') or '—')}<br>{esc(first)}</div><div><h3><a href="/studies/{esc(s['pmid'])}/">{esc(s['title'])}</a></h3><div class="journal">{esc(s.get('journal'))}{(' · DOI '+esc(s.get('doi'))) if s.get('doi') else ''}</div></div>{badge(s)}</article>'''


def topic_page(topic: dict, studies: list[dict], trials: list[dict], stats: dict) -> str:
    slug=topic["slug"]; ts=[s for s in studies if slug in s.get("topics",[])]; tt=[t for t in trials if slug in t.get("topics",[])]
    counts=Counter(s.get("design_class","e") for s in ts)
    maxv=max(counts.values()) if counts else 1
    mix=''.join(f'<div class="kv"><span>{esc(label)}</span><strong>{counts.get(cls,0)}</strong></div>' for cls,label in DESIGNS)
    latest=''.join(paper_row(s) for s in ts[:30]) or '<div class="empty">No publication records were returned for this topic in the latest refresh.</div>'
    trial_rows=''.join(f'<tr><td><a href="/trials/{esc(t["nct_id"])}/"><strong>{esc(t["title"])}</strong></a><br><small>{esc(t["nct_id"])}</small></td><td>{esc((t.get("status") or "").replace("_"," "))}</td><td>{esc(t.get("enrollment") or "—")}</td><td>{esc(t.get("last_update") or "—")}</td></tr>' for t in tt[:20]) or '<tr><td colspan="4">No matching ClinicalTrials.gov records in the current index.</td></tr>'
    commerce=''
    if slug in COMMERCE:
        label,url=COMMERCE[slug]
        commerce=f'<aside class="detail-card"><div class="eyebrow">Consumer context</div><h3>Research first, products second.</h3><p>This database separates research indexing from shopping. For readers looking for home wellness equipment related to this topic:</p><a class="button secondary" rel="sponsored" href="{esc(url)}">{esc(label)} at InHouse Wellness</a></aside>'
    body=f'''<section class="page-hero"><div class="wrap"><div class="breadcrumb"><a href="/">Home</a> / Topics / {esc(topic['name'])}</div><div class="eyebrow">Research topic</div><h1>{esc(topic['name'])}</h1><p class="lede">{esc(topic['short'])}</p></div></section>
<section class="section"><div class="wrap detail-grid"><div class="detail-card"><div class="eyebrow">Current index</div><h2>{len(ts)} publications · {len(tt)} trials</h2><p>Records can overlap with other topics. Counts describe what the current search strategy indexes; they do not measure clinical certainty.</p><h3>Study-design mix</h3>{mix}</div>{commerce or '<aside class="detail-card"><h3>How to read this page</h3><p>Open individual records for publication types and source links. The design label is descriptive, not a quality grade.</p><a class="button secondary" href="/evidence/">Study design guide</a></aside>'}</div></section>
<section class="section"><div class="wrap"><div class="section-head"><div><div class="eyebrow">Publications</div><h2>Latest indexed papers</h2></div><p>Metadata is sourced from PubMed. Full abstracts and article text are not republished here.</p></div><div class="paper-list">{latest}</div></div></section>
<section class="section"><div class="wrap"><div class="section-head"><div><div class="eyebrow">Research radar</div><h2>ClinicalTrials.gov records</h2></div></div><div class="table-wrap"><table><thead><tr><th>Study</th><th>Status</th><th>Enrollment</th><th>Updated</th></tr></thead><tbody>{trial_rows}</tbody></table></div></div></section>'''
    return shell(f"{topic['name']} Research | Health Research Database", topic["short"], f"https://healthresearchdatabase.com/topics/{slug}/", body)


def study_page(s: dict) -> str:
    authors=', '.join(s.get('authors') or []) or 'Not listed'
    topic_links=', '.join(f'<a href="/topics/{esc(slug)}/">{esc(name)}</a>' for slug,name in zip(s.get('topics',[]),s.get('topic_names',[])))
    pub_types=', '.join(s.get('publication_types') or []) or 'Not specified'
    mesh=', '.join((s.get('mesh') or [])[:18]) or 'Not listed'
    doi_link=f'<a href="https://doi.org/{esc(s["doi"])}" rel="noopener">DOI</a>' if s.get('doi') else ''
    body=f'''<section class="page-hero"><div class="wrap"><div class="breadcrumb"><a href="/">Home</a> / Study / PMID {esc(s['pmid'])}</div>{badge(s)}<h1 style="font-size:clamp(36px,5vw,60px);margin-top:18px">{esc(s['title'])}</h1><p class="lede">{esc(s.get('journal'))} · {esc(s.get('year') or 'Year not indexed')}</p></div></section>
<section class="section"><div class="wrap detail-grid"><div class="detail-card"><h2>Publication record</h2><div class="kv"><span>PMID</span><strong>{esc(s['pmid'])}</strong></div><div class="kv"><span>Authors</span><div>{esc(authors)}</div></div><div class="kv"><span>Journal</span><div>{esc(s.get('journal'))}</div></div><div class="kv"><span>Publication year</span><div>{esc(s.get('year') or '—')}</div></div><div class="kv"><span>Publication types</span><div>{esc(pub_types)}</div></div><div class="kv"><span>Indexed topics</span><div>{topic_links or '—'}</div></div><div class="kv"><span>MeSH headings</span><div>{esc(mesh)}</div></div><div class="source-links" style="margin-top:20px"><a href="{esc(s['pubmed_url'])}" rel="noopener">View on PubMed</a>{doi_link}</div></div><aside class="detail-card"><div class="eyebrow">How to interpret</div><h3>{esc(s.get('design_label'))}</h3><p>{esc(INTERPRETATION.get(s.get('design_class','e'),INTERPRETATION['e']))}</p><div class="notice">This index does not reproduce the paper's full abstract or convert the record into a treatment recommendation. Read the primary source before relying on the finding.</div></aside></div></section>'''
    return shell(f"{s['title']} | Health Research Database", f"PubMed record {s['pmid']} indexed by Health Research Database. {s.get('design_label','Research record')}.", f"https://healthresearchdatabase.com/studies/{s['pmid']}/", body)


def trial_page(t: dict) -> str:
    ints=', '.join(x.get('name','') for x in t.get('interventions',[]) if x.get('name')) or 'Not listed'
    cond=', '.join(t.get('conditions',[]) or []) or 'Not listed'
    loc=', '.join(t.get('locations',[]) or []) or 'Not listed'
    topic_links=', '.join(f'<a href="/topics/{esc(slug)}/">{esc(name)}</a>' for slug,name in zip(t.get('topics',[]),t.get('topic_names',[])))
    body=f'''<section class="page-hero"><div class="wrap"><div class="breadcrumb"><a href="/">Home</a> / Clinical trials / {esc(t['nct_id'])}</div><div class="eyebrow">ClinicalTrials.gov record</div><h1 style="font-size:clamp(36px,5vw,60px)">{esc(t['title'])}</h1><p class="lede">{esc((t.get('status') or 'Status unavailable').replace('_',' '))} · {esc(t['nct_id'])}</p></div></section>
<section class="section"><div class="wrap detail-grid"><div class="detail-card"><h2>Trial record</h2><div class="kv"><span>NCT ID</span><strong>{esc(t['nct_id'])}</strong></div><div class="kv"><span>Status</span><div>{esc((t.get('status') or '—').replace('_',' '))}</div></div><div class="kv"><span>Study type</span><div>{esc(t.get('study_type') or '—')}</div></div><div class="kv"><span>Phase</span><div>{esc(', '.join(t.get('phases') or []) or '—')}</div></div><div class="kv"><span>Enrollment</span><div>{esc(t.get('enrollment') or '—')}</div></div><div class="kv"><span>Conditions</span><div>{esc(cond)}</div></div><div class="kv"><span>Interventions</span><div>{esc(ints)}</div></div><div class="kv"><span>Locations</span><div>{esc(loc)}</div></div><div class="kv"><span>Indexed topics</span><div>{topic_links or '—'}</div></div><div class="kv"><span>Last update</span><div>{esc(t.get('last_update') or '—')}</div></div><div class="source-links" style="margin-top:20px"><a href="{esc(t['url'])}" rel="noopener">View on ClinicalTrials.gov</a></div></div><aside class="detail-card"><div class="eyebrow">Protocol ≠ result</div><h3>A registered study is not a positive finding.</h3><p>ClinicalTrials.gov records describe planned, ongoing or completed research. Registration alone does not establish that an intervention works, and some completed trials may not yet have published results.</p></aside></div></section>'''
    return shell(f"{t['title']} | Clinical Trial | Health Research Database", f"ClinicalTrials.gov study {t['nct_id']} indexed by Health Research Database.", f"https://healthresearchdatabase.com/trials/{t['nct_id']}/", body)


def write_csvs(studies: list[dict], trials: list[dict]):
    with (DATA/"studies.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["pmid","title","year","journal","design","doi","topics","pubmed_url"])
        for s in studies:w.writerow([s.get("pmid"),s.get("title"),s.get("year"),s.get("journal"),s.get("design_label"),s.get("doi"),"|".join(s.get("topic_names",[])),s.get("pubmed_url")])
    with (DATA/"trials.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["nct_id","title","status","study_type","enrollment","topics","last_update","url"])
        for t in trials:w.writerow([t.get("nct_id"),t.get("title"),t.get("status"),t.get("study_type"),t.get("enrollment"),"|".join(t.get("topic_names",[])),t.get("last_update"),t.get("url")])


def generate(topics: list[dict], studies: list[dict], trials: list[dict]):
    now=datetime.now(timezone.utc)
    topic_stats={}
    for t in topics:
        slug=t["slug"]
        ss=[s for s in studies if slug in s.get("topics",[])]
        tt=[x for x in trials if slug in x.get("topics",[])]
        topic_stats[slug]={"studies":len(ss),"trials":len(tt),"designs":dict(Counter(s.get("design_class","e") for s in ss))}
    has_data = bool(studies or trials)
    stats={"generated_at":now.isoformat() if has_data else None,"updated_label":now.strftime("%b %-d, %Y") if has_data else "Pending first refresh","total_studies":len(studies),"total_trials":len(trials),"total_topics":len(topics),"active_trials":sum(1 for t in trials if t.get("status") in {"RECRUITING","NOT_YET_RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION"}),"topics":topic_stats}
    save_json(STATS_FILE,stats)
    write_csvs(studies,trials)
    # Remove previously generated detail directories only, preserving /trials/index.html.
    studies_dir=ROOT/"studies";studies_dir.mkdir(exist_ok=True)
    trials_dir=ROOT/"trials";trials_dir.mkdir(exist_ok=True)
    for p in studies_dir.iterdir():
        if p.is_dir():
            for c in p.rglob('*'):
                if c.is_file(): c.unlink()
            p.rmdir()
    for p in trials_dir.iterdir():
        if p.is_dir():
            for c in p.rglob('*'):
                if c.is_file(): c.unlink()
            p.rmdir()
    for t in topics:
        d=ROOT/"topics"/t["slug"];d.mkdir(parents=True,exist_ok=True);(d/"index.html").write_text(topic_page(t,studies,trials,stats),encoding="utf-8")
    for s in studies:
        d=studies_dir/s["pmid"];d.mkdir(parents=True,exist_ok=True);(d/"index.html").write_text(study_page(s),encoding="utf-8")
    for t in trials:
        d=trials_dir/t["nct_id"];d.mkdir(parents=True,exist_ok=True);(d/"index.html").write_text(trial_page(t),encoding="utf-8")
    urls=["/","/latest/","/trials/","/evidence/","/methodology/","/data-download/"]
    urls += [f"/topics/{t['slug']}/" for t in topics]
    urls += [f"/studies/{s['pmid']}/" for s in studies]
    urls += [f"/trials/{t['nct_id']}/" for t in trials]
    lastmod=now.strftime("%Y-%m-%d")
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>https://healthresearchdatabase.com{u}</loc><lastmod>{lastmod}</lastmod></url>\n' for u in urls)+'</urlset>\n'
    (ROOT/"sitemap.xml").write_text(sitemap,encoding="utf-8")
    print(f"Generated {len(studies)} study pages, {len(trials)} trial pages, {len(topics)} topic pages")


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--generate-only",action="store_true");ap.add_argument("--retmax",type=int,default=140);args=ap.parse_args()
    topics=json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
    existing_studies=json.loads(STUDIES_FILE.read_text(encoding="utf-8")) if STUDIES_FILE.exists() else []
    existing_trials=json.loads(TRIALS_FILE.read_text(encoding="utf-8")) if TRIALS_FILE.exists() else []
    if args.generate_only:
        generate(topics,existing_studies,existing_trials);return
    studies=fetch_pubmed(topics,args.retmax)
    trials=fetch_trials(topics)
    if not studies and existing_studies:
        print("WARNING: no PubMed records fetched; preserving existing studies",file=sys.stderr);studies=existing_studies
    if not trials and existing_trials:
        print("WARNING: no trial records fetched; preserving existing trials",file=sys.stderr);trials=existing_trials
    save_json(STUDIES_FILE,studies);save_json(TRIALS_FILE,trials);generate(topics,studies,trials)

if __name__=="__main__":main()
