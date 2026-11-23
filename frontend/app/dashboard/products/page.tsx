"use client";
import { useCallback, useEffect, useState } from "react";
import { rs } from "@/lib/api";
import { sb } from "@/lib/supabase";
import { useStore } from "../layout";

type V = { id: string; size: string; stock: number };
type P = { id: string; sku: string; name: string; category: string; color: string; description: string; price_pkr: number; active: boolean; variants: V[] };
const SIZES = ["S", "M", "L", "XL"];
const ORDER = ["XS", "S", "M", "L", "XL", "XXL"];

export default function Products() {
  const { store } = useStore();
  const [items, setItems] = useState<P[] | null>(null);
  const [err, setErr] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    sb().from("products").select("id,sku,name,category,color,description,price_pkr,active,variants(id,size,stock)")
      .eq("store_id", store.id).order("category").order("name")
      .then(({ data, error }) => {
        if (error) setErr(error.message);
        setItems(((data as P[]) || []).map((p) => ({ ...p, variants: [...p.variants].sort((a, b) => ORDER.indexOf(a.size) - ORDER.indexOf(b.size)) })));
      });
  }, [store.id]);
  useEffect(load, [load]);

  async function run(q: PromiseLike<{ error: { message: string } | null }>) {
    const { error } = await q;
    setErr(error ? error.message : "");
    load();
  }

  if (!items) return <p className="text-sm text-black/60">Loading…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Products <span className="text-sm font-normal text-black/50">({items.length})</span></h1>
        <button onClick={() => setAdding(!adding)} className="bg-brand text-white rounded-lg px-3 py-1.5 text-sm font-semibold">{adding ? "Close" : "Add product"}</button>
      </div>
      {err && <p className="text-sm text-red-700">{err}</p>}
      {adding && <AddForm storeId={store.id} onDone={() => { setAdding(false); load(); }} onError={setErr} />}
      <div className="bg-white border border-black/10 rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-black/55 border-b border-black/10">
            <tr><th className="p-3">Product</th><th className="p-3">Price (PKR)</th><th className="p-3">Stock by size</th><th className="p-3">Active</th></tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id} className={`border-b border-black/5 align-top ${p.active ? "" : "opacity-50"}`}>
                <td className="p-3"><div className="font-medium">{p.name}</div><div className="text-xs text-black/50">{p.sku} · {p.category} · {p.color}</div></td>
                <td className="p-3">
                  <input type="number" min={0} defaultValue={p.price_pkr} key={p.price_pkr}
                    onBlur={(e) => { const n = Number(e.target.value); if (n >= 0 && n !== p.price_pkr) run(sb().from("products").update({ price_pkr: n }).eq("id", p.id)); }}
                    className="w-24 border border-black/15 rounded px-2 py-1" />
                  <div className="text-xs text-black/50 mt-0.5">{rs(p.price_pkr)}</div>
                </td>
                <td className="p-3">
                  <div className="flex gap-2 flex-wrap">
                    {p.variants.map((v) => (
                      <label key={v.id} className="text-xs text-black/60">{v.size}
                        <input type="number" min={0} defaultValue={v.stock} key={v.stock}
                          onBlur={(e) => { const n = Number(e.target.value); if (n >= 0 && n !== v.stock) run(sb().from("variants").update({ stock: n }).eq("id", v.id)); }}
                          className={`block w-14 border rounded px-1.5 py-1 text-sm text-ink ${v.stock === 0 ? "border-red-300 bg-red-50" : "border-black/15"}`} />
                      </label>
                    ))}
                  </div>
                </td>
                <td className="p-3">
                  <input type="checkbox" checked={p.active} onChange={(e) => run(sb().from("products").update({ active: e.target.checked }).eq("id", p.id))} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AddForm({ storeId, onDone, onError }: { storeId: string; onDone: () => void; onError: (m: string) => void }) {
  const [f, setF] = useState({ sku: "", name: "", category: "", color: "", price: "", description: "" });
  const [stock, setStock] = useState<Record<string, string>>({ S: "5", M: "5", L: "5", XL: "5" });
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    const { data, error } = await sb().from("products").insert({
      store_id: storeId, sku: f.sku.trim().toUpperCase(), name: f.name.trim(), category: f.category.trim(),
      color: f.color.trim(), description: f.description.trim(), price_pkr: Number(f.price),
    }).select("id").single();
    if (error || !data) return onError(error?.message || "insert failed");
    const rows = SIZES.map((s) => ({ product_id: data.id, store_id: storeId, size: s, stock: Math.max(0, Number(stock[s]) || 0) }));
    const r = await sb().from("variants").insert(rows);
    if (r.error) return onError(r.error.message);
    onError("");
    onDone();
  }

  const cls = "border border-black/15 rounded-lg px-3 py-2 text-sm w-full";
  return (
    <form onSubmit={save} className="bg-white border border-black/10 rounded-xl p-4 grid grid-cols-2 md:grid-cols-3 gap-3">
      <input required placeholder="SKU (e.g. TEE-RED-BSC)" value={f.sku} onChange={set("sku")} className={cls} />
      <input required placeholder="Name" value={f.name} onChange={set("name")} className={cls} />
      <input placeholder="Category (hoodie, tee…)" value={f.category} onChange={set("category")} className={cls} />
      <input placeholder="Color" value={f.color} onChange={set("color")} className={cls} />
      <input required type="number" min={0} placeholder="Price PKR" value={f.price} onChange={set("price")} className={cls} />
      <input placeholder="Description" value={f.description} onChange={set("description")} className={cls} />
      <div className="col-span-2 md:col-span-3 flex gap-3 items-end flex-wrap">
        {SIZES.map((s) => (
          <label key={s} className="text-xs text-black/60">{s} stock
            <input type="number" min={0} value={stock[s]} onChange={(e) => setStock({ ...stock, [s]: e.target.value })} className="block w-16 border border-black/15 rounded px-2 py-1 text-sm text-ink" />
          </label>
        ))}
        <button className="ml-auto bg-brand text-white rounded-lg px-4 py-2 text-sm font-semibold">Save product</button>
      </div>
    </form>
  );
}
