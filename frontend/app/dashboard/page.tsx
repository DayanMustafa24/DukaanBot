"use client";
import { useEffect, useState } from "react";
import { rs } from "@/lib/api";
import { sb } from "@/lib/supabase";
import { useStore } from "./layout";

type O = { total: number; status: string; created_at: string };
type L = { thread_id: string; user_id: string; tokens_in: number; tokens_out: number };

const PIN = Number(process.env.NEXT_PUBLIC_PRICE_IN_PER_MTOK || 0);
const POUT = Number(process.env.NEXT_PUBLIC_PRICE_OUT_PER_MTOK || 0);

export default function Overview() {
  const { store } = useStore();
  const [orders, setOrders] = useState<O[] | null>(null);
  const [logs, setLogs] = useState<L[]>([]);

  useEffect(() => {
    sb().from("orders").select("total,status,created_at").eq("store_id", store.id).range(0, 4999)
      .then(({ data }) => setOrders((data as O[]) || []));
    sb().from("chat_log").select("thread_id,user_id,tokens_in,tokens_out").eq("store_id", store.id).range(0, 9999)
      .then(({ data }) => setLogs((data as L[]) || []));
  }, [store.id]);

  if (!orders) return <p className="text-sm text-black/60">Loading…</p>;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const live = orders.filter((o) => o.status !== "cancelled");
  const todays = live.filter((o) => new Date(o.created_at) >= today);
  const revenue = live.reduce((s, o) => s + o.total, 0);
  const convs = new Set(logs.map((l) => `${l.user_id}:${l.thread_id}`)).size;
  const tin = logs.reduce((s, l) => s + l.tokens_in, 0);
  const tout = logs.reduce((s, l) => s + l.tokens_out, 0);
  const cost = (tin * PIN + tout * POUT) / 1e6;
  const conv = convs ? Math.round((live.length / convs) * 100) : 0;

  const cards: [string, string, string?][] = [
    ["Orders today", String(todays.length), rs(todays.reduce((s, o) => s + o.total, 0))],
    ["Total orders", String(live.length), `${orders.filter((o) => o.status === "new").length} new`],
    ["Revenue", rs(revenue)],
    ["Conversations", String(convs)],
    ["Chat → order", `${conv}%`],
    ["AI token cost", PIN || POUT ? `$${cost.toFixed(3)}` : "n/a", `${tin.toLocaleString()} in / ${tout.toLocaleString()} out`],
  ];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Overview</h1>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {cards.map(([k, v, sub]) => (
          <div key={k} className="bg-white border border-black/10 rounded-xl p-4">
            <div className="text-xs text-black/55">{k}</div>
            <div className="text-2xl font-bold mt-1">{v}</div>
            {sub && <div className="text-xs text-black/55 mt-0.5">{sub}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
