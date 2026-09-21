create or replace function public.persist_ingested_opportunity(
    p_opportunity_id uuid,
    p_source_name text,
    p_external_id text,
    p_source_url text,
    p_raw_metadata jsonb,
    p_opportunity jsonb,
    p_content_hash text,
    p_create_snapshot boolean,
    p_change_summary jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_source_id uuid;
    v_opportunity_id uuid;
    v_created boolean := false;
    v_updated boolean := false;
    v_snapshot_created boolean := false;
begin
    select id
    into v_source_id
    from public.sources
    where name = p_source_name
    limit 1;

    if v_source_id is null then
        raise exception 'Unknown ingestion source: %', p_source_name;
    end if;

    if p_opportunity_id is null then
        insert into public.opportunities (
            title,
            institution,
            department,
            location_text,
            country,
            description,
            research_area,
            funding_status,
            funding_amount_gbp,
            funding_text,
            tuition_covered,
            stipend_text,
            international_students_eligible,
            visa_notes,
            start_date,
            deadline,
            deadline_text,
            status,
            application_url,
            project_url,
            source_posted_at,
            content_hash,
            raw_metadata
        )
        values (
            p_opportunity ->> 'title',
            p_opportunity ->> 'institution',
            p_opportunity ->> 'department',
            p_opportunity ->> 'location_text',
            coalesce(
                p_opportunity ->> 'country',
                'United Kingdom'
            ),
            p_opportunity ->> 'description',
            p_opportunity ->> 'research_area',
            coalesce(
                p_opportunity ->> 'funding_status',
                'unknown'
            ),
            nullif(
                p_opportunity ->> 'funding_amount_gbp',
                ''
            )::numeric,
            p_opportunity ->> 'funding_text',
            nullif(
                p_opportunity ->> 'tuition_covered',
                ''
            )::boolean,
            p_opportunity ->> 'stipend_text',
            nullif(
                p_opportunity
                    ->> 'international_students_eligible',
                ''
            )::boolean,
            p_opportunity ->> 'visa_notes',
            nullif(
                p_opportunity ->> 'start_date',
                ''
            )::date,
            nullif(
                p_opportunity ->> 'deadline',
                ''
            )::date,
            p_opportunity ->> 'deadline_text',
            coalesce(
                p_opportunity ->> 'status',
                'unknown'
            ),
            p_opportunity ->> 'application_url',
            p_opportunity ->> 'project_url',
            nullif(
                p_opportunity ->> 'source_posted_at',
                ''
            )::timestamptz,
            p_content_hash,
            coalesce(
                p_opportunity -> 'raw_metadata',
                '{}'::jsonb
            )
        )
        returning id into v_opportunity_id;

        v_created := true;

    else
        v_opportunity_id := p_opportunity_id;

        update public.opportunities
        set
            title = p_opportunity ->> 'title',
            institution = p_opportunity ->> 'institution',
            department = p_opportunity ->> 'department',
            location_text = p_opportunity ->> 'location_text',
            country = coalesce(
                p_opportunity ->> 'country',
                country
            ),
            description = p_opportunity ->> 'description',
            research_area = p_opportunity ->> 'research_area',
            funding_status = coalesce(
                p_opportunity ->> 'funding_status',
                funding_status
            ),
            funding_amount_gbp = nullif(
                p_opportunity ->> 'funding_amount_gbp',
                ''
            )::numeric,
            funding_text = p_opportunity ->> 'funding_text',
            tuition_covered = nullif(
                p_opportunity ->> 'tuition_covered',
                ''
            )::boolean,
            stipend_text = p_opportunity ->> 'stipend_text',
            international_students_eligible = nullif(
                p_opportunity
                    ->> 'international_students_eligible',
                ''
            )::boolean,
            visa_notes = p_opportunity ->> 'visa_notes',
            start_date = nullif(
                p_opportunity ->> 'start_date',
                ''
            )::date,
            deadline = nullif(
                p_opportunity ->> 'deadline',
                ''
            )::date,
            deadline_text = p_opportunity ->> 'deadline_text',
            status = coalesce(
                p_opportunity ->> 'status',
                status
            ),
            application_url = p_opportunity ->> 'application_url',
            project_url = p_opportunity ->> 'project_url',
            source_posted_at = nullif(
                p_opportunity ->> 'source_posted_at',
                ''
            )::timestamptz,
            content_hash = p_content_hash,
            raw_metadata = coalesce(
                p_opportunity -> 'raw_metadata',
                raw_metadata
            ),
            last_seen_at = now()
        where id = v_opportunity_id;

        if not found then
            raise exception
                'Opportunity % does not exist',
                v_opportunity_id;
        end if;

        v_updated := true;
    end if;

    insert into public.opportunity_sources (
        opportunity_id,
        source_id,
        external_id,
        source_url,
        last_seen_at,
        raw_metadata
    )
    values (
        v_opportunity_id,
        v_source_id,
        p_external_id,
        p_source_url,
        now(),
        coalesce(p_raw_metadata, '{}'::jsonb)
    )
    on conflict (source_id, source_url)
    do update set
        opportunity_id = excluded.opportunity_id,
        external_id = excluded.external_id,
        last_seen_at = now(),
        raw_metadata = excluded.raw_metadata;

    if p_create_snapshot then
        insert into public.opportunity_snapshots (
            opportunity_id,
            source_id,
            content_hash,
            snapshot_data,
            change_summary
        )
        values (
            v_opportunity_id,
            v_source_id,
            p_content_hash,
            p_opportunity,
            coalesce(
                p_change_summary,
                '{}'::jsonb
            )
        );

        v_snapshot_created := true;
    end if;

    return jsonb_build_object(
        'opportunity_id', v_opportunity_id,
        'created', v_created,
        'updated', v_updated,
        'snapshot_created', v_snapshot_created
    );
end;
$$;

revoke all
on function public.persist_ingested_opportunity(
    uuid,
    text,
    text,
    text,
    jsonb,
    jsonb,
    text,
    boolean,
    jsonb
)
from public;

grant execute
on function public.persist_ingested_opportunity(
    uuid,
    text,
    text,
    text,
    jsonb,
    jsonb,
    text,
    boolean,
    jsonb
)
to service_role;
