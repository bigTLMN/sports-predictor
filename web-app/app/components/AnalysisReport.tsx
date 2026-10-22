'use client';

import { useI18n } from '@/lib/i18n';

type FactRow = {
  key: string;
  en: string;
  zh: string;
  rec: number;
  opp: number;
  avg?: number | null;
  rec_rank?: number | null;
  opp_rank?: number | null;
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
  rank?: { ppg?: number | null; papg?: number | null; margin?: number | null };
  streak?: string;
  ats?: [number, number, number] | null;
  ou?: [number, number, number] | null;
  rest?: number | null;
};

export type AnalysisFacts = {
  profile_games?: number;
  profile_through?: string | null;
  league_teams?: number;
  season_teams?: number;
  rows?: FactRow[];
  form?: { rec?: FactForm; opp?: FactForm };
  volatility?: { rec?: number | null; opp?: number | null };
  projection?: {
    model_margin?: number;
    raw_margin?: number;
    market_margin?: number;
    edge?: number;
    pred_total?: number;
    total_line?: number | null;
    total_edge?: number | null;
  };
  probability?: {
    cover?: number;
    win_model?: number;
    win_market?: number | null;
    total?: number | null;
    sigma_spread?: number;
    sigma_total?: number;
    sigma_measured?: boolean;
  };
  effects?: {
    years?: number;
    home_margin?: number;
    home_win_rate?: number;
    home_n?: number;
    b2b_margin?: number;
    b2b_win_rate?: number;
    b2b_n?: number;
    avg_total?: number;
  };
  record?: {
    spread?: [number, number];
    total?: [number, number];
    spread_at_conf?: [number, number] | null;
  };
};

