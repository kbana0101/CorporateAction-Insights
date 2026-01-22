"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
    const pathname = usePathname(); // Get the current path
  const router = useRouter(); // For programmatic navigation

  const handleNavigation = (href: string) => {
    if (pathname === href) {
      // Force refresh if navigating to the same route
      router.replace(href);
    }
  };
  return (
    <html lang="en">
      <body className="flex h-screen">
        {/* LEFT SIDEBAR */}
        <aside className="w-56 bg-gray-900 text-white p-4">
          <h2 className="text-lg font-semibold mb-6">
            Announcement Insights
          </h2>

          <nav className="flex flex-col gap-3">
            <Link
              href="/chat"
              className={`hover:bg-gray-700 px-3 py-2 rounded ${
                pathname === "/chat" ? "bg-gray-700" : ""
              }`}
              onClick={() => handleNavigation("/chat")}
            >
              💬 Chat
            </Link>

            <Link
              href="/corporate-actions"
              className={`hover:bg-gray-700 px-3 py-2 rounded ${
                pathname === "/corporate-actions" ? "bg-gray-700" : ""
              }`}
              onClick={() => handleNavigation("/corporate-actions")}
            >
              🏢 Corporate Actions
            </Link>
          </nav>
        </aside>

        {/* MAIN CONTENT */}
        <main className="flex-1 overflow-auto bg-gray-50 relative">
          {children}
        </main>
      </body>
    </html>
  );
}
