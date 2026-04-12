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
