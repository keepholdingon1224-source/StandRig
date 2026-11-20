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

**最新判定（2026-11-20）: 005・006の正式合格を維持。007は実行完了、補助版の数値・GUI検査成功、完全自動分離不合格、独立IoU未測定。ユーザー視覚評価「良さそうに見える」（MUSE中継）。ChatGPTは補助版の範囲限定合格を提案、正式承認待ち。008は分離精度改善を提案、未承認・未開始。GUI直接MP4・Windows実機は残件。**


004で003を完全再現し、髪の中心線長保持と裾の距離拘束を実装。全240枚PNG・8秒MP4/GIF・左右比較・グラフ・独立検査を保存した。公式183件と証拠整合性10項目は成功したが、髪の辺長比0.798870〜1.201133と30fps境界速度段差（髪2.947091、裾4.274729px/s）が基準未達。**004総合は不合格**。ChatGPTによる映像品質評価、Windows実機確認、新方式のGUI統合は未実施。


## 2026-11-17 / 005-final-acceptance（ChatGPT判定・ユーザー視覚承認）

- **総合合格（合成素材を用いた8秒オフライン動画の範囲）**。独立検査の証拠整合性・数値18項目すべて合格。ユーザー本人が003/004/005比較、005三連ループ、005統合動画を視聴し「合格」と判定したことをMUSEが中継。ChatGPTは数値記録を照合し総合合格を確定。ChatGPT自身による動画直接再生ではない。
- [正式合格記録と根拠](results/005-spatiotemporal-constraints/FINAL-ACCEPTANCE.md)。005の元成果物・検査ログは変更なし。既存005実行ログの「視覚評価待ち」は実行時点の履歴として保存し、本節が最新判定を示す。
- **残件**：髪幅保持（最大約9.8%縮み）・縦曲率悪化、裾辺長比の小幅悪化、GUI未統合。任意素材自動リギングや全身制作は未検証。
- **次段階は提案のみ**：006としてGUI統合可否の小規模検証を優先候補とする。ユーザーの次段階承認まで実装・実験は開始しない。SONY分離と追加課金なしを維持。

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


## 2026-11-16T21:45:37Z / 005-spatiotemporal-constraints（2026-11-17 JST）

1. **日時・目的:** ユーザー2026-11-17実行承認に基づき、004の髪全辺長・裾の柔らかさ・ループ速度を改善。004視覚評価「いいよ」、追加要望「スカートの波打ちを柔らかくしてくれてもいいかも」を暫定承認として記録し、004数値・総合不合格は維持。
2. **コマンド・環境:** 初期`work`/`c3166aa`、作業ツリーclean。GitHub指定ブランチ先端`15020757c16e8652cc356ccbab057719b2259b0c`を確認・取得し、同ブランチへfast-forward。Linux/Node/Python NumPy・SciPy・Matplotlib・Pillow、既存ローカルffmpeg。`npm run build`、`node experiments/005-prepare.mjs`、`OPENBLAS_NUM_THREADS=1 python experiments/005-solve.py`、`node experiments/005-spatiotemporal-constraints.mjs`、`MPLCONFIGDIR=$PWD/work/mpl python experiments/005-plot.py`、`npm test`、`node experiments/005-verify.mjs`。独立検査が補助指標/物理状態検査も実行。詳細環境は[manifest](results/005-spatiotemporal-constraints/manifest.json)。
3. **変更ファイル:** `experiments/005-*`7本、`results/005-spatiotemporal-constraints/`、本書、PROJECT.md、実験/成果物索引。003/004のコード・成果物・ログおよび製品ソースは無変更。main/原作者/SONYプロジェクトへの変更なし。
4. **成功・失敗:** build exit0、公式schema/smoke16/Node183成功・失敗0/skip0。最終独立20項目成功・数値18チェック成功（exit0）。全482座標再生成一致、003の240PNG再計算一致、004の全座標/240PNG再描画一致、005の240PNG再描画一致。全動画/GIFを全デコード、8秒30fps240枚、3回再生版24秒720枚を確認。髪辺比0.901536〜1.098376、中心線1.000000〜1.019090、範囲147.977665px。裾辺比0.947091〜1.058099、範囲66.800470px。境界速度差1.419529/0.750531px/s、根元・反転/縮退・ループ位置・同位相60Hzメッシュ速度差0。実60Hz振り子状態も元トレースと再現一致。**数値合格、005ユーザー視覚評価待ち、総合未合格**。失敗151px試行・平滑化候補・初回検査ハッシュ不一致を保存し、修正前を成功扱いしない。
5. **成果物:** [005報告](results/005-spatiotemporal-constraints/README.md)、[MP4](results/005-spatiotemporal-constraints/hair-skirt-loop.mp4)、[GIF](results/005-spatiotemporal-constraints/preview.gif)、[240PNG](results/005-spatiotemporal-constraints/frames/)、[003/004/005比較](results/005-spatiotemporal-constraints/comparison-003-004-005.mp4)、[A/B/C/D](results/005-spatiotemporal-constraints/comparison-A-B-C-D.mp4)、[裾拡大比較](results/005-spatiotemporal-constraints/hem-closeup-004-005.mp4)、[数値](results/005-spatiotemporal-constraints/metrics.json)、[独立検査](results/005-spatiotemporal-constraints/verification.json)。グラフ・最悪時刻画像・コード・失敗・ログは報告から参照。
6. **未解決:** 髪幅は最大約9.8%縮小し縦方向曲率が004より悪化。髪可動範囲は004より約29.7%減（指定147pxを維持）。裾辺長比は少し悪化するが許容内。裾平滑化は全周期のオフライン正則化で、時間積分XPBD・新たな裾方向物理波伝播は未実装。新方式のネイティブGUI統合・Windows実機・身体衝突・全身制作は未実施。視覚的柔らかさは数値だけでは判定せずユーザー審査待ち。追加課金/有料API/別エンジン移行なし。
7. **ChatGPTに評価してほしい事項:** 004/005裾比較の滑らかさ、揺れ戻し、プリーツ/金トリム、ループの見え方。髪の幅・曲率の悪化と振幅のトレードオフ。Codex静止比較は参考で、005のユーザー視覚承認は未取得。

