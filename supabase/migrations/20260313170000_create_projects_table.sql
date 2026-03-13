create extension if not exists pgcrypto;

create table if not exists public.projects (
  id text primary key,
  address text not null,
  kcd_color text not null,
  kcd_style text not null,
  drawer_type text not null,
  uppers_height integer not null,
  crown_molding text not null,
  designer text not null,
  created_at date not null,
  updated_at timestamptz not null default timezone('utc', now()),
  project_data jsonb not null
);

create index if not exists projects_created_at_idx on public.projects (created_at desc);
create index if not exists projects_updated_at_idx on public.projects (updated_at desc);

alter table public.projects enable row level security;

create or replace function public.set_projects_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists trg_projects_updated_at on public.projects;
create trigger trg_projects_updated_at
before update on public.projects
for each row
execute function public.set_projects_updated_at();
