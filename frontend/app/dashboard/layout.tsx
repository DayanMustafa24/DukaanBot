"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { OwnerStore, sb, useOwnerStore } from "@/lib/supabase";

const Ctx = createContext<{ store: OwnerStore; setStore: (s: OwnerStore) => void } | null>(null);
export const useStore = () => useContext(Ctx)!;

const NAV = [
  ["/dashboard", "Overview"],
  ["/dashboard/orders", "Orders"],
  ["/dashboard/products", "Products"],
  ["/dashboard/conversations", "Conversations"],
  ["/dashboard/settings", "Settings"],
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const r = useRouter();
  const path = usePathname();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    sb().auth.getSession().then(({ data }) => {
      if (!data.session) r.replace("/login");
      else setAuthed(true);
    });
  }, [r]);

  if (!authed) return <div className="p-8 text-sm text-black/60">Loading…</div>;
  return <Gate path={path}>{children}</Gate>;
}

function Gate({ children, path }: { children: React.ReactNode; path: string }) {
  const r = useRouter();
  const { store, state, setStore } = useOwnerStore();

  async function logout() {
    await sb().auth.signOut();
    r.replace("/login");
  }

  if (state === "loading") return <div className="p-8 text-sm text-black/60">Loading…</div>;
  if (state === "none" || !store)
    return (
      <div className="p-8 max-w-lg text-sm space-y-3">
        <p className="font-semibold">No store is linked to this account.</p>
        <p className="text-black/70">
          Run <code className="bg-black/5 px-1 rounded">python scripts/link_owner.py your@email.com</code> from <code className="bg-black/5 px-1 rounded">backend/</code>, then reload.
        </p>
        <button onClick={logout} className="underline text-brand">Sign out</button>
      </div>
    );

  return (
    <Ctx.Provider value={{ store, setStore }}>
      <div className="min-h-screen">
        <header className="bg-white border-b border-black/10">
          <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-4">
            <span className="font-bold text-brand">{store.name}</span>
            <nav className="flex gap-1 overflow-x-auto flex-1">
              {NAV.map(([href, label]) => (
                <Link key={href} href={href}
                  className={`px-3 py-1.5 rounded-lg text-sm whitespace-nowrap ${path === href ? "bg-brand-light text-brand-dark font-semibold" : "text-black/70 hover:bg-black/5"}`}>
                  {label}
                </Link>
              ))}
            </nav>
            <Link href={`/s/${store.slug}`} target="_blank" className="text-sm text-black/60 hover:underline hidden sm:block">View store ↗</Link>
            <button onClick={logout} className="text-sm text-black/60 hover:underline">Sign out</button>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
      </div>
    </Ctx.Provider>
  );
}
