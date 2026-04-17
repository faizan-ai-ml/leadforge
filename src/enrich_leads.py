import time
import os
from dotenv import load_dotenv
from google import genai
import database

def enrich_pending_leads():
    print("\n" + "═" * 52)
    print("   AI Lead Enricher (Background Job Runner)")
    print("═" * 52)

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = input("\n  Enter Gemini API Key: ").strip()
        
    if not api_key:
        print("  ⚠ No API key provided! Exiting.")
        return

    ai_client = genai.Client(api_key=api_key)
    
    leads = database.get_pending_leads()
    if not leads:
        print("  ✅  No 'Pending AI' leads found in the database. You are all caught up!")
        return
        
    print(f"\n  Found {len(leads)} leads pending AI enrichment.")
    print("  Starting background enrichment process (will respect Google's Rate Limits)...\n")
    
    last_ai_call_time = 0
    success_count = 0
    fail_count = 0
    
    for i, lead in enumerate(leads, 1):
        lead_id = lead['id']
        name = lead['name']
        website_text = lead['raw_website_text']
        business_type = lead['search_query'].split(" in ")[0] if " in " in (lead['search_query'] or "") else "business"
        
        print(f"  [{i}/{len(leads)}] Enriching: {name[:30]:<30} ", end="", flush=True)

        if not website_text or len(website_text.strip()) < 50:
            database.update_lead_ai_data(lead_id, "Not enough website data to analyze", "")
            database.update_lead_status(lead_id, "Failed (No Text)")
            fail_count += 1
            print("- ⚠ No text")
            continue
            
        text_to_analyze = website_text[:6000]
        
        prompt = f"""
You are an expert sales assistant. Read the following scraped website text from a '{business_type}'.
Based on this text, provide exactly two things separated by the delimiter '|||':
1) A short 1-sentence summary of what this business does and what makes them unique.
2) A short, highly personalized 2-to-3 sentence cold email drafted to the owner. Compliment them on a specific detail from their website history/about, point out that you can help them bring in more customers with a better website, and ask for a quick chat.

Website Text:
{text_to_analyze}
"""
        max_retries = 3
        success = False
        
        for attempt in range(max_retries):
            # Throttle 15 RPM to be safe. We pause right before the API call.
            elapsed = time.time() - last_ai_call_time
            if elapsed < 5.5:
                time.sleep(5.5 - elapsed)
                
            last_ai_call_time = time.time()

            try:
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                text_resp = response.text
                if not text_resp:
                    raise Exception("Empty Response")
                    
                parts = text_resp.split('|||')
                summary = parts[0].strip()
                draft = parts[1].strip() if len(parts) > 1 else ""
                
                database.update_lead_ai_data(lead_id, summary, draft)
                success_count += 1
                success = True
                print("- ✅ Done")
                break
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'quota' in error_msg or '429' in error_msg or 'exhausted' in error_msg or '503' in error_msg:
                    if attempt < max_retries - 1:
                        sleep_time = 15 * (attempt + 1)
                        print(f"\n      [!] Rate limit hit. Waiting {sleep_time}s to retry...", end="", flush=True)
                        time.sleep(sleep_time)
                        continue
                
                database.update_lead_ai_data(lead_id, f"AI Error: {str(e)}", "")
                database.update_lead_status(lead_id, "Failed")
                fail_count += 1
                print(f"- ❌ Error: {str(e)[:50]}")
                break
                
        if not success and attempt == max_retries - 1:
             # final attempt failed
             database.update_lead_status(lead_id, "Failed Rate Limit")
             
    print("\n" + "─" * 40)
    print(f"  Enrichment Complete!")
    print(f"  Successfully enriched : {success_count}")
    print(f"  Failed / Skipped    : {fail_count}")
    print("─" * 40 + "\n")
    
    # Export full DB to CSV
    os.makedirs(os.path.join(os.path.dirname(__file__), "output"), exist_ok=True)
    export_file = os.path.join(os.path.dirname(__file__), "output", f"all_enriched_leads_{int(time.time())}.csv")
    database.export_to_csv(export_file)

if __name__ == "__main__":
    enrich_pending_leads()
