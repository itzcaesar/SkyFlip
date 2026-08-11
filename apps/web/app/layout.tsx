import type { Metadata } from 'next';
import { QueryProvider } from '@/app/components/query-provider';
import { TerminalShell } from '@/app/components/terminal-shell';
import './globals.css';
import './minecraft.css';

export const metadata: Metadata = {
  title: 'SkyFlip — Market Intelligence',
  description: 'Evidence-based Hypixel SkyBlock Bazaar and Auction House analytics.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <TerminalShell>{children}</TerminalShell>
        </QueryProvider>
      </body>
    </html>
  );
}
