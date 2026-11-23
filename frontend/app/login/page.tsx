"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { sb } from "@/lib/supabase";

export default function Login() {
  const r = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function signIn(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    const { error } = await sb().auth.signInWithPassword({ email, password });
    setBusy(false);
    if (error) setMsg(error.message);
    else r.push("/dashboard");
  }

  async function signUp() {
    setBusy(true);
    setMsg("");
    const { data, error } = await sb().auth.signUp({ email, password });
    setBusy(false);
    if (error) setMsg(error.message);
    else if (data.session) r.push("/dashboard");
    else setMsg("Account created. Confirm via the email link if required, then sign in.");
  }

  return (
    <main className="min-h-screen grid place-items-center px-4">
      <form onSubmit={signIn} className="w-full max-w-sm bg-white border border-black/10 rounded-2xl p-6 space-y-4 shadow-sm">
        <div>
          <h1 className="text-xl font-bold">Seller dashboard</h1>
          <p className="text-sm text-black/60">Sign in to manage orders, products and conversations.</p>
        </div>
        <input type="email" required placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)}
          className="w-full border border-black/15 rounded-lg px-3 py-2 text-sm" />
        <input type="password" required minLength={6} placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)}
          className="w-full border border-black/15 rounded-lg px-3 py-2 text-sm" />
        {msg && <p className="text-sm text-red-700">{msg}</p>}
        <button disabled={busy} className="w-full bg-brand text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-60">
          {busy ? "..." : "Sign in"}
        </button>
        <button type="button" disabled={busy} onClick={signUp} className="w-full text-sm text-brand underline">
          Create account
        </button>
      </form>
    </main>
  );
}
