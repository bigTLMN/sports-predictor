import { supabase } from '@/lib/supabase';
import DateNavigator from './components/DateNavigator';
import StatsDashboard from './components/StatsDashboard';
import MatchCard from './components/MatchCard';
import Footer from './components/Footer';
import { format } from 'date-fns';
import { toZonedTime } from 'date-fns-tz';

export const revalidate = 0; // 確保數據即時更新

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
  // 抓取到隔日下午 (確保涵蓋所有時區的晚場比賽)
  const endUTC = new Date(targetDate + 'T23:59:59Z');
  endUTC.setHours(endUTC.getHours() + 14); 
  const endUTCString = endUTC.toISOString();

  // 3. 查詢當日比賽 (包含關聯資料)
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

  // 4. 查詢全歷史紀錄 (Raw Data)
  // 🔥 重點：這裡加入了 'total_outcome'，以便前端計算大小分勝率
  const { data: allHistoryData } = await supabase
    .from('aggregated_picks')
    .select(`spread_outcome, total_outcome, matches!inner (date)`)
    .or('spread_outcome.neq.null,total_outcome.neq.null') // 只要有任一結果就抓
    .order('matches(date)', { ascending: true });

  // 準備資料
  const picks = dailyData || [];
  // 簡單排序：按比賽 ID (通常也代表時間序)
  picks.sort((a: any, b: any) => a.matches.id - b.matches.id);

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

          {/* StatsDashboard (Client Component)
              現在負責：
              1. 顯示今日/累積勝率
              2. 管理 Tab 狀態 (Spread/Total/All)
              3. 根據 Tab 渲染下方的 TrendChart
          */}
          <StatsDashboard 
            dailyPicks={picks} 
            historyPicks={allHistoryData || []} 
          />

          {/* 賽事卡片列表 */}
          {picks.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-2xl border border-dashed border-slate-300">
              <div className="text-4xl mb-3">💤</div>
              <p className="text-slate-500 font-bold">No games scheduled</p>
              <p className="text-xs text-slate-400 mt-1">Please select another date</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {picks.map((pick: any, index: number) => (
                <MatchCard key={pick.id} pick={pick} index={index} />
              ))}
            </div>
          )}
        </div>
      </main>
      
      <Footer />
    </div>
  );
}