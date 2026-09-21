-- Backend ingestion worker permissions.
--
-- service_role is used only by trusted server-side ingestion code.
-- RLS remains enabled on all tables.

grant select on table public.sources
to service_role;

grant select, insert, update on table public.opportunities
to service_role;

grant select, insert, update on table public.opportunity_sources
to service_role;

grant select, insert on table public.opportunity_snapshots
to service_role;
