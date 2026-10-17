# Pi crontab 接管賽果、盤口與預測

日期：2026-10-17

第一段只把現有 GitHub Actions 管線搬到 Pi。不改模型、不改預測天數、不做過盤回測。

## 目標

Pi 上的 `tedliu` crontab 每 30 分鐘更新 Supabase 的賽果與盤口、結算已完賽預測、產出未來 1 天預測。台灣時間 22:00 那一輪才下載 Kaggle 資料並重訓，有檔案變更才 push 回 `main`。GitHub Actions 不再自行啟動。

## 排程

- 時區以 `Asia/Taipei` 為準，寫在腳本裡，不依賴 Pi 系統時區。
- crontab（保留既有其他工作）：

```cron
*/30 * * * * /home/tedliu/sports-predictor/scripts/pi_update.sh >> /home/tedliu/sports-predictor/logs/pi_update.log 2>&1
```

- 鎖放在腳本開頭（`flock -n`）。佔用中則寫 `already running` 並以結束碼 0 離開。Python 失敗的非 0 結束碼不會被記成 `already running`。
- 腳本一開始就 `cd /home/tedliu/sports-predictor`。

每一輪依序：

1. `scrape_schedule.py`：過去 3 天到未來 3 天的比分與 ESPN 盤口。
2. `grade_picks.py`：結算已完賽預測。
3. 僅當台北時間的小時為 22 且分鐘小於 30：`fetch_kaggle_data.py`、`build_player_features.py`、`train_model.py`、`utils/export_impact_data.py`。其他時段 log 寫明跳過重訓，含 22:30。
4. `aggregate_picks.py`：預測未來 1 天（維持 `PREDICT_DAYS = 1`）。
5. 刪除 `data/PlayerStatistics.csv`（若存在）。然後 `git add -f data/TeamStatistics.csv` 與 `git add .`。`.gitignore` 仍排除 `.env`、`.venv/`、`logs/`、`data/*.csv`（`TeamStatistics.csv` 除外）。沒有 staged 變更就不 commit。有變更才 commit 並 `git push origin main`。commit 訊息沿用 `🤖 Auto-update: Schedule, Odds, Picks & CSV Data`。禁止 force push。

任一步 Python 程序非 0 就停止，不 commit。下一輪 30 分鐘後再跑。

## Pi 環境

- 程式目錄：`/home/tedliu/sports-predictor`，已 clone，追蹤 `origin/main`。
- 腳本：`scripts/pi_update.sh`，使用專案內 `.venv` 的 Python。
- Log：`logs/pi_update.log`。把 `logs/` 加進 `.gitignore`。
- Python：先用系統的 3.14 建 `.venv` 並安裝 `requirements.txt`。若 `xgboost` 或 `scikit-learn` 沒有可用的 wheel，再安裝 Python 3.11 並重建 `.venv`。不使用 `/home/tedliu/.venv`。
- `.env` 從本機 `D:\sports-predictor\.env` 複製到 Pi 同一路徑，內容是 `SUPABASE_URL` 與 `SUPABASE_KEY`。不提交。
- `kaggle.json` 已在倉庫內，重訓沿用它。
- Pi 的 `origin` 改為 `git@github.com:bigTLMN/sports-predictor.git`。現有 SSH key 已能以 `bigTLMN` 登入。作者維持 Pi 上現有的 `bigTLMN` / `tedliu851005@gmail.com`。

## GitHub Actions

`daily_update.yml` 移除 `schedule` 與 `push` 觸發，只留 `workflow_dispatch`。避免 Pi push 之後 Actions 再跑一輪並互相推送。

## 驗收

1. 在 Pi 手動執行 `scripts/pi_update.sh` 一次，程序結束碼為 0，log 有這三步的輸出：抓賽程、結算、預測。
2. 手動執行時若不是台北時間 22:00–22:29，log 須顯示跳過重訓。
3. 若工作目錄有可提交變更，GitHub `main` 出現一筆上述訊息的 commit，且不是 force push。
4. Actions 的定時與 push 觸發已不在 workflow 檔裡；手動按鈕仍在。
5. 既有 crontab（SSD 清理、高鐵課表）仍在。

## 不做

- 不重做模型，不改特徵，不做過盤回測。
- 不把重訓改回每 30 分鐘或整個 22 點各跑一次。
- 不重啟其他 bot 的 systemd 服務。
