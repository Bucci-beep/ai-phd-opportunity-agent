truncate table
    public.opportunity_snapshots,
    public.applications,
    public.opportunity_supervisors,
    public.opportunity_sources,
    public.opportunities,
    public.supervisors,
    public.sources
restart identity cascade;

insert into public.sources (
    name,
    source_type,
    base_url
)
values
(
    'FindAPhD',
    'jobs_board',
    'https://www.findaphd.com'
),
(
    'jobs.ac.uk',
    'jobs_board',
    'https://www.jobs.ac.uk'
),
(
    'UKRI',
    'funding_body',
    'https://www.ukri.org'
);


insert into public.supervisors (
    name,
    institution,
    department,
    email,
    research_interests,
    bio,
    search_document
)
values
(
    'Dr Sarah Ahmed',
    'Example University',
    'School of Computer Science',
    'sarah.ahmed@example.ac.uk',
    array[
        'artificial intelligence',
        'machine learning',
        'digital health',
        'ECG analysis'
    ],
    'Researcher working on machine learning methods for clinical data and cardiovascular applications.',
    'artificial intelligence machine learning digital health ECG cardiovascular clinical AI'
);


insert into public.opportunities (
    title,
    institution,
    department,
    location_text,
    description,
    research_area,
    funding_status,
    funding_text,
    tuition_covered,
    stipend_text,
    international_students_eligible,
    deadline,
    status,
    application_url,
    search_document
)
values
(
    'Fully Funded PhD in Artificial Intelligence for Cardiovascular Monitoring',
    'Example University',
    'School of Computer Science',
    'Bristol, United Kingdom',
    'Research into machine learning methods for analysing ECG and wearable cardiovascular data.',
    'Artificial Intelligence and Digital Health',
    'fully_funded',
    'Full tuition fees and doctoral stipend',
    true,
    'UKRI aligned doctoral stipend',
    true,
    '2027-01-31',
    'open',
    'https://example.ac.uk/phd/ecg-ai',
    'fully funded PhD artificial intelligence machine learning ECG cardiovascular monitoring digital health wearable healthcare Bristol'
);

insert into public.opportunity_supervisors (
    opportunity_id,
    supervisor_id,
    is_primary
)
select
    o.id,
    s.id,
    true
from public.opportunities o
cross join public.supervisors s
where o.title =
    'Fully Funded PhD in Artificial Intelligence for Cardiovascular Monitoring'
and s.name = 'Dr Sarah Ahmed'
on conflict (opportunity_id, supervisor_id)
do nothing;


insert into public.opportunity_sources (
    opportunity_id,
    source_id,
    external_id,
    source_url
)
select
    o.id,
    s.id,
    'TEST-ECG-AI-001',
    'https://www.findaphd.com/test/ecg-ai'
from public.opportunities o
cross join public.sources s
where o.title =
    'Fully Funded PhD in Artificial Intelligence for Cardiovascular Monitoring'
and s.name = 'FindAPhD'
on conflict (source_id, source_url)
do nothing;


insert into public.opportunity_snapshots (
    opportunity_id,
    source_id,
    content_hash,
    snapshot_data
)
select
    o.id,
    s.id,
    'test_snapshot_hash_001',
    jsonb_build_object(
        'title', o.title,
        'institution', o.institution,
        'funding_status', o.funding_status,
        'deadline', o.deadline,
        'status', o.status
    )
from public.opportunities o
cross join public.sources s
where o.title =
    'Fully Funded PhD in Artificial Intelligence for Cardiovascular Monitoring'
and s.name = 'FindAPhD'
and not exists (
    select 1
    from public.opportunity_snapshots os
    where os.opportunity_id = o.id
    and os.content_hash = 'test_snapshot_hash_001'
);

