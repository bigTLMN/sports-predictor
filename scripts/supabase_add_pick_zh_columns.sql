-- Run once in Supabase SQL editor so aggregate_picks can store Traditional Chinese.
-- Optional but recommended: without these columns, upsert may ignore or error depending on API settings.

alter table public.aggregated_picks
  add column if not exists spread_logic_zh text;

alter table public.aggregated_picks
  add column if not exists analysis_content_zh text;

comment on column public.aggregated_picks.spread_logic_zh is '繁體中文讓分說明（與 spread_logic 並存）';
comment on column public.aggregated_picks.analysis_content_zh is '繁體中文系統分析（與 analysis_content 並存）';
