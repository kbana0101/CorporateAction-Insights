import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

async function getUserIdFromAuthHeader(req: Request) {
  const auth = req.headers.get("authorization");
  if (!auth || !auth.startsWith("Bearer ")) return null;
  const token = auth.split(" ")[1];
  try {
    const { data, error } = await supabase.auth.getUser(token as string);
    if (error) return null;
    return data.user?.id || null;
  } catch (e) {
    return null;
  }
}

export async function POST(req: Request, { params }: { params: { id: string } }) {
  try {
    const userId = await getUserIdFromAuthHeader(req);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { id: watchlistId } = params;

    // Ensure watchlist belongs to user
    const { data: wl, error: fetchErr } = await supabase
      .from("user_watchlists")
      .select("user_id")
      .eq("id", watchlistId)
      .single();
    if (fetchErr || !wl) return NextResponse.json({ error: "Not found" }, { status: 404 });
    if (wl.user_id !== userId) return NextResponse.json({ error: "Forbidden" }, { status: 403 });

    const body = await req.json();
    const scrip_code = body.scrip_code;
    if (!scrip_code) return NextResponse.json({ error: "Missing scrip_code" }, { status: 400 });

    // Try to fetch company name from companies table
    const { data: comp } = await supabase.from("companies").select("company").eq("scrip_code", scrip_code).limit(1).single();
    const company = comp?.company || body.company || null;

    const { data, error } = await supabase.from("watchlist_items").insert([
      { watchlist_id: watchlistId, scrip_code, company },
    ]).select().single();

    if (error) {
      console.error(error);
      return NextResponse.json({ error: "Failed to add item" }, { status: 500 });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Unexpected server error" }, { status: 500 });
  }
}
