'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { StatsType } from './StatsDashboard';

interface TrendData {
  date: string;
  winRate: number;
}

export default function TrendChart({ 
  data, 
  type = 'SPREAD', 
  days = 7 
}: { 
  data: TrendData[], 
  type?: StatsType, 
  days?: number 
}) {
  if (!data || data.length === 0) return null;

  const config = {
    SPREAD: { label: 'Spread Picks', color: '#F59E0B' }, 
    TOTAL:  { label: 'Total Picks',  color: '#10B981' }, 
    ALL:    { label: 'Combined',     color: '#6366F1' }, 
  };

  const { label, color } = config[type];

  return (
    <div className="w-full mb-2 select-none">
      
      {/* 標題區塊 */}
      <div className="flex justify-end items-end mb-2 px-1">
        <div className="text-[10px] font-black flex items-center gap-1" style={{ color }}>
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }}></span>
          {label} (Last {days} Days)
        </div>
      </div>
      
      <div className="w-full h-64 bg-[#1A1A1A] rounded-xl border border-gray-800 p-4 shadow-sm relative overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          {/* 🔥 修正 Margin: left 改為 0 或正數，讓 Y 軸標籤有空間顯示 */}
          <LineChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.5} />
            
            <XAxis 
              dataKey="date" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fontSize: 10, fill: '#94a3b8' }} 
              dy={10}
              minTickGap={days > 30 ? 30 : 10} 
              interval="preserveStartEnd"
            />
            
            {/* 🔥 新增 Y 軸標籤: 顯示 0, 25, 50, 75, 100 */}
            <YAxis 
              width={30}
              domain={[0, 100]} 
              axisLine={false}
              tickLine={false}
              ticks={[0, 25, 50, 75, 100]}
              tick={{ fontSize: 10, fill: '#64748b', fontWeight: 'bold' }}
            />
            
            <Tooltip 
              cursor={{ stroke: '#475569', strokeWidth: 1 }}
              contentStyle={{ 
                backgroundColor: '#0F172A', 
                border: '1px solid #1E293B', 
                borderRadius: '8px',
              }}
              itemStyle={{ color: color, fontWeight: 'bold', fontSize: '13px' }}
              labelStyle={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}
              formatter={(value: any) => [`${value}%`, 'Win Rate']}
            />
            
            <ReferenceLine y={50} stroke="#475569" strokeDasharray="3 3" />
            
            <Line 
              type="monotone" 
              dataKey="winRate" 
              stroke={color} 
              strokeWidth={2} 
              dot={days <= 30 ? { r: 3, fill: '#1A1A1A', stroke: color, strokeWidth: 2 } : false} 
              activeDot={{ r: 6, fill: color, stroke: '#FFF' }}
              animationDuration={500}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}