GitHub反映：成果物コミット `cd28e402942a3dfbaf8e515651e4ca1f6d165aa9` を指定Forkの同ブランチへ通常push（exit0）。公開時の確認でルートの `*.log` 除外を検出したため、005内だけの例外を追加し、公式/独立/失敗ログもGitHubへ保存する追記コミットを通常pushする。003/004・製品コードの差分なし。最終コミットIDとリモート一致はチャットで報告する。

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

## 2026-11-17T05:51:03Z / 006-gui-playback（2026-11-17 JST承認済み実行）

1. **日時・目的:** 2026-11-17 JST、ユーザー最終指示に基づき005の動き・素材を維持して標準GUIへ移行。開始時work/c3166aa clean。指定リモート最新9b8b4caをls-remote/fetchで確認しSHA明示で実験ブランチへ移動。005正式合格記録と指定248ファイル（240PNG+8基準）をSHA-256固定。
2. **環境・コマンド:** Linux、Node、既存Chromium headless、Playwright（work配下のみ）、Python NumPy/Pillow、FFmpeg。`npm run build`、`npm test`、`node experiments/006-bake.mjs`、専用service `--data-dir work/006-data --port 5180` と `work/006-fresh-data --port 5182`、006-gui/capture/fresh-session/evaluate/verify、006-monitor-verify.py/image-metrics.py。詳細コマンドと失敗は[README](results/006-gui-playback/README.md)と[logs](results/006-gui-playback/logs/)。
3. **変更:** experiments/006-*、results/006-gui-playback/、PROJECT.md、本書。既存Core/Runtime/Preview/Serviceソース・005以前のコード・成果物・合格記録は変更なし。単一位相parameter＋既存ArtMesh482キー、8秒1track/2keys。旧物理をモデル内で無効化。adapter/solver再実行/新schema不要。
4. **成功:** build、公式schema/smoke16/Node183全件成功（fail/skip0）。GUI import/play/pause/resume/stop/seek/loop on-off・26秒以上/3wrap・portable/motion download・新session再importを実操作。新service/新data dir復元も成功。GUI出力ファイルから評価した全482サンプル最大差7.1e−15px、実GUI描画行列からの差約1.62e−5px。18数値基準と幅/曲率/加速度/ジャーク監視を維持。software出力240PNGは005と全枚バイト一致。保存前後のGUI240PNGも全枚一致。MP4は8秒/640x360/30fps/240枚、3周期720枚/24秒、全decode。基準ハッシュ一致。
5. **失敗・再試行:** npmの既定cache先権限→work cacheへ変更。HTML rangeの0.01秒丸め→精密計測時だけstep any。追加sample上限のHTML数値文字列丸めが値域拒否→1e−12秒内側を実入力、誤差実測。採取完了前の独立検査→完了後再実行。同じmodel名でimport完了誤認→busy解除を待機。全失敗ログ保持。GUI/Canvasの画素差・三角形境界細線は残存し、数値誤差とは区別する。
6. **成果物:** [006報告](results/006-gui-playback/README.md)、[3列比較](results/006-gui-playback/comparison-005-gui-export.mp4)、[補助出力](results/006-gui-playback/exported-loop.mp4)、[GUI描画](results/006-gui-playback/gui-playback.mp4)、[3周期](results/006-gui-playback/three-loops.mp4)、[独立検査](results/006-gui-playback/verification.json)、[GUI操作](results/006-gui-playback/gui-verification.json)、[差分](results/006-gui-playback/differences/)。全入力/出力hashはmanifest。
7. **判定・未解決・ChatGPTレビュー依頼:** 数値・GUI操作・保存復元・補助動画検査成功。**006全体の最終合格は保留**。標準Canvasにはsoftware rendererとの差があるため、比較動画でユーザー本人の同等品質判断が必要。GUI直接MP4は未実装で残件。GPU描画は単一poseの探索確認のみ（全面検査済みとはしない）。Windows実機・全身・衝突・オンライン物理は未実施。追加課金/有料API/SONY関与なし。指定Fork実験ブランチへ通常commit/pushし、リモートSHAを照合する。main/上流への変更なし。


