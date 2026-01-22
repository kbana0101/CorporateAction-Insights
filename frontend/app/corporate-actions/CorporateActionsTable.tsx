import ActionRow from "./ActionRow";

interface CorporateAction {
  id: string;
  company: string;
  subject: string;
  description: string;
  announcement_date: string;
  local_pdf_path: string | null;
  ingested_at: string | null;
}

export default function CorporateActionsTable({ actions }: { actions: CorporateAction[] }) {
  return (
    <table className="w-full border text-sm">
      <thead>
        <tr className="bg-gray-100">
          <th>Company</th>
          <th>Subject</th>
          <th>Description</th>
          <th>Announcement Date</th>
          <th>PDF</th>
          <th>Chat</th>
        </tr>
      </thead>
      <tbody>
        {actions.map(action => (
          <ActionRow key={action.id} action={action} />
        ))}
      </tbody>
    </table>
  );
}
