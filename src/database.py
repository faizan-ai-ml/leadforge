import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'leads.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_source TEXT,
            search_query TEXT,
            name TEXT,
            category TEXT,
            rating TEXT,
            reviews TEXT,
            address TEXT,
            phone TEXT,
            website TEXT,
            email TEXT,
            facebook TEXT,
            instagram TEXT,
            linkedin TEXT,
            twitter TEXT,
            youtube TEXT,
            tiktok TEXT,
            tech_stack TEXT,
            has_contact_form TEXT,
            raw_website_text TEXT,
            company_summary TEXT,
            draft_email TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Gracefully add social & extra columns to existing database
    new_columns = ["facebook", "instagram", "linkedin", "twitter", "youtube", "tiktok", "tech_stack", "has_contact_form"]
    for col in new_columns:
        try:
            c.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
            
    conn.commit()
    conn.close()

def insert_lead(lead_source, search_query, lead_data):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO leads 
        (lead_source, search_query, name, category, rating, reviews, address, phone, website, email, facebook, instagram, linkedin, twitter, youtube, tiktok, tech_stack, has_contact_form, raw_website_text, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        lead_source,
        search_query,
        lead_data.get('name', ''),
        lead_data.get('category', ''),
        lead_data.get('rating', ''),
        lead_data.get('reviews', ''),
        lead_data.get('address', ''),
        lead_data.get('phone', ''),
        lead_data.get('website', ''),
        lead_data.get('email', ''),
        lead_data.get('facebook', ''),
        lead_data.get('instagram', ''),
        lead_data.get('linkedin', ''),
        lead_data.get('twitter', ''),
        lead_data.get('youtube', ''),
        lead_data.get('tiktok', ''),
        lead_data.get('tech_stack', ''),
        lead_data.get('has_contact_form', 'No'),
        lead_data.get('raw_website_text', ''),
        'Pending AI'
    ))
    conn.commit()
    conn.close()

def get_pending_leads():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM leads WHERE status = 'Pending AI'")
    leads = [dict(row) for row in c.fetchall()]
    conn.close()
    return leads

def update_lead_ai_data(lead_id, summary, draft):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE leads 
        SET company_summary = ?, draft_email = ?, status = 'Completed'
        WHERE id = ?
    ''', (summary, draft, lead_id))
    conn.commit()
    conn.close()

def update_lead_status(lead_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()

def export_to_csv(filename):
    import csv
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM leads ORDER BY created_at DESC")
    rows = c.fetchall()
    
    if not rows:
        print("  No leads in database to export.")
        return

    fieldnames = rows[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    conn.close()
    print(f"\n  ✅  Exported {len(rows)} leads to {filename}")

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
