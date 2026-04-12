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

const WINDOW_LABELS: Record<7 | 30 | 90, string> = {
  7: '7D',
  30: '30D',
  90: '90D',
};

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
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-6 transition-all">
      <p className="text-[11px] text-slate-600 leading-relaxed mb-4 px-0.5 border-l-2 border-amber-400 pl-3">
        {t('stats.intro')}
      </p>

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
                : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
            }`}
          >
            {tabLabel(tab)}
          </button>
        ))}
      </div>

      {/* 數據看板 */}
      <div className="grid grid-cols-2 gap-6 divide-x divide-slate-100 mb-6">
        <div className="text-center">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1">
            {t('stats.daily')} {metricLabel}
          </div>
          <div className="flex justify-center items-baseline gap-1.5">
            <span className="text-3xl font-black text-slate-800">{dayRate}%</span>
          </div>
          <div className="text-xs font-bold text-slate-400 mt-1 bg-slate-50 inline-block px-2 py-0.5 rounded">
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
          <div className="text-xs font-bold text-slate-400 mt-1 bg-slate-50 inline-block px-2 py-0.5 rounded">
            {statsData.season.wins}
            {t('common.win')} - {statsData.season.total - statsData.season.wins}
            {t('common.loss')}
          </div>
        </div>
      </div>

      {/* Trend Analysis：滾動視窗快照 + 圖 */}
      {hasHistory && (
        <div className="border-t border-slate-100 pt-4 animate-in fade-in duration-500 relative">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-4 px-1">
            <div>
              <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">{t('stats.trendTitle')}</div>
              <p className="text-[10px] text-slate-400 mt-0.5 leading-relaxed max-w-md">{t('stats.trendHint')}</p>
            </div>
            <div className="flex bg-slate-100 rounded-lg p-1 gap-1 shrink-0 self-end sm:self-auto">
              {([7, 30, 90] as const).map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDaysRange(d)}
                  className={`px-3 py-1 text-[10px] font-bold rounded-md transition-all ${
                    daysRange === d ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-400 hover:text-slate-600'
                  }`}
                >
                  {WINDOW_LABELS[d]}
                </button>
              ))}
            </div>
          </div>

          {/* 7 / 30 / 90 快照表 */}
          {rollingSnapshots && (
            <div className="mb-5 overflow-x-auto rounded-2xl border border-slate-200 bg-gradient-to-b from-slate-50/80 to-white">
              <table className="w-full text-left text-[11px] min-w-[320px]">
                <thead>
                  <tr className="border-b border-slate-200/80 text-[9px] uppercase tracking-widest text-slate-400">
                    <th className="py-2.5 pl-4 font-bold w-[28%]">{t('stats.market')}</th>
                    {rollingSnapshots.map((col) => (
                      <th
                        key={col.days}
                        className={`py-2.5 pr-4 text-right font-black ${
                          daysRange === col.days ? 'text-slate-900 bg-amber-500/10' : ''
                        }`}
                      >
                        {t('stats.nDays', { n: col.days })}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-bold text-slate-700">
                  <tr className="border-b border-slate-100/90">
                    <td className="py-2.5 pl-4 text-amber-700 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                      {t('stats.row.spread')}
                    </td>
                    {rollingSnapshots.map((col) => (
                      <td key={col.days} className={`py-2.5 pr-4 text-right tabular-nums ${daysRange === col.days ? 'bg-amber-500/5' : ''}`}>
                        <span className="text-emerald-700">{t('stats.legWin', { n: col.spread.w })}</span>
                        <span className="text-slate-300 mx-1">/</span>
                        <span className="text-rose-600">{t('stats.legLoss', { n: col.spread.l })}</span>
                        {col.spread.rate != null && (
                          <span className="text-slate-400 font-semibold ml-1.5">({col.spread.rate}%)</span>
                        )}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-slate-100/90">
                    <td className="py-2.5 pl-4 text-emerald-700 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      {t('stats.row.total')}
                    </td>
                    {rollingSnapshots.map((col) => (
                      <td key={col.days} className={`py-2.5 pr-4 text-right tabular-nums ${daysRange === col.days ? 'bg-emerald-500/5' : ''}`}>
                        <span className="text-emerald-700">{t('stats.legWin', { n: col.total.w })}</span>
                        <span className="text-slate-300 mx-1">/</span>
                        <span className="text-rose-600">{t('stats.legLoss', { n: col.total.l })}</span>
                        {col.total.rate != null && (
                          <span className="text-slate-400 font-semibold ml-1.5">({col.total.rate}%)</span>
                        )}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 pl-4 text-indigo-700 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                      {t('stats.row.combined')}
                    </td>
                    {rollingSnapshots.map((col) => (
                      <td key={col.days} className={`py-2.5 pr-4 text-right tabular-nums ${daysRange === col.days ? 'bg-indigo-500/5' : ''}`}>
                        <span className="text-emerald-700">{t('stats.legWin', { n: col.combined.w })}</span>
                        <span className="text-slate-300 mx-1">/</span>
                        <span className="text-rose-600">{t('stats.legLoss', { n: col.combined.l })}</span>
                        {col.combined.rate != null && (
                          <span className="text-slate-400 font-semibold ml-1.5">({col.combined.rate}%)</span>
                        )}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
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
