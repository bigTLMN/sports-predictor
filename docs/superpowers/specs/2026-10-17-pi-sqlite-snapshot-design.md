# Pi 外接碟 SQLite 與網站 JSON 快照

日期：2026-10-17

這份規格取代 [Pi crontab 規格](2026-10-17-pi-cron-pipeline-design.md) 裡「寫入 Supabase」的部分。排程頻率、22:00 才重訓、GitHub Actions 只留手動觸發，都維持那份規格。不重做模型，不做過盤回測，不買網域，不把 Pi 做成公開網址。

## 目標

賽程、盤口、預測與結算寫在 Pi 外接碟的 SQLite。網站仍是 [https://sports-predictor-teal.vercel.app](https://sports-predictor-teal.vercel.app)。Next.js 每次開啟頁面時讀 GitHub 上的 `web-app/data/public-snapshot.json`，不再連 Supabase。

Supabase 專案位址 `rzbcyoyhtuojajprlete.supabase.co` 已無法解析。`.env` 裡的 `SUPABASE_URL` 與 `SUPABASE_KEY` 留在檔案中，程式不再讀取。

## 磁碟

- 外接碟維持 NTFS，掛在 `/mnt/usb`，不格式化。
- 映像檔：`/mnt/usb/sports-predictor/nba.img`，大小 2GB，檔案系統 ext4。
- 開機掛到 `/mnt/sports-db`。`/etc/fstab` 加一行：`/mnt/usb/sports-predictor/nba.img /mnt/sports-db ext4 loop,defaults 0 0`。這一步用一次 root 權限。映像已存在就不要重建。
- 資料庫檔：`/mnt/sports-db/nba.sqlite`。掛載點擁有者是 `tedliu`，排程才寫得進去。
- Kaggle 的 CSV 與模型 `.pkl` 不放進這個映像。CSV 仍在專案目錄，模型仍由現有重訓流程產生。

`pi_update.sh` 在做任何事之前檢查 `/mnt/sports-db` 已掛載且可寫。沒掛上就以結束碼 1 離開，不跑 Python，不 commit。

## 資料表

只有三張表。不建 `leagues`。

`teams`：`id`、`code`、`name`、`full_name`、`logo_url`。`code` 唯一。每次排程先從 ESPN teams API upsert 這 30 隊。`scrape_teams.py` 改寫 SQLite，不再查 Supabase，也不再要求聯盟列。

`matches`：`id`、`date`、`start_time`、`home_team_id`、`away_team_id`、`status`、`home_score`、`away_score`、`period_scores`、`vegas_spread`、`vegas_total`。`period_scores` 存 JSON 文字。同一天同一組主客隊只有一列，用這三欄尋找既有比賽再更新。

`pi_update.sh` 在掛載檢查通過後的順序是：`scrape_teams.py`、`scrape_schedule.py`、`grade_picks.py`、既有的 22:00 重訓判斷、`aggregate_picks.py`、匯出快照、既有的 git commit。log 仍要印出 `抓賽程`、`結算`、`跳過重訓` 或 `開始重訓`、`預測`。

`aggregated_picks`：`id`、`match_id`、`recommended_team_id`、`confidence_score`、`spread_logic`、`spread_logic_zh`、`line_info`、`ou_pick`、`ou_line`、`ou_confidence`、`analysis_content`、`analysis_content_zh`、`predicted_margin`、`predicted_total`、`spread_outcome`、`total_outcome`、`created_at`。`match_id` 唯一。結算只填兩個 outcome 欄。

`scrape_schedule.py`、`grade_picks.py`、`aggregate_picks.py` 改讀寫這個 SQLite。`scrape_odds.py` 排程本來就沒呼叫，這次不改。

## 快照

三支腳本都成功之後、git commit 之前，寫出 `web-app/data/public-snapshot.json`。內容是：

```json
{
  "teams": [],
  "matches": [],
  "picks": []
}
```

`matches` 每列帶 `home_team` 與 `away_team`（`code`、`full_name`、`logo_url`）。`picks` 每列帶完整預測欄位、巢狀的 `matches`（含兩隊）與 `recommended_team`（`code`、`logo_url`）。單場頁與首頁沿用這個形狀，不改畫面元件的顯示邏輯。

倉庫裡先放一份空的合法 JSON，避免檔案还不存在。匯出失敗則整支 `pi_update.sh` 以非 0 結束，不 commit。內容與上一份相同時，現有的「沒有 staged 變更就不 commit」會略過 push。

## 網站

`app/page.tsx` 與 `app/match/[id]/page.tsx` 改讀這份快照。讀取位址是：

`https://raw.githubusercontent.com/bigTLMN/sports-predictor/main/web-app/data/public-snapshot.json`

使用 `cache: 'no-store'`。GitHub raw 仍可能慢約一分鐘才看到新 commit。讀取失敗或 JSON 不合法時，首頁顯示現有的空狀態，單場頁回 404。不再 import `lib/supabase.ts`；沒有其他引用就刪除該檔。Vercel 不為了快照單獨改建置設定。

## 驗收

1. `/mnt/sports-db` 在開機後已掛載，`nba.sqlite` 由 `tedliu` 可寫。
2. 非台北時間 22:00–22:29 手動跑 `scripts/pi_update.sh`，結束碼 0，log 含 `抓賽程`、`結算`、`跳過重訓`、`預測`。
3. `teams` 有 30 列，`matches` 有 ESPN 回傳的近幾日比賽。
4. 資料有變時，`main` 上的 `web-app/data/public-snapshot.json` 更新，且該 commit 不是 force push。
5. 首頁與單場頁的資料來自這份 JSON，專案內不再有對 Supabase client 的呼叫。
6. 既有 crontab 三條舊工作與每 30 分鐘的 `pi_update.sh` 都還在。

## 不做

- 不重做模型，不改 `PREDICT_DAYS`，不做過盤回測。
- 不格式化 `/mnt/usb`，不把 CSV 或 `.pkl` 放進 2GB 映像。
- 不建立 Pi 的公開網址，不使用 Cloudflare quick tunnel 當網站資料來源。
- 不重啟其他 bot 的 systemd 服務。
