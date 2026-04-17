from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import asyncio
import sys
from loguru import logger

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
import io
import csv
from fastapi.responses import StreamingResponse

from database.db import init_db, SessionLocal
from database.models import Campaign, Lead, SMTPConfig, EmailLog, UserPersona
import subprocess
from output.smtp_sender import send_email_blast
from ai.email_generator import generate_followup_email

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="LeadForge API SaaS")

# Allow Frontend to hit the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CampaignRequest(BaseModel):
    niche: str
    location: str
    max_leads: int = 10
    persona_id: int = None

class PersonaRequest(BaseModel):
    name: str
    objective: str
    resume_text: str = ""
    skills: str = ""
    value_proposition: str = ""

class SMTPConfigRequest(BaseModel):
    host: str
    port: int
    username: str
    password: str

def advance_campaign_sequence(campaign_id: int, db: Session, smtp_config: dict):
    leads = db.query(Lead).filter(Lead.campaign_id == campaign_id, Lead.status == 'emailed').all()
    results = {"advanced": 0, "errors": 0}
    for lead in leads:
        last_log = db.query(EmailLog).filter(EmailLog.lead_id == lead.id).order_by(EmailLog.step_number.desc()).first()
        if not last_log or last_log.status != "emailed":
            continue
            
        now = datetime.utcnow()
        days_since_sent = (now - last_log.sent_at).days
        # Override for testing: pretend days passed if testing
        if "--test-sequence" in sys.argv:
             days_since_sent += 5
             
        next_step = 0
        if last_log.step_number == 1 and days_since_sent >= 3:
            next_step = 2
        elif last_log.step_number == 2 and days_since_sent >= 4:
            next_step = 3
            
        if next_step > 0:
            logger.info(f"Advancing Lead {lead.id} to sequence step {next_step}...")
            draft = generate_followup_email(lead.business_name, next_step, lead.email_draft)
            if not draft: continue
            lead_dict = [{"id": lead.id, "business_name": lead.business_name, "email": lead.email, "email_draft": draft}]
            try:
                blast_res = send_email_blast(lead_dict, smtp_config=smtp_config)
                for detail in blast_res.get("details", []):
                    status = detail["status"]
                    db.add(EmailLog(lead_id=lead.id, campaign_id=campaign_id, step_number=next_step, status=status, error_message=detail.get("reason", "")))
                    if status == "emailed":
                        results["advanced"] += 1
            except Exception as e:
                logger.error(f"Sequence Error: {e}")
                results["errors"] += 1
    db.commit()
    return results

def advance_all_sequences(db: Session):
    config = db.query(SMTPConfig).order_by(SMTPConfig.id.desc()).first()
    if not config or not config.username: return
    smtp_config = {"host": config.host, "port": config.port, "username": config.username, "password": config.password}
    for camp in db.query(Campaign).all():
        try:
             advance_campaign_sequence(camp.id, db, smtp_config)
        except Exception as e:
             logger.error(f"Error testing campaign {camp.id}: {e}")

async def background_sequence_worker():
    """Endless loop that checks for daily sequences."""
    while True:
        try:
            logger.info("Running Automatic Sequence Worker...")
            db = SessionLocal()
            try:
                advance_all_sequences(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Sequence worker error: {e}")
        await asyncio.sleep(3600)

@app.on_event("startup")
def startup_event():
    init_db()
    asyncio.create_task(background_sequence_worker())

@app.get("/api/personas")
def list_personas(db: Session = Depends(get_db_session)):
    return db.query(UserPersona).all()

@app.post("/api/personas")
def create_persona(req: PersonaRequest, db: Session = Depends(get_db_session)):
    persona = UserPersona(
        name=req.name,
        objective=req.objective,
        resume_text=req.resume_text,
        skills=req.skills,
        value_proposition=req.value_proposition
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona

@app.post("/api/campaigns")
def create_campaign(req: CampaignRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db_session)):
    # 1. Instantly create the database record
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{req.niche} in {req.location} - {timestamp}"
    
    new_campaign = Campaign(name=name, niche=req.niche, location=req.location, persona_id=req.persona_id)
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    
    # 2. Fire the scraper pipeline in a dedicated OS process to isolate Playwright's event loop
    subprocess.Popen([
        sys.executable, "main.py",
        "--niche", req.niche,
        "--location", req.location,
        "--max-leads", str(req.max_leads),
        "--campaign-id", str(new_campaign.id)
    ])
    
    return {"message": "Campaign queued successfully", "campaign_id": new_campaign.id, "name": new_campaign.name}

@app.get("/api/settings/smtp")
def get_smtp_config(db: Session = Depends(get_db_session)):
    config = db.query(SMTPConfig).order_by(SMTPConfig.id.desc()).first()
    if config:
        return {
            "host": config.host or "smtp.gmail.com",
            "port": config.port or 587,
            "username": config.username or "",
            "password": config.password or "",
            "is_active": config.is_active
        }
    return {"host": "smtp.gmail.com", "port": 587, "username": "", "password": ""}

@app.post("/api/settings/smtp")
def save_smtp_config(req: SMTPConfigRequest, db: Session = Depends(get_db_session)):
    config = db.query(SMTPConfig).order_by(SMTPConfig.id.desc()).first()
    if not config:
        config = SMTPConfig()
        db.add(config)
    config.host = req.host
    config.port = req.port
    config.username = req.username
    config.password = req.password
    db.commit()
    return {"message": "SMTP configuration saved"}

@app.get("/api/campaigns")
def list_campaigns(db: Session = Depends(get_db_session)):
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "niche": c.niche,
            "location": c.location,
            "created_at": c.created_at
        }
        for c in campaigns
    ]

