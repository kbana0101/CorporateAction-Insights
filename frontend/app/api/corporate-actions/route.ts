import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
  try {
    //const today = new Date().toISOString().split("T")[0]; // YYYY-MM-DD
    const today = "2025-12-24";

    const { data, error } = await supabase
      .from("corporate_actions")
      .select(`
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
      `)
      .eq("trading_date", today)
      .order("announcement_datetime", { ascending: false });

    if (error) {
      console.error(error);
      return NextResponse.json(
        { error: "Failed to fetch corporate actions" },
        { status: 500 }
      );
    }

    const response = data.map((row) => ({
      ...row,
      is_pdf_available: Boolean(row.local_pdf_path),
      is_ingested: Boolean(row.ingested_at),
    }));

    return NextResponse.json(response);
  } catch (err) {
    console.error(err);
    return NextResponse.json(
      { error: "Unexpected server error" },
      { status: 500 }
    );
  }
}
