import CorporateActionsTable from "./CorporateActionsTable";

export default async function CorporateActionsPage() {
  let actions = [];
  let fetchError: string | null = null;

  try {
    const res = await fetch(
      "http://localhost:3000/api/corporate-actions",
      { cache: "no-store" }
    );

    const json = await res.json();

    if (!res.ok || !Array.isArray(json)) {
      fetchError = json?.error ?? "Failed to load corporate actions.";
    } else {
      actions = json;
    }
  } catch {
    fetchError = "Could not reach the server. Please try again later.";
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">
        Corporate Actions Dashboard
      </h1>

      {fetchError ? (
        <p className="text-red-600">{fetchError}</p>
      ) : actions.length === 0 ? (
        <p className="text-gray-500">No corporate actions found for today.</p>
      ) : (
        <CorporateActionsTable actions={actions} />
      )}
    </div>
  );
}
