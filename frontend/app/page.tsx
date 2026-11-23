import { redirect } from "next/navigation";

export default function Home() {
  redirect(`/s/${process.env.NEXT_PUBLIC_DEFAULT_STORE || "nazakat-threads"}`);
}
