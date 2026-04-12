'use client';

import Link from 'next/link';
import { format } from 'date-fns';
import { useI18n } from '@/lib/i18n';
import { modelSpreadCaptionForLocale, modelTotalShortForLocale } from '@/lib/pickModelLabels';
import { pickAnalysisContent, pickSpreadLogic } from '@/lib/pickLocalized';

export default function MatchDetailView({ pick }: { pick: any }) {
  const { t, locale } = useI18n();
  const m = pick.matches;

  const hasSpreadLine =
    pick.line_info != null && String(pick.line_info).trim() !== '';

  const spreadModelLine =
    pick.recommended_team?.code &&
    modelSpreadCaptionForLocale(pick.predicted_margin, pick.recommended_team.code, locale);
  const totalModelLine = modelTotalShortForLocale(pick.predicted_total, locale);

  const ouLabel =
    pick.ou_pick === 'OVER' ? t('card.ou.over') : pick.ou_pick === 'UNDER' ? t('card.ou.under') : pick.ou_pick;

  const spreadLogicDisplay = pickSpreadLogic(pick, locale);
  const analysisDisplay = pickAnalysisContent(pick, locale);

  return (
    <div className="min-h-screen bg-[#030712] text-white font-sans selection:bg-orange-500/30">
      <div className="p-6 border-b border-white/10 flex items-center justify-between bg-[#0D1117]">
        <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors group">
          <span className="group-hover:-translate-x-1 transition-transform">←</span>
          <span className="font-bold text-sm tracking-widest uppercase">{t('detail.back')}</span>
        </Link>
        <div className="text-orange-500 font-black tracking-tighter uppercase">{t('detail.edgePro')}</div>
      </div>

      <main className="max-w-4xl mx-auto p-6 md:p-12">
        <div className="flex flex-col md:flex-row justify-between items-center mb-16 gap-8 relative">
          <div className="flex flex-col items-center gap-4 flex-1">
            <img
              src={m.away_team.logo_url}
              className="w-24 h-24 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]"
              alt=""
            />
            <div className="text-center">
              <h2 className="text-3xl font-[1000] tracking-tighter">{m.away_team.full_name}</h2>
              <p className="text-slate-500 font-mono text-sm">{t('detail.away')}</p>
            </div>
          </div>

          <div className="flex flex-col items-center justify-center shrink-0 z-10">
            <div className="text-5xl font-black text-slate-700/30 italic absolute select-none">VS</div>
            <div className="bg-slate-800 text-slate-300 px-4 py-1 rounded-full text-xs font-mono mb-2 border border-slate-700">
              {format(new Date(m.start_time), 'MMM dd • HH:mm')}
            </div>
            <div className="text-center space-y-1">
              <div className="text-slate-400 text-xs font-bold tracking-widest uppercase">{t('detail.vegasSpread')}</div>
              <div className="text-xl font-black text-white">
                {m.home_team.code} {m.vegas_spread > 0 ? `+${m.vegas_spread}` : m.vegas_spread}
              </div>
            </div>
          </div>

          <div className="flex flex-col items-center gap-4 flex-1">
            <img
              src={m.home_team.logo_url}
              className="w-24 h-24 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]"
              alt=""
            />
            <div className="text-center">
              <h2 className="text-3xl font-[1000] tracking-tighter">{m.home_team.full_name}</h2>
              <p className="text-slate-500 font-mono text-sm">{t('detail.home')}</p>
            </div>
          </div>
        </div>

        <div className="mb-12">
          <div className="bg-gradient-to-br from-blue-900/40 to-slate-900 border border-blue-500/30 rounded-3xl p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 bg-blue-500 text-white text-xs font-black px-4 py-2 rounded-bl-2xl uppercase tracking-widest">
              {hasSpreadLine ? t('detail.officialPick') : t('detail.totalAnalysis')}
            </div>

            <div className="relative z-10 flex flex-col md:flex-row gap-8 items-center">
              <div className="flex-1">
                <div className="text-blue-400 font-bold tracking-widest uppercase text-xs mb-2">
                  {hasSpreadLine ? t('detail.algoProj') : t('detail.spreadWithheldLabel')}
                </div>
                <h3 className="text-4xl md:text-5xl font-black text-white mb-2 leading-none">
                  {hasSpreadLine ? pick.recommended_team.full_name : t('detail.noSpreadPick')}
                </h3>
                <p className="text-2xl text-slate-300 font-light">{spreadLogicDisplay}</p>
                {spreadModelLine && (
                  <p className="text-sm font-semibold text-orange-300/95 mt-3 tracking-tight">{spreadModelLine}</p>
                )}
              </div>

              <div className="flex flex-col items-center bg-black/20 p-6 rounded-2xl border border-white/5 backdrop-blur-sm">
                <span className="text-blue-400 text-xs font-black uppercase tracking-widest mb-1">
                  {hasSpreadLine ? t('detail.confidence') : t('card.confTotal')}
                </span>
                <span className="text-5xl font-black text-white">{pick.confidence_score}%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-1 h-6 bg-orange-500 rounded-full" />
              <h3 className="text-2xl font-black uppercase tracking-tight">{t('detail.systemAnalysis')}</h3>
            </div>

            <div className="bg-[#161b22] border border-slate-800 rounded-2xl p-8 shadow-xl">
              <div className="prose prose-invert max-w-none">
                {analysisDisplay ? (
                  analysisDisplay.split('\n').map((line: string, i: number) => (
                    <p
                      key={i}
                      className={`text-slate-300 leading-relaxed ${line.startsWith('•') ? 'font-bold text-white pl-4' : ''}`}
                    >
                      {line}
                    </p>
                  ))
                ) : (
                  <p className="text-slate-500 italic">{t('detail.generating')}</p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-1 h-6 bg-slate-700 rounded-full" />
              <h3 className="text-xl font-black uppercase tracking-tight text-slate-500">{t('detail.marketIntel')}</h3>
            </div>
            <div className="bg-[#161b22] border border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-center mb-4 pb-4 border-b border-slate-800">
                <span className="text-slate-400 text-xs font-bold uppercase">{t('detail.totalLine')}</span>
                <div className="text-right">
                  <span className="text-white font-mono font-bold">{m.vegas_total}</span>
                  {totalModelLine && (
                    <span className="text-violet-300 font-mono font-bold text-sm ml-2">· {totalModelLine}</span>
                  )}
                </div>
              </div>
              <div className="flex justify-between items-center mb-4 pb-4 border-b border-slate-800">
                <span className="text-slate-400 text-xs font-bold uppercase">{t('detail.aiTotal')}</span>
                <span
                  className={`font-mono font-bold ${pick.ou_pick === 'OVER' ? 'text-red-400' : 'text-blue-400'}`}
                >
                  {ouLabel}
                </span>
              </div>
              <div className="text-xs text-slate-600 text-center mt-4">
                {t('detail.updatedUtc', { time: format(new Date(pick.created_at), 'HH:mm') })}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
