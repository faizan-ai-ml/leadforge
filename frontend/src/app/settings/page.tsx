'use client';

import { useState, useEffect } from 'react';

export default function SettingsPage() {
    const [host, setHost] = useState('smtp.gmail.com');
    const [port, setPort] = useState(587);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [status, setStatus] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        // Fetch existing config
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/settings/smtp`)
            .then(res => res.json())
            .then(data => {
                if (data.host) setHost(data.host);
                if (data.port) setPort(data.port);
                if (data.username) setUsername(data.username);
                if (data.password) setPassword(data.password);
            })
            .catch(err => console.error("Could not fetch SMTP settings", err));
    }, []);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setStatus('');
        try {
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/settings/smtp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ host, port, username, password })
            });

            if (!res.ok) throw new Error('Failed to save settings');
            setStatus('SMTP Configuration saved successfully!');
            setTimeout(() => setStatus(''), 3000);
        } catch (error) {
            console.error(error);
            setStatus('Error saving settings.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: '600px', margin: '0 auto', background: '#fff', padding: '2rem', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
            <h2>SMTP Configuration (Sequence Engine)</h2>
            <p style={{ color: '#666', marginBottom: '2rem' }}>
                Enter your email provider credentials below. For Gmail, use an <strong>App Password</strong>.
                If these are filled, the LeadForge AI Sequence Engine will send real emails directly to your scraped leads.
            </p>

            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>SMTP Host</label>
                    <input 
                        type="text" 
                        value={host} 
                        onChange={e => setHost(e.target.value)} 
                        required 
                        style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc' }}
                    />
                </div>
                
                <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>SMTP Port</label>
                    <input 
                        type="number" 
                        value={port} 
                        onChange={e => setPort(parseInt(e.target.value))} 
                        required 
                        style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc' }}
                    />
                </div>

                <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Email / Username</label>
                    <input 
                        type="email" 
                        value={username} 
                        onChange={e => setUsername(e.target.value)} 
                        style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc' }}
                        placeholder="e.g. founder@myagency.com"
                    />
                </div>

                <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>App Password</label>
                    <input 
                        type="password" 
                        value={password} 
                        onChange={e => setPassword(e.target.value)} 
                        style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc' }}
                        placeholder="16-character App Password"
                    />
                </div>

                <div style={{ marginTop: '1rem' }}>
                    <button type="submit" disabled={isLoading} className="btn" style={{ width: '100%', fontSize: '1rem' }}>
                        {isLoading ? 'Saving...' : 'Save Configuration'}
                    </button>
                    {status && <p style={{ marginTop: '1rem', color: status.includes('Error') ? 'red' : 'green', textAlign: 'center', fontWeight: 'bold' }}>{status}</p>}
                </div>
            </form>
        </div>
    );
}
