'use client';

import { useState, useMemo } from 'react';
import { differenceInCalendarDays, parseISO } from 'date-fns';
import dynamic from 'next/dynamic';
import { useI18n } from '@/lib/i18n';

const TrendChart = dynamic(() => import('./TrendChart'), {
  ssr: false,
  loading: () => <div className="w-full h-64 bg-slate-100 animate-pulse rounded-xl" />,
});

export type StatsType = 'SPREAD' | 'TOTAL' | 'ALL';

interface StatsDashboardProps {
  dailyPicks: any[];
  historyPicks: any[];
}

function matchDayString(p: any): string | undefined {
  const d = p?.matches?.date;
  if (d == null) return undefined;
  return typeof d === 'string' ? d.slice(0, 10) : undefined;
}

/** 比賽日落在「今天往回算 N 個曆日」內（含今日） */
function inRollingCalendarWindow(p: any, days: number): boolean {
  const md = matchDayString(p);
  if (!md) return false;
  const d = parseISO(`${md}T12:00:00`);
  const diff = differenceInCalendarDays(new Date(), d);
  return diff >= 0 && diff < days;
}

function countSpreadLegs(picks: any[]): { w: number; l: number } {
  let w = 0;
  let l = 0;
  for (const p of picks) {
    if (p.spread_outcome === 'WIN') w++;
    else if (p.spread_outcome === 'LOSS') l++;
  }
  return { w, l };
}

function countTotalLegs(picks: any[]): { w: number; l: number } {
  let w = 0;
  let l = 0;
  for (const p of picks) {
    if (p.total_outcome === 'WIN') w++;
    else if (p.total_outcome === 'LOSS') l++;
  }
  return { w, l };
}

/** Combined = 每場的 spread 腿 + total 腿加總（與原 COMBINED 分母一致） */
function countCombinedLegs(picks: any[]): { w: number; l: number } {
  let w = 0;
  let l = 0;
  for (const p of picks) {
    if (p.spread_outcome === 'WIN') w++;
    else if (p.spread_outcome === 'LOSS') l++;
    if (p.total_outcome === 'WIN') w++;
    else if (p.total_outcome === 'LOSS') l++;
  }
  return { w, l };
}

function pct(w: number, l: number): number | null {
  const t = w + l;
  if (t === 0) return null;
  return Math.round((w / t) * 1000) / 10;
}

function filterPicksByTab(picks: any[], activeTab: StatsType) {
  let wins = 0;
  let total = 0;

  picks.forEach((p) => {
    if (activeTab === 'SPREAD' || activeTab === 'ALL') {
      if (p.spread_outcome === 'WIN') wins++;
      if (p.spread_outcome === 'WIN' || p.spread_outcome === 'LOSS') total++;
    }
    if (activeTab === 'TOTAL' || activeTab === 'ALL') {
      if (p.total_outcome === 'WIN') wins++;
      if (p.total_outcome === 'WIN' || p.total_outcome === 'LOSS') total++;
    }
  });
  return { wins, total };
}

