'use client';

import { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';

const TrendChart = dynamic(() => import('./TrendChart'), { 
  ssr: false,
  loading: () => <div className="w-full h-64 bg-slate-100 animate-pulse rounded-xl" /> 
});

export type StatsType = 'SPREAD' | 'TOTAL' | 'ALL';

interface StatsDashboardProps {
  dailyPicks: any[];   
  historyPicks: any[]; 
}

export default function StatsDashboard({ dailyPicks, historyPicks }: StatsDashboardProps) {
  const [activeTab, setActiveTab] = useState<StatsType>('SPREAD');
  const [daysRange, setDaysRange] = useState<7 | 30 | 90>(7);

  const statsData = useMemo(() => {
    const filterPicks = (picks: any[]) => {
      let wins = 0;
      let total = 0;
      
      picks.forEach(p => {
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
    };

    const dayStats = filterPicks(dailyPicks);
    const seasonStats = filterPicks(historyPicks);

    const dates = [...Array(daysRange)].map((_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - ((daysRange - 1) - i)); 
      return d.toISOString().split('T')[0];
    });

    const trend = dates.map(date => {
      const dayPicks = historyPicks.filter((p: any) => p.matches?.date?.startsWith(date));
      const { wins, total } = filterPicks(dayPicks);
      
      return {
        date: date.slice(5), // MM-DD
        fullDate: date,      
        winRate: total > 0 ? Math.round((wins / total) * 100) : 0,
        count: total,
        // 🔥 這裡加入 wins 和 total 讓 TrendChart 使用
        wins: wins,
        total: total
      };
    })
    .filter(t => t.count > 0);

    let label = 'Spread';
    if (activeTab === 'TOTAL') label = 'Total';
    if (activeTab === 'ALL') label = 'Combined';

    return {
      day: dayStats,
      season: seasonStats,
      trend: trend,
      label: label
    };
  }, [dailyPicks, historyPicks, activeTab, daysRange]); 

  const dayRate = statsData.day.total > 0 ? Math.round((statsData.day.wins / statsData.day.total) * 100) : 0;
  const seasonRate = statsData.season.total > 0 ? Math.round((statsData.season.wins / statsData.season.total) * 100) : 0;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-6 transition-all">
      
      {/* 頁籤切換 */}
      <div className="flex justify-center gap-2 mb-6">
        {(['SPREAD', 'TOTAL', 'ALL'] as StatsType[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-5 py-1.5 rounded-full text-xs font-black tracking-wider transition-all duration-300 ${
              activeTab === tab 
                ? 'bg-slate-900 text-white shadow-lg transform scale-105' 
                : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
            }`}
          >
            {tab === 'ALL' ? 'COMBINED' : tab}
          </button>
        ))}
      </div>

      {/* 數據看板 */}
      <div className="grid grid-cols-2 gap-6 divide-x divide-slate-100 mb-6">
        <div className="text-center">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1">
            Daily {statsData.label}
          </div>
          <div className="flex justify-center items-baseline gap-1.5">
            <span className="text-3xl font-black text-slate-800">{dayRate}%</span>
          </div>
          <div className="text-xs font-bold text-slate-400 mt-1 bg-slate-50 inline-block px-2 py-0.5 rounded">
            {statsData.day.wins}W - {statsData.day.total - statsData.day.wins}L
          </div>
        </div>

        <div className="text-center pl-6">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1">
            Season {statsData.label}
          </div>
          <div className="flex justify-center items-baseline gap-1.5">
            <span className={`text-3xl font-black ${seasonRate >= 53 ? 'text-green-600' : 'text-amber-500'}`}>
              {seasonRate}%
            </span>
          </div>
          <div className="text-xs font-bold text-slate-400 mt-1 bg-slate-50 inline-block px-2 py-0.5 rounded">
            {statsData.season.wins}W - {statsData.season.total - statsData.season.wins}L
          </div>
        </div>
      </div>

      {/* 整合圖表 */}
      {statsData.trend.length > 0 && (
        <div className="border-t border-slate-100 pt-4 animate-in fade-in duration-500 relative">
           
           {/* 天數切換按鈕 */}
           <div className="flex justify-between items-center mb-4 px-1">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Trend Analysis
              </div>
              <div className="flex bg-slate-100 rounded-lg p-1 gap-1">
                {[7, 30, 90].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDaysRange(d as any)}
                    className={`px-3 py-1 text-[10px] font-bold rounded-md transition-all ${
                      daysRange === d 
                        ? 'bg-white text-slate-800 shadow-sm' 
                        : 'text-slate-400 hover:text-slate-600'
                    }`}
                  >
                    {d}D
                  </button>
                ))}
              </div>
           </div>

           <div style={{ minHeight: '300px', width: '100%' }}>
              <TrendChart data={statsData.trend as any[]} type={activeTab} days={daysRange} />
           </div>
        </div>
      )}
      
    </div>
  );
}