@app.get("/api/campaigns/{campaign_id}")
def get_campaign(campaign_id: int, db: Session = Depends(get_db_session)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).all()
    return {
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
            "niche": campaign.niche,
            "location": campaign.location,
            "created_at": campaign.created_at
        },
        "leads": [
            {
                "id": l.id,
                "business_name": l.business_name,
                "phone": l.phone,
                "website": l.website,
                "opportunity_score": l.opportunity_score,
                "tech_stack": l.tech_stack,
                "status": l.status,
                "email_draft": l.email_draft
            } for l in leads
        ],
        "leads_count": len(leads)
    }

@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db_session)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.post("/api/leads/{lead_id}/replied")
def mark_lead_replied(lead_id: int, db: Session = Depends(get_db_session)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = "replied"
    db.commit()
    return {"message": "Lead marked as replied. Sequence stopped."}

@app.post("/api/campaigns/{campaign_id}/force_sequence")
def force_sequence(campaign_id: int, db: Session = Depends(get_db_session)):
    config = db.query(SMTPConfig).order_by(SMTPConfig.id.desc()).first()
    if not config or not config.username:
         raise HTTPException(status_code=400, detail="SMTP Configuration missing.")
    smtp_config = {"host": config.host, "port": config.port, "username": config.username, "password": config.password}
    
    # Temporarily trick the script to override dates
    sys.argv.append("--test-sequence") 
    res = advance_campaign_sequence(campaign_id, db, smtp_config)
    sys.argv.remove("--test-sequence")
    
    return {"message": "Force sequence check complete", "results": res}

@app.post("/api/campaigns/{campaign_id}/send")
def send_campaign_emails(campaign_id: int, db: Session = Depends(get_db_session)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Get all audited leads that haven't been sent yet and actually have an email
    leads = db.query(Lead).filter(
        Lead.campaign_id == campaign_id,
        Lead.status == "audited", 
        Lead.email != None,
        Lead.email != "",
        Lead.email_draft != None
    ).all()
    
    if not leads:
        return {"message": "No valid leads found ready to email. (Must have an email extracted)", "results": {"success": 0}}
        
    # Serialize to dictionary for the SMTP function
    dict_leads = [{"id": l.id, "business_name": l.business_name, "email": l.email, "email_draft": l.email_draft} for l in leads]
        
    config = db.query(SMTPConfig).order_by(SMTPConfig.id.desc()).first()
    smtp_config = None
    if config and config.username and config.password:
        smtp_config = {
            "host": config.host,
            "port": config.port,
            "username": config.username,
            "password": config.password
        }

    # Fire the SMTP pipeline
    try:
        results = send_email_blast(dict_leads, smtp_config=smtp_config)
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"SMTP Infrastructure Error: {e}")
         
    # Update DB status based on SMTP results
    for detail in results.get("details", []):
         lead_id = detail["id"]
         status = detail["status"] # "emailed", "failed"
         
         # Save EmailLog
         error_msg = detail.get("reason", "")
         email_log = EmailLog(lead_id=lead_id, campaign_id=campaign_id, step_number=1, status=status, error_message=error_msg)
         db.add(email_log)
         
         if status == "emailed":
              db_lead = db.query(Lead).filter(Lead.id == lead_id).first()
              if db_lead:
                  db_lead.status = "emailed"
                  
    db.commit()
    return {"message": "Email sequence complete", "results": results}

@app.get("/api/campaigns/{campaign_id}/export")
def export_campaign_csv(campaign_id: int, db: Session = Depends(get_db_session)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        "Business Name", "Phone", "Email", "Website", "Address",
        "Opportunity Score", "Status", "Tech Stack", "Facebook", "Instagram", "LinkedIn", "AI Pitch Angle", "Email Draft"
    ])
    
    for l in leads:
        writer.writerow([
            l.business_name,
            l.phone,
            l.email,
            l.website,
            l.address,
            l.opportunity_score,
            l.status,
            l.tech_stack,
            l.facebook,
            l.instagram,
            l.linkedin,
            l.pitch_angle_used,
            l.email_draft
        ])
        
    output.seek(0)
    
    # Format a safe filename
    safe_name = "".join(c for c in campaign.name if c.isalnum() or c in (' ', '_', '-')).replace(' ', '_')
    filename = f"LeadForge_{safe_name}.csv"
    
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

