import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase-server";

export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

export async function GET() {
  try {
    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("corporate_actions")
      .select("category")
      .neq("category", null)
      .order("category", { ascending: true });

    if (error) {
      throw new Error(error.message);
    }

    const categories = Array.from(new Set((data ?? []).map((r: any) => r.category))).filter(Boolean);

    return NextResponse.json({ categories });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Failed to fetch categories" }, { status: 500 });
  }
}
