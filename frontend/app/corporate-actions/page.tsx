import CorporateActionsTable from "./CorporateActionsTable";

export default async function CorporateActionsPage() {
  const res = await fetch(
    "http://localhost:3000/api/corporate-actions",
    { cache: "no-store" }
  );

  const json = await res.json();

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">
        Corporate Actions Dashboard
      </h1>

      <CorporateActionsTable actions={json} />
    </div>
  );
}
