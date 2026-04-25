import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "AI Parliament Control Room",
  description: "Realtime debate operations dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="container" style={{ paddingBottom: 0 }}>
          <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <strong>AI Parliament Control Room</strong>
              <div className="muted">Realtime decision intelligence dashboard</div>
            </div>
            <nav style={{ display: "flex", gap: 16 }}>
              <Link href="/">Dashboard</Link>
            </nav>
          </div>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
