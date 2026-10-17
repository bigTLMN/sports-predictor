declare module "@/lib/snapshot.mjs" {
  export type SnapshotTeam = {
    code?: string;
    full_name?: string;
    logo_url?: string | null;
    nba_team_id?: number;
  };

  export type SnapshotMatch = {
    id: number;
    date: string;
    [key: string]: unknown;
  };

  export type SnapshotPick = {
    match_id: number;
    matches?: { date?: string };
    [key: string]: unknown;
  };

  export type Snapshot = {
    teams: SnapshotTeam[];
    matches: SnapshotMatch[];
    picks: SnapshotPick[];
  };

  export function loadSnapshot(): Promise<Snapshot>;
  export function matchesOnDate(snapshot: Snapshot, yyyyMmDd: string): SnapshotMatch[];
  export function latestDate(snapshot: Snapshot, today: string): string | null;
  export function pickForMatch(snapshot: Snapshot, matchId: string | number): SnapshotPick | null;
  export function historyPicks(snapshot: Snapshot): SnapshotPick[];
}
