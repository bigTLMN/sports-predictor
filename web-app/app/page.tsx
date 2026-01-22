import { supabase } from '@/lib/supabase';
import DateNavigator from './components/DateNavigator';
import StatsDashboard from './components/StatsDashboard';
import { format } from 'date-fns';

export const revalidate = 0;

// 定義資料結構
interface Match {
  date: string;
  home_team: { code: string; full_name?: string };
  away_team: { code: string; full_name?: string };
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
  const todayStr = format(new Date(), 'yyyy-MM-dd');
  const targetDate = (params.date as string) || todayStr;

  // 1. 抓取「當天」的資料 (用於顯示卡片)
  const { data: dailyData } = await supabase
    .from('aggregated_picks')
    .select(`
      *,
      matches!inner (
        date, status, home_score, away_score,
        home_team: teams!matches_home_team_id_fkey (code, full_name),
        away_team: teams!matches_away_team_id_fkey (code, full_name)
      ),
      recommended_team: teams!aggregated_picks_recommended_team_id_fkey (code, logo_url)
    `)
    .eq('matches.date', targetDate)
    .order('confidence_score', { ascending: false });

  // 2. 抓取「所有已結算」的歷史資料 (用於計算累積勝率)
  // [修正重點]: 移除 .not('matches', 'is', null) 這種錯誤寫法
  // 直接選取欄位，我們會在下面用 JS 濾掉還沒結算的
  const { data: historyData } = await supabase
    .from('aggregated_picks')
    .select('spread_outcome, ou_outcome');

  const picks = (dailyData || []) as any as Pick[];
  const history = (historyData || []) as { spread_outcome?: string; ou_outcome?: string }[];

  // --- 統計邏輯 ---
  
  // A. 計算本日 (Daily Stats)
  const dailyStats = {
    spreadWin: picks.filter(p => p.spread_outcome === 'WIN').length,
    spreadTotal: picks.filter(p => p.spread_outcome === 'WIN' || p.spread_outcome === 'LOSS').length,
    ouWin: picks.filter(p => p.ou_outcome === 'WIN').length,
    ouTotal: picks.filter(p => p.ou_outcome === 'WIN' || p.ou_outcome === 'LOSS').length,
  };

  // B. 計算累積 (Cumulative Stats)
  // 這裡會統計資料庫裡「每一筆」有結果的資料
  const cumulativeStats = {
    spreadWin: history.filter(p => p.spread_outcome === 'WIN').length,
    spreadTotal: history.filter(p => p.spread_outcome === 'WIN' || p.spread_outcome === 'LOSS').length,
    ouWin: history.filter(p => p.ou_outcome === 'WIN').length,
    ouTotal: history.filter(p => p.ou_outcome === 'WIN' || p.ou_outcome === 'LOSS').length,
  };

  return (
    <main className="min-h-screen bg-gray-50 p-4 md:p-8 font-sans">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-black text-gray-900 text-center mb-1 tracking-tight">
          🏀 AI 賽事預測
        </h1>
        <p className="text-center text-gray-400 text-xs font-medium mb-6">POWERED BY SUPABASE & NEXT.JS</p>
        
        <DateNavigator />

        {/* 統計儀表板：現在 Cumulative 數據應該正常了 */}
        <StatsDashboard daily={dailyStats} cumulative={cumulativeStats} />

        {/* 預測卡片列表 */}
        {picks.length === 0 ? (
          <div className="text-center text-gray-400 py-12 bg-white rounded-xl border border-gray-100 border-dashed">
            <div className="text-4xl mb-2">📭</div>
            <div className="font-bold">No Data Available</div>
            <div className="text-xs mt-1">Check the date or run the scraper.</div>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {picks.map((pick, index) => (
              <div key={index} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
                
                {/* Header */}
                <div className="bg-gray-50 px-4 py-3 border-b border-gray-100 flex justify-between items-center">
                  <div className="text-xs font-bold text-gray-400">{pick.matches.date}</div>
                  <div className="text-right">
                    <div className="text-sm font-black text-gray-800">
                      {pick.matches.away_team.code} <span className="text-gray-400 font-normal">@</span> {pick.matches.home_team.code}
                    </div>
                    {pick.matches.status === 'STATUS_FINAL' && (
                       <div className="text-xs font-mono text-gray-500 mt-0.5">
                         {pick.matches.away_score} - {pick.matches.home_score}
                       </div>
                    )}
                  </div>
                </div>

                {/* Body: Spread Pick */}
                <div className="p-4 relative">
                  {pick.spread_outcome === 'WIN' && (
                    <div className="absolute top-3 right-3 bg-green-100 text-green-700 text-[10px] font-black px-2 py-0.5 rounded border border-green-200">WIN</div>
                  )}
                  {pick.spread_outcome === 'LOSS' && (
                    <div className="absolute top-3 right-3 bg-red-100 text-red-700 text-[10px] font-black px-2 py-0.5 rounded border border-red-200">LOSS</div>
                  )}

                  <div className="flex justify-between items-start mb-3">
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-gray-400 tracking-wider uppercase">Spread Pick</span>
                      <span className="text-[10px] text-gray-500 font-mono bg-gray-100 px-1.5 py-0.5 rounded w-fit mt-1">
                        {pick.line_info || 'PK'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 mb-2">
                    {pick.recommended_team?.logo_url ? (
                      <img src={pick.recommended_team.logo_url} className="w-10 h-10 object-contain" alt={pick.recommended_team.code} />
                    ) : (
                      <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-xs font-bold text-gray-400">?</div>
                    )}
                    <div>
                      <div className="text-2xl font-black text-gray-900 leading-none">
                        {pick.recommended_team?.code}
                      </div>
                      <div className="text-[10px] text-gray-500 mt-1 line-clamp-1">
                        {pick.spread_logic || 'AI Model Analysis'}
                      </div>
                    </div>
                    <div className="ml-auto text-2xl font-black text-green-600 tracking-tighter">
                      {pick.confidence_score}%
                    </div>
                  </div>
                </div>

                {/* Footer: O/U Pick */}
                {pick.ou_pick && (
                  <div className="px-4 py-3 bg-slate-50 border-t border-gray-100 flex justify-between items-center relative">
                    {pick.ou_outcome === 'WIN' && (
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 bg-green-100 text-green-700 text-[10px] font-black px-2 py-0.5 rounded border border-green-200">WIN</div>
                    )}
                    {pick.ou_outcome === 'LOSS' && (
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 bg-red-100 text-red-700 text-[10px] font-black px-2 py-0.5 rounded border border-red-200">LOSS</div>
                    )}

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-slate-400 uppercase">Total</span>
                      <div className={`text-sm font-black ${pick.ou_pick === 'OVER' ? 'text-red-500' : 'text-blue-600'}`}>
                        {pick.ou_pick} {pick.ou_line}
                      </div>
                    </div>
                    <div className={`text-[10px] font-bold text-slate-400 ${pick.ou_outcome ? 'mr-12' : ''}`}>
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