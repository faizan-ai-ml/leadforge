# Changelog

All notable changes to this project will be documented in this file.

## [v0.2.0] - Architecture Upgrade
### Added
- Complete rewrite into a modular SaaS architecture (`scraper/`, `auditor/`, `ai/`, `database/`).
- Migrated primary AI from Gemini to free Groq API (Llama 3) with local Ollama fallback.
- Replaced SQLite with robust PostgreSQL using SQLAlchemy.
- Upgraded Website Auditor with comprehensive SEO, Mobile/UX, Trust, and Technical stack checks using BeautifulSoup.
- Implemented Lead Opportunity Scoring system (0-100) to prioritize high-value targets.
- Built advanced AI Email Generator with 4-angle prompt rotation and spam word detection.
- Introduced polite web scraping features: rotating User-Agents, random exponential backoff, and robots.txt evaluation.
- Added automated mobile viewport feature, capturing screenshots of prospect websites via Playwright.

## [v0.1.0] - Initial MVP
### Added
- Local script-based MVP to extract Google Maps listings.
- Playwright-powered basic web extraction.
- Offline SQLite tracking.
- Simple Gemini AI integration for basic summarization.
