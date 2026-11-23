"use client";
import { useState } from "react";
import { sb } from "@/lib/supabase";
import { useStore } from "../layout";

export default function Settings() {
  const { store, setStore } = useStore();
  const [name, setName] = useState(store.name);
  const [description, setDescription] = useState(store.description);
  const [chat, setChat] = useState(store.telegram_chat_id || "");
  const [policies, setPolicies] = useState<Record<string, string>>(
    Object.fromEntries(Object.entries(store.policies || {}).map(([k, v]) => [k, String(v)])),
  );
  const [delivery, setDelivery] = useState(JSON.stringify(store.delivery || {}, null, 2));
  const [msg, setMsg] = useState("");

  async function save(e: React.FormEvent) {
    e.preventDefault();
    let del: Record<string, unknown>;
    try {
      del = JSON.parse(delivery);
    } catch {
      return setMsg("Delivery settings are not valid JSON.");
    }
    const patch = { name: name.trim(), description: description.trim(), telegram_chat_id: chat.trim() || null, policies, delivery: del };
    const { error } = await sb().from("stores").update(patch).eq("id", store.id);
    if (error) return setMsg(error.message);
    setStore({ ...store, ...patch });
    setMsg("Saved. The assistant picks this up within about a minute.");
  }

  const cls = "w-full border border-black/15 rounded-lg px-3 py-2 text-sm";
  return (
    <form onSubmit={save} className="max-w-2xl space-y-4">
      <h1 className="text-xl font-bold">Store settings</h1>
      <label className="block text-sm font-medium">Store name<input value={name} onChange={(e) => setName(e.target.value)} className={`${cls} mt-1`} /></label>
      <label className="block text-sm font-medium">Description<textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} className={`${cls} mt-1`} /></label>
      <div>
        <div className="text-sm font-medium mb-1">Policies</div>
        {Object.entries(policies).map(([k, v]) => (
          <label key={k} className="block text-xs text-black/60 mb-2">{k}
            <textarea rows={2} value={v} onChange={(e) => setPolicies({ ...policies, [k]: e.target.value })} className={`${cls} mt-1 text-ink`} />
          </label>
        ))}
      </div>
      <label className="block text-sm font-medium">Delivery (JSON)
        <textarea rows={6} value={delivery} onChange={(e) => setDelivery(e.target.value)} className={`${cls} mt-1 font-mono text-xs`} />
      </label>
      <label className="block text-sm font-medium">Telegram chat id (order alerts)
        <input value={chat} onChange={(e) => setChat(e.target.value)} className={`${cls} mt-1`} placeholder="e.g. 123456789" />
      </label>
      {msg && <p className="text-sm text-black/70">{msg}</p>}
      <button className="bg-brand text-white rounded-lg px-4 py-2 text-sm font-semibold">Save</button>
    </form>
  );
}
