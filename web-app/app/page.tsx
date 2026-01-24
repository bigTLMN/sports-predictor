import { supabase } from '@/lib/supabase';
import DateNavigator from './components/DateNavigator';
import StatsDashboard from './components/StatsDashboard';
import { format } from 'date-fns';
import { toZonedTime } from 'date-fns-tz'; // 建議安裝 date-fns-tz

export const revalidate = 0;

interface Match {
  id: number;
  date: string;
  start_time: string;
  home_team: { code: string; full_name?: string; logo_url?: string };
  away_team: { code: string; full_name?: string; logo_url?: string };
  home_score?: number;
  away_score?: number;
  status?: string;
  vegas_spread?: number; // 新增
  vegas_total?: number;  // 新增
}

interface Pick {
  confidence_score: number;
  spread_logic?: string;
  line_info?: string;     // 這是 Vegas Spread
  ou_pick?: string;
  ou_line?: number;       // 這是 Vegas Total
  ou_confidence?: number;
  spread_outcome?: string; 
  ou_outcome?: string;      
  matches: Match;
  recommended_team: { code: string; logo_url?: string };
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  
  // 設定時區 (美東) 避免跨日問題
  const timeZone = 'America/New_York';
  const now = new Date();
  const zonedDate = toZonedTime(now, timeZone);
  const todayStr = format(zonedDate, 'yyyy-MM-dd');
  
  const targetDate = (params.date as string) || todayStr;

  // 計算 UTC 查詢範圍
  const startUTC = new Date(targetDate + 'T00:00:00Z').toISOString();
  const endUTC = new Date(targetDate + 'T23:59:59Z');
  endUTC.setHours(endUTC.getHours() + 12); 
  const endUTCString = endUTC.toISOString();

  const { data: dailyData } = await supabase
    .from('aggregated_picks')
    .select(`
      *,
      matches!inner (
        id, date, status, home_score, away_score, start_time, vegas_spread, vegas_total,
        home_team: teams!matches_home_team_id_fkey (code, full_name, logo_url),
        away_team: teams!matches_away_team_id_fkey (code, full_name, logo_url)
      ),
      recommended_team: teams!aggregated_picks_recommended_team_id_fkey (code, logo_url)
    `)
    .gte('matches.date', startUTC)
    .lt('matches.date', endUTCString);

  // 排序
  let picks = (dailyData || []) as any as Pick[];
  picks.sort((a, b) => a.matches.id - b.matches.id);

  // 簡易統計
  const dailyStats = {
    spreadWin: picks.filter(p => p.spread_outcome === 'WIN').length,
    spreadTotal: picks.filter(p => p.spread_outcome === 'WIN' || p.spread_outcome === 'LOSS').length,
    ouWin: picks.filter(p => p.ou_outcome === 'WIN').length,
    ouTotal: picks.filter(p => p.ou_outcome === 'WIN' || p.ou_outcome === 'LOSS').length,
  };

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-8 font-sans">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-black text-slate-900 text-center mb-1 tracking-tight">
          🏀 AI BALLER
        </h1>
        <p className="text-center text-slate-400 text-xs font-medium mb-6">DAILY AI VALUE PICKS</p>
        
        <DateNavigator />
        <StatsDashboard daily={dailyStats} cumulative={{spreadWin:0, spreadTotal:0, ouWin:0, ouTotal:0}} />

