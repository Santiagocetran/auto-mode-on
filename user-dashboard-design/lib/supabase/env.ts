/** URL del proyecto Supabase. En Docker, el server usa la red interna (SUPABASE_URL). */
export function getSupabaseUrl(): string {
  const url = process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL
  if (!url) {
    throw new Error(
      "Falta la URL de Supabase. Configura SUPABASE_URL o NEXT_PUBLIC_SUPABASE_URL.",
    )
  }
  return url
}
