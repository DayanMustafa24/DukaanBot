const rand = (n: number) => crypto.randomUUID().replace(/-/g, "").slice(0, n);

/** Anonymous customer id, persisted in this browser. Long-term memory is keyed by it. */
export function getUserId(): string {
  let id = localStorage.getItem("dk_user_id");
  if (!id) {
    id = "u_" + rand(16);
    localStorage.setItem("dk_user_id", id);
  }
  return id;
}

export function getThreadId(): string {
  let id = localStorage.getItem("dk_thread_id");
  if (!id) {
    id = newThreadId();
  }
  return id;
}

export function newThreadId(): string {
  const id = "t_" + rand(12);
  localStorage.setItem("dk_thread_id", id);
  return id;
}
