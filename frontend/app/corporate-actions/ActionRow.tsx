import Link from "next/link";

interface CorporateAction {
  id: string;
  company: string;
  subject: string;
  description: string;
  announcement_datetime: string;
  local_pdf_path: string | null;
  ingested_at: string | null;
}



export default function ActionRow({ action }: { action: CorporateAction }) {
    const BASE_PDF_DIR = "/home/kbana/code/ai-pdf-chatbot-langchain/backend/corp_action_ingestion";
  return (
    <tr className="border-t">
      <td style={{ width: "20%" }}>{action.company}</td>
      <td style={{ width: "20%" }}>{action.subject}</td>
      <td style={{ width: "40%" }}>{action.description}</td>
      <td className="align-middle text-center" style={{ width: "10%" }}>{action.announcement_datetime}</td>

      {/* 1️⃣ VIEW PDF */}
      <td className="align-middle text-center" style={{ width: "5%" }}>
        {action.local_pdf_path ? (
          <a
            href={`/api/pdf?path=${encodeURIComponent(BASE_PDF_DIR + "/" + action.local_pdf_path.replace(/\\/g, "/"))}`}
            target="_blank"
            className="text-blue-600 underline"
          >
            View
          </a>
        ) : (
          <span className="text-gray-400">Not downloaded</span>
        )}
      </td>
      <td className="align-middle text-center" style={{ width: "5%" }}>
        {action.ingested_at ? (
            <Link
            href={`/chat?doc_id=${action.id}`}
            className="text-indigo-600 underline"
            >
            Chat
            </Link>
        ) : (
            <span className="text-gray-400">Not ready</span>
        )}
      </td>
    </tr>
  );
}
 
