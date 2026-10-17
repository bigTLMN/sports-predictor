import json
import sqlite_store

SNAPSHOT_PATH = "web-app/data/public-snapshot.json"


def write_snapshot(conn, path=SNAPSHOT_PATH):
    payload = sqlite_store.export_snapshot(conn)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    write_snapshot(sqlite_store.connect())
