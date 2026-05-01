import CorporateActionsTable from "./CorporateActionsTable";
import { getCorporateActions } from "./getCorporateActions";

export const dynamic = "force-dynamic";

export default async function CorporateActionsPage() {
  let actions: string | any[] = [];
  let fetchError: string | null = null;

  try {
    actions = await getCorporateActions();
  } catch (err) {
    fetchError =
      err instanceof Error ? err.message : "Failed to load corporate actions.";
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
