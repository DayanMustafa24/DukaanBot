"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { sendChat, ToolCall } from "@/lib/api";
import { getThreadId, getUserId, newThreadId } from "@/lib/session";

type Msg = { role: "user" | "bot"; text: string; tools?: string[] };
export type Prompt = { text: string; nonce: number } | null;

const TOOL_LABEL: Record<string, string> = {
  search_catalog: "Searched catalog",
  get_product: "Checked stock",
  calculate_total: "Calculated total",
  propose_order: "Prepared order",
  create_order: "Order placed",
  notify_seller: "Seller notified",
  get_order_status: "Looked up order",
};

const SUGGESTIONS = [
  "Black hoodie 3000 se kam mein hai? L size chahiye",
  "Show me kurtas for Eid",
  "Delivery kitne din mein hoti hai?",
];

export default function ChatWidget({ slug, storeName, prompt }: { slug: string; storeName: string; prompt: Prompt }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const ids = useRef({ user: "", thread: "" });
  const endRef = useRef<HTMLDivElement>(null);
  const lastNonce = useRef(0);

  useEffect(() => {
    ids.current = { user: getUserId(), thread: getThreadId() };
    try {
      const saved = localStorage.getItem(`dk_msgs_${ids.current.thread}`);
      if (saved) setMsgs(JSON.parse(saved));
    } catch {}
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
    if (ids.current.thread) {
      try {
        localStorage.setItem(`dk_msgs_${ids.current.thread}`, JSON.stringify(msgs.slice(-40)));
      } catch {}
    }
  }, [msgs, busy, open]);

  const send = useCallback(
    async (text: string) => {
      const t = text.trim();
      if (!t || busy) return;
      setOpen(true);
      setInput("");
      setMsgs((m) => [...m, { role: "user", text: t }]);
      setBusy(true);
      try {
        const res = await sendChat({ user_id: ids.current.user, thread_id: ids.current.thread, message: t, store_slug: slug });
        const tools = Array.from(new Set((res.tool_calls as ToolCall[]).map((c) => TOOL_LABEL[c.name] || c.name)));
        setMsgs((m) => [...m, { role: "bot", text: res.reply, tools }]);
      } catch {
        setMsgs((m) => [...m, { role: "bot", text: "Sorry, I couldn't reach the shop assistant. Please try again." }]);
      } finally {
        setBusy(false);
      }
    },
    [busy, slug]
  );

  useEffect(() => {
    if (prompt && prompt.nonce !== lastNonce.current) {
      lastNonce.current = prompt.nonce;
      send(prompt.text);
    }
  }, [prompt, send]);

  const reset = () => {
    ids.current.thread = newThreadId();
    setMsgs([]);
  };

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-brand px-5 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-brand-dark"
        >
          <span className="text-lg">💬</span> Chat with {storeName}
        </button>
      )}
      {open && (
        <div className="fixed inset-0 z-50 flex flex-col bg-white sm:inset-auto sm:bottom-5 sm:right-5 sm:h-[600px] sm:w-[390px] sm:rounded-2xl sm:shadow-2xl sm:ring-1 sm:ring-black/10">
          <div className="flex items-center justify-between rounded-t-2xl bg-brand px-4 py-3 text-white">
            <div>
              <div className="text-sm font-semibold">{storeName} assistant</div>
              <div className="text-xs text-white/80">Ask about products, sizes, delivery, or place an order</div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={reset} className="rounded-md bg-white/15 px-2 py-1 text-xs hover:bg-white/25">New chat</button>
              <button onClick={() => setOpen(false)} className="rounded-md bg-white/15 px-2 py-1 text-xs hover:bg-white/25" aria-label="Close">✕</button>
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto bg-paper px-3 py-4">
            {msgs.length === 0 && (
              <div className="space-y-2">
                <p className="text-sm text-black/60">Assalam o Alaikum! How can I help you shop today?</p>
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} className="block w-full rounded-xl border border-brand/30 bg-white px-3 py-2 text-left text-sm text-brand-dark hover:bg-brand-light">
                    {s}
                  </button>
                ))}
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className="max-w-[85%]">
                  <div className={`whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm leading-relaxed ${m.role === "user" ? "bg-brand text-white" : "bg-white text-ink shadow-sm ring-1 ring-black/5"}`}>
                    {m.text}
                  </div>
                  {m.tools && m.tools.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {m.tools.map((t) => (
                        <span key={t} className="rounded-full bg-brand-light px-2 py-0.5 text-[10px] font-medium text-brand-dark">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex justify-start">
                <div className="typing rounded-2xl bg-white px-3 py-3 shadow-sm ring-1 ring-black/5"><span /><span /><span /></div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex gap-2 border-t border-black/10 bg-white p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message…"
              maxLength={1000}
              className="flex-1 rounded-full border border-black/15 px-4 py-2 text-sm outline-none focus:border-brand"
            />
            <button disabled={busy || !input.trim()} className="rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
