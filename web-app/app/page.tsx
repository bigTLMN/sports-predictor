import { supabase } from '@/lib/supabase';
import DateNavigator from './components/DateNavigator';
import StatsDashboard from './components/StatsDashboard';
import MatchCard from './components/MatchCard';
import Footer from './components/Footer';
import { format } from 'date-fns';
import { toZonedTime } from 'date-fns-tz';

export const revalidate = 0;

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;

  const timeZone = 'America/New_York';
  const now = new Date();
  const zonedDate = toZonedTime(now, timeZone);
  const todayStr = format(zonedDate, 'yyyy-MM-dd');
  const targetDate = (params.date as string) || todayStr;

  // ==========================================
  // 🔥 關鍵修正：調整查詢時區 (NBA Day Logic)
  // ==========================================
  const startDate = new Date(targetDate);
  startDate.setUTCHours(11, 0, 0, 0); 
  const startUTC = startDate.toISOString();

  const endDate = new Date(startDate);
  endDate.setHours(endDate.getHours() + 24);
  const endUTC = endDate.toISOString();

  // 1. 先抓取比賽
  const { data: matchesData } = await supabase
    .from('matches')
    .select(`
      id, date, status, home_score, away_score, start_time, vegas_spread, vegas_total,
      home_team: teams!matches_home_team_id_fkey (code, full_name, logo_url),
      away_team: teams!matches_away_team_id_fkey (code, full_name, logo_url)
    `)
    .gte('start_time', startUTC)
    .lt('start_time', endUTC)
    .order('start_time', { ascending: true });

  const matches = matchesData || [];
  const matchIds = matches.map(m => m.id);

  // 2. 再抓取預測
  let picksMap = new Map();
  
  if (matchIds.length > 0) {
    const { data: picksData } = await supabase
      .from('aggregated_picks')
      .select(`
        *,
        recommended_team: teams!aggregated_picks_recommended_team_id_fkey (code, logo_url)
      `)
      .in('match_id', matchIds);
      
    (picksData || []).forEach((p: any) => {
      picksMap.set(p.match_id, p);
    });
  }

  // 3. 合併資料
  const picks = matches.map((match: any) => {
    const prediction = picksMap.get(match.id) || {};
    
    return {
      ...prediction,     
      matches: match,    
      match_id: match.id 
    };
  });

  // 4. 歷史紀錄
  const { data: allHistoryData } = await supabase
    .from('aggregated_picks')
    .select(`spread_outcome, total_outcome, matches!inner (date)`)
    .or('spread_outcome.neq.null,total_outcome.neq.null')
    .order('matches(date)', { ascending: true });

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#1F2937] to-[#030712] font-sans flex flex-col text-white tracking-tight font-medium">
      <div className="h-[3px] w-full bg-gradient-to-r from-[#855e23] via-[#dfbd69] to-[#855e23] shadow-[0_0_12px_#dfbd69] brightness-110" />
      
      <main className="flex-1 p-4 md:p-8 bg-[radial-gradient(circle_at_top,rgba(255,165,0,0.05)_0%,transparent_50%)]">
        <div className="w-full max-w-3xl mx-auto px-4 md:px-0">
          
          {/* Hero Banner */}
          <div className="relative w-full h-48 md:h-60 mb-12 overflow-hidden rounded-2xl border-t-2 border-white/40 shadow-[0_0_40px_rgba(223,189,105,0.3)] [animation:aurora_4s_ease-in-out_infinite]">
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

          <div className="mb-10 ">
            <div className="bg-[#0D1117] rounded-xl p-1 border-2 border-slate-200/20">
              <DateNavigator />
            </div>
          </div>

          <div className="mb-8 relative">
            <div className="absolute -inset-1 bg-orange-500 rounded-2xl blur-2xl opacity-5" />
            <div className="relative">
              <StatsDashboard dailyPicks={picks} historyPicks={allHistoryData || []} />
            </div>
          </div>

          <div className="space-y-6">
             <div className="flex items-center gap-4">
                <h2 className="text-2xl font-black uppercase tracking-tight text-slate-100">Market Board</h2>
                <div className="h-[1px] flex-1 bg-gradient-to-r from-slate-800 to-transparent"></div>
             </div>

            {picks.length === 0 ? (
              <div className="text-center py-24 border-4 border-[#0D1117] rounded-[3rem] bg-slate-900/10">
                <p className="text-slate-800 text-6xl font-black opacity-50 mb-2 uppercase tracking-tighter">No Action</p>
                <p className="text-slate-500 font-bold uppercase tracking-[0.2em] text-[10px]">Scouting for new edges...</p>
              </div>
            ) : (
              <div className="grid gap-6">
                {picks.map((pick: any, index: number) => (
                  <div key={pick.match_id} className="group relative">
                    <div className="absolute inset-0 bg-orange-500 rounded-2xl translate-x-1 translate-y-1 opacity-0 group-hover:opacity-10 transition-all duration-300" />
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