## 2026-11-18 / 006-final-acceptance（ChatGPT判定・ユーザー視覚承認）

- **006総合合格（対象範囲限定）**。ユーザー本人は比較動画 comparison-005-gui-export.mp4 を目視し「合格とします」と判定、Canvas三角形境界・輪郭・色差を許容。MUSE中継の承認とChatGPTによるGitHub検証記録の照合に基づく。
- 独立検査18/18、数値基準18/18、GUI操作13/13、公式Node183件成功。全482サンプルでCore最大差約7.1e-15px、GUI最大差約1.62e-5px。補助software出力240PNGは005と全枚一致、GUI再読み込み前後も全枚一致、005基準ハッシュ一致。
- [正式合格記録](results/006-gui-playback/FINAL-ACCEPTANCE.md)。元の006実行報告と検査JSONの保留表記は実行時点の履歴として保存する。本節が最新判定。005と006の既存成果物・検査ログは変更しない。
- **合格範囲・残件**：標準GUIのベイク済み再生、保存復元、補助MP4出力。GUI直接MP4未実装、Windows実機未確認、GPU全周期未検証。005の髪幅・縦曲率・裾辺長比は監視継続。
- **007は提案のみ・未開始**：実キャラクター画像への段階的適用を第一候補、実素材上の品質改善を第二候補とする。素材の権利・公開可否、対象範囲と進行はユーザー判断待ち。SONY完全分離・追加課金なし。

## 2026-11-18 JST / 007-character-application

1. **日時・目的**。MUSE経由の最終承認後、指定Forkの `experiment/rigging-validation-20261115` を別ディレクトリへ取得。基準 `13dc02a48f9ace0e2c657dbb751fd7ae865a9138`、開始時clean。入力PNGのSHA-256は承認値と同一。
2. **環境・実行**。Linux、Node 24.22.1/npm 11.9.0、Python/NumPy/SciPy/Pillow/OpenCV、FFmpeg、Chromium。公式 `npm run build`、schema/smoke 16件および `npm test` のNode 183件が成功。007-reference、segment、rig、bake、GUI、verifyのコマンドは[実験報告](results/007-character-application/README.md)参照。005・006コードと成果物1,643ファイルのSHA-256照合に成功。
3. **変更**。`experiments/007-*`、`results/007-character-application/`、`PROGRESS.md`、`PROJECT.md`。
4. **A〜E**。A自動版は左結び目上の混入と右根元の欠落。左右各1行の指定を使用した補助版でBとCを実施。最初のスカート辺長比上限1.108を位相調整で1.088へ改善。DはGUI操作13件成功。Eは保存データを独立検査し、数値・操作検査に成功。IoUと基準素材版は独立確認済みマスク未入手のため未実施。視覚合格は保留。
5. **成果物**。[統合8秒](results/007-character-application/character-loop.mp4)、[3周期24秒](results/007-character-application/three-loops.mp4)、[独立検査](results/007-character-application/verification.json)、[GUI操作](results/007-character-application/gui-verification.json)、[全成果物索引](results/007-character-application/README.md)。
6. **未解決**。左毛束先端周辺の暗い断片、ブラウスの色補間、GUI中立姿勢の三角形境界と低アルファ画素、独立マスクと視覚承認。GUI直接MP4出力は継続残件。追加課金・外部有料API・SONY関連素材の利用なし。
7. **ChatGPTレビュー依頼**。左の袖・腰の補完、左右の根元と裾の境界、GUI描画差分とユーザー確認用の観点、独立マスク検証の設計を確認してほしい。


## 2026-11-20 / 007レビュー・008提案（ChatGPT）

- [007報告](results/007-character-application/README.md)、[独立検査](results/007-character-application/verification.json)、[自動化評価](results/007-character-application/automation-report.json)、`experiments/007-segment.py` を照合。補助版の数値・操作検査成功、左右根元の手動分離行538/452、裾位相の個別調整あり。完全自動分離は失敗、独立IoU未測定。ユーザーの「良さそうに見える」は肯定的視覚評価として記録し、明示的な正式合格承認とは区別する。
- 補助版限定合格を推奨。左毛束先端の暗い断片、左袖・腰の補完、GUI三角形境界と低アルファ画素は残件。ChatGPT自身は動画を直接再生していない。
- 008案：独立した可視領域マスクを先に固定し、007自動版・改善した局所輪郭/根元推定・反転推論・形状位置合わせによる反対側の構造事前情報を比較。左右非対称を維持し、隠れ領域の推測を可視IoUに混ぜない。各可動部位IoU 0.90以上を維持。追加の未使用素材による汎用性検査を推奨。005〜007の既存成果物は保護。008は承認前に開始しない。
