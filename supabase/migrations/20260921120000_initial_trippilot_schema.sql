create extension if not exists pgcrypto;

create table public.trips (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  origin text not null,
  destination text not null,
  start_date date not null,
  end_date date not null,
  travellers integer not null check (travellers > 0),
  budget numeric(12, 2) not null check (budget >= 0),
  currency text not null default 'INR' check (char_length(currency) = 3),
  status text not null default 'planning',
  data_mode text not null default 'demo' check (data_mode in ('demo', 'live')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (end_date > start_date)
);

create table public.trip_preferences (
  trip_id uuid primary key references public.trips(id) on delete cascade,
  interests text[] not null default '{}',
  pace text not null default 'balanced' check (pace in ('relaxed', 'balanced', 'packed')),
  hotel_style text,
  transport_preferences text[] not null default '{}'
);

create table public.trip_options (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips(id) on delete cascade,
  type text not null check (type in ('flight', 'hotel', 'place')),
  provider text not null,
  provider_id text not null,
  payload jsonb not null,
  booking_url text,
  retrieved_at timestamptz not null,
  expires_at timestamptz,
  unique (trip_id, type, provider, provider_id)
);

create table public.itinerary_items (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips(id) on delete cascade,
  provider_place_id text,
  title text not null,
  category text not null,
  start_at timestamptz not null,
  end_at timestamptz not null,
  latitude double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  cost numeric(12, 2) not null default 0 check (cost >= 0),
  currency text not null default 'INR' check (char_length(currency) = 3),
  travel_from_previous_minutes integer not null default 0 check (travel_from_previous_minutes >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (end_at > start_at)
);

create table public.user_selections (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips(id) on delete cascade,
  option_id uuid references public.trip_options(id) on delete cascade,
  selection_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.trip_events (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips(id) on delete cascade,
  type text not null,
  occurred_at timestamptz not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.trip_alerts (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid not null references public.trips(id) on delete cascade,
  event_id uuid references public.trip_events(id) on delete set null,
  status text not null default 'open',
  severity text not null,
  title text not null,
  message text not null,
  proposed_plan jsonb,
  decision text check (decision is null or decision in ('accepted', 'rejected')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  trip_id uuid references public.trips(id) on delete cascade,
  model text not null,
  graph_version text not null,
  status text not null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  estimated_cost numeric(12, 6) check (estimated_cost is null or estimated_cost >= 0),
  error jsonb
);

create table public.agent_tool_calls (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.agent_runs(id) on delete cascade,
  tool_name text not null,
  input jsonb not null default '{}'::jsonb,
  output_summary jsonb,
  status text not null,
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  retry_count integer not null default 0 check (retry_count >= 0),
  created_at timestamptz not null default now()
);

create index trips_user_id_idx on public.trips(user_id);
create index trips_dates_idx on public.trips(start_date, end_date);
create index trip_options_trip_id_type_idx on public.trip_options(trip_id, type);
create index itinerary_items_trip_id_start_at_idx on public.itinerary_items(trip_id, start_at);
create index trip_events_trip_id_occurred_at_idx on public.trip_events(trip_id, occurred_at desc);
create index trip_alerts_trip_id_status_idx on public.trip_alerts(trip_id, status);
create index agent_runs_trip_id_started_at_idx on public.agent_runs(trip_id, started_at desc);
create index agent_tool_calls_run_id_created_at_idx on public.agent_tool_calls(run_id, created_at);

alter table public.trips enable row level security;
alter table public.trip_preferences enable row level security;
alter table public.trip_options enable row level security;
alter table public.itinerary_items enable row level security;
alter table public.user_selections enable row level security;
alter table public.trip_events enable row level security;
alter table public.trip_alerts enable row level security;
alter table public.agent_runs enable row level security;
alter table public.agent_tool_calls enable row level security;

revoke all on table public.trips from anon, authenticated;
revoke all on table public.trip_preferences from anon, authenticated;
revoke all on table public.trip_options from anon, authenticated;
revoke all on table public.itinerary_items from anon, authenticated;
revoke all on table public.user_selections from anon, authenticated;
revoke all on table public.trip_events from anon, authenticated;
revoke all on table public.trip_alerts from anon, authenticated;
revoke all on table public.agent_runs from anon, authenticated;
revoke all on table public.agent_tool_calls from anon, authenticated;

comment on schema public is 'TripPilot data is server-only until user authentication policies are introduced.';
