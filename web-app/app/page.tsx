import {
  loadSnapshot,
  latestDate,
  matchesOnDate,
  historyPicks,
} from '@/lib/snapshot.mjs';
import DateNavigator from './components/DateNavigator';
import StatsDashboard from './components/StatsDashboard';
import HomeMarketBoard from './components/HomeMarketBoard';
import Footer from './components/Footer';
import AppearanceSwitch from './components/AppearanceSwitch';
import { format } from 'date-fns';
import { toZonedTime } from 'date-fns-tz';
import { redirect } from 'next/navigation';

// 強制動態渲染，確保每次進來都會重新跑邏輯
export const dynamic = 'force-dynamic';
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

  const snapshot = await loadSnapshot();

  // ==========================================
  // 🔥 1. 自動跳轉邏輯 (Auto-Redirect) - 強力版
  // ==========================================
  if (!params.date) {
    console.log(`🔍 [Redirect Check] Checking for games from ${todayStr}...`);

    const redirectDate = latestDate(snapshot, todayStr);
    if (redirectDate) {
      console.log(`🚀 [Redirect] Found game on ${redirectDate}, redirecting...`);
      redirect(`/?date=${redirectDate}`);
    } else {
      console.log(`⚠️ [Redirect] No future games found. Staying on today.`);
    }
  }

  const targetDate = (params.date as string) || todayStr;

  const matches = matchesOnDate(snapshot, targetDate);
  const matchIds = matches.map((m) => m.id);

  let picksMap = new Map();
  if (matchIds.length > 0) {
    snapshot.picks
      .filter((p) => matchIds.includes(p.match_id))
      .forEach((p) => {
        picksMap.set(p.match_id, p);
      });
  }

  const picks = matches.map((match: any) => {
    const prediction = picksMap.get(match.id) || {};
    return { ...prediction, matches: match, match_id: match.id };
  });

  const allHistoryData = historyPicks(snapshot);

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 dark:bg-gradient-to-b dark:from-[#1F2937] dark:to-[#030712] dark:text-white font-sans flex flex-col tracking-tight font-medium">
      <div className="h-[3px] w-full bg-gradient-to-r from-[#855e23] via-[#dfbd69] to-[#855e23] shadow-[0_0_12px_#dfbd69] brightness-110" />
      
      <main className="flex-1 p-4 md:p-8 bg-[radial-gradient(circle_at_top,rgba(255,165,0,0.05)_0%,transparent_50%)]">
        <div className="w-full max-w-3xl mx-auto px-4 md:px-0">
          
          {/* Hero Banner */}
          <div className="relative w-full h-48 md:h-60 mb-8">
            <a href="/" className="absolute inset-0 z-0 block overflow-hidden rounded-2xl border-t-2 border-white/40 shadow-[0_0_40px_rgba(223,189,105,0.3)] [animation:aurora_4s_ease-in-out_infinite] group cursor-pointer transition-transform duration-300 hover:scale-[1.01]">
              <img 
                src="/cover.png" 
                className="absolute inset-0 w-full h-full object-cover mix-blend-color-burn opacity-50 saturate-150 sepia-[.50]"
              />
              <div className="absolute inset-0 flex flex-col justify-end p-6 md:p-10">
                <div className="relative z-10">
                  <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-none uppercase text-white group-hover:text-orange-100 transition-colors">
                    EDGE <span className="text-orange-400 group-hover:text-orange-300">ANALYTICS</span>
                  </h1>
                  <div className="flex items-center gap-3 mt-5">
                    <p className="bg-orange-500 text-black font-black px-3 py-1 text-xs uppercase tracking-tighter group-hover:bg-orange-400 transition-colors">
                      Data Driven
                    </p>
                    <p className="text-slate-400 font-bold text-xs tracking-[0.3em] uppercase border-l border-slate-700 pl-3 group-hover:text-slate-300 transition-colors">
                      Systematic Value
                    </p>
                  </div>
                </div>
              </div>
            </a>
            <div className="absolute top-1 right-1.5 z-20">
              <AppearanceSwitch compact />
            </div>
          </div>

          <div className="mb-8 ">
            <div className="bg-white rounded-xl p-1 border-2 border-slate-200 dark:bg-[#0D1117] dark:border-slate-200/20">
              <DateNavigator />
            </div>
          </div>

          <div className="mb-8 relative">
            <div className="absolute -inset-1 bg-orange-500 rounded-2xl blur-2xl opacity-5" />
            <div className="relative">
              <StatsDashboard dailyPicks={picks} historyPicks={allHistoryData || []} />
            </div>
          </div>

          <HomeMarketBoard picks={picks} />
        </div>
      </main>
      <Footer />
    </div>
  );
}
