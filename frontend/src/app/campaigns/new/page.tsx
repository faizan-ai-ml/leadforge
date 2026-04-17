'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function NewCampaign() {
  const router = useRouter();
  const [niche, setNiche] = useState('Plumbers');
  const [location, setLocation] = useState('Dubai');
  const [maxLeads, setMaxLeads] = useState(10);
  const [loading, setLoading] = useState(false);
  const [personas, setPersonas] = useState<any[]>([]);
  const [personaId, setPersonaId] = useState<number | ''>('');

  useEffect(() => {
     fetch('http://127.0.0.1:8000/api/personas')
      .then(r => r.json())
      .then(d => {
         setPersonas(d);
         if (d.length > 0) setPersonaId(d[0].id);
      })
      .catch(e => console.error(e));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await fetch('http://127.0.0.1:8000/api/campaigns', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ niche, location, max_leads: maxLeads, persona_id: personaId === '' ? null : personaId }),
      });
      
      if (res.ok) {
        const data = await res.json();
        // Redirect to live campaign tracker
        router.push(`/campaigns/${data.campaign_id}`);
      } else {
        alert("Failed to start campaign");
      }
    } catch (e) {
      console.error(e);
      alert("Error starting campaign - is the python API server actively running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '3rem', maxWidth: '600px', margin: '0 auto' }}>
      <h2 style={{ marginBottom: '2rem', textAlign: 'center' }}>Launch New Campaign</h2>
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <label>Target Niche</label>
          <input 
            type="text" 
            value={niche} 
            onChange={(e) => setNiche(e.target.value)} 
            required 
            placeholder="e.g. Plumbers, Roofers, Dentists" 
          />
        </div>
        
        <div className="input-group">
          <label>Location</label>
          <input 
            type="text" 
            value={location} 
            onChange={(e) => setLocation(e.target.value)} 
            required 
            placeholder="e.g. Dubai, New York, London" 
          />
        </div>
        
        <div className="input-group">
          <label>Max Leads to Scrape</label>
          <input 
            type="number" 
            value={maxLeads || ''} 
            onChange={(e) => setMaxLeads(parseInt(e.target.value) || 0)} 
            required 
            min="1"
            max="50"
          />
        <div className="input-group">
          <label>Campaign Persona (Objective)</label>
          <select 
            value={personaId} 
            onChange={(e) => setPersonaId(parseInt(e.target.value) || '')} 
            required
            style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', marginBottom: '1rem', background: '#fff' }}
          >
            <option value="" disabled>Select a Persona</option>
            {personas.map(p => (
              <option key={p.id} value={p.id}>{p.name} ({p.objective})</option>
            ))}
          </select>
        </div>
        
        <button type="submit" className="btn" style={{ width: '100%', marginTop: '1rem' }} disabled={loading}>
          {loading ? (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', justifyContent: 'center' }}>
              <div className="spinner"></div> Initiating Pipeline...
            </div>
          ) : 'Launch Scraper Engine'}
        </button>
      </form>
    </div>
  );
}
