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

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  try {
    const userId = await getUserIdFromAuthHeader(req);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { id } = params;
    const body = await req.json();
    const name = body.name;
    if (!name) return NextResponse.json({ error: "Missing name" }, { status: 400 });

    // Ensure ownership
    const { data: existing, error: fetchErr } = await supabase
      .from("user_watchlists")
      .select("user_id")
      .eq("id", id)
      .single();
    if (fetchErr || !existing) return NextResponse.json({ error: "Not found" }, { status: 404 });
    if (existing.user_id !== userId) return NextResponse.json({ error: "Forbidden" }, { status: 403 });

    const { data, error } = await supabase
      .from("user_watchlists")
      .update({ name, updated_at: new Date().toISOString() })
      .eq("id", id)
      .select()
      .single();

    if (error) {
      console.error(error);
      return NextResponse.json({ error: "Failed to update" }, { status: 500 });
    }

    return NextResponse.json(data);
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Unexpected server error" }, { status: 500 });
  }
}

export async function DELETE(req: Request, { params }: { params: { id: string } }) {
  try {
    const userId = await getUserIdFromAuthHeader(req);
    if (!userId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const { id } = params;

    // Ensure ownership
    const { data: existing, error: fetchErr } = await supabase
      .from("user_watchlists")
      .select("user_id")
      .eq("id", id)
      .single();
    if (fetchErr || !existing) return NextResponse.json({ error: "Not found" }, { status: 404 });
    if (existing.user_id !== userId) return NextResponse.json({ error: "Forbidden" }, { status: 403 });

    const { error } = await supabase.from("user_watchlists").delete().eq("id", id);
    if (error) {
      console.error(error);
      return NextResponse.json({ error: "Failed to delete" }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Unexpected server error" }, { status: 500 });
  }
}
