-- Registro de tandas
create table public.tanda_runs (
    id bigserial primary key,
    fecha date not null,
    slot text check (slot in ('09','12','15')) not null,
    status text check (status in ('scheduled','running','finished','missed','recovered')) default 'scheduled',
    started_at timestamptz,
    finished_at timestamptz,
    nota text
);

-- Outbox para control de llamadas y evitar duplicados
create table public.outbox_calls (
    id bigserial primary key,
    deudor_id bigint references public.deudores(id) on delete cascade,
    fecha date not null,
    slot text not null,
    unique_key text unique, -- hash de deudor_id|fecha|slot
    call_id_retell text,
    status text check (status in ('pending','sent','acked','error')) default 'pending',
    retries int default 0,
    last_error text,
    updated_at timestamptz default now()
);

-- Eventos recibidos desde webhook de Retell
create table public.webhook_events (
    id bigserial primary key,
    call_id_retell text,
    event_type text,
    payload_json jsonb,
    received_at timestamptz default now(),
    processed_at timestamptz,
    status text check (status in ('queued','processed','error')) default 'queued'
);

-- Dead-letter queue para eventos fallidos
create table public.webhook_dlq (
    id bigserial primary key,
    event_id bigint references public.webhook_events(id) on delete cascade,
    error_msg text,
    created_at timestamptz default now()
);
