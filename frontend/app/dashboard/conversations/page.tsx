"use client";
import { useEffect, useMemo, useState } from "react";
import { sb } from "@/lib/supabase";
import { useStore } from "../layout";

type Row = {
  id: number; user_id: string; thread_id: string; role: string; content: string;
  tool_calls: { name: string; args: unknown; result: string }[] | null; tokens_in: number; tokens_out: number; latency_ms: number; created_at: string;
};

export default function Conversations() {
  const { store } = useStore();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [sel, setSel] = useState<string | null>(null);

  useEffect(() => {
    sb().from("chat_log")
      .select("id,user_id,thread_id,role,content,tool_calls,tokens_in,tokens_out,latency_ms,created_at")
      .eq("store_id", store.id).order("id", { ascending: false }).limit(1500)
      .then(({ data }) => setRows((data as Row[]) || []));
  }, [store.id]);

  const threads = useMemo(() => {
    const m = new Map<string, Row[]>();
    for (const r of rows || []) {
      const k = `${r.user_id}\u0000${r.thread_id}`;
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(r);
    }
    return [...m.entries()].map(([k, rs]) => ({ key: k, rows: [...rs].reverse(), last: rs[0].created_at }));
  }, [rows]);

  if (!rows) return <p className="text-sm text-black/60">Loading…</p>;
  const cur = threads.find((t) => t.key === sel) || threads[0];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Conversations <span className="text-sm font-normal text-black/50">({threads.length})</span></h1>
      {threads.length === 0 && <p className="text-sm text-black/60">No conversations yet.</p>}
      <div className="grid md:grid-cols-[280px_1fr] gap-4">
        <div className="bg-white border border-black/10 rounded-xl max-h-[70vh] overflow-y-auto">
          {threads.map((t) => (
            <button key={t.key} onClick={() => setSel(t.key)}
              className={`block w-full text-left px-3 py-2.5 border-b border-black/5 ${cur?.key === t.key ? "bg-brand-light" : "hover:bg-black/[.03]"}`}>
              <div className="text-sm font-medium truncate">{t.rows[0].content}</div>
              <div className="text-xs text-black/50">{t.rows.length} msgs · {new Date(t.last).toLocaleString()}</div>
            </button>
          ))}
        </div>
        {cur && (
          <div className="bg-white border border-black/10 rounded-xl p-4 max-h-[70vh] overflow-y-auto space-y-3">
            {cur.rows.map((r) => (
              <div key={r.id} className={r.role === "user" ? "text-right" : ""}>
                <div className={`inline-block max-w-[85%] text-left rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap ${r.role === "user" ? "bg-brand text-white" : "bg-black/5"}`}>
                  {r.content}
                </div>
                {r.role === "assistant" && (
                  <div className="mt-1 space-y-1">
                    {(r.tool_calls || []).map((t, i) => (
                      <details key={i} className="text-xs text-black/60">
                        <summary className="cursor-pointer">🔧 {t.name}</summary>
                        <pre className="whitespace-pre-wrap bg-black/[.03] rounded p-2 mt-1">{JSON.stringify(t.args)}{"\n→ "}{t.result}</pre>
                      </details>
                    ))}
                    <div className="text-[11px] text-black/40">{r.tokens_in} in / {r.tokens_out} out · {r.latency_ms} ms</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
