-- Tabla de deudores
create table public.deudores (
    id bigserial primary key,
    nombre text not null,
    dni text not null,
    telefono_e164 text not null, -- formato +549...
    producto text,
    monto_adeudado numeric(12,2) not null default 0,
    cuotas_adeudadas int not null default 0,
    mora_tipo text check (mora_tipo in ('Temprana','Tardía')),
    dias_mora int not null default 0,
    opt_out boolean default false,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Log detallado de llamadas
create table public.llamadas_log (
    id bigserial primary key,
    deudor_id bigint references public.deudores(id) on delete cascade,
    call_id_retell text,
    batch_id_retell text,
    fecha_llamada date not null,
    slot text check (slot in ('09','12','15')),
    estado text,
    resultado text,
    duracion_seg int,
    costo numeric(10,2),
    mensaje text,
    created_at timestamptz default now()
);

-- Resumen de llamadas por deudor
create table public.llamadas_resumen (
    deudor_id bigint primary key references public.deudores(id) on delete cascade,
    intentos_total int not null default 0,
    dias_distintos_intentados int not null default 0,
    ultimo_intento_ts timestamptz,
    ultimo_resultado text,
    flag_incontactable boolean default false,
    flag_finalizado boolean default false,
    updated_at timestamptz default now()
);

-- Agenda de recall (reagendados)
create table public.agenda_recall (
    id bigserial primary key,
    deudor_id bigint references public.deudores(id) on delete cascade,
    recall_ts timestamptz not null,
    nota text,
    estado text check (estado in ('pendiente','agendado','llamado','cancelado')) default 'pendiente',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Pool diario (selección de deudores para el día)
create table public.pool_diario (
    id bigserial primary key,
    fecha date not null,
    deudor_id bigint references public.deudores(id) on delete cascade,
    slot_09 boolean default true,
    slot_12 boolean default true,
    slot_15 boolean default true,
    estado text check (estado in ('pendiente','en_progreso','completo','descartado')) default 'pendiente',
    prioridad int default 0,
    created_at timestamptz default now()
);
