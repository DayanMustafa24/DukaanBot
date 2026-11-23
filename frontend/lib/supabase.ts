"use client";
import { createClient, SupabaseClient } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

let _c: SupabaseClient | null = null;
export function sb(): SupabaseClient {
  if (!_c) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key) throw new Error("NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY missing");
    _c = createClient(url, key);
  }
  return _c;
}

export type OwnerStore = {
  id: string;
  slug: string;
  name: string;
  description: string;
  policies: Record<string, string>;
  delivery: Record<string, unknown>;
  telegram_chat_id: string | null;
};

/** The store owned by the signed-in seller (RLS guarantees only their own row is visible). */
export function useOwnerStore() {
  const [store, setStore] = useState<OwnerStore | null>(null);
  const [state, setState] = useState<"loading" | "none" | "ok">("loading");
  const [error, setError] = useState<string>("");
  useEffect(() => {
    sb()
      .from("stores")
      .select("id, slug, name, description, policies, delivery, telegram_chat_id")
      .limit(1)
      .then(({ data, error }) => {
        if (error) setError(`${error.message}${error.code ? ` (${error.code})` : ""}`);
        if (data && data[0]) {
          setStore(data[0] as OwnerStore);
          setState("ok");
        } else setState("none");
      });
  }, []);
  return { store, state, setStore, error };
}
