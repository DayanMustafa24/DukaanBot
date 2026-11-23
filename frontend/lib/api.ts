export const API = (process.env.NEXT_PUBLIC_API_BASE || "http://localhost:7860").replace(/\/$/, "");

export type SizeStock = { size: string; stock: number };
export type Product = {
  sku: string;
  name: string;
  category: string;
  color: string;
  description: string;
  price_pkr: number;
  sizes: SizeStock[];
};
export type StoreData = {
  store: { slug: string; name: string; description: string; policies: Record<string, string>; delivery: Record<string, unknown> };
  products: Product[];
};
export type ToolCall = { name: string; args: unknown; result: string };
export type ChatReply = { reply: string; tool_calls: ToolCall[]; tokens: { in: number; out: number } };

export async function fetchStore(slug: string): Promise<StoreData> {
  const r = await fetch(`${API}/store/${encodeURIComponent(slug)}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`store ${slug}: ${r.status}`);
  return r.json();
}

export async function sendChat(body: { user_id: string; thread_id: string; message: string; store_slug: string }): Promise<ChatReply> {
  const r = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`chat: ${r.status}`);
  return r.json();
}

export const rs = (n: number) => `Rs ${n.toLocaleString("en-US")}`;
