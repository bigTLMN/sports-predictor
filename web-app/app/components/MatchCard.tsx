'use client';

import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { twMerge } from 'tailwind-merge';
import Link from 'next/link';
import { modelSpreadCaptionForLocale, modelTotalShortForLocale } from '@/lib/pickModelLabels';
import { useI18n } from '@/lib/i18n';
import { pickSpreadLogic } from '@/lib/pickLocalized';

interface MatchCardProps {
  pick: any;
  index: number;
}

export default function MatchCard({ pick, index }: MatchCardProps) {
  const { t, locale } = useI18n();
  const m = pick.matches;

  const hasSpreadLine =
    pick.line_info != null && String(pick.line_info).trim() !== '';
  const hasOuPick = !!(pick.ou_pick && pick.ou_line != null && pick.ou_line !== '');
  const hasPrediction =
    (!!pick.recommended_team && hasSpreadLine) || hasOuPick;

  const isFinished = m.status === 'STATUS_FINISHED' || m.status === 'STATUS_FINAL' || m.status === 'Final';

  const modelSpreadCaptionText =
    hasSpreadLine && pick.recommended_team
      ? modelSpreadCaptionForLocale(pick.predicted_margin, pick.recommended_team.code, locale)
      : null;

  const spreadText =
    m.vegas_spread !== null
      ? m.vegas_spread > 0
        ? `+${m.vegas_spread}`
        : m.vegas_spread
      : t('card.pk');

  // 政策 B 不發佈讓分時，aggregate 會把 confidence_score 設成「大小分信心」；若仍用同一門檻會誤標 High Value
  const isHighConfidence =
    hasPrediction && hasSpreadLine && pick.confidence_score >= 80;

  const ouLabel =
    pick.ou_pick === 'OVER' ? t('card.ou.over') : pick.ou_pick === 'UNDER' ? t('card.ou.under') : pick.ou_pick;

  const spreadLogicDisplay = pickSpreadLogic(pick, locale);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="group relative h-full"
    >
      <Link
        href={hasPrediction ? `/match/${pick.match_id}` : '#'}
        className={`block h-full ${!hasPrediction && 'cursor-default pointer-events-none'}`}
      >
        <div
          className={twMerge(
            'bg-white rounded-2xl shadow-sm border overflow-hidden transition-all relative h-full',
            hasPrediction ? 'hover:shadow-lg transform group-hover:-translate-y-1' : 'bg-slate-50',
            isHighConfidence ? 'border-blue-200 ring-2 ring-blue-100/50' : 'border-slate-200'
          )}
        >
          {isHighConfidence && (
            <div className="absolute top-0 right-0 z-20">
              <div className="bg-gradient-to-l from-blue-600 to-blue-500 text-white text-[9px] font-black px-2 py-1 rounded-bl-xl shadow-sm uppercase tracking-wider flex items-center gap-1">
                🔥 {t('card.highValue')}
              </div>
            </div>
          )}

          <div className="absolute top-0 left-0 bg-slate-900 text-white px-3 py-1.5 rounded-br-xl z-10 shadow-sm">
            <div className="text-[9px] font-bold tracking-widest text-slate-400 uppercase mb-0.5">{t('card.vegas')}</div>
            <div className="text-xs font-black leading-none flex items-center gap-1">
              <span>{m.home_team.code}</span>
              <span className="text-yellow-400">{spreadText}</span>
            </div>
          </div>

          <div className="pt-10 pb-4 px-4 flex justify-between items-center bg-gradient-to-b from-slate-50 to-white">
            <div className="flex flex-col items-center w-1/3 relative">
              <div className="w-14 h-14 p-2 bg-white rounded-full shadow-sm border border-slate-100 mb-2 flex items-center justify-center transition-transform duration-300">
                <img
                  src={m.away_team.logo_url || '/placeholder.png'}
                  className="w-full h-full object-contain"
                  alt={m.away_team.code}
                />
              </div>
              <span className="font-bold text-slate-700">{m.away_team.code}</span>
              {isFinished && <span className="text-xl font-black text-slate-900 mt-1">{m.away_score}</span>}
            </div>

            <div className="flex flex-col items-center w-1/3">
              <span className="text-[10px] font-black text-slate-300 tracking-widest">{t('card.at')}</span>
              {isFinished ? (
                <span className="text-[10px] font-bold bg-slate-100 text-slate-500 px-2 py-0.5 rounded mt-1 border border-slate-200">
                  {t('card.final')}
                </span>
              ) : (
                <span className="text-[10px] font-bold text-slate-400 mt-1 font-mono bg-slate-50 px-2 py-0.5 rounded border border-slate-100">
                  {format(new Date(m.start_time), 'HH:mm')}
                </span>
              )}
            </div>

            <div className="flex flex-col items-center w-1/3 relative">
              <div className="w-14 h-14 p-2 bg-white rounded-full shadow-sm border border-slate-100 mb-2 flex items-center justify-center transition-transform duration-300">
                <img
                  src={m.home_team.logo_url || '/placeholder.png'}
                  className="w-full h-full object-contain"
                  alt={m.home_team.code}
                />
              </div>
              <span className="font-bold text-slate-700">{m.home_team.code}</span>
              {isFinished && <span className="text-xl font-black text-slate-900 mt-1">{m.home_score}</span>}
            </div>
          </div>

          <div className="px-4 pb-4">
            <div
              className={twMerge(
                'rounded-xl p-3 border relative overflow-hidden transition-colors',
                hasPrediction
                  ? isHighConfidence
                    ? 'bg-blue-50/50 border-blue-100'
                    : 'bg-slate-50 border-slate-100'
                  : 'bg-slate-50/50 border-slate-100/50 border-dashed'
              )}
            >
              {hasPrediction ? (
                <>
                  <div className="flex justify-between items-center mb-3 relative z-10">
                    <div className="flex items-center gap-2">
                      <span
                        className={twMerge(
                          'w-2 h-2 rounded-full animate-pulse',
                          isHighConfidence ? 'bg-blue-600' : 'bg-slate-400'
                        )}
                      />
                      <span
                        className={twMerge(
                          'text-[10px] font-black uppercase tracking-widest',
                          isHighConfidence ? 'text-blue-700' : 'text-slate-400'
                        )}
                      >
                        {t('card.aiAnalysis')}
                      </span>
                    </div>

                    <div className="flex items-center gap-1 text-[9px] font-black uppercase text-slate-400 bg-white/60 px-2 py-1 rounded border border-slate-200/60 group-hover:bg-orange-500 group-hover:text-white group-hover:border-orange-500 transition-all shadow-sm">
                      {t('card.viewAnalysis')}
                      <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>

                  {hasSpreadLine && pick.recommended_team ? (
                    <div className="flex justify-between items-start mb-3 relative z-10">
                      <div className="flex items-center gap-3">
                        <img src={pick.recommended_team.logo_url} className="w-8 h-8 object-contain drop-shadow-sm" />
                        <div>
                          <div className="text-base font-black text-slate-800 leading-snug flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
                            <span>
                              {pick.recommended_team.code}{' '}
                              <span className="text-xs font-bold text-slate-400">{t('card.toCover')}</span>
                            </span>
                            {modelSpreadCaptionText && (
                              <span className="text-[11px] font-bold text-orange-600 tracking-tight">
                                · {modelSpreadCaptionText}
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] font-medium text-slate-500 mt-1 bg-white/80 px-1.5 py-0.5 rounded border border-slate-100/50 inline-block backdrop-blur-sm">
                            {spreadLogicDisplay || t('card.valueBetFallback')}
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-col items-end w-20">
                        <div className={twMerge('text-xl font-black', isHighConfidence ? 'text-blue-600' : 'text-slate-600')}>
                          {pick.confidence_score}%
                        </div>
                        <div className="w-full h-1.5 bg-slate-200 rounded-full mt-1 overflow-hidden">
                          <div
                            className={twMerge(
                              'h-full rounded-full',
                              isHighConfidence ? 'bg-gradient-to-r from-blue-400 to-blue-600' : 'bg-slate-400'
                            )}
                            style={{ width: `${pick.confidence_score}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="mb-3 relative z-10 space-y-2">
                      <p className="text-[11px] font-bold text-amber-700/90 leading-snug">
                        {spreadLogicDisplay || t('card.spreadWithheld')}
                      </p>
                      <div className="flex justify-end w-full">
                        <div className="flex flex-col items-end w-20">
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                            {t('card.confTotal')}
                          </span>
                          <div
                            className={twMerge(
                              'text-xl font-black',
                              isHighConfidence ? 'text-blue-600' : 'text-slate-600'
                            )}
                          >
                            {pick.confidence_score}%
                          </div>
                          <div className="w-full h-1.5 bg-slate-200 rounded-full mt-1 overflow-hidden">
                            <div
                              className={twMerge(
                                'h-full rounded-full',
                                isHighConfidence ? 'bg-gradient-to-r from-blue-400 to-blue-600' : 'bg-slate-400'
                              )}
                              style={{ width: `${pick.confidence_score}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="w-full h-px bg-slate-200/60 my-2" />

                  <div className="flex justify-between items-center relative z-10">
                    <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
                      <span className="text-[10px] font-bold text-slate-400 uppercase">{t('card.totalRow')}</span>
                      <span className="text-xs font-black text-slate-700">{m.vegas_total ?? '--'}</span>
                      {modelTotalShortForLocale(pick.predicted_total, locale) && (
                        <span className="text-[10px] font-bold text-violet-600">
                          · {modelTotalShortForLocale(pick.predicted_total, locale)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-black px-2 py-0.5 rounded ${
                          pick.ou_pick === 'OVER'
                            ? 'bg-red-50 text-red-600 border border-red-100'
                            : 'bg-blue-50 text-blue-600 border border-blue-100'
                        }`}
                      >
                        {ouLabel}
                      </span>
                      <span className="text-[10px] font-bold text-slate-400">({pick.ou_confidence}%)</span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-5 text-center space-y-2 opacity-60">
                  <span className="w-2 h-2 bg-slate-300 rounded-full animate-pulse" />
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                    {t('card.aiPending')}
                  </span>
                  <span className="text-[9px] text-slate-300 font-mono">{t('card.waitingData')}</span>
                </div>
              )}
            </div>
          </div>

          {hasPrediction && (pick.spread_outcome || pick.total_outcome) && (
            <div className="flex border-t border-slate-100 divide-x divide-slate-100 bg-white">
              <div
                className={`flex-1 py-2 flex flex-col items-center justify-center ${
                  hasSpreadLine && pick.spread_outcome === 'WIN'
                    ? 'bg-green-50/50'
                    : hasSpreadLine && pick.spread_outcome === 'LOSS'
                      ? 'bg-red-50/50'
                      : ''
                }`}
              >
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">{t('card.spreadFooter')}</span>
                <span
                  className={`text-xs font-black ${
                    !hasSpreadLine
                      ? 'text-slate-400'
                      : pick.spread_outcome === 'WIN'
                        ? 'text-green-600'
                        : pick.spread_outcome === 'LOSS'
                          ? 'text-red-500'
                          : 'text-slate-500'
                  }`}
                >
                  {hasSpreadLine ? pick.spread_outcome || '-' : '—'}
                </span>
              </div>

              <div
                className={`flex-1 py-2 flex flex-col items-center justify-center ${
                  pick.total_outcome === 'WIN' ? 'bg-green-50/50' : pick.total_outcome === 'LOSS' ? 'bg-red-50/50' : ''
                }`}
              >
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">{t('card.totalFooter')}</span>
                <span
                  className={`text-xs font-black ${
                    pick.total_outcome === 'WIN'
                      ? 'text-green-600'
                      : pick.total_outcome === 'LOSS'
                        ? 'text-red-500'
                        : 'text-slate-500'
                  }`}
                >
                  {pick.total_outcome || '-'}
                </span>
              </div>
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  );
}
