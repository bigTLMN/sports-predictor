import { supabase } from '@/lib/supabase';
import { notFound } from 'next/navigation';
import { format } from 'date-fns';
import Link from 'next/link';

export const revalidate = 0;

// 🔥 修正 1: 定義 params 為 Promise
interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function MatchDetail({ params }: PageProps) {
  // 🔥 修正 2: 必須先 await params
  const { id } = await params;

  // 1. 根據 URL 的 id 抓取該場比賽的詳細預測
  const { data: pick } = await supabase
    .from('aggregated_picks')
    .select(`
      *,
      matches!inner (
        *,
        home_team: teams!matches_home_team_id_fkey (*),
        away_team: teams!matches_away_team_id_fkey (*)
      ),
      recommended_team: teams!aggregated_picks_recommended_team_id_fkey (*)
    `)
    .eq('match_id', id) // 🔥 這裡使用解構出來的 id
    .single();

  if (!pick) {
    return notFound();
  }

  const m = pick.matches;
  
  return (
    <div className="min-h-screen bg-[#030712] text-white font-sans selection:bg-orange-500/30">
      
      {/* Navbar / Back Button */}
      <div className="p-6 border-b border-white/10 flex items-center justify-between bg-[#0D1117]">
         <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors group">
            <span className="group-hover:-translate-x-1 transition-transform">←</span>
            <span className="font-bold text-sm tracking-widest uppercase">Back to Market</span>
         </Link>
         <div className="text-orange-500 font-black tracking-tighter uppercase">Edge Analytics Pro</div>
      </div>

      <main className="max-w-4xl mx-auto p-6 md:p-12">
        
        {/* Section 1: Matchup Header */}
        <div className="flex flex-col md:flex-row justify-between items-center mb-16 gap-8 relative">
            {/* Away Team */}
            <div className="flex flex-col items-center gap-4 flex-1">
                <img src={m.away_team.logo_url} className="w-24 h-24 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]" />
                <div className="text-center">
                    <h2 className="text-3xl font-[1000] tracking-tighter">{m.away_team.full_name}</h2>
                    <p className="text-slate-500 font-mono text-sm">AWAY</p>
                </div>
            </div>

            {/* VS Info */}
            <div className="flex flex-col items-center justify-center shrink-0 z-10">
                <div className="text-5xl font-black text-slate-700/30 italic absolute select-none">VS</div>
                <div className="bg-slate-800 text-slate-300 px-4 py-1 rounded-full text-xs font-mono mb-2 border border-slate-700">
                    {format(new Date(m.start_time), 'MMM dd • HH:mm')}
                </div>
                <div className="text-center space-y-1">
                    <div className="text-slate-400 text-xs font-bold tracking-widest uppercase">Vegas Spread</div>
                    <div className="text-xl font-black text-white">
                        {m.home_team.code} {m.vegas_spread > 0 ? `+${m.vegas_spread}` : m.vegas_spread}
                    </div>
                </div>
            </div>

            {/* Home Team */}
            <div className="flex flex-col items-center gap-4 flex-1">
                <img src={m.home_team.logo_url} className="w-24 h-24 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]" />
                <div className="text-center">
                    <h2 className="text-3xl font-[1000] tracking-tighter">{m.home_team.full_name}</h2>
                    <p className="text-slate-500 font-mono text-sm">HOME</p>
                </div>
            </div>
        </div>

        {/* Section 2: AI Recommendation Hero */}
        <div className="mb-12">
            <div className="bg-gradient-to-br from-blue-900/40 to-slate-900 border border-blue-500/30 rounded-3xl p-8 relative overflow-hidden">
                <div className="absolute top-0 right-0 bg-blue-500 text-white text-xs font-black px-4 py-2 rounded-bl-2xl uppercase tracking-widest">
                    Official Pick
                </div>
                
                <div className="relative z-10 flex flex-col md:flex-row gap-8 items-center">
                    <div className="flex-1">
                        <div className="text-blue-400 font-bold tracking-widest uppercase text-xs mb-2">Algorithm Projection</div>
                        <h3 className="text-4xl md:text-5xl font-black text-white mb-2 leading-none">
                            {pick.recommended_team.full_name}
                        </h3>
                        <p className="text-2xl text-slate-300 font-light">
                            {pick.spread_logic}
                        </p>
                    </div>
                    
                    {/* Confidence Meter */}
                    <div className="flex flex-col items-center bg-black/20 p-6 rounded-2xl border border-white/5 backdrop-blur-sm">
                        <span className="text-blue-400 text-xs font-black uppercase tracking-widest mb-1">Confidence</span>
                        <span className="text-5xl font-black text-white">{pick.confidence_score}%</span>
                    </div>
                </div>
            </div>
        </div>

        {/* Section 3: The "Professional Analysis" (Prompt Content) */}
        <div className="grid md:grid-cols-3 gap-8">
            <div className="md:col-span-2 space-y-6">
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-1 h-6 bg-orange-500 rounded-full"></div>
                    <h3 className="text-2xl font-black uppercase tracking-tight">System Analysis</h3>
                </div>
                
                <div className="bg-[#161b22] border border-slate-800 rounded-2xl p-8 shadow-xl">
                    <div className="prose prose-invert max-w-none">
                        {/* 這裡渲染從後端生成的文案，處理換行符號 */}
                        {pick.analysis_content ? (
                             pick.analysis_content.split('\n').map((line: string, i: number) => (
                                <p key={i} className={`text-slate-300 leading-relaxed ${line.startsWith('•') ? 'font-bold text-white pl-4' : ''}`}>
                                    {line}
                                </p>
                            ))
                        ) : (
                            <p className="text-slate-500 italic">Detailed analysis is generating...</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Sidebar: Key Stats */}
            <div className="space-y-6">
                 <div className="flex items-center gap-3 mb-2">
                    <div className="w-1 h-6 bg-slate-700 rounded-full"></div>
                    <h3 className="text-xl font-black uppercase tracking-tight text-slate-500">Market Intel</h3>
                </div>
                <div className="bg-[#161b22] border border-slate-800 rounded-2xl p-6">
                    <div className="flex justify-between items-center mb-4 pb-4 border-b border-slate-800">
                        <span className="text-slate-400 text-xs font-bold uppercase">Total Line</span>
                        <span className="text-white font-mono font-bold">{m.vegas_total}</span>
                    </div>
                    <div className="flex justify-between items-center mb-4 pb-4 border-b border-slate-800">
                         <span className="text-slate-400 text-xs font-bold uppercase">AI Total</span>
                         <span className={`font-mono font-bold ${pick.ou_pick === 'OVER' ? 'text-red-400' : 'text-blue-400'}`}>
                            {pick.ou_pick}
                         </span>
                    </div>
                    <div className="text-xs text-slate-600 text-center mt-4">
                        Data updated at {format(new Date(pick.created_at), 'HH:mm')} UTC
                    </div>
                </div>
            </div>
        </div>

      </main>
    </div>
  );
}