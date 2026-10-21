import sqlite_store


def settle(conn):
    rows = conn.execute(
        """
        SELECT p.id AS pick_id, p.line_info, p.recommended_team_id, p.ou_pick, p.ou_line,
               p.spread_outcome, p.total_outcome,
               m.home_team_id, m.home_score, m.away_score, m.vegas_total, m.status
        FROM aggregated_picks p
        JOIN matches m ON m.id = p.match_id
        WHERE m.status IN ('STATUS_FINAL', 'STATUS_FINISHED', 'Final')
        """
    ).fetchall()
    updated = 0
    for row in rows:
        spread = total = None
        if row["spread_outcome"] is None and row["line_info"] not in (None, ""):
            margin = row["home_score"] - row["away_score"]
            covered = margin + float(row["line_info"])
            if row["recommended_team_id"] == row["home_team_id"]:
                spread = "WIN" if covered > 0 else "LOSS" if covered < 0 else "PUSH"
            else:
                spread = "LOSS" if covered > 0 else "WIN" if covered < 0 else "PUSH"
        total_line = row["ou_line"] if row["ou_line"] not in (None, "") else row["vegas_total"]
        if (
            row["total_outcome"] is None
            and row["ou_pick"]
            and total_line not in (None, "")
            and row["home_score"] is not None
            and row["away_score"] is not None
        ):
            points = row["home_score"] + row["away_score"]
            line = float(total_line)
            if points == line:
                total = "PUSH"
            elif row["ou_pick"] == "OVER":
                total = "WIN" if points > line else "LOSS"
            else:
                total = "WIN" if points < line else "LOSS"
        if spread is None and total is None:
            continue
        sqlite_store.grade_pick(conn, row["pick_id"], spread, total)
        updated += 1
    return updated


def grade_picks():
    print("1. 正在進行賽果結算 (Grading)...")
    updates_count = settle(sqlite_store.connect())
    if updates_count == 0:
        print("✅ 無需結算的預測。")
    else:
        print(f"🎉 結算完成！共更新 {updates_count} 筆資料。")


if __name__ == "__main__":
    grade_picks()
