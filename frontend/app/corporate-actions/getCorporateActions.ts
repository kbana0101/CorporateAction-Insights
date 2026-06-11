import { unstable_noStore as noStore } from "next/cache";
import {
  createSupabaseServerClient,
  getTodayIST,
} from "@/lib/supabase-server";

const CORPORATE_ACTIONS_SELECT = `
  id,
  company,
  scrip_code,
  subject,
  description,
  category,
  announcement_type,
  attachment_url,
  local_pdf_path,
  announcement_datetime,
  trading_date,
  ingested_at
`;

export async function getCorporateActions(tradingDate?: string, category?: string | null) {
  noStore();

  const supabase = createSupabaseServerClient();
  const date = tradingDate ?? getTodayIST();

  // Build base query and apply category filter if provided
  let query = supabase.from("corporate_actions").select(CORPORATE_ACTIONS_SELECT).eq("trading_date", date).order("announcement_datetime", { ascending: false });
  if (category) {
    query = query.eq("category", category);
  }

  const { data: rows, error: qError } = await query;

  if (qError) {
    throw new Error(qError.message);
  }

  return (rows ?? []).map((row) => ({
    ...row,
    is_pdf_available: Boolean(row.attachment_url),
    is_ingested: Boolean(row.ingested_at),
  }));
}
