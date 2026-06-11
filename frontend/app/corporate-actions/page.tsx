import CorporateActionsClient from "./CorporateActionsClient";

export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

export default function CorporateActionsPage() {
  return (
    <div className="p-6">
      
      <CorporateActionsClient />
    </div>
  );
}
