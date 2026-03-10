'use client';

import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { twMerge } from 'tailwind-merge';
import Link from 'next/link';

// 定義各節比分型別
type PeriodScores = {
  home: number[];
  away: number[];
};

interface MatchCardProps {
  pick: any; 
  index: number;
}

export default function MatchCard({ pick, index }: MatchCardProps) {
  const m = pick.matches;
  
  // 🔥 關鍵判斷：根據是否有 'recommended_team' 來決定是否顯示預測內容
  const hasPrediction = !!pick.recommended_team;

  const isFinished = m.status === 'STATUS_FINISHED' || m.status === 'STATUS_FINAL' || m.status === 'Final';
  const isLive = m.status === 'STATUS_IN_PROGRESS';
  
  const spreadText = m.vegas_spread !== null 
    ? (m.vegas_spread > 0 ? `+${m.vegas_spread}` : m.vegas_spread) 
    : 'PK';

  // 若無預測，信心度視為 0
  const isHighConfidence = hasPrediction && pick.confidence_score >= 80;

  // 🔥 處理各節比分 (League Pass 風格)
  const periodScores = m.period_scores as PeriodScores | null;
  const showScoreboard = (isFinished || isLive) && periodScores;

  // 計算總共幾節 (最少4節)
  const totalPeriods = periodScores ? Math.max(4, periodScores.home.length) : 4;
  
  // 產生表頭
  const headers = Array.from({ length: totalPeriods }, (_, i) => {
    if (i < 4) return `Q${i + 1}`;
    return `OT${i - 3}`;
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="group relative h-full"
    >
      {/* 連結控制：只有當有預測時才允許點擊跳轉 */}
      <Link href={hasPrediction ? `/match/${pick.match_id}` : '#'} className={`block h-full ${!hasPrediction && 'cursor-default pointer-events-none'}`}>
          <div className={twMerge(
            "bg-white rounded-2xl shadow-sm border overflow-hidden transition-all relative h-full flex flex-col",
            hasPrediction ? "hover:shadow-lg transform group-hover:-translate-y-1" : "bg-slate-50",
            isHighConfidence ? "border-blue-200 ring-2 ring-blue-100/50" : "border-slate-200"
          )}>
            
            {/* High Value Tag */}
            {isHighConfidence && (
                <div className="absolute top-0 right-0 z-20">
                    <div className="bg-gradient-to-l from-blue-600 to-blue-500 text-white text-[9px] font-black px-2 py-1 rounded-bl-xl shadow-sm uppercase tracking-wider flex items-center gap-1">
                        🔥 High Value
                    </div>
                </div>
            )}

            {/* 左上角 Badge：真實盤口 */}
            <div className="absolute top-0 left-0 bg-slate-900 text-white px-3 py-1.5 rounded-br-xl z-10 shadow-sm">
                <div className="text-[9px] font-bold tracking-widest text-slate-400 uppercase mb-0.5">VEGAS</div>
                <div className="text-xs font-black leading-none flex items-center gap-1">
                <span>{m.home_team.code}</span>
                <span className="text-yellow-400">{spreadText}</span>
                </div>
            </div>

            {/* Header: 對戰組合 */}
            <div className="pt-10 pb-2 px-4 flex justify-between items-center bg-gradient-to-b from-slate-50 to-white">
                {/* 客隊 */}
                <div className="flex flex-col items-center w-1/3 relative">
                    <div className="w-14 h-14 p-2 bg-white rounded-full shadow-sm border border-slate-100 mb-2 flex items-center justify-center">
                        <img src={m.away_team.logo_url || '/placeholder.png'} className="w-full h-full object-contain" alt={m.away_team.code} />
                    </div>
                    <span className="font-bold text-slate-700">{m.away_team.code}</span>
                    {(isFinished || isLive) && <span className="text-xl font-black text-slate-900 mt-1">{m.away_score}</span>}
                </div>

                {/* VS / 時間 */}
                <div className="flex flex-col items-center w-1/3">
                    <span className="text-[10px] font-black text-slate-300 tracking-widest">AT</span>
                    {isFinished ? (
                        <span className="text-[10px] font-bold bg-slate-100 text-slate-500 px-2 py-0.5 rounded mt-1 border border-slate-200">FINAL</span>
                    ) : (
                        <span className="text-[10px] font-bold text-slate-400 mt-1 font-mono bg-slate-50 px-2 py-0.5 rounded border border-slate-100">
                        {format(new Date(m.start_time), 'HH:mm')}
                        </span>
                    )}
                </div>

                {/* 主隊 */}
                <div className="flex flex-col items-center w-1/3 relative">
                    <div className="w-14 h-14 p-2 bg-white rounded-full shadow-sm border border-slate-100 mb-2 flex items-center justify-center">
                        <img src={m.home_team.logo_url || '/placeholder.png'} className="w-full h-full object-contain" alt={m.home_team.code} />
                    </div>
                    <span className="font-bold text-slate-700">{m.home_team.code}</span>
                    {(isFinished || isLive) && <span className="text-xl font-black text-slate-900 mt-1">{m.home_score}</span>}
                </div>
            </div>

            {/* 🔥 新增：League Pass 風格記分板 (只在有分數時顯示) */}
            {showScoreboard && (
                <div className="px-4 pb-4 bg-white">
                    <div className="w-full overflow-x-auto no-scrollbar">
                        <table className="w-full text-center text-[12px] border-collapse">
                            <thead>
                                <tr className="text-slate-400 font-bold uppercase tracking-wider border-b border-slate-100">
                                    <th className="py-1 text-left w-8"></th>
                                    {headers.map(h => (
                                        <th key={h} className="py-1 min-w-[20px]">{h}</th>
                                    ))}
                                    <th className="py-1 text-slate-600">T</th>
                                </tr>
                            </thead>
                            <tbody className="font-mono text-slate-500 font-medium">
                                {/* 客隊 */}
                                <tr className="border-b border-slate-50">
                                    <td className="py-1 text-left font-bold text-slate-700">{m.away_team.code}</td>
                                    {Array.from({ length: totalPeriods }).map((_, i) => (
                                        <td key={i} className="py-1">{periodScores?.away[i] ?? '-'}</td>
                                    ))}
                                    <td className="py-1 font-black text-slate-900">{m.away_score}</td>
                                </tr>
                                {/* 主隊 */}
                                <tr>
                                    <td className="py-1 text-left font-bold text-slate-700">{m.home_team.code}</td>
                                    {Array.from({ length: totalPeriods }).map((_, i) => (
                                        <td key={i} className="py-1">{periodScores?.home[i] ?? '-'}</td>
                                    ))}
                                    <td className="py-1 font-black text-slate-900">{m.home_score}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Body: AI 預測區塊 (自動填滿剩餘高度) */}
            <div className="px-4 pb-4 flex-1 flex flex-col justify-end">
                <div className={twMerge(
                    "rounded-xl p-3 border relative overflow-hidden transition-colors w-full",
                    hasPrediction 
                        ? (isHighConfidence ? "bg-blue-50/50 border-blue-100" : "bg-slate-50 border-slate-100")
                        : "bg-slate-50/50 border-slate-100/50 border-dashed"
                )}>
                
                {hasPrediction ? (
                    <>
                        <div className="flex justify-between items-center mb-3 relative z-10">
                            <div className="flex items-center gap-2">
                                <span className={twMerge("w-2 h-2 rounded-full animate-pulse", isHighConfidence ? "bg-blue-600" : "bg-slate-400")}></span>
                                <span className={twMerge("text-[10px] font-black uppercase tracking-widest", isHighConfidence ? "text-blue-700" : "text-slate-400")}>AI Analysis</span>
                            </div>

                            <div className="flex items-center gap-1 text-[9px] font-black uppercase text-slate-400 bg-white/60 px-2 py-1 rounded border border-slate-200/60 group-hover:bg-orange-500 group-hover:text-white group-hover:border-orange-500 transition-all shadow-sm">
                                View Analysis
                                <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M9 5l7 7-7 7"></path></svg>
                            </div>
                        </div>

                        <div className="flex justify-between items-start mb-3 relative z-10">
                            <div className="flex items-center gap-3">
                                <img src={pick.recommended_team.logo_url} className="w-8 h-8 object-contain drop-shadow-sm" />
                                <div>
                                    <div className="text-base font-black text-slate-800 leading-none">
                                        {pick.recommended_team.code} <span className="text-xs font-bold text-slate-400">to cover</span>
                                    </div>
                                    <div className="text-[10px] font-medium text-slate-500 mt-1 bg-white/80 px-1.5 py-0.5 rounded border border-slate-100/50 inline-block backdrop-blur-sm">
                                        {pick.spread_logic || 'Value Bet Analysis'}
                                    </div>
                                </div>
                            </div>
                            
                            <div className="flex flex-col items-end w-20">
                                <div className={twMerge("text-xl font-black", isHighConfidence ? "text-blue-600" : "text-slate-600")}>
                                    {pick.confidence_score}%
                                </div>
                                <div className="w-full h-1.5 bg-slate-200 rounded-full mt-1 overflow-hidden">
                                    <div 
                                        className={twMerge("h-full rounded-full", isHighConfidence ? "bg-gradient-to-r from-blue-400 to-blue-600" : "bg-slate-400")} 
                                        style={{ width: `${pick.confidence_score}%` }}
                                    ></div>
                                </div>
                            </div>
                        </div>

                        <div className="w-full h-px bg-slate-200/60 my-2"></div>

                        <div className="flex justify-between items-center relative z-10">
                            <div className="flex items-center gap-1.5">
                                <span className="text-[10px] font-bold text-slate-400 uppercase">Total</span>
                                <span className="text-xs font-black text-slate-700">{m.vegas_total || '--'}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className={`text-xs font-black px-2 py-0.5 rounded ${pick.ou_pick === 'OVER' ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-blue-50 text-blue-600 border border-blue-100'}`}>
                                    {pick.ou_pick}
                                </span>
                                <span className="text-[10px] font-bold text-slate-400">({pick.ou_confidence}%)</span>
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="flex flex-col items-center justify-center py-5 text-center space-y-2 opacity-60">
                         <span className="w-2 h-2 bg-slate-300 rounded-full animate-pulse"></span>
                         <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">AI Analysis Pending</span>
                         <span className="text-[9px] text-slate-300 font-mono">Waiting for data...</span>
                    </div>
                )}
                </div>
            </div>
            
            {/* Footer: 結果狀態 */}
            {hasPrediction && (pick.spread_outcome || pick.total_outcome) && (
                <div className="flex border-t border-slate-100 divide-x divide-slate-100 bg-white">
                    <div className={`flex-1 py-2 flex flex-col items-center justify-center ${pick.spread_outcome === 'WIN' ? 'bg-green-50/50' : pick.spread_outcome === 'LOSS' ? 'bg-red-50/50' : ''}`}>
                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Spread</span>
                        <span className={`text-xs font-black ${pick.spread_outcome === 'WIN' ? 'text-green-600' : pick.spread_outcome === 'LOSS' ? 'text-red-500' : 'text-slate-500'}`}>
                            {pick.spread_outcome || '-'}
                        </span>
                    </div>
                    
                    <div className={`flex-1 py-2 flex flex-col items-center justify-center ${pick.total_outcome === 'WIN' ? 'bg-green-50/50' : pick.total_outcome === 'LOSS' ? 'bg-red-50/50' : ''}`}>
                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Total</span>
                        <span className={`text-xs font-black ${pick.total_outcome === 'WIN' ? 'text-green-600' : pick.total_outcome === 'LOSS' ? 'text-red-500' : 'text-slate-500'}`}>
                            {pick.total_outcome || '-'}
                        </span>
                    </div>
                </div>
            )}
        </div>
      </Link>
    </motion.div>
  );
}