<div align="center">
  <h1>🚀 LeadForge AI</h1>
  <p><strong>The Autonomous Multi-Persona Scraper & AI Email Engine</strong></p>
  
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Next.js](https://img.shields.io/badge/Next.js-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
  [![Playwright](https://img.shields.io/badge/Playwright-45ba4b?style=for-the-badge&logo=Playwright)](https://playwright.dev/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
  [![Groq](https://img.shields.io/badge/Groq-f55036?style=for-the-badge&logo=groq)](https://groq.com)
</div>

<hr>

## 🧠 What is LeadForge?

LeadForge is an elite, open-source AI Sales and Networking SaaS. It completely automates the process of identifying prospects, auditing their online footprint, and drafting hyper-personalized cold outreach sequences.

Whether you are an **Agency** looking for B2B Clients, a **Freelancer** seeking contract work, or a **Software Engineer** hunting for a high-paying job, LeadForge dynamically alters its scraping logic and AI prompt systems to fit your exact *Persona*.

---

## ⚡ Core Architecture

LeadForge is built with a heavy emphasis on bypass resilience and AI orchestration via a powerful separation of concerns:

- **Frontend (Next.js/React):** A beautiful glassmorphism dashboard to manage Campaign tracking, Email logs, and dynamic User Personas.
- **Backend (Python FastAPI):** Handles background task execution, database modeling, and the Sequence Engine loop.
- **The Scraper (Playwright & curl_cffi):** Deploys stealth browsers rotating residential proxies to bypass Cloudflare and scrape Google Maps listings natively.
- **Auditor & AI (Groq & Llama3):** Audits HTML DOM structures and scores target companies. The Multi-Agent Swarm then drafts contextual multi-step sequences (e.g., Pitch -> Bump -> Breakup).

---

## 🚀 Key Features

*   **Multi-Persona Swarm:** Create specific profiles for Job Hunting, Freelance, or Agency. The AI Strategist reads the scraped company data and pitches you perfectly based on your exact playbook.
*   **Automated Background Sequence Engine:** A natively built chronological background loop. If a prospect hasn't replied in 3 days, the engine automatically drafts an AI Follow-up and dispatches it via SMTP. 
*   **Automated "Kill Switch":** Click "Mark Replied" in the UI and the backend severs the specific lead from the sequence loops to prevent accidental spam.
*   **Database Integrated SMTP:** Manage email connection strings securely inside the dashboard rather than hardcoded `.env` files.
*   **Deep Website Auditing:** Detects exact Tech Stacks, missing mobile optimization, and extracts decision-maker emails hidden deep in HTML footers.

---

## 💻 Tech Stack Setup

### 1. Requirements
* Python 3.10+
* Node.js v18+
* PostgreSQL DB Instance
* Groq API Key (For high-speed LLM interference)
* An SMTP account (e.g., Gmail App Password)

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:password@localhost/leadforge
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
SIMULATE_EMAIL=True # Set to False to send real emails
```

### 3. Running Locally (Development)

**Start the Backend:**
```bash
pip install -r requirements.txt
playwright install chromium
uvicorn api.server:app --reload --port 8000
```

**Start the Next.js UI:**
```bash
cd frontend
npm install
npm run dev
```
Access the dashboard at `http://localhost:3000`.

---

## 🐳 Docker Production Setup
For VPS deployment (e.g., DigitalOcean), LeadForge is fully containerized. 

```bash
docker-compose up --build -d
```
*This instantly provisions the PostgreSQL DB, the FastAPI server, the Playwright dependencies, and mounts the volumes securely.*

---

## 📜 Legal Disclaimer
LeadForge is built for responsible B2B outreach and analytical auditing. Users must comply with their local SPAM laws (CAN-SPAM, GDPR) when dispatching sequences via the SMTP Engine. Playwright scraping components must be used ethically respecting `robots.txt` when possible.

---
<div align="center">
  <i>Developed to automate the hustle.</i>
</div>
