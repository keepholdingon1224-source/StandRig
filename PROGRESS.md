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

004で003を完全再現し、髪の中心線長保持と裾の距離拘束を実装。全240枚PNG・8秒MP4/GIF・左右比較・グラフ・独立検査を保存した。公式183件と証拠整合性10項目は成功したが、髪の辺長比0.798870〜1.201133と30fps境界速度段差（髪2.947091、裾4.274729px/s）が基準未達。**004総合は不合格**。ChatGPTによる映像品質評価、Windows実機確認、新方式のGUI統合は未実施。


## 2026-11-16 / 004-deformation-constraints

1. **日時・目的:** 2026-11-16 JST（計算開始13:36 UTC以降）。003の髪1束・スカート裾1枚を保持し、中心線長保持・布距離拘束を同一条件で比較。
2. **コマンド・環境:** Linux、Node v24.22.1、npm11.9.0、ffmpeg/ffprobe、StandRig software renderer。初期 `work` / `c3166aa138f07bc289027c7a9060fc64cc0f082a`、未コミット変更なし。`git ls-remote`で指定先端 `1d37e35edd0b13b3182118d91e50dbb187194e3f` を確認し、別worktree `/workspace/standrig-004` を作成。`npm ci --cache "$PWD/work/npm-cache"`、`npm run build`、`npm test`、`node experiments/004-deformation-constraints.mjs`、`node experiments/004-verify.mjs`、`python experiments/004-plot.py`。検査コード内で003を出力先だけ変更して再実行。正式コマンドと各方式は[004報告](results/004-deformation-constraints/README.md)。
3. **変更ファイル:** `experiments/004-deformation-constraints.mjs`、`experiments/004-verify.mjs`、`experiments/004-plot.py`、`results/004-deformation-constraints/`、本書、`PROJECT.md`、実験/成果物索引、`.gitignore`（scratch work除外）。製品コード、003コード・成果物、初期チェックアウトは変更なし。
4. **成功・失敗:** npm ci/build/公式test最終exit0、schema/smoke16/Node183成功・失敗0・skip0。003の240枚PNGは再計算とバイト一致。004の482サンプル全393,312辺観測・246,784三角形観測を独立再測定し一致、全座標再生成ハッシュ一致、240枚再描画一致、動画/GIF全デコード成功、反転/縮退/根元変位/画面切れ0。生成exit0。独立検査は証拠整合性10項目成功だが**数値3項目未達によりexit1・不合格**。髪辺長比0.798870〜1.201133、髪/裾30fps境界速度差2.947091/4.274729px/s。中心線1.000000、先端範囲210.508009/67.081430px、裾辺長比0.955130〜1.052548。初回方式・依存解決・cache書込み・背景検査失敗は[報告](results/004-deformation-constraints/README.md)とattempts/logsに保存し最終成功と混同しない。
5. **成果物:** [README](results/004-deformation-constraints/README.md)、[MP4](results/004-deformation-constraints/hair-skirt-loop.mp4)、[GIF](results/004-deformation-constraints/preview.gif)、[左右比較動画](results/004-deformation-constraints/comparison.mp4)、[PNG240枚](results/004-deformation-constraints/frames/)、[グラフ](results/004-deformation-constraints/timeseries.png)、[数値](results/004-deformation-constraints/metrics.json)、[検査](results/004-deformation-constraints/verification.json)、[公式test](results/004-deformation-constraints/logs/npm-test-final.log)。ワイヤーフレーム・同時刻比較8枚・モデル/全座標・各ログはREADMEから参照。
6. **未解決:** 髪の全辺長拘束、両パーツ境界速度、裾の面積変化/通常速度変化の悪化、人の映像品質評価。身体衝突、布裏面生成、完全3D奥行き、身体接続、全身制作は対象外・未実装。新ソルバーのネイティブGUI再生への統合とWindows実機確認は未実施。追加課金・外部有料AI API・SONY素材/コード/認証の利用なし。閾値の緩和・入力振幅の削減なし。
7. **ChatGPTに評価してほしい事項:** 同時刻比較動画で髪の輪郭/横断歪み、裾プリーツ/金トリムの面積変化、境界速度の見え方を確認し、中心線と辺長の同時最適化および滑らかな布拘束の優先順位を評価してほしい。ChatGPTレビューは未実施。

