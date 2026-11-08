-- Supabase SQL Editor?êÏÑú ?§Ìñâ?òÏÑ∏??create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

create table if not exists videos (
    id uuid primary key default uuid_generate_v4(),
    youtube_id text unique,
    title text not null,
    description text,
    tags text[],
    topic_category text not null,
    topic_title text not null,
    script_text text not null,
    hook_text text,
    structure_json jsonb,
    duration_seconds integer default 30,
    status text not null default 'draft',
    scheduled_at timestamptz,
    published_at timestamptz,
    thumbnail_path text,
    video_path text,
    error_message text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists video_metrics (
    id uuid primary key default uuid_generate_v4(),
    video_id uuid references videos(id) on delete cascade,
    date date not null,
    views bigint default 0,
    likes bigint default 0,
    comments bigint default 0,
    shares bigint default 0,
    subscribers_gained bigint default 0,
    avg_view_duration_seconds numeric(6,2),
    retention_graph jsonb,
    ctr numeric(5,2),
    impression_count bigint,
    traffic_sources jsonb,
    collected_at timestamptz default now(),
    unique(video_id, date)
);

create table if not exists prompt_versions (
    id uuid primary key default uuid_generate_v4(),
    component text not null,
    version integer not null,
    prompt_template text not null,
    system_prompt text,
    model_name text not null,
    temperature numeric(3,2),
    performance_score numeric(5,2),
    is_active boolean default false,
    notes text,
    created_at timestamptz default now(),
    unique(component, version)
);

create table if not exists pipeline_runs (
    id uuid primary key default uuid_generate_v4(),
    run_id text,
    status text not null,
    video_id uuid references videos(id),
    started_at timestamptz default now(),
    completed_at timestamptz,
    duration_seconds integer,
    steps_completed jsonb,
    error_step text,
    error_details text,
    github_run_url text
);

create index if not exists idx_videos_status on videos(status);
create index if not exists idx_videos_published_at on videos(published_at desc);
create index if not exists idx_metrics_video_date on video_metrics(video_id, date desc);
create index if not exists idx_prompt_active on prompt_versions(component, is_active) where is_active;

alter table videos enable row level security;
alter table video_metrics enable row level security;
alter table prompt_versions enable row level security;
alter table pipeline_runs enable row level security;
