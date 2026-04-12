'use client';

import MatchCard from './MatchCard';
import { useI18n } from '@/lib/i18n';

export default function HomeMarketBoard({
  picks,
}: {
  picks: any[];
}) {
  const { t } = useI18n();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <h2 className="text-2xl font-black uppercase tracking-tight text-slate-100">{t('home.marketTitle')}</h2>
        <div className="h-[1px] flex-1 bg-gradient-to-r from-slate-800 to-transparent" />
      </div>

      {picks.length === 0 ? (
        <div className="text-center py-24 border-4 border-[#0D1117] rounded-[3rem] bg-slate-900/10">
          <p className="text-slate-800 text-6xl font-black opacity-50 mb-2 uppercase tracking-tighter">
            {t('home.noAction')}
          </p>
          <p className="text-slate-500 font-bold uppercase tracking-[0.2em] text-[10px]">{t('home.noActionSub')}</p>
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
  );
}
