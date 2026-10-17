import assert from "node:assert/strict";
import { latestDate, matchesOnDate, pickForMatch, historyPicks, loadSnapshot } from "./snapshot.mjs";

const snapshot = {
  teams: [],
  matches: [
    { id: 1, date: "2026-10-17", start_time: "2026-10-17T23:00:00Z", home_team: { code: "LAL" }, away_team: { code: "BOS" } },
    { id: 2, date: "2026-10-18", start_time: "2026-10-18T23:00:00Z", home_team: { code: "NYK" }, away_team: { code: "MIA" } },
  ],
  picks: [
    { match_id: 1, spread_outcome: "WIN", total_outcome: null, matches: { date: "2026-10-17" } },
    { match_id: 2, spread_outcome: null, total_outcome: null, matches: { date: "2026-10-18" } },
  ],
};

assert.equal(latestDate(snapshot, "2026-10-18"), "2026-10-18");
assert.equal(latestDate(snapshot, "2026-10-19"), "2026-10-18");
assert.deepEqual(matchesOnDate(snapshot, "2026-10-17").map((m) => m.id), [1]);
assert.equal(pickForMatch(snapshot, "1").match_id, 1);
assert.equal(pickForMatch(snapshot, "9"), null);
assert.deepEqual(historyPicks(snapshot).map((p) => p.match_id), [1]);
assert.equal(typeof loadSnapshot, "function");
console.log("PASS snapshot");
