import { NextResponse } from "next/server";
import { getCorporateActions } from "@/app/corporate-actions/getCorporateActions";

export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

export async function GET() {
  try {
    const response = await getCorporateActions();
    return NextResponse.json(response);
  } catch (err) {
    console.error(err);
    return NextResponse.json(
      { error: "Failed to fetch corporate actions" },
      { status: 500 },
    );
  }
}
