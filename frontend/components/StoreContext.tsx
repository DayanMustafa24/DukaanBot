"use client";
import { createContext, useContext } from "react";
import type { OwnerStore } from "@/lib/supabase";

export const StoreCtx = createContext<{ store: OwnerStore; setStore: (s: OwnerStore) => void } | null>(null);
export const useStore = () => useContext(StoreCtx)!;
