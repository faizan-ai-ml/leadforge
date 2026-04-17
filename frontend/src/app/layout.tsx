import type { Metadata } from 'next'
import './globals.css'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'LeadForge AI SaaS',
  description: 'AI-Powered Local Business Prospecting Engine',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div className="container">
          <header className="header">
            <Link href="/" style={{ textDecoration: 'none' }}>
              <h1>LeadForge AI</h1>
            </Link>
            <nav style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <Link href="/personas" style={{ textDecoration: 'none', color: 'inherit', fontWeight: 'bold' }}>
                🎭 Personas
              </Link>
              <Link href="/settings" style={{ textDecoration: 'none', color: 'inherit', fontWeight: 'bold' }}>
                ⚙️ SMTP Settings
              </Link>
              <Link href="/campaigns/new" className="btn">
                + New Campaign
              </Link>
            </nav>
          </header>
          <main>
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
