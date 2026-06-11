"use client";

import React, { useEffect, useState } from "react";
import CorporateActionsTable from "./CorporateActionsTable";

interface Action {
  id: string;
  company: string;
  subject: string;
  description: string;
  announcement_datetime: string;
  attachment_url: string | null;
  ingested_at: string | null;
}

export default function CorporateActionsClient() {
  const [categories, setCategories] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCategories();
    fetchActions();
  }, []);

  async function fetchCategories() {
    try {
      const res = await fetch("/api/corporate-actions/categories");
      const json = await res.json();
      if (res.ok) {
        setCategories(json.categories || []);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function fetchActions(category?: string | null) {
    setLoading(true);
    setError(null);
    try {
      const url = category ? `/api/corporate-actions?category=${encodeURIComponent(category)}` : "/api/corporate-actions";
      const res = await fetch(url);
      const json = await res.json();
      if (res.ok) {
        setActions(json ?? []);
      } else {
        setError(json?.error || "Failed to fetch actions");
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch actions");
    } finally {
      setLoading(false);
    }
  }

  function onSelect(cat: string | null) {
    setSelected(cat);
    fetchActions(cat);
  }

  return (
    <div className="flex gap-6">
      <aside className="w-56 pr-4 border-r border-gray-200">
        <h3 className="font-semibold mb-2">Categories</h3>
        <ul className="space-y-2">
          <li>
            <button
              className={`text-left w-full ${selected === null ? "font-bold" : ""}`}
              onClick={() => onSelect(null)}
            >
              All
            </button>
          </li>
          {categories.map((cat) => (
            <li key={cat}>
              <button
                className={`text-left w-full ${selected === cat ? "font-bold" : ""}`}
                onClick={() => onSelect(cat)}
              >
                {cat}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex-1 pl-6">
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-xl font-semibold">Corporate Actions</h2>
          <div className="text-sm text-gray-600">count:  {actions.length}</div>
        </div>

        {selected ? (
          <div className="mb-2 text-sm text-gray-500">Category: {selected}</div>
        ) : null}

        {error ? (
          <p className="text-red-600">{error}</p>
        ) : loading ? (
          <p className="text-gray-600">Loading...</p>
        ) : actions.length === 0 ? (
          <p className="text-gray-500">No corporate actions found.</p>
        ) : (
          <CorporateActionsTable actions={actions} />
        )}
      </main>
    </div>
  );
}
