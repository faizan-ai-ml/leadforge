import argparse
import asyncio
import os
import time
from datetime import datetime
from loguru import logger
import yaml

from database.db import init_db, get_db
from database.models import Campaign, Lead, UserPersona
from scraper.google_maps import extract_google_maps_leads
from scraper.website_scraper import scrape_website_html
from scraper.screenshot import capture_screenshot
from auditor.rule_engine import audit_html
from auditor.scorer import calculate_opportunity_score, format_audit_summary_for_ai
from ai.email_generator import generate_cold_email
from output.csv_writer import export_leads_to_csv

# Load Config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
    log_dir = config.get("log_folder", "logs/")

os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logger.add(os.path.join(log_dir, f"run_{timestamp}.log"), rotation="5 MB", level="INFO")

async def process_campaign(niche: str, location: str, max_leads: int, pre_campaign_id: int = None):
    runtime_start = time.time()
    
    logger.info("=" * 60)
    logger.info(f"STARTING CAMPAIGN: {niche} in {location}")
    logger.info("=" * 60)
    
    # 1. Init Database & Campaign
    init_db()
    
    persona = None
    if pre_campaign_id:
        campaign_id = pre_campaign_id
        logger.info(f"Using provided Campaign ID from API: {campaign_id}")
        with get_db() as db:
            camp = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if camp and camp.persona_id:
                persona = db.query(UserPersona).filter(UserPersona.id == camp.persona_id).first()
    else:
        with get_db() as db:
            if db:
                campaign = Campaign(name=f"{niche} in {location} - {timestamp}", niche=niche, location=location)
                db.add(campaign)
                db.commit()
                db.refresh(campaign)
                campaign_id = campaign.id
            else:
                campaign_id = None
                logger.warning("Running without PostgreSQL connection. Data won't be saved to DB.")
            
    # 2. Scrape Google Maps
    initial_leads = await extract_google_maps_leads(niche, location, max_leads)
    
    if not initial_leads:
        logger.error("No leads found. Aborting pipeline.")
        return
        
    enriched_leads = []
    stats = {"scraped": len(initial_leads), "audited": 0, "emails": 0, "errors": 0}
    
    # 3. Process Each Lead
    for idx, lead_data in enumerate(initial_leads, 1):
        try:
            name = lead_data["business_name"]
            url = lead_data["website"]
            logger.info(f"[{idx}/{len(initial_leads)}] Processing: {name}")
            
            if not url:
                logger.warning(f"  Skipping deep audit for {name} - No website found.")
                lead_data["status"] = "skipped"
                enriched_leads.append(lead_data)
                continue
                
            # Phase 3a: Website HTML Scrape
            site_data = scrape_website_html(url)
            
            if site_data["blocked"]:
                 logger.warning(f"  {name} blocked our scraper. Marking as site_blocked.")
                 lead_data["status"] = "site_blocked"
                 enriched_leads.append(lead_data)
                 continue
                 
            # Merge scraped socials and emails
            for key in ["email", "facebook", "instagram", "linkedin"]:
                if site_data[key]: lead_data[key] = site_data[key]
                
            # Phase 3b: Automated Screenshot
            screenshot_path = await capture_screenshot(url, name)
            lead_data["screenshot_path"] = screenshot_path
                
            # Phase 4a: Rule-based Audit
            findings = audit_html(site_data["html"], url)
            
            # Extract detected tech stack and scraped emails
            lead_data["tech_stack"] = findings["tech"]["stack"]
            if not lead_data.get("email") and findings.get("contact", {}).get("emails"):
                # Pick the highest priority email. Natively regex grabs anything, we just take the first valid one
                # Usually info@ or contact@ shows up early in footers.
                lead_data["email"] = findings["contact"]["emails"][0]
            
            # Phase 4b: Opportunity Scoring
            score = calculate_opportunity_score(findings, lead_data.get("review_count", 0))
            lead_data["opportunity_score"] = score
            lead_data["audit_findings"] = findings
            
            summary = format_audit_summary_for_ai(findings)
            lead_data["audit_findings_summary"] = summary
            stats["audited"] += 1
            
            # Phase 5: AI Email Generation
            if lead_data.get("email") or True: # We generate it regardless, in case user finds email manually later
                draft, angle = generate_cold_email(name, summary, persona)
                if draft:
                     lead_data["email_draft"] = draft
                     lead_data["pitch_angle_used"] = angle
                     stats["emails"] += 1
                     
            lead_data["status"] = "audited"
            enriched_leads.append(lead_data)
            logger.info(f"  Successfully enriched & audited {name} (Score: {score})")
            
        except Exception as e:
            logger.error(f"Failed processing lead {lead_data.get('business_name')}: {e}")
            stats["errors"] += 1
            lead_data["status"] = "error"
            enriched_leads.append(lead_data)
            
    # 4. Save to Database
    if campaign_id:
        with get_db() as db:
            for ld in enriched_leads:
                 db_lead = Lead(
                     campaign_id=campaign_id,
                     business_name=ld.get("business_name"),
                     address=ld.get("address"),
                     phone=ld.get("phone"),
                     email=ld.get("email"),
                     website=ld.get("website"),
                     instagram=ld.get("instagram"),
                     facebook=ld.get("facebook"),
                     linkedin=ld.get("linkedin"),
                     rating=str(ld.get("rating", "")),
                     review_count=ld.get("review_count", 0),
                     tech_stack=ld.get("tech_stack"),
                     screenshot_path=ld.get("screenshot_path"),
                     opportunity_score=ld.get("opportunity_score", 0),
                     audit_findings=ld.get("audit_findings", {}),
                     email_draft=ld.get("email_draft"),
                     pitch_angle_used=ld.get("pitch_angle_used"),
                     status=ld.get("status")
                 )
                 db.add(db_lead)
            db.commit()
            logger.info("Saved all enriched DB logic successfully.")
            
    # 5. Export to CSV Format requested
    export_leads_to_csv(enriched_leads)
    
    # 6. End Run Logging Summary
    runtime_m, runtime_s = divmod(int(time.time() - runtime_start), 60)
    logger.info("=" * 60)
    logger.info("RUN COMPLETE")
    logger.info(f"Total scraped: {stats['scraped']} | Successfully audited: {stats['audited']} | Emails generated: {stats['emails']} | Errors: {stats['errors']} | Runtime: {runtime_m}m {runtime_s}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LeadForge AI Prospecting SaaS")
    parser.add_argument("--niche", type=str, required=True, help="Target business niche (e.g. 'Plumbers')")
    parser.add_argument("--location", type=str, required=True, help="Target location (e.g. 'Dubai')")
    parser.add_argument("--max-leads", type=int, default=10, help="Maximum number of leads to scrape")
    parser.add_argument("--campaign-id", type=int, default=None, help="Assigned Campaign ID from API")
    
    args = parser.parse_args()
    
    # Load default limit config to prevent massive accidental bills
    with open("config.yaml", "r") as f:
        conf = yaml.safe_load(f)
        max_limit = conf.get("max_leads_per_run", 50)
        final_max = min(args.max_leads, max_limit)
        
    asyncio.run(process_campaign(args.niche, args.location, final_max, args.campaign_id))
