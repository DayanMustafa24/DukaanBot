"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import ChatWidget, { Prompt } from "@/components/ChatWidget";
import { fetchStore, Product, rs, StoreData } from "@/lib/api";

const SWATCH: Record<string, string> = {
  black: "#1c1c1e", grey: "#9ca3af", navy: "#1e3a5f", maroon: "#7f1d1d", white: "#e5e7eb", olive: "#6b7a3a",
  beige: "#d6c6a5", blue: "#3b6ea5", khaki: "#b8a77a", floral: "#e9a8b8", mint: "#a8d8c3", brown: "#6b4423",
  multi: "#c084a8", assorted: "#6b7280",
};

function ProductCard({ p, onAsk }: { p: Product; onAsk: (t: string) => void }) {
  const base = SWATCH[p.color] || "#6b7280";
  const total = p.sizes.reduce((a, s) => a + s.stock, 0);
  return (
    <div className="group overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-black/5 transition hover:shadow-md">
      <div className="relative flex h-40 items-end p-3" style={{ background: `linear-gradient(135deg, ${base}, ${base}cc)` }}>
        <span className="rounded-full bg-black/35 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white">{p.category}</span>
        {total === 0 && <span className="absolute right-3 top-3 rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-red-600">Sold out</span>}
      </div>
      <div className="space-y-2 p-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold leading-snug">{p.name}</h3>
          <span className="whitespace-nowrap text-sm font-bold text-brand-dark">{rs(p.price_pkr)}</span>
        </div>
        <p className="line-clamp-2 text-xs text-black/55">{p.description}</p>
        <div className="flex flex-wrap gap-1">
          {p.sizes.map((s) => (
            <span key={s.size} className={`rounded-md border px-1.5 py-0.5 text-[10px] ${s.stock > 0 ? "border-black/20 text-black/70" : "border-black/10 text-black/30 line-through"}`}>
              {s.size}
            </span>
          ))}
        </div>
        <div className="flex gap-2 pt-1">
          <button onClick={() => onAsk(`Tell me about the ${p.name}`)} className="flex-1 rounded-lg border border-brand/40 px-2 py-1.5 text-xs font-medium text-brand-dark hover:bg-brand-light">
            Ask
          </button>
          <button disabled={total === 0} onClick={() => onAsk(`I want to buy the ${p.name}`)} className="flex-1 rounded-lg bg-brand px-2 py-1.5 text-xs font-semibold text-white hover:bg-brand-dark disabled:opacity-40">
            Buy via chat
          </button>
        </div>
      </div>
    </div>
  );
}

export default function StorePage() {
  const { slug } = useParams<{ slug: string }>();
  const [data, setData] = useState<StoreData | null>(null);
  const [err, setErr] = useState("");
  const [cat, setCat] = useState("All");
  const [prompt, setPrompt] = useState<Prompt>(null);

  useEffect(() => {
    fetchStore(slug).then(setData).catch(() => setErr("Could not load the store. Please refresh in a moment."));
  }, [slug]);

  const cats = useMemo(() => ["All", ...Array.from(new Set((data?.products || []).map((p) => p.category)))], [data]);
  const shown = (data?.products || []).filter((p) => cat === "All" || p.category === cat);
  const ask = (text: string) => setPrompt({ text, nonce: Date.now() });

  if (err) return <main className="mx-auto max-w-xl p-10 text-center text-sm text-red-700">{err}</main>;
  if (!data) return <main className="mx-auto max-w-xl p-10 text-center text-sm text-black/50">Loading store…</main>;

  const { store } = data;
  return (
    <main>
      <header className="border-b border-black/10 bg-ink text-paper">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-10">
          <span className="text-xs uppercase tracking-[0.2em] text-accent">Instagram favourites · Islamabad</span>
          <h1 className="text-3xl font-extrabold sm:text-4xl">{store.name}</h1>
          <p className="max-w-xl text-sm text-paper/70">{store.description}</p>
          <p className="text-xs text-paper/60">Chat with our assistant to find your size, get totals and order in Roman Urdu or English.</p>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-5 py-6">
        <div className="mb-5 flex flex-wrap gap-2">
          {cats.map((c) => (
            <button key={c} onClick={() => setCat(c)} className={`rounded-full px-3 py-1 text-xs font-medium ${cat === c ? "bg-brand text-white" : "bg-white text-black/70 ring-1 ring-black/10 hover:bg-brand-light"}`}>
              {c}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {shown.map((p) => (
            <ProductCard key={p.sku} p={p} onAsk={ask} />
          ))}
        </div>
      </section>

      <footer className="mx-auto max-w-6xl space-y-1 px-5 pb-24 pt-4 text-xs text-black/50">
        {Object.entries(store.policies).map(([k, v]) => (
          <p key={k}><span className="font-semibold capitalize">{k}:</span> {String(v)}</p>
        ))}
        <p className="pt-2">Powered by DukaanBot</p>
      </footer>

      <ChatWidget slug={store.slug} storeName={store.name} prompt={prompt} />
    </main>
  );
}
