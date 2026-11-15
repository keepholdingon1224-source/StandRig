# StandRig 検証プロジェクトの進捗

## 共同作業の入口

目的: AIによる2Dキャラクターの自動リギングの実用性を評価し、髪・スカート・リボンの高品質な二次動作の自動制作へ進める。

- Codex: 実装、実行、テスト、証拠保存、進捗更新。
- ChatGPT: GitHub上の記録・画像・ログを確認し、技術評価と次の実験計画を記録する。レビューは未実施なら未実施とする。
- [research/](research/README.md): 技術調査・評価。[experiments/](experiments/README.md): 実験コード。[results/](results/README.md): 成果物索引・新規成果物。
- 追加課金・購入なし。SONY共同プロジェクトのコード・素材・認証・サービスを使用しない。実験用ブランチで作業し、上流mainを変更しない。
- 作業先: https://github.com/keepholdingon1224-source/StandRig （origin）。公式リポジトリはupstreamとして参照のみ。実験ブランチ: `experiment/rigging-validation-20261115`。
- 各作業の最後に下記7項目を追記し、証拠と同じコミットに含める。成功／失敗／環境による阻害／未実行を区別する。

## 現在の判断

第一段階は図形サンプルでMCP編集・曲げ・描画・復元を確認済み。高品質キャラクターの自動制作は未実証。次は同一姿勢のRenderer比較と、権利処理済みの髪1束・リボン1本・スカート1枚の小規模評価が候補。ChatGPTによる計画のレビューは未実施。

## 2026-11-15 / 001-baseline（既存記録の要約）

1. **日時・目的:** 2026-11-15 UTC（元記録に開始・終了の厳密な時刻なし）。2Dリギング基盤の実動作を確認。
2. **コマンド・環境:** Linux、Node v24.22.1、npm 11.9.0、Chromium headless。`npm ci`、`npm run build`、`npm test`、`KEEP_SERVICE=1 node validation/probe.mjs`、`node validation/browser.mjs`。詳細は[技術報告](validation/REPORT.ja.md)。
3. **変更ファイル:** 記録コミット `6b9b588` の `validation/`（スクリプト2本、報告、ログ、PNG、JSON等）。製品ソースの変更なし。
4. **成功・失敗:** 最終runでschema、smoke16、Node183件成功・失敗0・skip0。MCP/曲げ/描画/復元成功。途中のネットワーク・listen制限、依存不足の失敗は別記録。実キャラ評価は未実行。
5. **成果物:** [成果物一覧](results/001-baseline/README.md)。元データは `validation/artifacts/`。
6. **未解決:** Canvasの三角形境界線、素材解像度の段差、身体・布の衝突、実キャラに対する自動拘束・ウェイト・キーフォーム設計、長時間の自然な揺れ。
7. **ChatGPTに評価してほしい事項:** 図形検証から言える実用範囲／限界、Canvas品質課題の優先度、実キャラ検証に先行する最小部位実験とその合格基準。

## 2026-11-15T07:22:59Z / 002-collaboration-layout

1. **日時・目的:** 上記UTC時刻に共有構成整備を開始。CodexとChatGPTがGitHubの同じ証拠を参照できる入口と記録規則を作成。
2. **コマンド・環境:** 同じLinuxワークスペース。`git status --short`、`git branch --show-current`、`git remote -v`、`git log -2`、`date -u`、`gh auth status`、GitHub接続アカウント・リポジトリ権限確認。編集後の検査コマンドと公開結果は後述。
3. **変更ファイル:** `AGENTS.md`、`PROGRESS.md`、`research/README.md`、`research/REVIEW_TEMPLATE.md`、`experiments/README.md`、`experiments/run-baseline.mjs`、`results/README.md`、`results/001-baseline/README.md`。元の `validation/` と製品コードは保持。
4. **成功・失敗:** 第一段階の183件成功は過去runの記録であり、今回再実行した結果ではない。今回は文書リンク・記録構成・追加入口の構文を確認する。製品ビルド・テスト・MCP・描画の再実行は未実施。
5. **成果物:** 上記共有ドキュメントと成果物索引。今回新しい画像・動画は生成しない。
6. **未解決:** 公式には書き込み権限なし。ユーザーが指定したFork `keepholdingon1224-source/StandRig` は公式のForkで `push:true` と確認でき、反映先の問題は解消。GitHub上の最終反映確認を残す。技術上の未解決課題は001-baselineから継続。
7. **ChatGPTに評価してほしい事項:** 001-baselineの証拠を読み、次の実験をRenderer同一姿勢比較と最小部位の二次動作のどちらから進めるか、合格条件と必要な素材を提案してほしい。[評価テンプレート](research/REVIEW_TEMPLATE.md)を使用する。

### 検査・GitHub反映

2026-11-15 UTC: `node --check experiments/run-baseline.mjs` と `git diff --check` はexit 0。Pythonで新規Markdown6ファイルのローカル相対リンク34件と、2つの実施記録それぞれの必須7項目、既存比較PNGの存在を検査し成功。製品コード・元の検証コード・成果物は変更していないため、npmの再導入・製品ビルド・183件の再実行は行っていない。

`gh auth status` は制限内では認証失敗と表示されたが、ネットワーク許可後は接続アカウントの認証成功を確認。GitHub APIでForkの親が `sayaka-aiart/StandRig` であること、作業先にpush権限があることを確認した。

ユーザーの反映先指定に従い `git remote rename origin upstream`、`git remote add origin https://github.com/keepholdingon1224-source/StandRig.git` を実行。新規実験ブランチへ通常のpushを行い、`git ls-remote origin refs/heads/experiment/rigging-validation-20261115` とローカルHEADの一致で確認する。公式へのpush、mainの変更、force pushは行わない。公開検証の結果と最終コミットIDはハンドオフに記載する。

今回の成果物索引: [002-collaboration-layout](results/002-collaboration-layout/README.md)。この追加後にもリンク検査を実施する。

最終ローカル検査: Markdown7ファイル・相対リンク44件がすべて存在、2記録それぞれの7項目を確認し成功。`node --check`、`git diff --check`、`git diff --cached --check` はexit 0。既存の製品コードと `validation/` の変更なしを確認。

GitHub反映成功: 共有構成コミット `d58d6e8e4ad6ee63b15d623c48b14d9777213b23` を `git -c credential.helper='!gh auth git-credential' push -u origin experiment/rigging-validation-20261115` でユーザーのForkへpush（exit 0）。`git ls-remote origin refs/heads/experiment/rigging-validation-20261115` のSHAが一致。過去の検証コミット `6b9b588` の画像・ログも同じブランチの履歴に含まれる。この結果の追記は別コミットで通常pushし、最終SHAをハンドオフで示す。公式とmainは変更していない。

## 次回記録テンプレート

### YYYY-MM-DDTHH:MM:SSZ / 実験ID

1. **日時・目的:**
2. **コマンド・環境:** OS、Node/npm、描画環境、対象コミット、実行場所と実際のコマンド。
3. **変更ファイル:**
4. **成功・失敗:** 実行結果・exit code・ログ。未実行・失敗・skip・環境制約を明示。
5. **成果物:** 画像・動画・ログ・設定へのリポジトリ内相対リンク。
6. **未解決:**
7. **ChatGPTに評価してほしい事項:**

GitHub反映: リポジトリURL、ブランチ、対象コミット、確認方法。コミット自身のIDは本文に自己参照で埋めず、Git履歴とハンドオフで示す。
