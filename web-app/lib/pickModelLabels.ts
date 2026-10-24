import { translateMessage, type Locale } from './locale-catalog';

/** @deprecated Prefer modelSpreadCaption(..., locale) with user locale */
export function modelSpreadCaption(pm: unknown, code: string): string | null {
  return modelSpreadCaptionForLocale(pm, code, 'en');
}

/** @deprecated Prefer modelTotalShortForLocale */
export function modelTotalShort(pt: unknown): string | null {
  return modelTotalShortForLocale(pt, 'en');
}

export function modelSpreadCaptionForLocale(
  pm: unknown,
  code: string,
  locale: Locale
): string | null {
  if (pm === null || pm === undefined) return null;
  const v = Number(pm);
  if (Number.isNaN(v)) return null;
  if (v > 0) {
    return translateMessage(locale, 'card.modelWinBy', { code, pts: v.toFixed(1) });
  }
  if (v < 0) {
    return translateMessage(locale, 'card.modelLoseBy', {
      code,
      pts: Math.abs(v).toFixed(1),
    });
  }
  return translateMessage(locale, 'card.modelPickem');
}

export function modelTotalShortForLocale(pt: unknown, locale: Locale): string | null {
  if (pt === null || pt === undefined || pt === '') return null;
  const n = Number(pt);
  if (Number.isNaN(n)) return null;
  return translateMessage(locale, 'card.modelTotalPts', { pts: n.toFixed(1) });
}

export function formatSignedLine(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  if (Math.abs(rounded) < 0.05) return 'PK';
  const body = Math.abs(rounded).toFixed(1);
  return rounded > 0 ? `+${body}` : `-${body}`;
}

export function formatTotalLine(value: number): string {
  return (Math.round(value * 10) / 10).toFixed(1);
}

function lineNumber(raw: unknown): number | null {
  if (raw === null || raw === undefined || raw === '') return null;
  const n = Number(raw);
  return Number.isNaN(n) ? null : n;
}

/** Closing home spread for display and grading; snapshot line_info is fallback only. */
export function pickSpreadHomeLine(
  match: { vegas_spread?: unknown },
  pick: { line_info?: unknown }
): number | null {
  return lineNumber(match.vegas_spread) ?? lineNumber(pick.line_info);
}

/** Saved total pick line for display and grading; closing vegas_total is fallback only. */
export function pickTotalLine(
  match: { vegas_total?: unknown },
  pick: { ou_line?: unknown }
): number | null {
  return lineNumber(pick.ou_line) ?? lineNumber(match.vegas_total);
}

/** Positive = recommended side covered vs the home-perspective spread line. */
export function actualSpreadCoverEdge(
  homeScore: number,
  awayScore: number,
  homeLine: number,
  recommendedIsHome: boolean
): number {
  const homeCover = homeScore - awayScore + homeLine;
  return recommendedIsHome ? homeCover : -homeCover;
}

/** Positive = picked side (over/under) cleared the total line. */
export function actualTotalEdge(
  homeScore: number,
  awayScore: number,
  totalLine: number,
  ouPick: string | undefined
): number | null {
  const pts = homeScore + awayScore;
  if (ouPick === 'OVER') return Math.round((pts - totalLine) * 10) / 10;
  if (ouPick === 'UNDER') return Math.round((totalLine - pts) * 10) / 10;
  return null;
}

/** Home-perspective line, flipped when the pick is the away team. */
export function recommendedCoverNumber(
  homeLine: unknown,
  recommendedCode: string | undefined,
  homeCode: string | undefined
): number | null {
  if (homeLine === null || homeLine === undefined || homeLine === '') return null;
  const line = Number(homeLine);
  if (!recommendedCode || !homeCode || Number.isNaN(line)) return null;
  return recommendedCode === homeCode ? line : -line;
}

/** Positive means the projected margin clears the recommended team's line. */
export function spreadCoverEdge(predictedMargin: unknown, coverNumber: number | null): number | null {
  if (coverNumber === null || predictedMargin === null || predictedMargin === undefined || predictedMargin === '') {
    return null;
  }
  const margin = Number(predictedMargin);
  if (Number.isNaN(margin)) return null;
  return Math.round((margin + coverNumber) * 10) / 10;
}

/** Positive means the projected total clears the picked side of the total. */
export function totalCoverEdge(
  predictedTotal: unknown,
  totalLine: unknown,
  ouPick: string | undefined
): number | null {
  if (predictedTotal === null || predictedTotal === undefined || predictedTotal === '') return null;
  if (totalLine === null || totalLine === undefined || totalLine === '') return null;
  const predicted = Number(predictedTotal);
  const line = Number(totalLine);
  if (Number.isNaN(predicted) || Number.isNaN(line)) return null;
  if (ouPick === 'OVER') return Math.round((predicted - line) * 10) / 10;
  if (ouPick === 'UNDER') return Math.round((line - predicted) * 10) / 10;
  return null;
}
