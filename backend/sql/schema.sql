-- DukaanBot schema (idempotent). Run via: python scripts/init_db.py
-- LangGraph checkpoint tables are created by PostgresSaver.setup() at app startup.

create table if not exists stores (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  owner_id uuid references auth.users(id) on delete set null,
  description text not null default '',
  policies jsonb not null default '{}'::jsonb,
  delivery jsonb not null default '{}'::jsonb,
  telegram_chat_id text,
  created_at timestamptz not null default now()
);

create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  store_id uuid not null references stores(id) on delete cascade,
  sku text not null,
  name text not null,
  category text not null default '',
  color text not null default '',
  description text not null default '',
  tags text not null default '',
  price_pkr int not null check (price_pkr >= 0),
  active boolean not null default true,
  unique (store_id, sku)
);

create table if not exists variants (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  size text not null,
  stock int not null default 0 check (stock >= 0),
  unique (product_id, size)
);

create table if not exists orders (
  id uuid primary key default gen_random_uuid(),
  order_no bigint generated always as identity (start with 1001),
  pending_id text unique,
  store_id uuid not null references stores(id) on delete cascade,
  user_id text not null,
  thread_id text,
  customer_name text not null,
  phone text not null,
  city text not null,
  address text not null,
  items jsonb not null,
  subtotal int not null,
  delivery_fee int not null,
  total int not null,
  payment_method text not null default 'cod',
  status text not null default 'new',
  created_at timestamptz not null default now()
);
create index if not exists orders_store_created on orders (store_id, created_at desc);
create index if not exists orders_store_user on orders (store_id, user_id);

create table if not exists chat_log (
  id bigint generated always as identity primary key,
  store_id uuid,
  user_id text not null,
  thread_id text not null,
  role text not null,
  content text not null,
  tool_calls jsonb,
  tokens_in int not null default 0,
  tokens_out int not null default 0,
  latency_ms int not null default 0,
  created_at timestamptz not null default now()
);
create index if not exists chat_log_store_created on chat_log (store_id, created_at desc);
create index if not exists chat_log_thread on chat_log (store_id, user_id, thread_id);

create table if not exists user_memory (
  store_id uuid not null references stores(id) on delete cascade,
  user_id text not null,
  key text not null,
  value text not null,
  updated_at timestamptz not null default now(),
  primary key (store_id, user_id, key)
);

-- Row level security: the dashboard (Supabase Auth user) only sees its own store.
-- The backend connects as the postgres role, which bypasses RLS, and scopes every query itself.
alter table stores enable row level security;
alter table products enable row level security;
alter table variants enable row level security;
alter table orders enable row level security;
alter table chat_log enable row level security;
alter table user_memory enable row level security;

drop policy if exists owner_stores on stores;
create policy owner_stores on stores for all
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());

drop policy if exists owner_products on products;
create policy owner_products on products for all
  using (store_id in (select id from stores where owner_id = auth.uid()))
  with check (store_id in (select id from stores where owner_id = auth.uid()));

drop policy if exists owner_variants on variants;
create policy owner_variants on variants for all
  using (store_id in (select id from stores where owner_id = auth.uid()))
  with check (store_id in (select id from stores where owner_id = auth.uid()));

drop policy if exists owner_orders on orders;
create policy owner_orders on orders for all
  using (store_id in (select id from stores where owner_id = auth.uid()))
  with check (store_id in (select id from stores where owner_id = auth.uid()));

drop policy if exists owner_chat_log on chat_log;
create policy owner_chat_log on chat_log for select
  using (store_id in (select id from stores where owner_id = auth.uid()));
-- user_memory: no policy on purpose (only the backend reads/writes it).
