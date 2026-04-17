# LeadForge AI — Automated Prospecting & Outreach Tool

**LeadForge AI** is a highly capable SaaS tool that automates the entire B2B prospecting lifecycle. It aggressively scrapes local business leads from Google Maps, programmatically audits their websites for SEO/UX flaws, and generates hyper-personalized, high-converting cold emails tailored directly to the specific weaknesses it found. 

## Who It's For
Built specifically for **Freelance Web Developers, Digital Marketing Agencies, and SEO Consultants** who need a constant stream of qualified local business leads but want to eliminate the soul-crushing manual work of finding them and evaluating their websites.

---

## Features
- **Intelligent Local Scraping**: Pulls highly targeted leads from Google Maps. 
- **Deep Website Inspection**: Programmatically scans websites for missing components (H1 tags, Mobile Viewports, Contact Forms, SSL certificates).
- **Tech Stack Detection**: Detects if targets are running WordPress, Shopify, Wix, or Squarespace.
- **Lead Opportunity Scoring**: Assigns a mathematically driven 0-100 opportunity score, highlighting clients with the most website flaws first.
- **AI-Powered Outreach Engine**: Uses high-speed Llama 3 models via Groq to craft unique cold emails dynamically referencing the exact missing features. Includes prompt-rotation to prevent sending duplicate emails.
- **Visual Evidence**: Captures full mobile-viewport screenshots to visually show business owners their broken mobile experiences.
- **Enterprise Database**: Powered by PostgreSQL and structured with SQLAlchemy.
- **Polite & Safe**: Rotates 15 modern user-agents, adds randomized human delays, and respects robots.txt.

---

## How It Works

```text
[ Input: Niche + Location ] 
            │
            ▼
[ Scrape Google Maps & Websites ] 
            │
            ▼
[ Audit: SEO, UX, SSL, Forms ] 
            │
            ▼
[ Score Lead & Inject into Prompt ] 
            │
            ▼
[ Generate Highly Personalized Email ] 
            │
            ▼
[ Export Complete CSV DataFrame ] 
```

---

## Tech Stack
| Technology | Functionality | Why It Was Chosen |
| :--- | :--- | :--- |
| **Python 3.10+** | Core Logic | Rapid development and unbeatable data ecosystem. |
| **Playwright** | Headless Scraping & Screenshots | Faster and more reliable than Selenium for dynamic pages. |
| **BeautifulSoup 4** | HTML DOM Parsing | Lightning fast for rule-based SEO and UX checks. |
| **PostgreSQL** | Enterprise Database | Handles concurrent connections and complex JSONB columns. |
| **SQLAlchemy** | ORM | Clean schema modeling and database agnostic features. |
| **Groq API** | Large Language Model | Insanely fast Llama-3 inference on a generous free tier. |
| **Loguru** | Application Logging | Superior terminal formatting and auto file-rotation. |
| **Pandas** | Tabular Processing | Powerful automated CSV building and sorting. |

---

## Installation

1. **Clone Repo**
```bash
git clone https://github.com/yourusername/leadforge-ai.git
cd leadforge-ai
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
playwright install chromium
```

4. **Environment Variables**
```bash
cp .env.example .env
# Open .env and add your free Groq API key: https://console.groq.com/
```

5. **Start PostgreSQL Database** (if using Docker)
```bash
docker-compose up -d
```

6. **Run the SaaS**
```bash
python main.py --niche "Plumbers" --location "Dubai" --max-leads 30
```

---

## Configuration

Control the engine by editing `config.yaml`:
- `max_leads_per_run`: Limit total extractions per queue.
- `delay_between_requests_min/max`: Used to define random human-like pacing delays.
- `screenshot_enabled`: Toggles Playwright mobile screenshot feature.
- `llm_provider`: Switch between "groq" (cloud) or "ollama" (local).
- `db_type`: Switch backend from "postgresql" to local "sqlite" if needed.

---

## Output Format

The engine exports to `output/` with a color-coding convention applied to the CSV. The exact headers are:

| business_name | address | phone | email | website | instagram | facebook | linkedin | rating | review_count | tech_stack | opportunity_score | https_missing | mobile_friendly | has_h1 | has_meta_desc | has_contact_form | has_tracking | screenshot_path | email_draft | pitch_angle_used | audit_findings_summary | status |

*Note: High opportunity scores (>70) indicate prime targets.*

**Example Output Row:**
`Acme Plumbing LLC | 123 Main St, Dubai | +971 50 123 4567 | info@acme.com | acme.com | ... | 4.2 | 8 | WordPress | 85 | Yes | No | No | No | No | No | /screenshots/Acme_Plumbing_LLC.png | ...`

---

## Example Email Generated

Instead of generic spam, the engine outputs contextually relevant drafts.

> Hi John,
>
> I was looking up plumbers in Dubai and found Acme Plumbing's site. I noticed your page currently lacks a mobile-responsive viewport tag, which makes it really hard for mobile visitors to click your phone number. Additionally, your site is missing a secure SSL certificate, which might be causing Google to flag it with a "Not Secure" warning to potential customers.
>
> We specialize in fixing exactly these technical issues to increase daily inbound calls. Would it be worth a quick 10-minute chat this week to see how we could help?
>
> Best,
> Alex

---

## Legal & Ethical Use
Data scraping and cold email outreach are heavily monitored disciplines. By using this tool, you acknowledge the terms listed in `LEGAL_DISCLAIMER.txt`. You are entirely responsible for CAN-SPAM, CASL, and GDPR compliance when emailing these leads. Do not utilize this system to spam. Use the intelligence provided to send high-value, highly-targeted offers.

---

## Roadmap
- [ ] Next.js React Dashboard GUI.
- [ ] End-to-end SMTP Mailgun integration (Send emails directly from DB).
- [ ] Multi-tenant Campaign Management.
- [ ] White-label feature for selling this as a service to sub-agencies.

---

## License 
MIT License. See `LICENSE` for more information.
