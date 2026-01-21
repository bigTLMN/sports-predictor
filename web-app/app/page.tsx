import { supabase } from '@/lib/supabase';
import DateNavigator from './components/DateNavigator';
import { format, addDays } from 'date-fns';

export const revalidate = 0; // 確保每次都抓最新資料，不要快取

interface Team {
  code: string;
  full_name?: string;
  logo_url?: string;
}

interface Match {
  date: string;
  home_team: Team;
  away_team: Team;
  home_score?: number;
  away_score?: number;
  status?: string;
}

interface Pick {
  confidence_score: number;
  consensus_logic: string;
  spread_logic?: string;
  line_info?: string;
  ou_pick?: string;
  ou_line?: number;
  ou_confidence?: number;
  outcome?: string; // WIN, LOSS, PUSH
  matches: Match;
  recommended_team: Team;
}

// Next.js 15 Update: searchParams 現在是一個 Promise
export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  // 1. 等待 searchParams 解析 (這是 Next.js 15 的新規定)
  const params = await searchParams;

  // 2. 預設日期邏輯
  const todayStr = format(new Date(), 'yyyy-MM-dd');
  
  // 使用解析後的 params 來讀取 date
  const targetDate = (params.date as string) || todayStr;

  // 3. 向 Supabase 查詢資料
  const { data, error } = await supabase
    .from('aggregated_picks')
    .select(`
      *,
      matches!inner (
        date,
        status,
        home_score,
        away_score,
        home_team: teams!matches_home_team_id_fkey (code, full_name),
        away_team: teams!matches_away_team_id_fkey (code, full_name)
      ),
      recommended_team: teams!aggregated_picks_recommended_team_id_fkey (code, logo_url)
    `)
    .eq('matches.date', targetDate) // 只抓這一天
    .order('confidence_score', { ascending: false });

  if (error) {
    console.error(error);
    return <div className="p-10 text-red-500">讀取資料發生錯誤</div>;
  }

  const picks = data as any as Pick[];

  // 計算當日戰績
  const totalGraded = picks.filter(p => p.outcome).length;
  const wins = picks.filter(p => p.outcome === 'WIN').length;
  const losses = picks.filter(p => p.outcome === 'LOSS').length;
  const winRate = totalGraded > 0 ? Math.round((wins / totalGraded) * 100) : 0;

  return (
    <main className="min-h-screen bg-gray-100 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 text-center mb-2">
          🏀 AI 賽事預測
        </h1>
        
        {/* 日期導航器 */}
        <DateNavigator />

        {/* 戰績顯示看板 (只有當天有結算資料時才顯示) */}
        {totalGraded > 0 && (
          <div className="mb-6 p-4 bg-gray-800 text-white rounded-xl shadow-lg text-center">
            <h2 className="text-sm text-gray-400 uppercase tracking-wider mb-1">Historical Performance</h2>
            <div className="text-2xl font-bold flex justify-center items-center gap-4">
              <span className="text-green-400">{wins} Wins</span>
              <span className="text-gray-500">/</span>
              <span className="text-red-400">{losses} Losses</span>
            </div>
            <div className="mt-1 text-sm font-mono bg-gray-700 inline-block px-2 py-0.5 rounded text-yellow-400">
              Win Rate: {winRate}%
            </div>
          </div>
        )}

        {/* 預測卡片列表 */}
        {picks.length === 0 ? (
          <div className="text-center text-gray-500 py-10">
            📭 這一天 ({targetDate}) 沒有預測資料
            <div className="text-xs mt-2">請按箭頭查看其他日期，或確認爬蟲是否執行</div>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {picks.map((pick, index) => (
              <div key={index} className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200 relative">
                
                {/* 輸贏印章 */}
                {pick.outcome === 'WIN' && (
                  <div className="absolute top-2 right-2 z-10 bg-green-100 text-green-700 border border-green-300 px-3 py-1 rounded-full font-black transform rotate-12 shadow-sm">
                    ✅ WIN
                  </div>
                )}
                {pick.outcome === 'LOSS' && (
                  <div className="absolute top-2 right-2 z-10 bg-red-100 text-red-700 border border-red-300 px-3 py-1 rounded-full font-black transform rotate-12 shadow-sm">
                    ❌ LOSS
                  </div>
                )}

                {/* Header */}
                <div className="bg-gray-50 px-6 py-3 border-b border-gray-100 flex justify-between items-center">
                  <span className="text-sm text-gray-500 font-mono">
                    {pick.matches.date}
                  </span>
                  <div className="text-right">
                     <span className="font-bold text-gray-700 block">
                       {pick.matches.away_team.code} @ {pick.matches.home_team.code}
                     </span>
                     {pick.matches.status === 'STATUS_FINAL' && (
                       <span className="text-xs text-gray-500 font-mono block">
                         {pick.matches.away_score} - {pick.matches.home_score}
                       </span>
                     )}
                  </div>
                </div>

                {/* SPREAD PICK */}
                <div className="p-5 border-b border-gray-100">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold text-gray-400 uppercase">Spread Pick</span>
                    <span className="text-xs bg-gray-200 px-2 py-1 rounded text-gray-600 font-mono">
                      {pick.line_info || 'PK'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                     <div className="flex items-center gap-3">
                        {pick.recommended_team?.logo_url ? (
                          <img src={pick.recommended_team.logo_url} className="w-10 h-10 object-contain" alt="" />
                        ) : (
                          <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-xs">N/A</div>
                        )}
                        <div>
                          <div className="text-2xl font-black text-blue-600 leading-none">
                            {pick.recommended_team?.code || 'TBD'}
                          </div>
                          <div className="text-xs text-gray-500 mt-1 max-w-[150px] truncate">
                            {pick.spread_logic || pick.consensus_logic || 'Model Analysis'}
                          </div>
                        </div>
                     </div>
                     <div className="text-right mt-4">
                        <div className="text-2xl font-bold text-green-600">{pick.confidence_score}%</div>
                     </div>
                  </div>
                </div>

                {/* O/U PICK */}
                {pick.ou_pick && (
                  <div className="px-5 py-3 bg-blue-50 flex justify-between items-center">
                     <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-blue-400 uppercase">Total</span>
                        <span className={`text-lg font-bold ${pick.ou_pick === 'OVER' ? 'text-red-500' : 'text-blue-600'}`}>
                          {pick.ou_pick} {pick.ou_line}
                        </span>
                     </div>
                     <div className="text-sm font-semibold text-gray-600">
                       {pick.ou_confidence}% Conf.
                     </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}