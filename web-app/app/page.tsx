import { supabase } from '@/lib/supabase';
import DateNavigator from './components/DateNavigator';
import StatsDashboard from './components/StatsDashboard';
import MatchCard from './components/MatchCard';
import Footer from './components/Footer';
import { format } from 'date-fns';
import { toZonedTime } from 'date-fns-tz';

export const revalidate = 0; // 強制不緩存，確保每次重新整理都抓到最新賠率與勝率

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;

  // 1. 【時間處理】設定時區為美東 (NBA/MLB 主要時區)
  const timeZone = 'America/New_York';
  const now = new Date();
  const zonedDate = toZonedTime(now, timeZone);
  const todayStr = format(zonedDate, 'yyyy-MM-dd');
  const targetDate = (params.date as string) || todayStr;

  // 2. 【範圍計算】處理 UTC 查詢範圍，多抓 14 小時以涵蓋跨日晚場比賽
  const startUTC = new Date(targetDate + 'T00:00:00Z').toISOString();
  const endUTC = new Date(targetDate + 'T23:59:59Z');
  endUTC.setHours(endUTC.getHours() + 14); 
  const endUTCString = endUTC.toISOString();

  // 3. 【當日數據】查詢 Supabase 聚合後的預測資料與關聯的球隊 Logo
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

  // 4. 【歷史紀錄】抓取過往所有已結算的結果，用於計算趨勢圖與總勝率
  const { data: allHistoryData } = await supabase
    .from('aggregated_picks')
    .select(`spread_outcome, total_outcome, matches!inner (date)`)
    .or('spread_outcome.neq.null,total_outcome.neq.null')
    .order('matches(date)', { ascending: true });

  const picks = dailyData || [];
  picks.sort((a: any, b: any) => a.matches.id - b.matches.id);

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#1F2937] to-[#030712] font-sans flex flex-col text-white tracking-tight font-medium">
      {/* 區塊 A: 頂部裝飾條 (Neon Bar) - 定義網站的主色調視覺線 */}
      <div className="h-[3px] w-full bg-gradient-to-r from-[#855e23] via-[#dfbd69] to-[#855e23] shadow-[0_0_12px_#dfbd69] brightness-110" />
      
      <main className="flex-1 p-4 md:p-8 bg-[radial-gradient(circle_at_top,rgba(255,165,0,0.05)_0%,transparent_50%)]">
        <div className="w-full max-w-3xl mx-auto px-4 md:px-0">
          
          {/* 區塊 B: Hero Banner (標題區) - 使用粗大字體與硬邊框營造專業街頭感 */}
          <div className="relative w-full h-48 md:h-60 mb-12 overflow-hidden rounded-2xl border-t-2 border-white/40 shadow-[0_0_40px_rgba(223,189,105,0.3)] [animation:aurora_4s_ease-in-out_infinite]">
            {/* 背景圖層: 使用 mix-blend-overlay 讓底圖與深藍色背景融合 */}
            <img 
              src="/cover.png" 
              className="absolute inset-0 w-full h-full object-cover mix-blend-color-burn opacity-50 saturate-150 sepia-[.50]"
            />
            <div className="absolute inset-0 flex flex-col justify-center p-8 md:p-12">
              <div className="relative z-10">
                <h1 className="text-5xl md:text-7xl font-[1000] tracking-tighter leading-none uppercase">
                  EDGE <span className="text-orange-400">ANALYTICS</span>
                </h1>
                <div className="flex items-center gap-3 mt-5">
                  {/* 標籤小元件 */}
                  <p className="bg-orange-500 text-black font-black px-3 py-1 text-xs uppercase tracking-tighter">
                    Data Driven
                  </p>
                  <p className="text-slate-400 font-bold text-xs tracking-[0.3em] uppercase border-l border-slate-700 pl-3">
                    Systematic Value
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 區塊 C: 日期導航 (Date Selector) - 包裹在深色容器內以突顯層次 */}
          <div className="mb-10 ">
            <div className="bg-[#0D1117] rounded-xl p-1 border-2 border-slate-200/20">
              <DateNavigator />
            </div>
          </div>

          {/* 區塊 D: 數據看板 (Dashboard) - 顯示勝率與趨勢圖，外層加入微發光 (Glow) 效果 */}
          <div className="mb-8 relative">
            <div className="absolute -inset-1 bg-orange-500 rounded-2xl blur-2xl opacity-5" />
            <div className="relative">
              <StatsDashboard dailyPicks={picks} historyPicks={allHistoryData || []} />
            </div>
          </div>

          {/* 區塊 E: 賽事列表 (Match List) - 展示今日所有對戰卡片 */}
          <div className="space-y-6">
             <div className="flex items-center gap-4">
                <h2 className="text-2xl font-black uppercase tracking-tight text-slate-100">Market Board</h2>
                <div className="h-[1px] flex-1 bg-gradient-to-r from-slate-800 to-transparent"></div>
             </div>

            {picks.length === 0 ? (
              /* 空狀態提示: 當天沒比賽時顯示 */
              <div className="text-center py-24 border-4 border-[#0D1117] rounded-[3rem] bg-slate-900/10">
                <p className="text-slate-800 text-6xl font-black opacity-50 mb-2 uppercase tracking-tighter">No Action</p>
                <p className="text-slate-500 font-bold uppercase tracking-[0.2em] text-[10px]">Scouting for new edges...</p>
              </div>
            ) : (
              /* 賽事卡片循環: 包含懸浮 (Hover) 的位移與發光效果 */
              <div className="grid gap-6">
                {picks.map((pick: any, index: number) => (
                  <div key={pick.id} className="group relative">
                    {/* 卡片後方的環境發光層 */}
                    <div className="absolute inset-0 bg-orange-500 rounded-2xl translate-x-1 translate-y-1 opacity-0 group-hover:opacity-10 transition-all duration-300" />
                    {/* 卡片本體 */}
                    <div className="relative bg-[#0D1117] rounded-2xl border border-slate-800 group-hover:border-orange-500/50 group-hover:-translate-x-1 group-hover:-translate-y-1 transition-all duration-300 shadow-2xl">
                      <MatchCard pick={pick} index={index} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}