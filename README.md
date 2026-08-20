# ⚖️ Los Angeles Legal & AI Job Hunter

An intelligent, resume-tailored job search, scraping, evaluation, and dashboard platform targeting **Legal, Entertainment Studio In-House, Corporate / Commercial Counsel, and Legal AI / LegalTech** opportunities in **Los Angeles County** requiring a **JD**, **State Bar of California admission**, and **1–4 years of experience**.

---

## 📋 Table of Contents
1. [Overview & Target Profile](#-overview--target-profile)
2. [Codebase Architecture & File Guide ("What is What")](#-codebase-architecture--file-guide-what-is-what)
3. [Hard Qualification Gates & Disqualification Rules](#-hard-qualification-gates--disqualification-rules)
4. [Resume Match Engine & Scoring Formula](#-resume-match-engine--scoring-formula)
5. [Multi-Source Scraping Pipeline](#-multi-source-scraping-pipeline)
6. [Universal Compensation & Salary Parser](#-universal-compensation--salary-parser)
7. [Geographic Proximity Engine (Anchored to 90038)](#-geographic-proximity-engine-anchored-to-90038)
8. [Dashboard Features & Sorting Modes](#-dashboard-features--sorting-modes)
9. [Quickstart & CLI Usage](#-quickstart--cli-usage)
10. [Daily Automations & GitHub Actions](#-daily-automations--github-actions)

---

## 🎯 Overview & Target Profile

The engine evaluates and ranks open job postings against the structured profile of **Harrison Wheeler**:
- **Education**: LMU Loyola Law School (JD, 2023), Production Editor *Loyola Entertainment Law Review*; USC (B.A., Philosophy, Politics & Law, cum laude, 2018).
- **Bar Admission**: State Bar of California admitted in 2023 (Active CA license, ~2 years post-bar experience).
- **AI & LegalTech Superpowers**: **Harvey Legal Engineer Certified**; prompt engineering, discovery/drafting automation, LLM evaluation workflows.
- **Entertainment In-House Experience**: MGM Studios (Business & Legal Affairs), AEG Worldwide (EVP General Counsel office), Gaumont International Television, NBCUniversal.
- **Practice Focus**: In-House Corporate / Commercial Counsel, Entertainment & Media Legal, Technology & AI Licensing, and BigLaw Corporate Transactions (excludes courtroom litigation).

---

## 🏛️ Codebase Architecture & File Guide ("What is What")

```
C:\Jobs\
├── main.py                             # CLI entrypoint and orchestrator
├── config.yaml                         # Configuration for queries, locations, filters, notifications
├── requirements.txt                    # Project Python dependencies
├── pytest.ini                          # Test suite runner configuration
├── setup_scheduler.ps1                 # Windows Task Scheduler automation script
├── .gitignore                          # Git ignore rules for virtualenvs, caches, logs
├── .github/
│   └── workflows/
│       └── daily_jobs.yml              # GitHub Actions daily automated scraper workflow
├── data/
│   ├── jobs.db                         # SQLite persistent database of all tracked jobs
│   └── digests/                        # Output folder for generated HTML daily briefings
├── src/
│   ├── config.py                       # Pydantic configuration data models & YAML loader
│   ├── db/
│   │   └── database.py                 # SQLite database layer with auto-deduplication & status tracking
│   ├── engine/
│   │   ├── candidate_profile.py        # Structured data model for Harrison Wheeler's resume
│   │   ├── resume_matcher.py           # Multi-dimensional candidate resume scoring engine
│   │   ├── scorer.py                   # Master scorer enforcing all Hard Gates and calling the matcher
│   │   ├── salary_parser.py            # Universal compensation regex parser
│   │   ├── exp_parser.py               # 1–4 years experience tiered sweet-spot & reach evaluator
│   │   ├── jd_detector.py              # Juris Doctor & Bar requirement detector
│   │   └── classifier.py               # Role & practice area classifier with regex word boundaries
│   ├── scrapers/
│   │   ├── base.py                     # JobPosting data model, text cleaner, and age calculator
│   │   ├── aggregator.py               # Scraper aggregator & deduplicator
│   │   ├── jobspy_scraper.py           # LinkedIn direct job search & extraction
│   │   ├── entertainmentcareers_scraper.py # EntertainmentCareers.net scraper with JSON-LD date parsing
│   │   ├── smartrecruiters_scraper.py  # SmartRecruiters ATS REST API scraper
│   │   ├── ats_scraper.py              # Direct Greenhouse & Lever company boards scraper
│   │   └── hydrator.py                 # Multi-threaded web page description & salary hydrator
│   ├── dashboard/
│   │   ├── app.py                      # FastAPI web backend with REST endpoints
│   │   └── templates/
│   │       └── index.html              # Alpine.js + Tailwind CSS responsive web dashboard
│   └── notifiers/
│       ├── digest_html.py              # Standalone executive HTML digest generator
│       ├── webhook.py                  # Discord and Slack webhook dispatcher
│       └── email_notifier.py           # SMTP HTML email sender
└── tests/
    ├── test_config.py                  # Config loader unit tests
    ├── test_database.py                # Database CRUD and deduplication tests
    ├── test_engine.py                  # Scoring and qualification gate tests
    ├── test_notifiers_dashboard.py     # FastAPI endpoints and digest tests
    └── test_scrapers.py                # Scraper base and cleaner tests
```

---

## 🛡️ Hard Qualification Gates & Disqualification Rules

Before a job posting receives candidate-tailored scoring, it must pass **6 strict Hard Gates** in [`src/engine/scorer.py`](src/engine/scorer.py). If any gate fails, the job is assigned **0% Match** and disqualified:

1. **30-Day Posting Recency Gate**:
   - Computes elapsed time since original release. Any posting older than **30 days** is strictly disqualified (0%).
2. **Strict Los Angeles County Geographic Gate**:
   - Must be located within Los Angeles County municipalities (*Los Angeles, Beverly Hills, Santa Monica, Culver City, Century City, Burbank, Universal City, Hollywood, El Segundo, Hawthorne, Commerce, Pasadena, Glendale, Woodland Hills, Calabasas, etc.*).
   - Explicitly rejects Orange County, San Diego, Bay Area, Northern California, or Out-of-State roles.
3. **State Bar of California & Jurisdictional Gate**:
   - Disqualifies postings mandating an out-of-state bar only (*e.g. "Must be licensed in New York State Bar"*) or foreign qualification (*"Solicitor or Barrister"*) without permitting California.
   - **Passes** postings that permit:
     - `State Bar of California`
     - `Member of New York Bar or other U.S. state bar` (*Peacock / NBCU*)
     - `Admission in New York or California` (*Paramount Pictures*)
     - `At least one U.S. state bar / Registered In-House Counsel` (*SpaceX / Telemundo*)
   - Disqualifies postings requiring in-person attendance at out-of-state headquarters (*e.g. ASCAP NYC HQ, ESPN Bristol CT*).
4. **Pure Litigation Disqualification Gate**:
   - Strictly excludes courtroom litigation associate roles (*Personal Injury, Lemon Law, Insurance Defense, Workers' Comp, Wage & Hour Class Action, Courtroom Litigation Associate*) to focus on In-House, Tech/AI, and Corporate Transactions.
5. **JD & Bar Admission Requirement Gate**:
   - Verified by [`src/engine/jd_detector.py`](src/engine/jd_detector.py) to require a Juris Doctor or active Bar license (disqualifies administrative, paralegal, recruiting, and operations roles).
6. **1–4 Years Experience Gate**:
   - Verified by [`src/engine/exp_parser.py`](src/engine/exp_parser.py). Roles requiring 5+, 7+, 10+ years, Senior Counsel, Partner, or General Counsel are strictly disqualified.

---

## 🎯 Resume Match Engine & Scoring Formula

Implemented in [`src/engine/resume_matcher.py`](src/engine/resume_matcher.py) and [`src/engine/candidate_profile.py`](src/engine/candidate_profile.py):

$$\text{Final Score} = \text{Base Hard Gates (50)} + \text{Dim 1 (20)} + \text{Dim 2 (15)} + \text{Dim 3 (10)} + \text{Dim 4 (5)}$$

| Dimension | Max Points | Criteria & Award Logic |
| :--- | :---: | :--- |
| **Hard Gates** | **50 pts** | Awarded automatically for passing all 6 eligibility gates. |
| **Dim 1: Practice Fit** | **20 pts** | **+20 pts**: Legal AI / Legal Engineer role &bull; **+20 pts**: Entertainment & Media Studio In-House &bull; **+18 pts**: Corporate / Commercial Counsel &bull; **+16 pts**: BigLaw Corporate Associate. |
| **Dim 2: Superpowers** | **15 pts** | **+6 pts**: AI workflows, LLM prompt engineering, GenAI &bull; **+5 pts**: Entertainment licensing, distribution, copyright &bull; **+4 pts**: Commercial contract drafting, discovery, motion practice. |
| **Dim 3: Experience Timing** | **10 pts** | **+10 pts (Prime)**: Explicit 1–3 years / Class of 2023 / 2nd-year associate &bull; **+5 pts (Reach)**: 3–4 years or 2–4 years reach &bull; **+6 pts**: Associate level unstated. |
| **Dim 4: Employer Affinity** | **5 pts** | **+5 pts**: Former employer alumni (*MGM Studios / NBCUniversal*) &bull; **+5 pts**: Entertainment peer (*Sony, Disney, Paramount, Live Nation, Riot*) &bull; **+5 pts**: BigLaw peer (*DLA Piper, Greenberg Traurig, Cooley*). |

---

## 🌐 Multi-Source Scraping Pipeline

All scrapers are orchestrated by [`src/scrapers/aggregator.py`](src/scrapers/aggregator.py):

1. **LinkedIn Direct Scraper** ([`src/scrapers/jobspy_scraper.py`](src/scrapers/jobspy_scraper.py)):
   - Executes multi-query search across 16 targeted legal and AI search phrases in Los Angeles.
2. **EntertainmentCareers.net Scraper** ([`src/scrapers/entertainmentcareers_scraper.py`](src/scrapers/entertainmentcareers_scraper.py)):
   - Multi-threaded parallel fetching across 10 entertainment legal categories.
   - Extracts exact posting dates from **JSON-LD Schema** (`<script type="application/ld+json">`).
   - Automatically skips filled or employer-removed listings.
3. **SmartRecruiters ATS REST API Scraper** ([`src/scrapers/smartrecruiters_scraper.py`](src/scrapers/smartrecruiters_scraper.py)):
   - Direct JSON API queries against official company boards: **NBCUniversal**, **Live Nation**, **Ubisoft**, **Square Enix**, **SEGA**, **Publicis Groupe**, **Avery Dennison**, **Mirantis**, **Axiado**, **Visa**, **Bosch**, **Cerebras**, **Epic Games**.
4. **Greenhouse & Lever ATS Scraper** ([`src/scrapers/ats_scraper.py`](src/scrapers/ats_scraper.py)):
   - Direct board queries for tech & gaming companies in LA (*Riot Games, SpaceX, Snap, Hulu, Netflix*).
5. **Multi-Threaded Description & Salary Hydrator** ([`src/scrapers/hydrator.py`](src/scrapers/hydrator.py)):
   - Background worker ensuring 100% of jobs have full multi-thousand-character descriptions.

---

## 💵 Universal Compensation & Salary Parser

Implemented in [`src/engine/salary_parser.py`](src/engine/salary_parser.py):
- Parses prefixed ranges: `$144,000 - $187,000` &rarr; `💵 $144k – $187k/yr`
- Parses un-prefixed decimal pay: `70,400.00 - 101,800.00 USD annually` &rarr; `💵 $70k – $102k/yr`
- Parses hourly wages: `$47.00 - $154.00 per hour` &rarr; `💵 $47 – $154/hr`
- Parses single compensation figures: `$225,000 / year` &rarr; `💵 $225k/yr`

---

## 📍 Geographic Proximity Engine (Anchored to 90038)

All job proximities are calculated from the central home anchor **`90038`** (*Hollywood, Los Angeles, CA* — `34.0888° N, 118.3308° W`) using the spherical **Haversine formula**:

| Target Hub | Distance from 90038 | Major Employers in Hub |
| :--- | :---: | :--- |
| **Hollywood** | **0.3 mi** | Paramount Pictures, Netflix, Sunset Studios |
| **Universal City** | **3.7 mi** | NBCUniversal, Telemundo, Focus Features |
| **Beverly Hills** | **4.1 mi** | Live Nation Entertainment, United Talent Agency (UTA), Buyerlink |
| **Century City** | **5.5 mi** | CAA, Fox Corporation, Greenberg Traurig |
| **Downtown LA (DTLA)** | **5.8 mi** | DLA Piper, Pillsbury Winthrop, Cooley LLP |
| **Culver City** | **6.0 mi** | Amazon MGM Studios, Prime Video, Sony Music Publishing |
| **Burbank** | **6.5 mi** | The Walt Disney Studios, Warner Bros. Discovery |
| **Westwood** | **6.8 mi** | LMU / UCLA Area, Westside firms |
| **Santa Monica** | **10.4 mi** | Riot Games, AWS Legal, Lionsgate |
| **Commerce** | **11.5 mi** | AltaMed Health Services Headquarters |
| **Hawthorne** | **12.0 mi** | SpaceX Corporate & Starlink Legal |
| **El Segundo** | **12.7 mi** | KRAFTON Inc. (PUBG), Tech & Gaming |

---

## 🎛️ Dashboard Features & Sorting Modes

The real-time local web application is located at [`src/dashboard/`](src/dashboard/):

- **Dynamic Category Filter Pills**: Automatically calculates active counts and **hides categories with 0 jobs** (e.g. hides *Legal Engineer* when 0 postings match).
- **4 Instant Sort Modes**:
  1. 🎯 **Sort by MATCH Score**: Highest match (100% &rarr; 75%) first.
  2. 💵 **Sort by PAY / Salary**: Highest annualized compensation first ($365k &rarr; $70k).
  3. 🕒 **Sort by Date (Newest)**: Orders by posting recency (🔥 Today &rarr; 🕒 1d &rarr; 🕒 2d &rarr; 🕒 1w).
  4. 📍 **Sort by Distance**: Orders by closest proximity from `90038` Hollywood.
- **Candidate Hero Card**: Highlights California Bar admission, Harvey certification, and focus areas.
- **Expandable Complete Descriptions**: Formatted with clean section headers (`📌`), indents, and character encoding mojibake fixes.
- **Application Tracking**: Toggle jobs as ⭐ *Saved* or ✅ *Applied*.

---

## 🚀 Quickstart & CLI Usage

### Prerequisites
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Command Line Tools
| Command | Description |
| :--- | :--- |
| `python main.py --dashboard` | Launches the interactive dashboard on **`http://localhost:8000`** |
| `python main.py --scrape` | Runs all scrapers, evaluates jobs, and updates SQLite database |
| `python main.py --digest` | Generates a standalone HTML daily digest in `data/digests/` |
| `python main.py --daily` | Runs full daily pipeline (scrape &rarr; score &rarr; digest &rarr; notifications) |
| `pytest` | Runs the automated test suite across all modules |

---

## ⏰ Daily Automations & GitHub Actions

### 1. Local Windows Task Scheduler
To automatically run the scraper every morning at 8:00 AM:
```powershell
powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1
```

### 2. GitHub Actions CI/CD
A cloud workflow is configured at [`.github/workflows/daily_jobs.yml`](.github/workflows/daily_jobs.yml) to execute daily scrapes, run tests, and generate briefing artifacts automatically on GitHub.

---

## 🌐 Live Dashboard
Start the dashboard anytime with:
```bash
python main.py --dashboard
```
And navigate to: **[http://localhost:8000](http://localhost:8000)**
