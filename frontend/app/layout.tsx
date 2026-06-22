"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase-client";
import { Button } from "@/components/ui/button";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname(); // Get the current path
  const router = useRouter(); // For programmatic navigation
  const [user, setUser] = useState<any | null>(null);

  const handleNavigation = (href: string) => {
    if (pathname === href) {
      // Force refresh if navigating to the same route
      router.replace(href);
    }
  };

  useEffect(() => {
    // Check session for protected routes and set user state
    const protectedPaths = ["/chat", "/corporate-actions", "/watchlists"];
    const check = async () => {
      try {
        const { data } = await supabase.auth.getSession();
        const session = (data as any)?.session;
        setUser(session?.user ?? null);
        if (protectedPaths.some((p) => pathname.startsWith(p)) && !session) {
          router.push("/login");
        }
      } catch (e) {
        // ignore
      }
    };

    check();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser((session as any)?.user ?? null);
    });

    return () => {
      listener?.subscription?.unsubscribe?.();
    };
  }, [pathname, router]);

  const signOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
    router.push("/login");
  };

  return (
    <html lang="en">
      <body className="flex h-screen">
        {/* LEFT SIDEBAR */}
        <aside className="w-56 bg-gray-900 text-white p-4">
          <h2 className="text-lg font-semibold mb-6">Announcement Insights</h2>

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

            <Link
              href="/watchlists"
              className={`hover:bg-gray-700 px-3 py-2 rounded ${
                pathname === "/watchlists" ? "bg-gray-700" : ""
              }`}
              onClick={() => handleNavigation("/watchlists")}
            >
              📌 Watchlists
            </Link>

            <div className="mt-4 border-t border-white/10 pt-4">
              {user ? (
                <Link
                  href="/login"
                  onClick={async (e) => {
                    e.preventDefault()
                    await signOut()
                  }}
                  className="hover:bg-gray-700 px-3 py-2 rounded"
                >
                  🔓 Sign out
                </Link>
              ) : (
                <Link href="/login" className="hover:bg-gray-700 px-3 py-2 rounded">
                  🔐 Login / Signup
                </Link>
              )}
            </div>
          </nav>
        </aside>

        {/* MAIN CONTENT */}
        <main className="flex-1 overflow-auto bg-gray-50 relative">{children}</main>
      </body>
    </html>
  );
}
