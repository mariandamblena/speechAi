-- Catálogo de estados de llamada
create table public.catalogo_estados_llamada (
    codigo text primary key,
    descripcion text,
    tipo text check (tipo in ('flujo','resultado')),
    activo boolean default true
);

-- Catálogo de slots horarios
create table public.catalogo_slots (
    slot text primary key,
    hora_inicio time,
    hora_fin time,
    activo boolean default true
);

-- Reglas de negocio parametrizables
create table public.reglas_negocio (
    id bigserial primary key,
    nombre text not null,
    valor text not null,
    descripcion text,
    activo boolean default true,
    updated_at timestamptz default now()
);
