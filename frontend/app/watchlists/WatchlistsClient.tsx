"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase-client";
import { api } from "@/lib/api";

export default function WatchlistsClient() {
  const [watchlists, setWatchlists] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchWatchlists();
  }, []);

  async function fetchWatchlists() {
    setLoading(true);
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const res = await fetch(api("/api/watchlists"), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const json = await res.json();
      if (res.ok) setWatchlists(json || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function createWatchlist(e: React.FormEvent) {
    e.preventDefault();
    if (!name) return;
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const res = await fetch(api("/api/watchlists"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        setName("");
        fetchWatchlists();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function startEdit(wl: any) {
    setEditingId(String(wl.id));
    setEditingName(wl.name || "");
  }

  async function saveEdit(e: React.FormEvent, id: string) {
    e.preventDefault();
    if (!editingName) return;
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const res = await fetch(api(`/api/watchlists/${id}`), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ name: editingName }),
      });
      if (res.ok) {
        setEditingId(null);
        setEditingName("");
        fetchWatchlists();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function deleteWatchlist(id: string) {
    if (!confirm("Delete this watchlist?")) return;
    try {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      const res = await fetch(api(`/api/watchlists/${id}`), {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) fetchWatchlists();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Watchlists</h2>
      </div>

      <form onSubmit={createWatchlist} className="mb-4">
        <input
          className="border px-2 py-1 mr-2"
          placeholder="New watchlist name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className="bg-blue-600 text-white px-3 py-1">Create</button>
      </form>

      {loading ? (
        <p>Loading...</p>
      ) : watchlists.length === 0 ? (
        <p className="text-gray-500">No watchlists yet.</p>
      ) : (
        <ul className="space-y-2">
          {watchlists.map((wl) => (
            <li key={wl.id} className="p-3 border rounded">
              <div className="flex justify-between items-center">
                <div>
                  {editingId === String(wl.id) ? (
                    <form onSubmit={(e) => saveEdit(e, String(wl.id))} className="flex items-center gap-2">
                      <input
                        className="border px-2 py-1"
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                      />
                      <button className="bg-green-600 text-white px-2 py-1">Save</button>
                      <button
                        type="button"
                        className="px-2 py-1"
                        onClick={() => {
                          setEditingId(null);
                          setEditingName("");
                        }}
                      >
                        Cancel
                      </button>
                    </form>
                  ) : (
                    <>
                      <Link href={`/watchlists/${wl.id}`} className="font-medium">
                        {wl.name}
                      </Link>
                      <div className="text-sm text-gray-600">{wl.watchlist_items?.length || 0} items</div>
                    </>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <button onClick={() => startEdit(wl)} className="text-sm text-gray-700">
                    Edit
                  </button>
                  <button onClick={() => deleteWatchlist(String(wl.id))} className="text-sm text-red-600">
                    Delete
                  </button>
                  <Link href={`/watchlists/${wl.id}`} className="text-blue-600">
                    Open
                  </Link>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
