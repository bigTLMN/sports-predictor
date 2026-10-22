const DEFAULT_SNAPSHOT_URL =
  "https://raw.githubusercontent.com/bigTLMN/sports-predictor/main/web-app/data/public-snapshot.json";

const EMPTY_SNAPSHOT = { teams: [], matches: [], picks: [] };

export async function loadSnapshot() {
  const url = process.env.SNAPSHOT_URL || DEFAULT_SNAPSHOT_URL;
  try {
    const joiner = url.includes("?") ? "&" : "?";
    const res = await fetch(`${url}${joiner}t=${Math.floor(Date.now() / 60000)}`, { cache: "no-store" });
    if (!res.ok) return { ...EMPTY_SNAPSHOT };
    const data = await res.json();
    return {
      teams: data.teams ?? [],
      matches: data.matches ?? [],
      picks: data.picks ?? [],
    };
  } catch {
    return { ...EMPTY_SNAPSHOT };
  }
}

export function matchesOnDate(snapshot, yyyyMmDd) {
  const start = new Date(`${yyyyMmDd}T11:00:00.000Z`);
  const end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
  return snapshot.matches
    .filter((m) => {
      const t = new Date(m.start_time).getTime();
      return t >= start.getTime() && t < end.getTime();
    })
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
}

export function latestDate(snapshot, today) {
  const dates = [...new Set(snapshot.matches.map((m) => m.date))].sort();
  const onOrAfter = dates.filter((d) => d >= today);
  if (onOrAfter.length) return onOrAfter[0];
  const before = dates.filter((d) => d < today);
  if (before.length) return before[before.length - 1];
  return null;
}

export function pickForMatch(snapshot, matchId) {
  const id = Number(matchId);
  return snapshot.picks.find((p) => p.match_id === id) ?? null;
}

export function historyPicks(snapshot) {
  return snapshot.picks
    .filter((p) => p.spread_outcome != null || p.total_outcome != null)
    .sort((a, b) => {
      const da = a.matches?.date ?? "";
      const db = b.matches?.date ?? "";
      return da.localeCompare(db);
    });
}
