'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { StatsType } from './StatsDashboard';

// 🔥 1. 更新介面，加入 wins 與 total
interface TrendData {
  date: string;
  winRate: number;
  wins: number;
  total: number;
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
      <div className="flex justify-end items-end mb-3 px-1">
        <div className="text-[12px] font-semibold flex items-center gap-1 bg-current/10 px-2 py-0.5 rounded-full backdrop-blur-sm" style={{ color }}>
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }}></span>
          {label} (Last {days} Days)
        </div>
      </div>
      
      <div className="w-full h-64 bg-[#1A1A1A] rounded-3xl border border--800 p-4 shadow-sm relative overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
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
                backgroundColor: 'rgba(15, 23, 42, 0.6)', 
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(223, 189, 105, 0.3)', 
                boxShadow: '0 10px 15px rgba(0,0,0,0.5)'
              }}
              itemStyle={{ color: color, fontWeight: 'bold', fontSize: '13px' }}
              labelStyle={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}
              // 🔥 2. 修改 Tooltip 顯示格式
              formatter={(value: number, name: string, props: any) => {
                const { wins, total } = props.payload;
                return [`${value}% (${wins}/${total})`, 'Win Rate'];
              }}
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