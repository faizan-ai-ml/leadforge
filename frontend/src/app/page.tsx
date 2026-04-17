'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function Dashboard() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCampaigns = async () => {
    try {
      // Connects to the local FastAPI backend
      const res = await fetch('http://127.0.0.1:8000/api/campaigns');
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
    // Poll every 5 seconds for live updates
    const interval = setInterval(fetchCampaigns, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-panel" style={{ padding: '2rem' }}>
      <h2>Recent Campaigns</h2>
      
      {loading && campaigns.length === 0 ? (
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div className="spinner"></div>
          <p>Connecting to backend...</p>
        </div>
      ) : campaigns.length === 0 ? (
        <p style={{ color: 'var(--text-secondary)' }}>No campaigns found. Start by creating a new one!</p>
      ) : (
        <div className="grid">
          {campaigns.map((camp) => (
            <Link key={camp.id} href={`/campaigns/${camp.id}`} style={{ textDecoration: 'none' }}>
              <div className="card glass-panel">
                <h3 className="card-title">{camp.name}</h3>
                <div className="card-meta">
                  <span>Niche: <strong>{camp.niche}</strong></span>
                  <span>Location: <strong>{camp.location}</strong></span>
                </div>
                <div className="badge high" style={{ marginTop: '0.5rem', alignSelf: 'flex-start' }}>
                  Open Campaign &rarr;
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
