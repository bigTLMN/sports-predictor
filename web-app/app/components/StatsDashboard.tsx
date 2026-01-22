'use client';

import { useState } from 'react';

type StatsType = 'SPREAD' | 'TOTAL' | 'ALL';

interface StatsProps {
  daily: {
    spreadWin: number; spreadTotal: number;
    ouWin: number; ouTotal: number;
  };
  cumulative: {
    spreadWin: number; spreadTotal: number;
    ouWin: number; ouTotal: number;
  };
}

export default function StatsDashboard({ daily, cumulative }: StatsProps) {
  const [activeTab, setActiveTab] = useState<StatsType>('SPREAD');

  // 計算勝率的小工具
  const calcRate = (wins: number, total: number) => 
    total > 0 ? Math.round((wins / total) * 100) : 0;

  // 根據 Tab 決定要顯示什麼數據
  const getDisplayData = () => {
    switch (activeTab) {
      case 'SPREAD':
        return {
          dayLabel: 'Daily Spread',
          dayWin: daily.spreadWin, dayTotal: daily.spreadTotal,
          allLabel: 'Season Spread',
          allWin: cumulative.spreadWin, allTotal: cumulative.spreadTotal,
        };
      case 'TOTAL':
        return {
          dayLabel: 'Daily Total',
          dayWin: daily.ouWin, dayTotal: daily.ouTotal,
          allLabel: 'Season Total',
          allWin: cumulative.ouWin, allTotal: cumulative.ouTotal,
        };
      case 'ALL':
        return {
          dayLabel: 'Daily Combined',
          dayWin: daily.spreadWin + daily.ouWin, 
          dayTotal: daily.spreadTotal + daily.ouTotal,
          allLabel: 'Season Combined',
          allWin: cumulative.spreadWin + cumulative.ouWin, 
          allTotal: cumulative.spreadTotal + cumulative.ouTotal,
        };
    }
  };

  const data = getDisplayData();
  const dayRate = calcRate(data.dayWin, data.dayTotal);
  const allRate = calcRate(data.allWin, data.allTotal);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
      {/* 頁籤切換 */}
      <div className="flex justify-center gap-2 mb-4">
        {['SPREAD', 'TOTAL', 'ALL'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab as StatsType)}
            className={`px-4 py-1 rounded-full text-xs font-bold transition-colors ${
              activeTab === tab 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {tab === 'ALL' ? 'COMBINED' : tab}
          </button>
        ))}
      </div>

      {/* 數據顯示區 */}
      <div className="grid grid-cols-2 gap-4 divide-x divide-gray-100">
        {/* 左邊：本日戰績 */}
        <div className="text-center">
          <div className="text-xs text-gray-400 uppercase font-bold mb-1">{data.dayLabel}</div>
          <div className="flex justify-center items-baseline gap-1">
            <span className="text-2xl font-black text-gray-800">{dayRate}%</span>
            <span className="text-xs text-gray-500">Win Rate</span>
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {data.dayWin}W - {data.dayTotal - data.dayWin}L
          </div>
        </div>

        {/* 右邊：累積戰績 */}
        <div className="text-center pl-4">
          <div className="text-xs text-gray-400 uppercase font-bold mb-1">{data.allLabel}</div>
          <div className="flex justify-center items-baseline gap-1">
            <span className={`text-2xl font-black ${allRate >= 50 ? 'text-green-600' : 'text-yellow-600'}`}>
              {allRate}%
            </span>
            <span className="text-xs text-gray-500">Win Rate</span>
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {data.allWin}W - {data.allTotal - data.allWin}L
          </div>
        </div>
      </div>
    </div>
  );
}