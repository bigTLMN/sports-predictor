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

/** Closing total for display and grading; saved ou_line is fallback when market line is missing. */
export function pickTotalLine(
  match: { vegas_total?: unknown },
  pick: { ou_line?: unknown }
): number | null {
  return lineNumber(match.vegas_total) ?? lineNumber(pick.ou_line);
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

export type PickOutcome = 'WIN' | 'LOSS' | 'PUSH';

/** Same rules as grade_picks.settle — keeps UI outcomes aligned with line display. */
export function settledSpreadOutcome(
  homeScore: number,
  awayScore: number,
  spreadHomeLine: number,
  recommendedIsHome: boolean
): PickOutcome {
  const edge = actualSpreadCoverEdge(homeScore, awayScore, spreadHomeLine, recommendedIsHome);
  if (edge > 0) return 'WIN';
  if (edge < 0) return 'LOSS';
  return 'PUSH';
}

export function settledTotalOutcome(
  homeScore: number,
  awayScore: number,
  totalLine: number,
  ouPick: string | undefined
): PickOutcome | null {
  const edge = actualTotalEdge(homeScore, awayScore, totalLine, ouPick);
  if (edge === null) return null;
  if (edge > 0) return 'WIN';
  if (edge < 0) return 'LOSS';
  return 'PUSH';
}

export function isFinishedMatch(status: string | undefined): boolean {
  return status === 'STATUS_FINISHED' || status === 'STATUS_FINAL' || status === 'Final';
}

/** Prefer live score + closing line over stored outcomes when a game is final. */
export function resolveDisplayedOutcomes(pick: {
  spread_outcome?: string | null;
  total_outcome?: string | null;
  ou_pick?: string;
  recommended_team?: { code?: string };
  matches?: {
    status?: string;
    home_score?: unknown;
    away_score?: unknown;
    home_team?: { code?: string };
    vegas_spread?: unknown;
    vegas_total?: unknown;
  };
  line_info?: unknown;
  ou_line?: unknown;
}): { spreadOutcome: string | null | undefined; totalOutcome: string | null | undefined } {
  const m = pick.matches;
  if (
    !m ||
    !isFinishedMatch(m.status) ||
    m.home_score == null ||
    m.away_score == null
  ) {
    return { spreadOutcome: pick.spread_outcome, totalOutcome: pick.total_outcome };
  }
  const home = Number(m.home_score);
  const away = Number(m.away_score);
  const spreadHomeLine = pickSpreadHomeLine(m, pick);
  const hasSpreadLine = spreadHomeLine !== null && !!pick.recommended_team;
  const totalLine = pickTotalLine(m, pick);
  return {
    spreadOutcome: hasSpreadLine
      ? settledSpreadOutcome(
          home,
          away,
          spreadHomeLine,
          pick.recommended_team?.code === m.home_team?.code
        )
      : pick.spread_outcome,
    totalOutcome:
      totalLine !== null && pick.ou_pick
        ? settledTotalOutcome(home, away, totalLine, pick.ou_pick)
        : pick.total_outcome,
  };
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
