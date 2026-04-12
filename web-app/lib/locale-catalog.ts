/** Shared message catalogs (no React) — safe for server + client. */

export type Locale = 'en' | 'zh-TW';

export const LOCALE_STORAGE_KEY = 'edge-analytics-locale';

type Messages = Record<string, string>;

const en: Messages = {
  'stats.intro':
    'These numbers summarize settled AI picks only. Spread = ATS vs the posted line; Total = over/under vs the line. Combined counts both legs per game. Switch tabs to change what the chart measures.',
  'stats.intro.zhNote': '',

  'stats.tab.spread': 'SPREAD',
  'stats.tab.total': 'TOTAL',
  'stats.tab.combined': 'COMBINED',
  'stats.label.spread': 'Spread',
  'stats.label.total': 'Total',
  'stats.label.combined': 'Combined',
  'stats.daily': 'Daily',
  'stats.allTime': 'All-time',
  'stats.trendTitle': 'Trend Analysis',
  'stats.trendHint':
    'Rolling win–loss by calendar day (chart matches the range on the right). Combined = spread + total legs per pick.',
  'stats.market': 'Market',
  'stats.days': 'days',
  'stats.nDays': '{n} days',
  'stats.legWin': '{n}W',
  'stats.legLoss': '{n}L',
  'stats.row.spread': 'Spread',
  'stats.row.total': 'Total',
  'stats.row.combined': 'Combined',
  'stats.noDailyResults':
    'No daily settled results in this range for {label}. Try 30D / 90D or wait for more games.',
  'stats.noHistory': 'No settled pick history yet.',

  'trend.dailyRate': '{label} · daily rate (by game day)',
  'trend.meanRates': 'Mean of daily rates:',
  'trend.meanFootnote': 'Aggregate W-L uses the table above (not the same as this mean).',

  'home.marketTitle': 'Market Board',
  'home.noAction': 'No Action',
  'home.noActionSub': 'Scouting for new edges...',

  'footer.title': 'EDGE ANALYTICS',
  'footer.disclaimer':
    'Data provided for informational purposes only. We do not guarantee the accuracy of predictions. Please bet responsibly. If you or someone you know has a gambling problem, seek help.',
  'footer.built': 'AI Sports Prediction Project. Built with Next.js & Python.',
  'footer.lang.en': 'English',
  'footer.lang.zh': '繁體中文',

  'common.win': 'W',
  'common.loss': 'L',

  // Match card
  'card.highValue': 'High Value',
  'card.vegas': 'VEGAS',
  'card.at': 'AT',
  'card.final': 'FINAL',
  'card.aiAnalysis': 'AI Analysis',
  'card.viewAnalysis': 'View Analysis',
  'card.toCover': 'to cover',
  'card.valueBetFallback': 'Value Bet Analysis',
  'card.confTotal': 'Conf. (Total)',
  'card.totalRow': 'Total',
  'card.aiPending': 'AI Analysis Pending',
  'card.waitingData': 'Waiting for data...',
  'card.spreadFooter': 'Spread',
  'card.totalFooter': 'Total',
  'card.spreadWithheld': 'Spread recommendation withheld.',
  'card.pk': 'PK',
  'card.modelWinBy': 'Model predicts {code} to win by {pts}',
  'card.modelLoseBy': 'Model predicts {code} to lose by {pts}',
  'card.modelPickem': "Model: pick'em",
  'card.modelTotalPts': 'model {pts}',
  'card.ou.over': 'OVER',
  'card.ou.under': 'UNDER',

  // Match detail
  'detail.back': 'Back to Market',
  'detail.edgePro': 'Edge Analytics Pro',
  'detail.away': 'AWAY',
  'detail.home': 'HOME',
  'detail.vegasSpread': 'Vegas Spread',
  'detail.officialPick': 'Official Pick',
  'detail.totalAnalysis': 'Total & Analysis',
  'detail.algoProj': 'Algorithm Projection',
  'detail.spreadWithheldLabel': 'Spread withheld',
  'detail.noSpreadPick': 'No spread pick',
  'detail.confidence': 'Confidence',
  'detail.systemAnalysis': 'System Analysis',
  'detail.marketIntel': 'Market Intel',
  'detail.totalLine': 'Total Line',
  'detail.aiTotal': 'AI Total',
  'detail.generating': 'Detailed analysis is generating...',
  'detail.updatedUtc': 'Data updated at {time} UTC',
};

