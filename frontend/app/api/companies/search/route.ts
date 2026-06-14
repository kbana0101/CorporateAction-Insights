import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const q = url.searchParams.get("q") || "";

    if (!q) return NextResponse.json([], { status: 200 });

    const term = `%${q}%`;
    const { data, error } = await supabase
      .from("companies")
      .select("scrip_code, company")
      .ilike("company", term)
      .limit(20)
      .order("company", { ascending: true });

    if (error) {
      console.error(error);
      return NextResponse.json({ error: "Failed to search companies" }, { status: 500 });
    }

    return NextResponse.json(data || []);
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Unexpected server error" }, { status: 500 });
  }
}
