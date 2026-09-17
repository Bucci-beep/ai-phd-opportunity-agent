create extension if not exists vector
with schema extensions;


create table public.sources (
    id uuid primary key default gen_random_uuid(),

    name text not null,

    source_type text not null
        check (
            source_type in (
                'university',
                'jobs_board',
                'funding_body',
                'research_portal',
                'manual',
                'other'
            )
        ),

    base_url text,

    is_active boolean not null default true,

    crawl_config jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.research_profiles (
    id uuid primary key default gen_random_uuid(),

    user_id uuid not null
        references auth.users(id)
        on delete cascade,

    name text not null,

    headline text,
    summary text,

    research_interests text[] not null default '{}',
    skills text[] not null default '{}',
    preferred_topics text[] not null default '{}',
    preferred_locations text[] not null default '{}',
    preferred_funding_types text[] not null default '{}',

    minimum_funding_gbp numeric,

    requires_visa_sponsorship boolean not null default false,

    search_document text,

    embedding extensions.vector(768),
    embedding_model text,
    embedding_updated_at timestamptz,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (user_id)
);

create table public.supervisors (
    id uuid primary key default gen_random_uuid(),

    name text not null,

    institution text,
    department text,

    email text,
    profile_url text,
    orcid text,

    bio text,

    research_interests text[] not null default '{}',

    search_document text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.opportunities (
    id uuid primary key default gen_random_uuid(),

    title text not null,

    institution text not null,
    department text,

    location_text text,
    country text not null default 'United Kingdom',

    description text,
    research_area text,

    funding_status text not null default 'unknown'
        check (
            funding_status in (
                'fully_funded',
                'partially_funded',
                'unfunded',
                'unknown'
            )
        ),

    funding_amount_gbp numeric,
    funding_text text,
    tuition_covered boolean,
    stipend_text text,

    international_students_eligible boolean,
    visa_notes text,

    start_date date,
    deadline date,
    deadline_text text,

    status text not null default 'unknown'
        check (
            status in (
                'open',
                'closed',
                'rolling',
                'unknown'
            )
        ),

    application_url text,
    project_url text,

    source_posted_at timestamptz,

    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),

    content_hash text,

    search_document text,

    embedding extensions.vector(768),
    embedding_model text,
    embedding_updated_at timestamptz,

    raw_metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.opportunity_sources (
    id uuid primary key default gen_random_uuid(),

    opportunity_id uuid not null
        references public.opportunities(id)
        on delete cascade,

    source_id uuid not null
        references public.sources(id)
        on delete cascade,

    external_id text,
    source_url text not null,

    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),

    raw_metadata jsonb not null default '{}'::jsonb,

    unique (source_id, source_url)
);

create table public.opportunity_supervisors (
    opportunity_id uuid not null
        references public.opportunities(id)
        on delete cascade,

    supervisor_id uuid not null
        references public.supervisors(id)
        on delete cascade,

    is_primary boolean not null default false,

    primary key (
        opportunity_id,
        supervisor_id
    )
);

create table public.applications (
    id uuid primary key default gen_random_uuid(),

    research_profile_id uuid not null
        references public.research_profiles(id)
        on delete cascade,

    opportunity_id uuid not null
        references public.opportunities(id)
        on delete cascade,

    status text not null default 'saved'
        check (
            status in (
                'saved',
                'reviewing',
                'preparing',
                'applied',
                'interview',
                'rejected',
                'withdrawn',
                'offer'
            )
        ),

    applied_at timestamptz,

    external_application_reference text,

    notes text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (
        research_profile_id,
        opportunity_id
    )
);

create table public.opportunity_snapshots (
    id uuid primary key default gen_random_uuid(),

    opportunity_id uuid not null
        references public.opportunities(id)
        on delete cascade,

    source_id uuid
        references public.sources(id)
        on delete set null,

    captured_at timestamptz not null default now(),

    content_hash text not null,

    snapshot_data jsonb not null,

    change_summary jsonb not null default '{}'::jsonb
);

create index opportunities_status_idx
on public.opportunities(status);

create index opportunities_deadline_idx
on public.opportunities(deadline);

create index opportunities_funding_status_idx
on public.opportunities(funding_status);

create index opportunities_last_seen_idx
on public.opportunities(last_seen_at);

create index opportunity_sources_opportunity_idx
on public.opportunity_sources(opportunity_id);

create index opportunity_sources_source_idx
on public.opportunity_sources(source_id);

create index opportunity_snapshots_opportunity_idx
on public.opportunity_snapshots(opportunity_id);

create index applications_profile_idx
on public.applications(research_profile_id);

create index applications_opportunity_idx
on public.applications(opportunity_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger sources_set_updated_at
before update on public.sources
for each row
execute function public.set_updated_at();

create trigger research_profiles_set_updated_at
before update on public.research_profiles
for each row
execute function public.set_updated_at();

create trigger supervisors_set_updated_at
before update on public.supervisors
for each row
execute function public.set_updated_at();

create trigger opportunities_set_updated_at
before update on public.opportunities
for each row
execute function public.set_updated_at();

create trigger applications_set_updated_at
before update on public.applications
for each row
execute function public.set_updated_at();

alter table public.sources enable row level security;
alter table public.research_profiles enable row level security;
alter table public.supervisors enable row level security;
alter table public.opportunities enable row level security;
alter table public.opportunity_sources enable row level security;
alter table public.opportunity_supervisors enable row level security;
alter table public.applications enable row level security;
alter table public.opportunity_snapshots enable row level security;


create policy "users can manage own research profile"
on public.research_profiles
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);


create policy "users can read own applications"
on public.applications
for select
to authenticated
using (
    exists (
        select 1
        from public.research_profiles rp
        where rp.id = applications.research_profile_id
        and rp.user_id = auth.uid()
    )
);


create policy "users can create own applications"
on public.applications
for insert
to authenticated
with check (
    exists (
        select 1
        from public.research_profiles rp
        where rp.id = applications.research_profile_id
        and rp.user_id = auth.uid()
    )
);


create policy "users can update own applications"
on public.applications
for update
to authenticated
using (
    exists (
        select 1
        from public.research_profiles rp
        where rp.id = applications.research_profile_id
        and rp.user_id = auth.uid()
    )
)
with check (
    exists (
        select 1
        from public.research_profiles rp
        where rp.id = applications.research_profile_id
        and rp.user_id = auth.uid()
    )
);


create policy "users can delete own applications"
on public.applications
for delete
to authenticated
using (
    exists (
        select 1
        from public.research_profiles rp
        where rp.id = applications.research_profile_id
        and rp.user_id = auth.uid()
    )
);


create policy "authenticated users can read sources"
on public.sources
for select
to authenticated
using (true);


create policy "authenticated users can read supervisors"
on public.supervisors
for select
to authenticated
using (true);


create policy "authenticated users can read opportunities"
on public.opportunities
for select
to authenticated
using (true);


create policy "authenticated users can read opportunity sources"
on public.opportunity_sources
for select
to authenticated
using (true);


create policy "authenticated users can read opportunity supervisors"
on public.opportunity_supervisors
for select
to authenticated
using (true);

alter table public.opportunities
add column search_tsv tsvector
generated always as (
    to_tsvector(
        'english',
        coalesce(search_document, '')
    )
) stored;


alter table public.research_profiles
add column search_tsv tsvector
generated always as (
    to_tsvector(
        'english',
        coalesce(search_document, '')
    )
) stored;


create index opportunities_search_tsv_idx
on public.opportunities
using gin(search_tsv);


create index research_profiles_search_tsv_idx
on public.research_profiles
using gin(search_tsv);


create index opportunities_embedding_hnsw_idx
on public.opportunities
using hnsw (
    embedding extensions.vector_cosine_ops
);

