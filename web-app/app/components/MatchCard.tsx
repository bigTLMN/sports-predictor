'use client';

import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { twMerge } from 'tailwind-merge';
import Link from 'next/link';
import { formatSignedLine, formatTotalLine, recommendedCoverNumber } from '@/lib/pickModelLabels';
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

  const spreadText =
    m.vegas_spread !== null && m.vegas_spread !== undefined && m.vegas_spread !== ''
      ? formatSignedLine(Number(m.vegas_spread))
      : t('card.pk');

  // 政策 B 不發佈讓分時，aggregate 會把 confidence_score 設成「大小分信心」；若仍用同一門檻會誤標 High Value
  const isHighConfidence =
    hasPrediction && hasSpreadLine && pick.confidence_score >= 80;

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
    hasOuPick && ouLabel && totalLineText
      ? t('card.totalCoverLine', { side: ouLabel, line: totalLineText })
      : null;

  const spreadLogicDisplay = pickSpreadLogic(pick, locale);
  const outcomeText = (value: string | null | undefined) => {
    if (value === 'WIN') return t('common.win');
    if (value === 'LOSS') return t('common.loss');
    if (value === 'PUSH') return t('common.push');
    return '-';
  };

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
            'bg-white dark:bg-[#161b22] rounded-2xl shadow-sm border overflow-hidden transition-all relative h-full text-slate-800 dark:text-slate-100',
            hasPrediction ? 'hover:shadow-lg transform group-hover:-translate-y-1' : 'bg-slate-50 dark:bg-slate-900',
            isHighConfidence ? 'border-blue-200 ring-2 ring-blue-100/50 dark:border-blue-900 dark:ring-blue-900/40' : 'border-slate-200 dark:border-slate-800'
          )}
        >
          {isHighConfidence && (
            <div className="absolute top-0 right-0 z-20">
              <div className="bg-gradient-to-l from-blue-600 to-blue-500 text-white text-sm font-black px-2 py-1 rounded-bl-xl shadow-sm uppercase tracking-wider flex items-center gap-1">
                🔥 {t('card.highValue')}
              </div>
            </div>
          )}

          <div className="absolute top-0 left-0 bg-slate-900 text-white px-3 py-1.5 rounded-br-xl z-10 shadow-sm">
            <div className="text-sm font-bold tracking-widest text-slate-400 uppercase mb-0.5">{t('card.vegas')}</div>
            <div className="text-base font-black leading-none flex items-center gap-1">
              <span>{m.home_team.code}</span>
              <span className="text-yellow-400">{spreadText}</span>
            </div>
            {totalLineText && (
              <div className="text-base font-black leading-none mt-1 text-yellow-400 tabular-nums">
                {t('card.vegasTotal')} {totalLineText}
              </div>
            )}
          </div>

          <div className={`${totalLineText ? 'pt-20' : 'pt-14'} pb-4 px-4 flex justify-between items-center bg-gradient-to-b from-slate-50 to-white dark:from-[#161b22] dark:to-[#161b22]`}>
            <div className="flex flex-col items-center w-1/3 relative">
              <div className="w-14 h-14 p-2 bg-white dark:bg-slate-900 rounded-full shadow-sm border border-slate-100 dark:border-slate-700 mb-2 flex items-center justify-center transition-transform duration-300">
                <img
                  src={m.away_team.logo_url || '/placeholder.png'}
                  className="w-full h-full object-contain"
                  alt={m.away_team.code}
                />
              </div>
              <span className="text-lg font-bold text-slate-700 dark:text-slate-100">{m.away_team.code}</span>
              {isFinished && <span className="text-xl font-black text-slate-900 dark:text-white mt-1">{m.away_score}</span>}
            </div>

            <div className="flex flex-col items-center w-1/3">
              <span className="text-sm font-black text-slate-500 dark:text-slate-300 tracking-widest">{t('card.at')}</span>
              {isFinished ? (
                <span className="text-sm font-bold bg-white text-slate-800 px-2 py-0.5 rounded mt-1 border border-slate-300 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-600">
                  {t('card.final')}
                </span>
              ) : (
                <span className="text-sm font-bold text-slate-800 mt-1 bg-white px-2 py-0.5 rounded border border-slate-300 dark:bg-slate-800 dark:text-slate-100 dark:border-slate-600">
                  {format(new Date(m.start_time), 'HH:mm')}
                </span>
              )}
            </div>

            <div className="flex flex-col items-center w-1/3 relative">
              <div className="w-14 h-14 p-2 bg-white dark:bg-slate-900 rounded-full shadow-sm border border-slate-100 dark:border-slate-700 mb-2 flex items-center justify-center transition-transform duration-300">
                <img
                  src={m.home_team.logo_url || '/placeholder.png'}
                  className="w-full h-full object-contain"
                  alt={m.home_team.code}
                />
              </div>
              <span className="text-lg font-bold text-slate-700 dark:text-slate-100">{m.home_team.code}</span>
              {isFinished && <span className="text-xl font-black text-slate-900 dark:text-white mt-1">{m.home_score}</span>}
            </div>
          </div>

          <div className="px-4 pb-4">
            <div
              className={twMerge(
                'rounded-xl p-3 border relative overflow-hidden transition-colors',
                hasPrediction
                  ? isHighConfidence
                    ? 'bg-blue-50/50 border-blue-100 dark:bg-blue-950/40 dark:border-blue-900'
                    : 'bg-slate-50 border-slate-100 dark:bg-slate-900/50 dark:border-slate-800'
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
                          'text-sm font-black uppercase tracking-widest',
                          isHighConfidence ? 'text-blue-700 dark:text-blue-300' : 'text-slate-600 dark:text-slate-300'
                        )}
                      >
                        {t('card.aiAnalysis')}
                      </span>
                    </div>

                    <div className="flex items-center gap-1 text-sm font-black uppercase text-slate-900 bg-white border border-slate-300 px-2 py-1 rounded shadow-sm dark:text-white dark:bg-slate-700 dark:border-slate-500 group-hover:bg-orange-500 group-hover:text-white group-hover:border-orange-500 transition-all">
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
                          <div className="text-lg font-black text-slate-800 dark:text-white leading-snug flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
                            <span>{spreadPickText}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-col items-end w-20">
                        <div className={twMerge('text-xl font-black', isHighConfidence ? 'text-blue-600 dark:text-blue-300' : 'text-slate-700 dark:text-slate-100')}>
                          {pick.confidence_score}%
                        </div>
                        <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full mt-1 overflow-hidden">
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
                      <p className="text-sm font-bold text-amber-800 dark:text-amber-300 leading-snug">
                        {spreadLogicDisplay || t('card.spreadWithheld')}
                      </p>
                      <div className="flex justify-end w-full">
                        <div className="flex flex-col items-end w-20">
                          <span className="text-sm font-bold text-slate-400 uppercase tracking-wider">
                            {t('card.confTotal')}
                          </span>
                          <div
                            className={twMerge(
                              'text-xl font-black',
                              isHighConfidence ? 'text-blue-600 dark:text-blue-300' : 'text-slate-700 dark:text-slate-100'
                            )}
                          >
                            {pick.confidence_score}%
                          </div>
                          <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full mt-1 overflow-hidden">
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

                  {totalCoverText && (
                    <>
                      <div className="w-full h-px bg-slate-200/60 my-2" />
                      <div className="flex justify-between items-center relative z-10">
                        <span
                          className={`text-base font-black ${
                            pick.ou_pick === 'OVER' ? 'text-red-600 dark:text-red-400' : 'text-blue-700 dark:text-blue-300'
                          }`}
                        >
                          {totalCoverText}
                        </span>
                        <span className="text-sm font-bold text-slate-600 dark:text-slate-300">({pick.ou_confidence}%)</span>
                      </div>
                    </>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-5 text-center space-y-2 opacity-60">
                  <span className="w-2 h-2 bg-slate-300 rounded-full animate-pulse" />
                  <span className="text-sm font-black uppercase tracking-widest text-slate-600 dark:text-slate-300">
                    {t('card.aiPending')}
                  </span>
                  <span className="text-sm text-slate-600 dark:text-slate-300">{t('card.waitingData')}</span>
                </div>
              )}
            </div>
          </div>

          {hasPrediction && (pick.spread_outcome || pick.total_outcome) && (
            <div className="flex border-t border-slate-100 dark:border-slate-800 divide-x divide-slate-100 dark:divide-slate-800 bg-white dark:bg-[#161b22]">
              <div
                className={`flex-1 py-2 flex flex-col items-center justify-center ${
                  hasSpreadLine && pick.spread_outcome === 'WIN'
                    ? 'bg-green-50/50'
                    : hasSpreadLine && pick.spread_outcome === 'LOSS'
                      ? 'bg-red-50/50'
                      : ''
                }`}
              >
                <span className="text-sm font-bold text-slate-400 uppercase tracking-wider">{t('card.spreadFooter')}</span>
                <span
                  className={`text-base font-black ${
                    !hasSpreadLine
                      ? 'text-slate-400'
                      : pick.spread_outcome === 'WIN'
                        ? 'text-green-600'
                        : pick.spread_outcome === 'LOSS'
                          ? 'text-red-500'
                          : 'text-slate-500'
                  }`}
                >
                  {hasSpreadLine ? outcomeText(pick.spread_outcome) : '—'}
                </span>
              </div>

              <div
                className={`flex-1 py-2 flex flex-col items-center justify-center ${
                  pick.total_outcome === 'WIN' ? 'bg-green-50/50' : pick.total_outcome === 'LOSS' ? 'bg-red-50/50' : ''
                }`}
              >
                <span className="text-sm font-bold text-slate-400 uppercase tracking-wider">{t('card.totalFooter')}</span>
                <span
                  className={`text-base font-black ${
                    pick.total_outcome === 'WIN'
                      ? 'text-green-600'
                      : pick.total_outcome === 'LOSS'
                        ? 'text-red-500'
                        : 'text-slate-500'
                  }`}
                >
                  {outcomeText(pick.total_outcome)}
                </span>
              </div>
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  );
}
