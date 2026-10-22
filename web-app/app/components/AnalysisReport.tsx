'use client';

import { useI18n } from '@/lib/i18n';

type FactRow = {
  key: string;
  en: string;
  zh: string;
  rec: number;
  opp: number;
  unit: string;
  better: 'high' | 'low' | null;
};

type FactForm = {
  games: number;
  wins?: number;
  losses?: number;
  home?: [number, number];
  away?: [number, number];
  ppg?: number;
  papg?: number;
  margin?: number;
  streak?: string;
  ats?: [number, number, number] | null;
  ou?: [number, number, number] | null;
  rest?: number | null;
};

export type AnalysisFacts = {
  profile_games?: number;
  profile_through?: string | null;
  rows?: FactRow[];
  form?: { rec?: FactForm; opp?: FactForm };
  projection?: {
    model_margin?: number;
    raw_margin?: number;
    market_margin?: number;
    edge?: number;
    pred_total?: number;
    total_line?: number | null;
    total_edge?: number | null;
  };
};

const SHOWN_ROWS = ['ppg', 'papg', 'net', 'fg', 'tp', 'reb', 'ast', 'tov', 'paint', 'bench'];

function winnerOf(row: FactRow): 'rec' | 'opp' | null {
  if (!row.better || row.rec === row.opp) return null;
  const recBetter = row.better === 'high' ? row.rec > row.opp : row.rec < row.opp;
  return recBetter ? 'rec' : 'opp';
}

function fmt(v: number, key: string, unit: string): string {
  if (key === 'net') return `${v > 0 ? '+' : ''}${v.toFixed(1)}`;
  return `${v.toFixed(1)}${unit}`;
}

/** Renders the research write-up: `## ` headings, `• **label** ...` bullets, plain paragraphs. */
export function AnalysisText({ text }: { text: string }) {
  const lines = text.split('\n').filter((l) => l.trim() !== '');
  return (
    <div className="space-y-3">
      {lines.map((line, i) => {
        if (line.startsWith('## ')) {
          return (
            <h4
              key={i}
              className={`text-sm font-black uppercase tracking-widest text-orange-600 dark:text-orange-400 ${i === 0 ? '' : 'pt-4'}`}
            >
              {line.slice(3)}
            </h4>
          );
        }
        if (line.startsWith('•')) {
          const body = line.replace(/^•\s*/, '');
          const parts = body.split(/\*\*/);
          return (
            <p key={i} className="pl-4 leading-relaxed text-slate-800 dark:text-slate-100 border-l-2 border-slate-200 dark:border-slate-700">
              {parts.map((part, j) =>
                j % 2 === 1 ? (
                  <span key={j} className="font-bold text-slate-900 dark:text-white">
                    {part}
                  </span>
                ) : (
                  <span key={j}>{part}</span>
                )
              )}
            </p>
          );
        }
        return (
          <p key={i} className="leading-relaxed text-slate-700 dark:text-slate-300">
            {line}
          </p>
        );
      })}
    </div>
  );
}

export function FactsTable({
  facts,
  recCode,
  oppCode,
}: {
  facts: AnalysisFacts;
  recCode: string;
  oppCode: string;
}) {
  const { t, locale } = useI18n();
  const rows = (facts.rows ?? []).filter((r) => SHOWN_ROWS.includes(r.key));
  if (rows.length === 0) return null;
  const zh = locale === 'zh-TW';

  const forms = facts.form;
  const formRow = (label: string, pick: (f: FactForm) => string | null) => {
    if (!forms?.rec?.games || !forms?.opp?.games) return null;
    const a = pick(forms.rec);
    const b = pick(forms.opp);
    if (a === null || b === null) return null;
    return (
      <tr key={label} className="border-t border-slate-200 dark:border-slate-800">
        <td className="py-2 pr-3 text-slate-600 dark:text-slate-300">{label}</td>
        <td className="py-2 px-2 text-right tabular-nums text-slate-900 dark:text-white">{a}</td>
        <td className="py-2 pl-2 text-right tabular-nums text-slate-900 dark:text-white">{b}</td>
      </tr>
    );
  };

  return (
    <div className="bg-white border border-slate-200 dark:bg-[#161b22] dark:border-slate-800 rounded-2xl p-5 sm:p-6">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-sm font-black uppercase tracking-widest text-slate-700 dark:text-slate-200">
          {t('detail.factsTitle')}
        </span>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          {t('detail.factsNote', { n: facts.profile_games ?? 0 })}
        </span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <th className="pb-2 text-left font-bold">{t('detail.factsMetric')}</th>
            <th className="pb-2 px-2 text-right font-black text-slate-900 dark:text-white">{recCode}</th>
            <th className="pb-2 pl-2 text-right font-bold">{oppCode}</th>
          </tr>
        </thead>
        <tbody>
          {formRow(t('detail.factsRecord'), (f) => `${f.wins}-${f.losses}`)}
          {formRow(t('detail.factsStreak'), (f) => f.streak ?? null)}
          {formRow(t('detail.factsAts'), (f) => (f.ats ? `${f.ats[0]}-${f.ats[1]}` : null))}
          {rows.map((row) => {
            const win = winnerOf(row);
            const winCls = 'font-bold text-emerald-700 dark:text-emerald-300';
            const loseCls = 'text-slate-500 dark:text-slate-400';
            const evenCls = 'text-slate-900 dark:text-white';
            return (
              <tr key={row.key} className="border-t border-slate-200 dark:border-slate-800">
                <td className="py-2 pr-3 text-slate-600 dark:text-slate-300">{zh ? row.zh : row.en}</td>
                <td className={`py-2 px-2 text-right tabular-nums ${win === 'rec' ? winCls : win === 'opp' ? loseCls : evenCls}`}>
                  {fmt(row.rec, row.key, row.unit)}
                </td>
                <td className={`py-2 pl-2 text-right tabular-nums ${win === 'opp' ? winCls : win === 'rec' ? loseCls : evenCls}`}>
                  {fmt(row.opp, row.key, row.unit)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
