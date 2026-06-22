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

export async function DELETE(req: Request, { params }: { params: { id: string; itemId: string } }) {
  try {
    const userId = await getUserIdFromAuthHeader(req);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { id: watchlistId, itemId } = params;

    // Ensure watchlist belongs to user
    const { data: wl, error: fetchErr } = await supabase
      .from("user_watchlists")
      .select("user_id")
      .eq("id", watchlistId)
      .single();
    if (fetchErr || !wl) return NextResponse.json({ error: "Not found" }, { status: 404 });
    if (wl.user_id !== userId) return NextResponse.json({ error: "Forbidden" }, { status: 403 });

    const { error } = await supabase.from("watchlist_items").delete().eq("id", itemId).eq("watchlist_id", watchlistId);
    if (error) {
      console.error(error);
      return NextResponse.json({ error: "Failed to delete item" }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Unexpected server error" }, { status: 500 });
  }
}
