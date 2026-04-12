import type { Locale } from './locale-catalog';

/** DB 有繁中欄位時優先；否則將既有英文範本翻成繁中（舊資料相容）。 */
export function pickSpreadLogic(pick: any, locale: Locale): string {
  const raw = pick?.spread_logic;
  if (raw == null || raw === '') return '';
  if (locale !== 'zh-TW') return String(raw);
  const zh = pick?.spread_logic_zh;
  if (typeof zh === 'string' && zh.trim() !== '') return zh;
  return legacySpreadLogicEnToZh(String(raw)) ?? String(raw);
}

export function pickAnalysisContent(pick: any, locale: Locale): string {
  const raw = pick?.analysis_content;
  if (raw == null || raw === '') return '';
  if (locale !== 'zh-TW') return String(raw);
  const zh = pick?.analysis_content_zh;
  if (typeof zh === 'string' && zh.trim() !== '') return zh;
  return legacyAnalysisEnToZh(String(raw)) ?? String(raw);
}

function legacySpreadLogicEnToZh(en: string): string | null {
  const s = en.trim();
  let m = /^AI projects (\w+) to win by ([\d.]+) pts\.?$/.exec(s);
  if (m) return `AI 預測 ${m[1]} 贏 ${m[2]} 分`;
  m = /^AI projects (\w+) to lose by ([\d.]+) pts\.?$/.exec(s);
  if (m) return `AI 預測 ${m[1]} 輸 ${m[2]} 分`;
  if (s.includes('Spread pick withheld') || s.includes('large underdog filter'))
    return '因大受讓政策，本場不發佈讓分建議。';
  return null;
}

/** 對應 aggregate_picks 產生的英文範本（舊資料無 analysis_content_zh 時） */
function legacyAnalysisEnToZh(en: string): string | null {
  const trimmed = en.trim();
  if (trimmed === 'Analysis unavailable based on current data.') {
    return '目前資料不足，無法產出分析。';
  }
  if (!trimmed.includes('Our AI model identifies') && !trimmed.includes('Data analysis suggests')) {
    return null;
  }

  const featMap: [RegExp, string][] = [
    [/Shooting Efficiency \(L5\)/g, '投籃效率（近5場）'],
    [/3-Point Shooting \(L5\)/g, '三分投射（近5場）'],
    [/Free Throw Reliability \(L5\)/g, '罰球穩定度（近5場）'],
    [/Rebounding Presence \(L5\)/g, '籃板影響力（近5場）'],
    [/Ball Movement \(L5\)/g, '傳導與助攻（近5場）'],
    [/Defensive Pressure \(L5\)/g, '防守壓迫（近5場）'],
    [/Rim Protection \(L5\)/g, '護框阻攻（近5場）'],
    [/Ball Security \(L5\)/g, '失誤控制（近5場）'],
    [/Net Rating Trend \(L5\)/g, '正負值趨勢（近5場）'],
    [/Paint Scoring \(L5\)/g, '禁區得分（近5場）'],
    [/Winning Momentum \(L5\)/g, '勝率動能（近5場）'],
  ];

  let t = en;
  for (const [re, zh] of featMap) t = t.replace(re, zh);

  t = t.replace(
    /^Our AI model identifies a statistical edge for (\w+) over (\w+)\./m,
    'AI 模型指出：$1 相對 $2，在近期統計指標上較占優勢。'
  );

  t = t.replace(
    /• \*\*([^*]+)\*\*: Shows a (slight|significant|dominant) advantage in recent form\./g,
    (_full, name: string, intens: string) => {
      const z = intens === 'dominant' ? '強烈' : intens === 'significant' ? '明顯' : '輕微';
      return `• **${name}**：近 5 場呈現「${z}」優勢。`;
    }
  );

  t = t.replace(
    /Comparing the recent 5-game trends, (\w+)'s performance in (.+) is a key indicator for this matchup\./,
    '綜合近 5 場走勢，$1 在「$2」上的表現是本場關鍵指標。'
  );

  t = t.replace(
    /Data analysis suggests a close matchup based on recent performance\./g,
    '數據顯示雙方近況接近，賽事可能較為拉鋸。'
  );

  if (t.trim() === trimmed) return null;
  return t;
}
