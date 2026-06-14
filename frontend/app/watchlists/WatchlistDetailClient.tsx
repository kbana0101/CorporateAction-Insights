"use client";

import React, { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase-client";
import CompaniesSearch from "./CompaniesSearch";
import { api } from "@/lib/api";

export default function WatchlistDetailClient({ id }: { id: string }) {
  const [watchlist, setWatchlist] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchWatchlist();
  }, [id]);

  async function fetchWatchlist() {
    setLoading(true);
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const res = await fetch(api("/api/watchlists"), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const json = await res.json();
      if (res.ok) {
        const found = (json || []).find((w: any) => String(w.id) === String(id));
        setWatchlist(found || null);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function removeItem(itemId: string) {
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const res = await fetch(api(`/api/watchlists/${id}/items/${itemId}`), {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) fetchWatchlist();
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">{watchlist?.name || "Watchlist"}</h2>
        <div className="text-sm text-gray-600">{watchlist?.watchlist_items?.length || 0} items</div>
      </div>

      <CompaniesSearch watchlistId={id} onAdded={fetchWatchlist} />

      {loading ? (
        <p>Loading...</p>
      ) : !watchlist ? (
        <p className="text-gray-500">Watchlist not found.</p>
      ) : (
        <table className="w-full border text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="p-2 text-center">Company</th>
              <th className="p-2 text-center">Scrip</th>
              <th className="p-2 text-center">Added</th>
              <th className="p-2 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {watchlist.watchlist_items?.map((it: any) => (
              <tr key={it.id} className="border-t">
                <td className="p-2 text-center">{it.company}</td>
                <td className="p-2 text-center">{it.scrip_code}</td>
                <td className="p-2 text-center">{new Date(it.added_at).toLocaleString()}</td>
                <td className="p-2 text-center">
                  <button onClick={() => removeItem(it.id)} className="text-red-600">
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
