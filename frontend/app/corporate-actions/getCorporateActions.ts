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

export async function getCorporateActions(tradingDate?: string) {
  noStore();

  const supabase = createSupabaseServerClient();
  const date = tradingDate ?? getTodayIST();

  const { data, error } = await supabase
    .from("corporate_actions")
    .select(CORPORATE_ACTIONS_SELECT)
    .eq("trading_date", date)
    .order("announcement_datetime", { ascending: false });

  if (error) {
    throw new Error(error.message);
  }

  return (data ?? []).map((row) => ({
    ...row,
    is_pdf_available: Boolean(row.local_pdf_path),
    is_ingested: Boolean(row.ingested_at),
  }));
}