const pct = (p: number | null | undefined) => (p == null ? '—' : `${Math.round(p * 100)}%`);
const signed = (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`;

/** Probabilities, the model's own record, and the historical effects behind the write-up. */
export function NumbersCard({
  facts,
  recCode,
  ouPick,
  withheld,
}: {
  facts: AnalysisFacts;
  recCode: string;
  ouPick: string | null | undefined;
  withheld: boolean;
}) {
  const { t } = useI18n();
  const p = facts.probability;
  const proj = facts.projection;
  const rec = facts.record;
  const eff = facts.effects;
  if (!p && !rec && !eff) return null;

  const spreadN = rec?.spread ? rec.spread[0] + rec.spread[1] : 0;
  const totalN = rec?.total ? rec.total[0] + rec.total[1] : 0;
  const bandN = rec?.spread_at_conf ? rec.spread_at_conf[0] + rec.spread_at_conf[1] : 0;
  const ouLabel = ouPick === 'OVER' ? t('card.ou.over') : ouPick === 'UNDER' ? t('card.ou.under') : '';

  const Row = ({ label, value, strong = false, sub }: { label: string; value: string; strong?: boolean; sub?: string }) => (
    <div className="flex items-baseline justify-between gap-3 border-t border-slate-200 py-2 first:border-t-0 dark:border-slate-800">
      <div className="min-w-0">
        <div className="text-sm text-slate-600 dark:text-slate-300">{label}</div>
        {sub ? <div className="text-xs text-slate-500 dark:text-slate-400">{sub}</div> : null}
      </div>
      <div className={`shrink-0 tabular-nums ${strong ? 'text-lg font-black text-slate-900 dark:text-white' : 'font-bold text-slate-900 dark:text-white'}`}>
        {value}
      </div>
    </div>
  );

  const bar = (value: number | null | undefined) => {
    if (value == null) return null;
    const w = Math.max(2, Math.min(100, Math.round(value * 100)));
    return (
      <div className="mt-1 h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-700">
        <div className="h-1.5 rounded-full bg-orange-500" style={{ width: `${w}%` }} />
      </div>
    );
  };

  return (
    <div className="bg-white border border-slate-200 dark:bg-[#161b22] dark:border-slate-800 rounded-2xl p-5 sm:p-6">
      <div className="mb-3 text-sm font-black uppercase tracking-widest text-slate-700 dark:text-slate-200">{t('detail.numbersTitle')}</div>
      {p ? (
        <div>
          {!withheld && proj?.market_margin !== undefined ? (
            <>
              <Row
                label={t('detail.numbersCover', { team: recCode })}
                value={pct(p.cover)}
                strong
                sub={t('detail.numbersEdge', { edge: signed(proj?.edge ?? 0), sigma: String(p.sigma_spread ?? '') })}
              />
              {bar(p.cover)}
              <Row label={t('detail.numbersBreakEven')} value="52.4%" />
            </>
          ) : null}
          <Row
            label={t('detail.numbersWin', { team: recCode })}
            value={p.win_market != null ? `${pct(p.win_model)} / ${pct(p.win_market)}` : pct(p.win_model)}
            sub={p.win_market != null ? t('detail.numbersWinSub') : undefined}
          />
          {p.total != null && ouLabel ? (
            <>
              <Row
                label={t('detail.numbersTotal', { side: ouLabel })}
                value={pct(p.total)}
                sub={t('detail.numbersTotalSub', { edge: signed(proj?.total_edge ?? 0), sigma: String(p.sigma_total ?? '') })}
              />
              {bar(p.total)}
            </>
          ) : null}
        </div>
      ) : null}
      {rec && (spreadN > 0 || totalN > 0) ? (
        <div className="mt-4">
          <div className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{t('detail.numbersRecord')}</div>
          {spreadN > 0 ? (
            <Row
              label={t('detail.numbersSpreadPicks')}
              value={`${rec.spread![0]}-${rec.spread![1]} (${pct(rec.spread![0] / spreadN)})`}
            />
          ) : null}
          {bandN >= 3 && !withheld ? (
            <Row label={t('detail.numbersAtConf')} value={`${rec.spread_at_conf![0]}-${rec.spread_at_conf![1]}`} />
          ) : null}
          {totalN > 0 ? (
            <Row label={t('detail.numbersTotalPicks')} value={`${rec.total![0]}-${rec.total![1]} (${pct(rec.total![0] / totalN)})`} />
          ) : null}
        </div>
      ) : null}
      {eff?.home_n ? (
        <div className="mt-4">
          <div className="mb-1 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {t('detail.numbersEffects', { years: String(eff.years ?? 3) })}
          </div>
          <Row
            label={t('detail.numbersHome')}
            value={`${signed(eff.home_margin ?? 0)} · ${pct(eff.home_win_rate)}`}
            sub={t('detail.numbersN', { n: (eff.home_n ?? 0).toLocaleString() })}
          />
          {eff.b2b_n ? (
            <Row
              label={t('detail.numbersB2b')}
              value={`${signed(eff.b2b_margin ?? 0)} · ${pct(eff.b2b_win_rate)}`}
              sub={t('detail.numbersN', { n: (eff.b2b_n ?? 0).toLocaleString() })}
            />
          ) : null}
          {eff.avg_total ? <Row label={t('detail.numbersAvgTotal')} value={eff.avg_total.toFixed(1)} /> : null}
        </div>
      ) : null}
    </div>
  );
}

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
  const hasAvg = rows.some((r) => r.avg != null);
  const nTeams = facts.league_teams ?? 0;
  const seasonTeams = facts.season_teams ?? 0;

  const rankTag = (rank: number | null | undefined, total: number) =>
    rank && total ? <span className="ml-1 text-[11px] font-normal text-slate-500 dark:text-slate-400">#{rank}</span> : null;

  const formRow = (
    label: string,
    pick: (f: FactForm) => string | null,
    rankKey?: 'ppg' | 'papg' | 'margin'
  ) => {
    if (!forms?.rec?.games || !forms?.opp?.games) return null;
    const a = pick(forms.rec);
    const b = pick(forms.opp);
    if (a === null || b === null) return null;
    return (
      <tr key={label} className="border-t border-slate-200 dark:border-slate-800">
        <td className="py-2 pr-2 text-slate-600 dark:text-slate-300">{label}</td>
        <td className="py-2 px-1 text-right tabular-nums text-slate-900 dark:text-white whitespace-nowrap">
          {a}
          {rankKey ? rankTag(forms.rec.rank?.[rankKey], seasonTeams) : null}
        </td>
        <td className="py-2 px-1 text-right tabular-nums text-slate-900 dark:text-white whitespace-nowrap">
          {b}
          {rankKey ? rankTag(forms.opp.rank?.[rankKey], seasonTeams) : null}
        </td>
        {hasAvg ? <td className="py-2 pl-1 text-right tabular-nums text-slate-500 dark:text-slate-400">—</td> : null}
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
            <th className="pb-2 px-1 text-right font-black text-slate-900 dark:text-white">{recCode}</th>
            <th className="pb-2 px-1 text-right font-bold">{oppCode}</th>
            {hasAvg ? <th className="pb-2 pl-1 text-right font-bold">{t('detail.factsLeague')}</th> : null}
          </tr>
        </thead>
        <tbody>
          {formRow(t('detail.factsRecord'), (f) => `${f.wins}-${f.losses}`)}
          {formRow(t('detail.factsStreak'), (f) => f.streak ?? null)}
          {formRow(t('detail.factsAts'), (f) => (f.ats ? `${f.ats[0]}-${f.ats[1]}` : null))}
          {formRow(t('detail.factsSeasonMargin'), (f) => (f.margin != null ? signed(f.margin) : null), 'margin')}
          {rows.map((row) => {
            const win = winnerOf(row);
            const winCls = 'font-bold text-emerald-700 dark:text-emerald-300';
            const loseCls = 'text-slate-500 dark:text-slate-400';
            const evenCls = 'text-slate-900 dark:text-white';
            return (
              <tr key={row.key} className="border-t border-slate-200 dark:border-slate-800">
                <td className="py-2 pr-2 text-slate-600 dark:text-slate-300">{zh ? row.zh : row.en}</td>
                <td className={`py-2 px-1 text-right tabular-nums whitespace-nowrap ${win === 'rec' ? winCls : win === 'opp' ? loseCls : evenCls}`}>
                  {fmt(row.rec, row.key, row.unit)}
                  {rankTag(row.rec_rank, nTeams)}
                </td>
                <td className={`py-2 px-1 text-right tabular-nums whitespace-nowrap ${win === 'opp' ? winCls : win === 'rec' ? loseCls : evenCls}`}>
                  {fmt(row.opp, row.key, row.unit)}
                  {rankTag(row.opp_rank, nTeams)}
                </td>
                {hasAvg ? (
                  <td className="py-2 pl-1 text-right tabular-nums text-slate-500 dark:text-slate-400">
                    {row.avg != null ? fmt(row.avg, row.key, row.unit) : '—'}
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
      {nTeams ? (
        <div className="mt-3 text-xs text-slate-500 dark:text-slate-400">{t('detail.factsRankNote', { n: nTeams })}</div>
      ) : null}
    </div>
  );
}
