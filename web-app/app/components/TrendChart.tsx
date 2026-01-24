'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface TrendData {
  date: string;
  winRate: number;
}

export default function TrendChart({ data }: { data: TrendData[] }) {
  // 如果沒有數據，就不顯示圖表
  if (!data || data.length === 0) return null;

  return (
    <div className="h-[200px] w-full mt-6 mb-2 select-none">
      <div className="flex justify-between items-end mb-2 px-1">
        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
          Winning Trend (Last 7 Days)
        </div>
        <div className="text-[10px] font-medium text-slate-300">
          Spread Picks
        </div>
      </div>
      
      <div className="w-full h-full bg-white rounded-xl border border-slate-100 p-2 shadow-sm">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis 
              dataKey="date" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fontSize: 10, fill: '#94a3b8' }} 
              interval="preserveStartEnd"
              dy={10}
            />
            <YAxis 
              hide 
              domain={[0, 100]} 
            />
            <Tooltip 
              contentStyle={{ 
                borderRadius: '8px', 
                border: 'none', 
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                padding: '8px 12px'
              }}
              itemStyle={{ color: '#2563eb', fontWeight: '900', fontSize: '14px' }}
              labelStyle={{ fontSize: '10px', color: '#64748b', marginBottom: '4px' }}
              // 🔥 修正處：將類型改為 any 以解決 TypeScript 報錯
              formatter={(value: any) => [`${value}%`, 'Win Rate']}
            />
            {/* 50% 勝率參考線 */}
            <ReferenceLine y={50} stroke="#cbd5e1" strokeDasharray="3 3" />
            
            <Line 
              type="monotone" 
              dataKey="winRate" 
              stroke="#2563eb" 
              strokeWidth={3} 
              dot={{ r: 4, fill: '#2563eb', strokeWidth: 2, stroke: '#fff' }}
              activeDot={{ r: 6, strokeWidth: 0 }}
              animationDuration={1500}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}