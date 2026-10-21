'use client';

import { useEffect, useState, useMemo } from 'react';
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
  const [trendOpen, setTrendOpen] = useState(false);

  useEffect(() => {
    try {
      if (localStorage.getItem('edge-analytics-trend-open') === '1') setTrendOpen(true);
    } catch {
      /* ignore */
    }
  }, []);

  const toggleTrend = () => {
    setTrendOpen((open) => {
      const next = !open;
      try {
        localStorage.setItem('edge-analytics-trend-open', next ? '1' : '0');
      } catch {
        /* ignore */
      }
      return next;
    });
  };

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
            className={`px-5 py-1.5 rounded-full text-sm font-black tracking-wider transition-all duration-300 ${
              activeTab === tab
                ? 'bg-slate-900 text-white shadow-lg transform scale-105'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            {tabLabel(tab)}
          </button>
        ))}
      </div>

      {/* 數據看板 */}
      <div className="grid grid-cols-2 gap-6 divide-x divide-slate-100 dark:divide-slate-800 mb-6">
        <div className="text-center">
          <div className="text-sm text-slate-600 dark:text-slate-300 uppercase font-bold tracking-widest mb-1">
            {t('stats.daily')} {metricLabel}
          </div>
          <div className="flex justify-center items-baseline gap-1.5">
            <span className="text-3xl font-black text-slate-800 dark:text-white">{dayRate}%</span>
          </div>
          <div className="text-sm font-bold text-slate-700 dark:text-slate-200 mt-1 bg-slate-100 dark:bg-slate-800 inline-block px-2 py-0.5 rounded">
            {statsData.day.wins}
            {t('common.win')} - {statsData.day.total - statsData.day.wins}
            {t('common.loss')}
          </div>
        </div>

        <div className="text-center pl-6">
          <div className="text-sm text-slate-600 dark:text-slate-300 uppercase font-bold tracking-widest mb-1">
            {t('stats.allTime')} {metricLabel}
          </div>
          <div className="flex justify-center items-baseline gap-1.5">
            <span className={`text-3xl font-black ${seasonRate >= 53 ? 'text-green-600' : 'text-amber-500'}`}>
              {seasonRate}%
            </span>
          </div>
          <div className="text-sm font-bold text-slate-700 dark:text-slate-200 mt-1 bg-slate-100 dark:bg-slate-800 inline-block px-2 py-0.5 rounded">
            {statsData.season.wins}
            {t('common.win')} - {statsData.season.total - statsData.season.wins}
            {t('common.loss')}
          </div>
        </div>
      </div>

      {/* Trend Analysis：滾動視窗快照 + 圖 */}
      {hasHistory && (
        <div className="border-t border-slate-200 dark:border-slate-700 pt-4 relative">
          <div className="rounded-xl border border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-800/80">
            <div className="flex items-center justify-between gap-3 px-3 py-2.5">
              <button
                type="button"
                onClick={toggleTrend}
                aria-expanded={trendOpen}
                className="flex flex-1 items-center gap-2 text-left text-sm font-bold text-slate-800 dark:text-white uppercase tracking-wider"
              >
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-white dark:bg-white dark:text-slate-900 ${trendOpen ? '' : 'animate-[trend-nudge_1.2s_ease-in-out_infinite]'}`}
                >
                  <svg
                    className={`h-3.5 w-3.5 transition-transform duration-300 ${trendOpen ? 'rotate-90' : ''}`}
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path d="M7 5l6 5-6 5V5z" />
                  </svg>
                </span>
                {t('stats.trendTitle')}
              </button>
              {trendOpen && (
                <div className="flex bg-slate-200 dark:bg-slate-900 rounded-lg p-1 gap-1 shrink-0">
                  {([7, 30, 90] as const).map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDaysRange(d)}
                      className={`px-3 py-1 text-sm font-bold rounded-md transition-all ${
                        daysRange === d ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-950 dark:text-white' : 'text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white'
                      }`}
                    >
                      {t('stats.nDays', { n: d })}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className={`grid transition-[grid-template-rows] duration-300 ease-out ${trendOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
              <div className="overflow-hidden min-h-0">
                <div className="px-3 pb-3">
                  {rollingSnapshots && (
                    <RollingBoard snapshots={rollingSnapshots} activeDays={daysRange} t={t} />
                  )}

                  {statsData.trend.length > 0 ? (
                    <div style={{ minHeight: '300px', width: '100%' }}>
                      <TrendChart data={statsData.trend as any[]} type={activeTab} days={daysRange} />
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 py-12 text-center text-sm font-bold text-slate-600 dark:border-slate-600 dark:bg-slate-900/40 dark:text-slate-300">
                      {t('stats.noDailyResults', { label: metricLabel })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {!hasHistory && (
        <p className="text-center text-sm text-slate-400 mt-2">{t('stats.noHistory')}</p>
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
      <div className="grid grid-cols-4 gap-2 text-sm font-bold tracking-wide text-slate-500">
        <div />
        {snapshots.map((col) => (
          <div key={col.days} className={`text-right ${activeDays === col.days ? 'text-[#dfbd69]' : ''}`}>
            {t('stats.nDays', { n: col.days })}
          </div>
        ))}
      </div>
      {rows.map((row) => (
        <div key={row.key} className="grid grid-cols-4 gap-2 items-end border-t border-white/10 mt-2 pt-2">
          <div className="text-sm font-bold">{row.label}</div>
          {snapshots.map((col) => {
            const leg = col[row.key];
            return (
              <div key={col.days} className="text-right">
                <div className={`text-2xl font-bold leading-none tabular-nums ${activeDays === col.days ? 'text-[#dfbd69]' : 'text-white'}`}>
                  {rateText(leg)}
                </div>
                <div className="mt-1 text-sm font-bold text-slate-400 tabular-nums">{record(leg)}</div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
