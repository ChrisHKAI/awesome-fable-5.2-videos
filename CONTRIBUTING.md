# 如何補充

這份清單收的是公開帖裡、和 **Claude Fable 5.2** 有關的材料。畫面畫廊只收作者自己說用 Fable 5.2 做出來的畫面。模型已由 Anthropic 在 2026-11-10（香港時間）宣布，並與 Claude Mythos 5.2 同時推出。本庫沒有重跑任何一條。

## 可以進畫面畫廊的

- 原帖看得到畫面：影片、動圖，或作品本身的圖片，而且是作者自己用 Fable 5.2 做出來的。
- 作者自己的作品。轉貼別人的影片時，請改記原作者，不要把它算成新的一條。
- 和別的模型的對照可以收，但畫面必須是作者自己跑出來的。`comparison_with` 只寫作者點名的對象，並註明標籤來自作者，不是本庫復現。
- 提示詞必須是帖文裡能逐字核對的公開文字。只寫了場景、或只說「用了同一個 prompt」而沒貼出來，`prompt` 維持 `null`，不要補寫。
- 只看到一半、或其餘要求在影片裡，`prompt_partial` 設為 `true`，並在註記寫明缺了什麼。

## 不要進畫面畫廊的

- 官方宣傳片。官宣主帖放在「官方發布」。
- 只是轉用官方宣傳片的帖。
- 基準整理片，以及把官方評測表重講一遍的帖。放到「編程與基準轉述」或「基準整理片」。
- 轉述別人的作品或結論。
- 純價格、額度、速度、相容性提醒。放到對應的脈絡區。
- Mythos 5.2 的帖，除非它直接和 Fable 對照（含官方說明兩者同底）。收進來時 `mythos_comparison` 要是 `true`，README 要標成 Mythos 5.2 對照。

Fast mode 的官方說法是輸出約 2.5×、價格 2×。美元 **$16／$80** 是二手推算，沒有在官方原帖裡核到之前，維持「未核實」，不要寫成定價。

## 送出前

1. 在 `data/videos.json` 加上條目。`attribution` 用 `creator_reported`，`independently_reproduced` 維持 `false`。
2. 時間寫 Asia/Hong_Kong（UTC+8）。互動數字註明是哪一次快照。未知的數字留 null，不要補 0，除非原帖就是 0。
3. 有提示詞才新增 `prompts/<slug>.md`，Prompt 區塊與 JSON 逐字相同。
4. 預覽只用可追溯的公開縮圖（`https://pbs.twimg.com/`）。不要把完整影片檔放進倉庫。看過預覽幀才把 `preview_frame_reviewed` 設為 `true`。
5. 跑 `python3 scripts/render_readme.py`，再跑 `python3 scripts/validate.py`。它會核對 id、網址、去重、提示詞檔，以及 README 上的數字。要重查連結再加 `--links`。

x.com 連結必須是 `https://x.com/{handle}/status/{id}`，handle 和 id 與條目一致，而且整庫不重複。

創作者要求修改或撤下自己的作品時，請開 issue。本庫會改連結或移除條目，不會主張那些作品的著作權。