GitHub反映成功: 実装・成果物コミット `62ba6adc1a9c09956d3210e5b5f6a1df8d7592b6` を指定Forkの `experiment/rigging-validation-20261115` へ通常push（exit0）。`git ls-remote` の同ブランチSHAとローカルHEADの一致を確認。初期 `work` チェックアウトは未変更・clean、003と製品ソースの差分なし。本追記は別の記録コミットとして同ブランチへ通常pushし、その最終SHAをチャットで報告する。公式/mainとFork/mainは変更していない。

## 2026-11-15T12:03:16Z / 003-secondary-loop

1. **日時・目的:** 2026-11-15 12:03～12:09 UTC。権利上問題のない髪1束・スカート裾1枚で、手作業を抑えたメッシュ・揺れ・8秒ループ生成を実行。
2. **コマンド・環境:** Linux / Node v24.22.1 / npm 11.9.0 / ローカルffmpeg・ffprobe。開始コミット `1fdcfed3d6464c82cdc9293d0702c110821d6c6e`。`node experiments/003-secondary-loop.mjs`、`node experiments/003-verify.mjs`、`npm test`。MP4生成引数は[video-command.json](results/003-secondary-loop/video-command.json)、GIF生成コマンドは[実験報告](results/003-secondary-loop/README.md)。既存ビルドを使い、npm ci/buildは今回未実行。StandRig coreの実物理・メッシュ評価・サーバー描画を使い、今回MCPやブラウザGUIは未実行。
3. **変更ファイル:** `experiments/003-secondary-loop.mjs`、`experiments/003-verify.mjs`、`results/003-secondary-loop/`（コード保存版・素材2枚・モデル2種・モーション・全240枚PNG・MP4/GIF・比較画像・失敗記録・検査ログ）、`PROGRESS.md`、`experiments/README.md`、`results/README.md`。製品コードは変更しない。
4. **成功・失敗:** 最終runは生成時9項目・独立検査14項目成功。npm testはschema/smoke16/Node183件成功、失敗0・skip0。根元移動0・三角形反転0・端の画面切れ0・空画像0。0秒と8秒のPNG差0、同位相位置差7.65e-14px。MP4は8秒・30fps・240枚、全デコード成功。初回は子プロセスEPERM、pivotによる画面切れ、速度測定方法の誤りがあり、成功扱いせず[失敗記録](results/003-secondary-loop/attempts/first-run.log)と[初回画像](results/003-secondary-loop/attempts/first-contact-sheet.png)を保存。測定は閾値を変えず修正し、ベイク境界の速度変化1.472px/sも別途記録。
5. **成果物:** [成果物と技術報告](results/003-secondary-loop/README.md)、[MP4](results/003-secondary-loop/hair-skirt-loop.mp4)、[GIF](results/003-secondary-loop/preview.gif)、[PNG](results/003-secondary-loop/frames/)、[数値](results/003-secondary-loop/metrics.json)、[独立検査](results/003-secondary-loop/verification.json)、[公式テスト](results/003-secondary-loop/npm-test.log)。すべてオリジナル合成fixture。作業用モデルディレクトリ・認証情報・他プロジェクトの素材は含めない。
6. **未解決:** 辺長比0.7496～1.2294の伸縮、通常のベイクキーで最大60.103px/sの速度変化、広い髪振幅、身体への接続・衝突・布面拘束・奥行き・実キャラクターの自然さ。ループは24秒の事前計算を必要とする。自動化したのは既知の役割・上下方向に基づく手順で、任意画像からのAI推定ではない。頂点手編集・手描き・キーフレーム手付けは0回だが、Codexによるアルゴリズム・定数設計、pivot修正、検査修正は必要だった。
7. **ChatGPTに評価してほしい事項:** 動画の髪と裾の自然さ・変形の違和感、伸縮と速度変化の許容基準、中心線の長さ保持と布面拘束のどちらを次に実装すべきか、頭皮／腰の固定素材と自由形状の根元推定をどう段階化するか。レビューは未実施。

公開先は指定Forkの同じ実験ブランチ。コミット・push後にリモートSHAを確認し最終ハンドオフで報告する。追加課金・購入なし、SONY共同プロジェクトへのアクセスなし、公式mainへの変更なし。

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
