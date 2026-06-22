"use client";

import React, { useState } from "react";
import { supabase } from "@/lib/supabase-client";
import { api } from "@/lib/api";

export default function CompaniesSearch({ watchlistId, onAdded }: { watchlistId: string; onAdded: () => void }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  async function search() {
    if (!q) return;
    setLoading(true);
    try {
      const res = await fetch(api(`/api/companies/search?q=${encodeURIComponent(q)}`));
      const json = await res.json();
      if (res.ok) setResults(json || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function add(scrip_code: string, company: string) {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const res = await fetch(api(`/api/watchlists/${watchlistId}/items`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ scrip_code, company }),
      });
      if (res.ok) {
        onAdded();
      }
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="mb-4">
      <div className="flex">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search companies by name or scrip"
          className="border px-2 py-1 mr-2 flex-1"
        />
        <button onClick={search} className="bg-gray-700 text-white px-3">
          Search
        </button>
      </div>
      {loading ? <p>Searching...</p> : null}
      <ul className="mt-2 space-y-2">
        {results.map((r) => (
          <li key={r.scrip_code} className="p-2 border rounded flex justify-between">
            <div>
              <div className="font-medium">{r.company}</div>
              <div className="text-sm text-gray-600">{r.scrip_code}</div>
            </div>
            <button onClick={() => add(r.scrip_code, r.company)} className="bg-green-600 text-white px-2 py-1">
              Add
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
