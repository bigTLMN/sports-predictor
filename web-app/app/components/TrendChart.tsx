// web-app/app/components/TrendChart.tsx
'use client';

import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { StatsType } from './StatsDashboard';
import { useI18n } from '@/lib/i18n';

export interface TrendData {
  date: string;
  winRate: number;
  wins: number;
  total: number;
}

function ChartTooltip(props: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: TrendData }>;
  label?: string | number;
  color: string;
}) {
  const { active, payload, label, color } = props;
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload as TrendData | undefined;
  if (!row) return null;
  return (
    <div
      className="rounded-xl px-3 py-2 shadow-xl border"
      style={{
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        borderColor: 'rgba(223, 189, 105, 0.25)',
      }}
    >
      <p className="text-[11px] text-slate-400 mb-1">{label}</p>
      <p className="text-[13px] font-bold tabular-nums" style={{ color }}>
        {row.winRate}% <span className="text-slate-400 font-semibold">({row.wins}/{row.total})</span>
      </p>
    </div>
  );
}

export default function TrendChart({
  data,
  type = 'SPREAD',
  days = 7,
}: {
  data: TrendData[];
  type?: StatsType;
  days?: number;
}) {
  if (!data || data.length === 0) return null;

  return <TrendChartInner data={data} type={type} days={days} />;
}

function TrendChartInner({
  data,
  type,
  days,
}: {
  data: TrendData[];
  type: StatsType;
  days: number;
}) {
  const { t } = useI18n();

  const labelKey = type === 'ALL' ? 'combined' : type === 'TOTAL' ? 'total' : 'spread';
  const metricLabel = t(`stats.label.${labelKey}`);

  const config = {
    SPREAD: { color: '#F59E0B', gradientId: 'trendSpread' },
    TOTAL: { color: '#10B981', gradientId: 'trendTotal' },
    ALL: { color: '#6366F1', gradientId: 'trendAll' },
  };

  const { color, gradientId } = config[type];

  const meanOfDailyRates =
    data.length > 0
      ? Math.round(data.reduce((s, d) => s + d.winRate, 0) / data.length)
      : 0;

  return (
    <div className="w-full mb-2 select-none">
      <div className="flex flex-wrap justify-between items-end gap-2 mb-3 px-1">
        <div
          className="text-[12px] font-semibold flex items-center gap-1.5 bg-current/10 px-2.5 py-1 rounded-full backdrop-blur-sm"
          style={{ color }}
        >
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
          {t('trend.dailyRate', { label: metricLabel })}
        </div>
        <div className="text-right max-w-[220px]">
          <div className="text-[10px] font-bold text-slate-500">
            {t('trend.meanRates')}{' '}
            <span className="text-slate-800 tabular-nums">{meanOfDailyRates}%</span>
          </div>
          <div className="text-[9px] text-slate-400 leading-tight mt-0.5">{t('trend.meanFootnote')}</div>
        </div>
      </div>

      <div className="w-full h-64 bg-[#1A1A1A] rounded-3xl border border-slate-800 p-4 shadow-sm relative overflow-hidden ring-1 ring-white/[0.03]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.5} />
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              dy={10}
              minTickGap={10}
              interval="preserveStartEnd"
            />
            <YAxis
              width={34}
              domain={[0, 100]}
              axisLine={false}
              tickLine={false}
              ticks={[0, 25, 50, 75, 100]}
              tick={{ fontSize: 10, fill: '#64748b', fontWeight: 'bold' }}
            />

            {/* Single tooltip: Area+Line share winRate — default would duplicate rows */}
            <Tooltip
              cursor={{ stroke: '#475569', strokeWidth: 1 }}
              content={(tooltipProps) => <ChartTooltip {...tooltipProps} color={color} />}
            />

            <ReferenceLine y={50} stroke="#475569" strokeDasharray="3 3" />
            <Area
              type="monotone"
              dataKey="winRate"
              stroke="none"
              fill={`url(#${gradientId})`}
              fillOpacity={1}
              isAnimationActive={true}
              animationDuration={400}
            />
            <Line
              type="monotone"
              dataKey="winRate"
              stroke={color}
              strokeWidth={2.5}
              dot={{ r: days > 30 ? 2 : 3, fill: '#1A1A1A', stroke: color, strokeWidth: 2 }}
              activeDot={{ r: 6, fill: color, stroke: '#FFF' }}
              animationDuration={500}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
