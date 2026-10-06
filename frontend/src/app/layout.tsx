import { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';
import { AuthNav } from '@/components/ui/AuthNav';

export const metadata: Metadata = {
  title: 'DataChat | AI-Augmented Analytics',
  description: 'Connect your database. Ask questions. Get insights. Build predictions.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <nav className="top-nav">
          <div className="nav-container">
            <Link href="/" className="logo" style={{ textDecoration: 'none' }}>DataChat</Link>
            <AuthNav />
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
