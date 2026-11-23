"use client";
import { useCallback, useEffect, useState } from "react";
import { rs } from "@/lib/api";
import { sb } from "@/lib/supabase";
import { useStore } from "@/components/StoreContext";

type Item = { name: string; size: string; qty: number; line: number };
type Order = {
  id: string; order_no: number; status: string; customer_name: string; phone: string; city: string; address: string;
  items: Item[]; delivery_fee: number; total: number; payment_method: string; created_at: string;
};
const STATUSES = ["new", "confirmed", "shipped", "delivered", "cancelled"];
const COLOR: Record<string, string> = {
  new: "bg-amber-100 text-amber-800", confirmed: "bg-blue-100 text-blue-800", shipped: "bg-purple-100 text-purple-800",
  delivered: "bg-green-100 text-green-800", cancelled: "bg-red-100 text-red-800",
};

export default function Orders() {
  const { store } = useStore();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [filter, setFilter] = useState("all");
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    sb().from("orders").select("*").eq("store_id", store.id).order("created_at", { ascending: false }).limit(200)
      .then(({ data, error }) => {
        if (error) setErr(error.message);
        setOrders((data as Order[]) || []);
      });
  }, [store.id]);
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]);

  async function setStatus(o: Order, status: string) {
    if (status === o.status) return;
    // Cancelling restores stock so the catalogue stays accurate.
    if (status === "cancelled" && o.status !== "cancelled") {
      for (const it of o.items) {
        const { data: p } = await sb().from("products").select("id").eq("store_id", store.id).eq("name", it.name).limit(1);
        if (p && p[0]) {
          const { data: v } = await sb().from("variants").select("id,stock").eq("product_id", p[0].id).ilike("size", it.size).limit(1);
          if (v && v[0]) await sb().from("variants").update({ stock: v[0].stock + it.qty }).eq("id", v[0].id);
        }
      }
    }
    if (o.status === "cancelled" && status !== "cancelled") {
      setErr("A cancelled order cannot be reopened (stock was already returned).");
      return;
    }
    const { error } = await sb().from("orders").update({ status }).eq("id", o.id);
    if (error) setErr(error.message);
    load();
  }

  if (!orders) return <p className="text-sm text-black/60">Loading…</p>;
  const shown = filter === "all" ? orders : orders.filter((o) => o.status === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold">Orders</h1>
        <div className="flex gap-1 flex-wrap">
          {["all", ...STATUSES].map((s) => (
            <button key={s} onClick={() => setFilter(s)}
              className={`px-3 py-1 rounded-full text-xs border ${filter === s ? "bg-brand text-white border-brand" : "bg-white border-black/15"}`}>
              {s}
            </button>
          ))}
        </div>
      </div>
      {err && <p className="text-sm text-red-700">{err}</p>}
      {shown.length === 0 && <p className="text-sm text-black/60">No orders yet.</p>}
      <div className="space-y-3">
        {shown.map((o) => (
          <div key={o.id} className="bg-white border border-black/10 rounded-xl p-4">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="font-semibold">DK-{o.order_no} <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${COLOR[o.status] || "bg-black/5"}`}>{o.status}</span></div>
                <div className="text-xs text-black/55">{new Date(o.created_at).toLocaleString()} · {o.payment_method === "bank_transfer" ? "Bank transfer" : "COD"}</div>
              </div>
              <select value={o.status} onChange={(e) => setStatus(o, e.target.value)} className="border border-black/15 rounded-lg px-2 py-1 text-sm">
                {STATUSES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <ul className="mt-3 text-sm space-y-0.5">
              {o.items.map((i, k) => <li key={k}>{i.qty} × {i.name} ({i.size}) <span className="text-black/50">— {rs(i.line)}</span></li>)}
            </ul>
            <div className="mt-2 text-sm">Delivery {o.delivery_fee ? rs(o.delivery_fee) : "free"} · <b>Total {rs(o.total)}</b></div>
            <div className="mt-2 text-sm text-black/70">{o.customer_name} · {o.phone} · {o.address}, {o.city}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
