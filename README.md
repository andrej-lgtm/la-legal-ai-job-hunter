# ⚖️ Los Angeles Legal & AI Job Hunter

An automated daily job intelligence engine targeting legal, in-house, and legal-AI opportunities in **Los Angeles and the LA Metro area** requiring a **JD** and **1–3 years of experience**.

---

## 🎯 Target Criteria
- **Target Roles**:
  - 🏢 **In-House / Corporate Counsel** (Junior Corporate Counsel, Commercial Counsel, Associate Legal Counsel)
  - ⚖️ **Associate Counsel** (Law firm / institutional counsel 1–3 years)
  - 🛠️ **Legal Engineer / Legal Ops** (Legal Engineer, Legal Technologist, Solutions Engineer)
  - 🤖 **Legal & AI** (AI Governance, AI Policy, Generative AI Legal, Prompt Engineer Legal)
- **Target Experience**: 1–3 years (rejects senior 5+, 7+, 10+ year roles, while prioritizing junior & associate openings).
- **Target Degree**: JD required / California Bar admission.
- **Target Locations**: Los Angeles, Santa Monica, Century City, Culver City, Pasadena, Burbank, Irvine/OC, + CA Remote.

---

## 🚀 Quick Start

### 1. Run the Daily Job Hunter (Immediate)
```bash
python main.py --run-now
```
This fetches the latest postings from LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, and direct LegalTech ATS boards (Greenhouse, Lever), evaluates each role, updates `data/jobs.db`, and creates a standalone HTML briefing in `data/digests/daily_digest_YYYY-MM-DD.html`.

### 2. Launch the Interactive Local Web Dashboard
```bash
python main.py --dashboard
```
Open **`http://localhost:8000`** in your browser to:
- Browse and search all matches.
- Filter by category (*In-House*, *Legal AI*, *Legal Engineer*, *Associate Counsel*).
- Track job statuses (*Active*, *Saved*, *Applied*).
- Click 1-click **Apply** buttons.
- Trigger on-demand scrapes directly from the browser.

---

## ⚙️ Configuration (`config.yaml`)
You can easily adjust search queries, target cities, and notifications in [`config.yaml`](config.yaml):
- **Email Digest**: Set `notifications.email.enabled: true` and enter your SMTP details.
- **Discord / Slack / Telegram**: Set `notifications.webhook.enabled: true` and paste your webhook URL.

---

## ⏰ Daily Automation

### Windows Task Scheduler (1-Click Local Automation)
Run PowerShell as Administrator and execute:
```powershell
.\setup_scheduler.ps1
```
This registers a daily task that runs automatically at **8:00 AM** in the background.

### GitHub Actions (Cloud Automation)
Push this repository to GitHub — a pre-configured workflow in `.github/workflows/daily_jobs.yml` will automatically run every morning in the cloud.

---

## 🧪 Running Tests
```bash
pytest
```
