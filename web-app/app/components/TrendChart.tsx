'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface TrendData {
  date: string;
  winRate: number;
}

export default function TrendChart({ data }: { data: TrendData[] }) {
  if (!data || data.length === 0) return null;

  return (
    <div className="h-[200px] w-full mt-4">
      <div className="text-xs font-bold text-slate-400 mb-2 uppercase tracking-wider">
        7-Day Win Rate Trend
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis 
            dataKey="date" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fontSize: 10, fill: '#94a3b8' }} 
            interval="preserveStartEnd"
          />
          <YAxis 
            hide 
            domain={[0, 100]} 
          />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            itemStyle={{ color: '#2563eb', fontWeight: 'bold', fontSize: '12px' }}
            formatter={(value: number) => [`${value}%`, 'Win Rate']}
          />
          <ReferenceLine y={50} stroke="#cbd5e1" strokeDasharray="3 3" />
          <Line 
            type="monotone" 
            dataKey="winRate" 
            stroke="#2563eb" 
            strokeWidth={3} 
            dot={{ r: 4, fill: '#2563eb', strokeWidth: 2, stroke: '#fff' }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}