const zhTW: Messages = {
  'stats.intro':
    '以下為「已結算」的 AI 建議統計。Spread＝依盤口讓分是否過關；Total＝依大小分盤口是否過關。Combined＝同一場同時計入讓分腿與大小分腿。切換上方分頁可改變圖表與表格的統計範圍。',
  'stats.intro.zhNote': '',

  'stats.tab.spread': '讓分',
  'stats.tab.total': '大小',
  'stats.tab.combined': '合併',
  'stats.label.spread': '讓分',
  'stats.label.total': '大小',
  'stats.label.combined': '合併',
  'stats.daily': '今日區間',
  'stats.allTime': '累積',
  'stats.trendTitle': '走勢分析',
  'stats.trendHint':
    '依比賽日的滾動勝負（圖表與右側 7／30／90 天範圍一致）。合併＝每筆 pick 同時計讓分與大小分兩腿。',
  'stats.market': '盤別',
  'stats.days': '天',
  'stats.nDays': '{n} 天',
  'stats.legWin': '{n}勝',
  'stats.legLoss': '{n}負',
  'stats.row.spread': '讓分',
  'stats.row.total': '大小',
  'stats.row.combined': '合併',
  'stats.noDailyResults': '此區間與「{label}」尚無每日已結算資料，可改選 30 天／90 天或待更多場次。',
  'stats.noHistory': '尚無已結算的歷史紀錄。',

  'trend.dailyRate': '{label} · 依比賽日的每日命中率',
  'trend.meanRates': '每日命中率平均：',
  'trend.meanFootnote': '總體勝負以上方表格為準（與此平均值意義不同）。',

  'home.marketTitle': '盤面',
  'home.noAction': '本日無賽事',
  'home.noActionSub': '等待新邊際…',

  'footer.title': 'EDGE ANALYTICS',
  'footer.disclaimer':
    '資料僅供資訊參考，不保證預測準確。請理性看待投注；若有博弈困擾請尋求協助。',
  'footer.built': 'AI 運動預測專題。以 Next.js 與 Python 建置。',
  'footer.lang.en': 'English',
  'footer.lang.zh': '繁體中文',

  'common.win': '勝',
  'common.loss': '負',

  'card.highValue': '高價值',
  'card.vegas': '盤口',
  'card.at': '開賽',
  'card.final': '完賽',
  'card.aiAnalysis': 'AI 分析',
  'card.viewAnalysis': '查看分析',
  'card.toCover': '過盤',
  'card.valueBetFallback': '價值分析',
  'card.confTotal': '信心（大小分）',
  'card.totalRow': '大小分',
  'card.aiPending': 'AI 分析準備中',
  'card.waitingData': '等待資料…',
  'card.spreadFooter': '讓分',
  'card.totalFooter': '大小',
  'card.spreadWithheld': '本場不發佈讓分建議。',
  'card.pk': '平盤',
  'card.modelWinBy': '模型預測 {code} 贏 {pts} 分',
  'card.modelLoseBy': '模型預測 {code} 輸 {pts} 分',
  'card.modelPickem': '模型：平盤',
  'card.modelTotalPts': '模型 {pts}',
  'card.ou.over': '大分',
  'card.ou.under': '小分',

  'detail.back': '返回盤面',
  'detail.edgePro': 'Edge Analytics Pro',
  'detail.away': '客隊',
  'detail.home': '主隊',
  'detail.vegasSpread': '盤口讓分',
  'detail.officialPick': '正式讓分',
  'detail.totalAnalysis': '大小分與分析',
  'detail.algoProj': '模型預測',
  'detail.spreadWithheldLabel': '讓分未發佈',
  'detail.noSpreadPick': '無讓分建議',
  'detail.confidence': '信心',
  'detail.systemAnalysis': '系統分析',
  'detail.marketIntel': '盤面資訊',
  'detail.totalLine': '大小分盤口',
  'detail.aiTotal': 'AI 大小',
  'detail.generating': '詳細分析產生中…',
  'detail.updatedUtc': '資料更新時間 {time}（UTC）',
};

export const catalogs: Record<Locale, Messages> = { en, 'zh-TW': zhTW };

export function interpolate(
  template: string,
  vars?: Record<string, string | number>
): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}

export function translateMessage(
  locale: Locale,
  key: string,
  vars?: Record<string, string | number>
): string {
  const msg = catalogs[locale][key] ?? catalogs.en[key] ?? key;
  return interpolate(msg, vars);
}
