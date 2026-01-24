import { supabase } from '@/lib/supabase';
import DateNavigator from './components/DateNavigator';
import StatsDashboard from './components/StatsDashboard';
import TrendChart from './components/TrendChart';
import MatchCard from './components/MatchCard'; // 新增
import Footer from './components/Footer';       // 新增
import { format } from 'date-fns';
import { toZonedTime } from 'date-fns-tz';

export const revalidate = 0;

// 定義介面
interface Match {
  id: number;
  date: string;
  start_time: string;
  home_team: { code: string; full_name?: string; logo_url?: string };
  away_team: { code: string; full_name?: string; logo_url?: string };
  home_score?: number;
  away_score?: number;
  status?: string;
  vegas_spread?: number;
  vegas_total?: number;
}

interface Pick {
  confidence_score: number;
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

  // 1. 設定時區 (美東)
  const timeZone = 'America/New_York';
  const now = new Date();
  const zonedDate = toZonedTime(now, timeZone);
  const todayStr = format(zonedDate, 'yyyy-MM-dd');
  const targetDate = (params.date as string) || todayStr;

  // 2. 計算查詢範圍 (UTC)
  const startUTC = new Date(targetDate + 'T00:00:00Z').toISOString();
  const endUTC = new Date(targetDate + 'T23:59:59Z');
  endUTC.setHours(endUTC.getHours() + 14); 
  const endUTCString = endUTC.toISOString();

  // 3. 查詢當日比賽
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

  // 4. 查詢歷史數據 (for TrendChart)
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  
  const { data: historyData } = await supabase
    .from('aggregated_picks')
    .select(`spread_outcome, matches!inner (date)`)
    .gte('matches.date', sevenDaysAgo.toISOString())
    .not('spread_outcome', 'is', null);

  // --- 資料統計 ---
  // TrendData
  const trendMap = new Map<string, { wins: number; total: number }>();
  (historyData || []).forEach((pick: any) => {
    const dateStr = pick.matches.date.split('T')[0];
    const shortDate = dateStr.slice(5); 
    if (!trendMap.has(shortDate)) trendMap.set(shortDate, { wins: 0, total: 0 });
    const dayStat = trendMap.get(shortDate)!;
    if (pick.spread_outcome === 'WIN') dayStat.wins++;
    if (pick.spread_outcome === 'WIN' || pick.spread_outcome === 'LOSS') dayStat.total++;
  });

  const trendData = Array.from(trendMap.entries())
    .map(([date, stat]) => ({
      date: date,
      winRate: stat.total > 0 ? Math.round((stat.wins / stat.total) * 100) : 0
    }))
    .sort((a, b) => a.date.localeCompare(b.date));

  // Dashboard Stats
  const cumulativeStats = {
    spreadWin: (historyData || []).filter((p: any) => p.spread_outcome === 'WIN').length,
    spreadTotal: (historyData || []).filter((p: any) => p.spread_outcome === 'WIN' || p.spread_outcome === 'LOSS').length,
    ouWin: 0, ouTotal: 0, // 簡化，若有需要可再加
  };

  let picks = (dailyData || []) as any as Pick[];
  picks.sort((a, b) => a.matches.id - b.matches.id);

  const dailyStats = {
    spreadWin: picks.filter(p => p.spread_outcome === 'WIN').length,
    spreadTotal: picks.filter(p => p.spread_outcome === 'WIN' || p.spread_outcome === 'LOSS').length,
    ouWin: picks.filter(p => p.ou_outcome === 'WIN').length,
    ouTotal: picks.filter(p => p.ou_outcome === 'WIN' || p.ou_outcome === 'LOSS').length,
  };

  return (
    <div className="min-h-screen bg-slate-300 font-sans flex flex-col">
      <main className="flex-1 p-4 md:p-8">
        <div className="max-w-3xl mx-auto">
          
          {/* Hero Banner */}
          <div className="relative w-full h-40 md:h-56 rounded-2xl overflow-hidden shadow-lg mb-8 group select-none">
              <img 
                  src="/cover.png" 
                  alt="Edge Analytics" 
                  className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-700"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-900/90 via-slate-900/20 to-transparent flex flex-col justify-end p-6">
                  <div className="relative">
                      <h1 className="text-3xl md:text-5xl font-black text-white tracking-tighter mb-1 drop-shadow-lg">
                          EDGE <span className="text-yellow-500">ANALYTICS</span>
                      </h1>
                      <p className="text-slate-300 text-[10px] md:text-xs font-bold tracking-[0.2em] uppercase opacity-90">
                          Find the Value. Beat the Odds.
                      </p>
                  </div>
              </div>
          </div>

          <DateNavigator />

          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 mb-6">
             <StatsDashboard daily={dailyStats} cumulative={cumulativeStats} />
             {trendData.length > 0 && (
               <div className="border-t border-slate-100 mt-5 pt-2">
                 <TrendChart data={trendData} />
               </div>
             )}
          </div>

          {/* 卡片列表 (使用 MatchCard) */}
          {picks.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-2xl border border-dashed border-slate-300">
              <div className="text-4xl mb-3">💤</div>
              <p className="text-slate-500 font-bold">No games scheduled</p>
              <p className="text-xs text-slate-400 mt-1">Please select another date</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {picks.map((pick, index) => (
                <MatchCard key={pick.matches.id} pick={pick} index={index} />
              ))}
            </div>
          )}
        </div>
      </main>
      
      {/* Footer */}
      <Footer />
    </div>
  );
}