        {picks.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-2">💤</div>
            <p className="text-slate-400">No games scheduled for this date.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {picks.map((pick, index) => {
              const m = pick.matches;
              const isFinished = m.status === 'STATUS_FINISHED' || m.status === 'STATUS_FINAL';
              
              // 格式化盤口顯示
              const spreadText = m.vegas_spread && m.vegas_spread > 0 ? `+${m.vegas_spread}` : m.vegas_spread;
              
              return (
                <div key={index} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-all relative">
                  
                  {/* --- 左上角：真實盤口 (Vegas Odds) --- */}
                  <div className="absolute top-0 left-0 bg-slate-900 text-white px-3 py-1.5 rounded-br-xl z-10">
                    <div className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">VEGAS</div>
                    <div className="text-sm font-black leading-none">
                      {m.home_team.code} {spreadText || 'PK'}
                    </div>
                  </div>

                  {/* Header: 對戰組合 + LOGO */}
                  <div className="pt-10 pb-4 px-4 flex justify-between items-center bg-gradient-to-b from-slate-50 to-white">
                    {/* 客隊 */}
                    <div className="flex flex-col items-center w-1/3">
                      <img src={m.away_team.logo_url || '/placeholder.png'} className="w-12 h-12 object-contain mb-2" alt={m.away_team.code} />
                      <span className="font-bold text-slate-700">{m.away_team.code}</span>
                      {isFinished && <span className="text-xl font-black text-slate-900">{m.away_score}</span>}
                    </div>

                    {/* 中間 VS / 時間 */}
                    <div className="flex flex-col items-center w-1/3">
                      <span className="text-xs font-bold text-slate-300">AT</span>
                      {isFinished ? (
                         <span className="text-[10px] font-bold bg-slate-100 text-slate-500 px-2 py-1 rounded mt-1">FINAL</span>
                      ) : (
                         <span className="text-[10px] font-bold text-slate-400 mt-1">{format(new Date(m.start_time), 'HH:mm')}</span>
                      )}
                    </div>

                    {/* 主隊 */}
                    <div className="flex flex-col items-center w-1/3">
                      <img src={m.home_team.logo_url || '/placeholder.png'} className="w-12 h-12 object-contain mb-2" alt={m.home_team.code} />
                      <span className="font-bold text-slate-700">{m.home_team.code}</span>
                      {isFinished && <span className="text-xl font-black text-slate-900">{m.home_score}</span>}
                    </div>
                  </div>

                  {/* Body: AI 預測區塊 */}
                  <div className="px-4 pb-4">
                    <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                        <span className="text-xs font-black text-blue-600 uppercase tracking-wider">AI Prediction</span>
                      </div>

                      {/* 1. Spread/Moneyline Pick */}
                      <div className="flex justify-between items-center mb-3">
                        <div className="flex items-center gap-3">
                          <img src={pick.recommended_team.logo_url} className="w-8 h-8 object-contain" />
                          <div>
                             <div className="text-lg font-black text-slate-800 leading-none">
                               {pick.recommended_team.code} <span className="text-sm font-normal text-slate-500">to cover</span>
                             </div>
                             <div className="text-[10px] text-slate-400 mt-0.5">{pick.spread_logic}</div>
                          </div>
                        </div>
                        <div className="text-xl font-black text-blue-600">{pick.confidence_score}%</div>
                      </div>

                      <div className="w-full h-px bg-slate-200 my-2"></div>

                      {/* 2. Total Pick */}
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="text-xs font-bold text-slate-500">Total {pick.ou_line}</span>
                        </div>
                        <div className="flex items-center gap-2">
                           <span className={`text-sm font-black ${pick.ou_pick === 'OVER' ? 'text-red-500' : 'text-blue-500'}`}>
                             {pick.ou_pick}
                           </span>
                           <span className="text-xs font-bold text-slate-300">({pick.ou_confidence}%)</span>
                        </div>
                      </div>

                    </div>
                  </div>
                  
                  {/* Footer: 結果狀態 (如果有) */}
                  {(pick.spread_outcome || pick.ou_outcome) && (
                    <div className="flex border-t border-slate-100 divide-x divide-slate-100">
                       <div className={`flex-1 py-1.5 text-center text-[10px] font-black ${pick.spread_outcome === 'WIN' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'}`}>
                          SPREAD: {pick.spread_outcome}
                       </div>
                       <div className={`flex-1 py-1.5 text-center text-[10px] font-black ${pick.ou_outcome === 'WIN' ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'}`}>
                          TOTAL: {pick.ou_outcome}
                       </div>
                    </div>
                  )}

                </div>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}