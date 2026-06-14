import { createClient, SupabaseClient } from "@supabase/supabase-js"

const url = process.env.NEXT_PUBLIC_SUPABASE_URL
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!url || !anonKey) {
  throw new Error("NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set")
}

declare global {
  // eslint-disable-next-line no-var
  var __supabase: SupabaseClient | undefined
}

const _create = () =>
  createClient(url as string, anonKey as string, {
    auth: { persistSession: true, detectSessionInUrl: false },
  })

const supabase: SupabaseClient = (globalThis.__supabase ??= _create())

if (process.env.NODE_ENV !== "production") {
  globalThis.__supabase = supabase
}

export { supabase }
export default supabase
