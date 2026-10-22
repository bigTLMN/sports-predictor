'use client';

import Link from 'next/link';
import { format } from 'date-fns';
import { useI18n } from '@/lib/i18n';
import { formatSignedLine, formatTotalLine, recommendedCoverNumber } from '@/lib/pickModelLabels';
import { pickAnalysisContent } from '@/lib/pickLocalized';
import AppearanceSwitch from '@/app/components/AppearanceSwitch';
import { AnalysisText, FactsTable, NumbersCard } from '@/app/components/AnalysisReport';

export default function MatchDetailView({ pick }: { pick: any }) {
  const { t, locale } = useI18n();
  const m = pick.matches;

  const hasSpreadLine =
    pick.line_info != null && String(pick.line_info).trim() !== '';

  const ouLabel =
    pick.ou_pick === 'OVER' ? t('card.ou.over') : pick.ou_pick === 'UNDER' ? t('card.ou.under') : pick.ou_pick;

  const homeLineForCover =
    m.vegas_spread !== null && m.vegas_spread !== undefined && m.vegas_spread !== ''
      ? m.vegas_spread
      : pick.line_info;
  const coverNumber = hasSpreadLine
    ? recommendedCoverNumber(homeLineForCover, pick.recommended_team?.code, m.home_team?.code)
    : null;
  const coverLineText = coverNumber === null ? null : formatSignedLine(coverNumber);
  const spreadPickText = [pick.recommended_team?.code, coverLineText, t('card.toCover')]
    .filter((part) => part)
    .join(' ');
  const totalSource =
    m.vegas_total !== null && m.vegas_total !== undefined && m.vegas_total !== ''
      ? m.vegas_total
      : pick.ou_line;
  const totalLineNumber = Number(totalSource);
  const totalLineText = Number.isNaN(totalLineNumber) ? null : formatTotalLine(totalLineNumber);
  const totalCoverText =
    ouLabel && totalLineText
      ? t('card.totalCoverLine', { side: ouLabel, line: totalLineText })
      : ouLabel
        ? `${ouLabel} ${t('card.toCover')}`
        : null;

  const analysisDisplay = pickAnalysisContent(pick, locale);
  const facts = pick.analysis_facts && typeof pick.analysis_facts === 'object' ? pick.analysis_facts : null;
  const recCode = pick.recommended_team?.code ?? '';
  const oppCode = recCode === m.home_team?.code ? m.away_team?.code ?? '' : m.home_team?.code ?? '';

  return (
    <div className="min-h-screen overflow-x-hidden bg-slate-100 text-slate-900 dark:bg-[#030712] dark:text-white font-sans selection:bg-orange-500/30">
      <div className="p-4 md:p-6 border-b border-slate-200 dark:border-white/10 flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-[#0D1117]">
        <Link href="/" className="flex items-center gap-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors group">
          <span className="group-hover:-translate-x-1 transition-transform">←</span>
          <span className="font-bold text-sm tracking-wide uppercase">{t('detail.back')}</span>
        </Link>
        <div className="flex max-w-full flex-wrap items-center justify-end gap-2">
          <AppearanceSwitch compact />
          <div className="text-orange-500 font-black tracking-tighter uppercase">{t('detail.edgePro')}</div>
        </div>
      </div>

      <main className="max-w-4xl mx-auto p-4 sm:p-6 md:p-12">
        <div className="flex flex-col md:flex-row justify-between items-center mb-16 gap-8 relative">
          <div className="flex flex-col items-center gap-4 flex-1">
            <img
              src={m.away_team.logo_url}
              className="w-24 h-24 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]"
              alt=""
            />
            <div className="text-center">
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight break-words">{m.away_team.full_name}</h2>
              <p className="text-slate-500 text-sm">{t('detail.away')}</p>
            </div>
          </div>

          <div className="flex flex-col items-center justify-center shrink-0 z-10">
            <div className="text-5xl font-black text-slate-700/30 italic absolute select-none">VS</div>
            <div className="bg-slate-800 text-slate-300 px-4 py-1 rounded-full text-sm mb-2 border border-slate-700">
              {format(new Date(m.start_time), 'MMM dd • HH:mm')}
            </div>
            <div className="text-center space-y-1">
              <div className="text-slate-600 dark:text-slate-300 text-sm font-bold tracking-widest uppercase">{t('card.vegas')}</div>
              <div className="text-xl font-black text-slate-900 dark:text-white">
                {m.home_team.code}{' '}
                {m.vegas_spread !== null && m.vegas_spread !== undefined && m.vegas_spread !== ''
                  ? formatSignedLine(Number(m.vegas_spread))
                  : t('card.pk')}
              </div>
              {totalLineText && (
                <div className="text-lg font-black text-yellow-600 dark:text-yellow-400 tabular-nums">
                  {t('card.vegasTotal')} {totalLineText}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col items-center gap-4 flex-1">
            <img
              src={m.home_team.logo_url}
              className="w-24 h-24 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]"
              alt=""
            />
            <div className="text-center">
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight break-words">{m.home_team.full_name}</h2>
              <p className="text-slate-500 text-sm">{t('detail.home')}</p>
            </div>
          </div>
        </div>

        <div className="mb-12">
          <div className="bg-gradient-to-br from-blue-900/40 to-slate-900 border border-blue-500/30 rounded-3xl p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 bg-blue-500 text-white text-sm font-black px-4 py-2 rounded-bl-2xl uppercase tracking-widest">
              {hasSpreadLine ? t('detail.officialPick') : t('detail.totalAnalysis')}
            </div>

            <div className="relative z-10 flex flex-col md:flex-row gap-8 items-center">
              <div className="flex-1">
                <div className="text-blue-400 font-bold tracking-widest uppercase text-sm mb-2">
                  {hasSpreadLine ? t('detail.algoProj') : t('detail.spreadWithheldLabel')}
                </div>
                <h3 className="text-4xl md:text-5xl font-black text-white mb-2 leading-none">
                  {hasSpreadLine ? spreadPickText : t('detail.noSpreadPick')}
                </h3>
              </div>

              <div className="flex flex-col items-center bg-black/20 p-6 rounded-2xl border border-white/5 backdrop-blur-sm">
                <span className="text-blue-400 text-sm font-black uppercase tracking-widest mb-1">
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

            <div className="bg-white border border-slate-200 dark:bg-[#161b22] dark:border-slate-800 rounded-2xl p-5 sm:p-8 shadow-xl">
              {analysisDisplay ? (
                <AnalysisText text={analysisDisplay} />
              ) : (
                <p className="text-slate-500 italic">{t('detail.generating')}</p>
              )}
            </div>
            {facts ? <FactsTable facts={facts} recCode={recCode} oppCode={oppCode} /> : null}
          </div>

          <div className="space-y-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-1 h-6 bg-slate-700 rounded-full" />
              <h3 className="text-xl font-black uppercase tracking-tight text-slate-700 dark:text-slate-200">{t('detail.marketIntel')}</h3>
            </div>
            <div className="bg-white border border-slate-200 dark:bg-[#161b22] dark:border-slate-800 rounded-2xl p-6">
              <div className="flex justify-between items-center mb-4 pb-4 border-b border-slate-800">
                <span className="text-slate-600 dark:text-slate-300 text-sm font-bold uppercase">{t('detail.totalLine')}</span>
                <div className="text-right">
                  <span className="text-slate-900 dark:text-white font-bold tabular-nums">{totalLineText ?? m.vegas_total}</span>
                </div>
              </div>
              <div className="flex justify-between items-center mb-4 pb-4 border-b border-slate-800">
                <span className="text-slate-600 dark:text-slate-300 text-sm font-bold uppercase">{t('detail.aiTotal')}</span>
                <span
                  className={`font-bold tabular-nums ${pick.ou_pick === 'OVER' ? 'text-red-400' : 'text-blue-400'}`}
                >
                  {totalCoverText ?? '—'}
                </span>
              </div>
              <div className="text-sm text-slate-600 text-center mt-4">
                {t('detail.updatedUtc', { time: format(new Date(pick.created_at), 'HH:mm') })}
              </div>
            </div>
            {facts ? <NumbersCard facts={facts} recCode={recCode} ouPick={pick.ou_pick} withheld={!hasSpreadLine} /> : null}
          </div>
        </div>
      </main>
    </div>
  );
}
