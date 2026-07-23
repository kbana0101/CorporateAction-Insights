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

export async function GET(req: Request) {
  try {
    const userId = await getUserIdFromAuthHeader(req);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { data, error } = await supabase
      .from("user_watchlists")
      .select("id, name, created_at, watchlist_items(id, scrip_code, company, added_at)")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });

    if (error) {
      console.error(error);
      return NextResponse.json({ error: "Failed to fetch watchlists" }, { status: 500 });
    }

    return NextResponse.json(data);
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Unexpected server error" }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const userId = await getUserIdFromAuthHeader(req);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const body = await req.json();
    const name = body.name;
    if (!name) return NextResponse.json({ error: "Missing name" }, { status: 400 });

    const { data, error } = await supabase.from("user_watchlists").insert([
      { user_id: userId, name },
    ]).select().single();

    if (error) {
      console.error(error);
      return NextResponse.json({ error: "Failed to create watchlist" }, { status: 500 });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Unexpected server error" }, { status: 500 });
  }
}