export default function StatsDashboard({ dailyPicks, historyPicks }: StatsDashboardProps) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<StatsType>('SPREAD');
  const [daysRange, setDaysRange] = useState<7 | 30 | 90>(7);

  const rollingSnapshots = useMemo(() => {
    const windows = [7, 30, 90] as const;
    if (!historyPicks?.length) return null;

    return windows.map((days) => {
      const subset = historyPicks.filter((p) => inRollingCalendarWindow(p, days));
      const sp = countSpreadLegs(subset);
      const to = countTotalLegs(subset);
      const cb = countCombinedLegs(subset);
      return {
        days,
        spread: { ...sp, rate: pct(sp.w, sp.l) },
        total: { ...to, rate: pct(to.w, to.l) },
        combined: { ...cb, rate: pct(cb.w, cb.l) },
      };
    });
  }, [historyPicks]);

  const statsData = useMemo(() => {
    const filterPicks = (picks: any[]) => filterPicksByTab(picks, activeTab);

    const dayStats = filterPicks(dailyPicks);
    const seasonStats = filterPicks(historyPicks);

    const dates = [...Array(daysRange)].map((_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (daysRange - 1 - i));
      return d.toISOString().split('T')[0];
    });

    const trend = dates
      .map((date) => {
        const dayPicks = historyPicks.filter((p: any) => p.matches?.date?.startsWith(date));
        const { wins, total } = filterPicks(dayPicks);

        return {
          date: date.slice(5),
          fullDate: date,
          winRate: total > 0 ? Math.round((wins / total) * 100) : 0,
          count: total,
          wins,
          total,
        };
      })
      .filter((t) => t.count > 0);

    const labelKey: 'spread' | 'total' | 'combined' =
      activeTab === 'TOTAL' ? 'total' : activeTab === 'ALL' ? 'combined' : 'spread';

    return {
      day: dayStats,
      season: seasonStats,
      trend,
      labelKey,
    };
  }, [dailyPicks, historyPicks, activeTab, daysRange]);

  const dayRate = statsData.day.total > 0 ? Math.round((statsData.day.wins / statsData.day.total) * 100) : 0;
  const seasonRate =
    statsData.season.total > 0 ? Math.round((statsData.season.wins / statsData.season.total) * 100) : 0;

  const hasHistory = historyPicks && historyPicks.length > 0;

  const tabLabel = (tab: StatsType) =>
    tab === 'ALL' ? t('stats.tab.combined') : tab === 'TOTAL' ? t('stats.tab.total') : t('stats.tab.spread');

  const metricLabel = t(`stats.label.${statsData.labelKey}`);

  return (
    <div className="bg-white text-slate-900 dark:bg-[#161b22] dark:text-slate-100 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800 p-5 mb-6 transition-all">
      {/* 頁籤切換 */}
      <div className="flex justify-center gap-2 mb-6">
        {(['SPREAD', 'TOTAL', 'ALL'] as StatsType[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`px-5 py-1.5 rounded-full text-xs font-black tracking-wider transition-all duration-300 ${
              activeTab === tab
                ? 'bg-slate-900 text-white shadow-lg transform scale-105'
                : 'bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700'
            }`}
          >
            {tabLabel(tab)}
          </button>
        ))}
      </div>

      {/* 數據看板 */}
      <div className="grid grid-cols-2 gap-6 divide-x divide-slate-100 dark:divide-slate-800 mb-6">
        <div className="text-center">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1">
            {t('stats.daily')} {metricLabel}
          </div>
          <div className="flex justify-center items-baseline gap-1.5">
            <span className="text-3xl font-black text-slate-800 dark:text-white">{dayRate}%</span>
          </div>
          <div className="text-xs font-bold text-slate-400 mt-1 bg-slate-50 dark:bg-slate-800 inline-block px-2 py-0.5 rounded">
            {statsData.day.wins}
            {t('common.win')} - {statsData.day.total - statsData.day.wins}
            {t('common.loss')}
          </div>
        </div>

        <div className="text-center pl-6">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1">
            {t('stats.allTime')} {metricLabel}
          </div>
          <div className="flex justify-center items-baseline gap-1.5">
            <span className={`text-3xl font-black ${seasonRate >= 53 ? 'text-green-600' : 'text-amber-500'}`}>
              {seasonRate}%
            </span>
          </div>
          <div className="text-xs font-bold text-slate-400 mt-1 bg-slate-50 dark:bg-slate-800 inline-block px-2 py-0.5 rounded">
            {statsData.season.wins}
            {t('common.win')} - {statsData.season.total - statsData.season.wins}
            {t('common.loss')}
          </div>
        </div>
      </div>

      {/* Trend Analysis：滾動視窗快照 + 圖 */}
      {hasHistory && (
        <div className="border-t border-slate-100 dark:border-slate-800 pt-4 animate-in fade-in duration-500 relative">
          <div className="flex items-center justify-between gap-3 mb-4 px-1">
              <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{t('stats.trendTitle')}</div>
            <div className="flex bg-slate-100 rounded-lg p-1 gap-1 shrink-0">
              {([7, 30, 90] as const).map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDaysRange(d)}
                  className={`px-3 py-1 text-[10px] font-bold rounded-md transition-all ${
                    daysRange === d ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-400 hover:text-slate-600'
                  }`}
                >
                  {t('stats.nDays', { n: d })}
                </button>
              ))}
            </div>
          </div>

          {rollingSnapshots && (
            <RollingBoard snapshots={rollingSnapshots} activeDays={daysRange} t={t} />
          )}

          {statsData.trend.length > 0 ? (
            <div style={{ minHeight: '300px', width: '100%' }}>
              <TrendChart data={statsData.trend as any[]} type={activeTab} days={daysRange} />
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 py-12 text-center text-xs font-bold text-slate-400">
              {t('stats.noDailyResults', { label: metricLabel })}
            </div>
          )}
        </div>
      )}

      {!hasHistory && (
        <p className="text-center text-[10px] text-slate-400 mt-2">{t('stats.noHistory')}</p>
      )}
    </div>
  );
}

type Leg = { w: number; l: number; rate: number | null };
type Snapshot = {
  days: number;
  spread: Leg;
  total: Leg;
  combined: Leg;
};

function RollingBoard({
  snapshots,
  activeDays,
  t,
}: {
  snapshots: Snapshot[];
  activeDays: number;
  t: (key: string, vars?: Record<string, string | number>) => string;
}) {
  const rows: { key: keyof Pick<Snapshot, 'spread' | 'total' | 'combined'>; label: string }[] = [
    { key: 'spread', label: t('stats.row.spread') },
    { key: 'total', label: t('stats.row.total') },
    { key: 'combined', label: t('stats.row.combined') },
  ];
  const rateText = (leg: Leg) => (leg.rate == null ? '—' : `${leg.rate}%`);
  const record = (leg: Leg) => `${t('stats.legWin', { n: leg.w })} ${t('stats.legLoss', { n: leg.l })}`;

  return (
    <div className="mb-5 rounded-2xl bg-[#0D1117] text-white p-4">
      <div className="grid grid-cols-4 gap-2 text-[10px] font-bold tracking-wide text-slate-500">
        <div />
        {snapshots.map((col) => (
          <div key={col.days} className={`text-right ${activeDays === col.days ? 'text-[#dfbd69]' : ''}`}>
            {t('stats.nDays', { n: col.days })}
          </div>
        ))}
      </div>
      {rows.map((row) => (
        <div key={row.key} className="grid grid-cols-4 gap-2 items-end border-t border-white/10 mt-2 pt-2">
          <div className="text-xs font-bold">{row.label}</div>
          {snapshots.map((col) => {
            const leg = col[row.key];
            return (
              <div key={col.days} className="text-right">
                <div className={`text-lg font-bold leading-none tabular-nums ${activeDays === col.days ? 'text-[#dfbd69]' : 'text-white'}`}>
                  {rateText(leg)}
                </div>
                <div className="mt-1 text-[10px] font-bold text-slate-400 tabular-nums">{record(leg)}</div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
