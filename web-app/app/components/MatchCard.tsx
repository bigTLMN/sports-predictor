'use client';

import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { twMerge } from 'tailwind-merge';
import Link from 'next/link';

type PeriodScores = {
  home: number[];
  away: number[];
};

interface PickHistory {
  time: string;
  logic: string;
  line: string;
  team_id: number;
}

interface MatchCardProps {
  pick: any; 
  index: number;
}

// 🔥 動態盤口轉換器 (改用 Code 比對，徹底解決 ID 遺失導致的 undefined 問題)
const getFormattedSpreadByCode = (homeSpreadVal: any, targetTeamCode: string, homeTeamCode: string) => {
    if (homeSpreadVal === null || homeSpreadVal === undefined || homeSpreadVal === '') return 'PK';
    
    const spreadNum = parseFloat(String(homeSpreadVal));
    if (isNaN(spreadNum) || spreadNum === 0) return 'PK';

    const isHome = targetTeamCode === homeTeamCode;
    
    // 如果推薦的是客隊，就把主隊的盤口正負號反轉
    const targetSpread = isHome ? spreadNum : -spreadNum;
    
    // 正數加上 + 號，負數自帶 - 號
    return targetSpread > 0 ? `+${targetSpread}` : `${targetSpread}`;
};

export default function MatchCard({ pick, index }: MatchCardProps) {
  const m = pick.matches;
  
  const hasPrediction = !!pick.recommended_team;
  const isFinished = m.status === 'STATUS_FINISHED' || m.status === 'STATUS_FINAL' || m.status === 'Final';
  const isLive = m.status === 'STATUS_IN_PROGRESS';
  
  // 提取球隊 Code，用來進行精準比對
  const homeCode = m.home_team?.code;
  const awayCode = m.away_team?.code;
  const recCode = pick.recommended_team?.code;
  const isCurrentHome = recCode === homeCode;
  const currentRecIdStr = String(pick.recommended_team_id);

  // 左上角 Vegas 標籤 (永遠顯示主隊真實盤口)
  const vegasBadgeText = m.vegas_spread !== null && m.vegas_spread !== 0
    ? (m.vegas_spread > 0 ? `+${m.vegas_spread}` : m.vegas_spread) 
    : 'PK';

  const isHighConfidence = hasPrediction && pick.confidence_score >= 80;
  const periodScores = m.period_scores as PeriodScores | null;
  const showScoreboard = (isFinished || isLive) && periodScores;
  const totalPeriods = periodScores ? Math.max(4, periodScores.home.length) : 4;
  
  const headers = Array.from({ length: totalPeriods }, (_, i) => {
    if (i < 4) return `Q${i + 1}`;
    return `OT${i - 3}`;
  });

  const fallbackLogo = "https://upload.wikimedia.org/wikipedia/en/0/03/National_Basketball_Association_logo.svg";

  // 🔥 計算目前「正確帶有 +/- 的讓分」
  const currentFormattedSpread = getFormattedSpreadByCode(m.vegas_spread, recCode, homeCode);
  
  // 🔥 過濾幽靈歷史紀錄，並推算歷史紀錄的球隊代號
  const rawHistory: PickHistory[] = pick.history ? [...pick.history].reverse() : [];
  const pickHistory = rawHistory.filter((hist) => {
      if (hist.line === null || hist.line === 'None' || hist.line === undefined) return false;
      if ((hist.line === '0' || hist.line === '0.0') && m.vegas_spread !== 0) return false;
      
      // 反推歷史紀錄的球隊 Code (如果 ID 跟當前推薦一樣就是 recCode，否則就是對手)
      const histCode = String(hist.team_id) === currentRecIdStr 
          ? recCode 
          : (isCurrentHome ? awayCode : homeCode);
          
      const formattedHistSpread = getFormattedSpreadByCode(hist.line, histCode, homeCode);
      
      // 如果盤口跟球隊都沒變，就隱藏這筆歷史
      if (formattedHistSpread === currentFormattedSpread && histCode === recCode) {
          return false; 
      }
      return true;
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="group relative h-full"
    >
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
                <span>{homeCode}</span>
                <span className="text-yellow-400">{vegasBadgeText}</span>
                </div>
            </div>

            {/* Header: 對戰組合 */}
            <div className="pt-10 pb-2 px-4 flex justify-between items-center bg-gradient-to-b from-slate-50 to-white">
                <div className="flex flex-col items-center w-1/3 relative">
                    <div className="w-14 h-14 p-2 bg-white rounded-full shadow-sm border border-slate-100 mb-2 flex items-center justify-center">
                        <img 
                            src={m.away_team.logo_url || fallbackLogo} 
                            className="w-full h-full object-contain" 
                            alt={awayCode} 
                            onError={(e) => { e.currentTarget.src = fallbackLogo; }}
                        />
                    </div>
                    <span className="font-bold text-slate-700">{awayCode}</span>
                    {(isFinished || isLive) && <span className="text-xl font-black text-slate-900 mt-1">{m.away_score}</span>}
                </div>

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

                <div className="flex flex-col items-center w-1/3 relative">
                    <div className="w-14 h-14 p-2 bg-white rounded-full shadow-sm border border-slate-100 mb-2 flex items-center justify-center">
                        <img 
                            src={m.home_team.logo_url || fallbackLogo} 
                            className="w-full h-full object-contain" 
                            alt={homeCode} 
                            onError={(e) => { e.currentTarget.src = fallbackLogo; }}
                        />
                    </div>
                    <span className="font-bold text-slate-700">{homeCode}</span>
                    {(isFinished || isLive) && <span className="text-xl font-black text-slate-900 mt-1">{m.home_score}</span>}
                </div>
            </div>

            {/* 記分板 */}
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
                                <tr className="border-b border-slate-50">
                                    <td className="py-1 text-left font-bold text-slate-700">{awayCode}</td>
                                    {Array.from({ length: totalPeriods }).map((_, i) => (
                                        <td key={i} className="py-1">{periodScores?.away[i] ?? '-'}</td>
                                    ))}
                                    <td className="py-1 font-black text-slate-900">{m.away_score}</td>
                                </tr>
                                <tr>
                                    <td className="py-1 text-left font-bold text-slate-700">{homeCode}</td>
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

            {/* Body: AI 預測區塊 */}
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

                        {/* 🔥 核心預測 (Latest Pick) */}
                        <div className="flex justify-between items-center mb-3 relative z-10">
                            <div className="flex items-center gap-3">
                                <img 
                                    src={pick.recommended_team.logo_url || fallbackLogo} 
                                    className="w-8 h-8 object-contain drop-shadow-sm" 
                                    onError={(e) => { e.currentTarget.src = fallbackLogo; }}
                                />
                                <div>
                                    <div className="text-base font-black text-slate-800 leading-none flex items-center gap-1.5">
                                        {recCode}
                                        {/* 🔥 完美對應正負號 */}
                                        <span className="text-sm font-bold text-blue-600 bg-blue-100/50 px-1.5 py-0.5 rounded">
                                            {currentFormattedSpread}
                                        </span>
                                    </div>
                                    <div className="text-[9px] font-bold text-blue-500 mt-1 uppercase tracking-wider flex items-center gap-1">
                                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                        Latest Update • {pick.created_at ? format(new Date(pick.created_at), 'MM/dd HH:mm') : '--:--'}
                                    </div>
                                </div>
                            </div>
                            
                            <div className="flex flex-col items-end w-16 md:w-20 shrink-0">
                                <div className={twMerge("text-lg md:text-xl font-black", isHighConfidence ? "text-blue-600" : "text-slate-600")}>
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

                        {/* 🔥 預測時間線 (Prediction History) */}
                        {pickHistory.length > 0 && (
                            <div className="mt-1 pt-2 border-t border-slate-200/60 border-dashed relative z-10">
                                <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Timeline History</div>
                                <div className="space-y-1.5 max-h-24 overflow-y-auto no-scrollbar">
                                    {pickHistory.map((hist, idx) => {
                                        // 完美判斷歷史紀錄的隊伍代號與對應盤口
                                        const histCode = String(hist.team_id) === currentRecIdStr 
                                            ? recCode 
                                            : (isCurrentHome ? awayCode : homeCode);
                                            
                                        const formattedHistSpread = getFormattedSpreadByCode(hist.line, histCode, homeCode);
                                        
                                        return (
                                            <div key={idx} className="border-l-2 border-slate-300 pl-2 opacity-60 hover:opacity-100 transition-opacity">
                                                <div className="flex justify-between items-center">
                                                    <span className="text-[11px] font-bold text-slate-600">
                                                        {histCode} {formattedHistSpread}
                                                    </span>
                                                    <span className="text-[9px] font-mono text-slate-400">
                                                        {format(new Date(hist.time), 'MM/dd HH:mm')}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

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