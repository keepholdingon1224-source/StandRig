# 実験006 — 005ベイク済みモデルの標準GUI再生

2026-11-17承認に基づき実行。**既存形式による変換・標準GUI操作・保存復元・補助MP4出力は実現。006全体の最終合格は保留**。GUI直接MP4は未実装。Canvas描画には005software rendererとの画素差と三角形境界の細線があり、同等映像品質のユーザー審査が必要。許容基準は緩和していない。

- [方式・仕様調査](IMPLEMENTATION.md) / [基準ハッシュ](baseline-hashes.json) / [manifest](manifest.json)
- [入力モデル](005-baked-model.srig) / [入力モーション](005-baked-motion.json)
- GUIから実際にdownload: [モデル](gui-exported-model.srig) / [モーション](gui-exported-motion.json)
- [数値](metrics.json) / [独立検査](verification.json) / [GUI操作](gui-verification.json) / [新規service・新規data dir復元](fresh-session.json)
- [005と補助出力の左右比較](comparison-005-006.mp4) / **[005・GUI・補助出力の3列比較](comparison-005-gui-export.mp4)**
- [補助書き出しMP4](exported-loop.mp4) / [3周期](three-loops.mp4) / [GUI採取描画MP4](gui-playback.mp4)
- [実GUI画面と全240枚×2session](gui-screenshots/) / [連続再生phase記録](continuous-loop-samples.json)
- [書出し240枚](frames/) / [画素差分](differences/) / [ログ・失敗記録](logs/)

## 判定の読み方

GUI書き出しファイル→MotionController→ArtMeshの全482測定点で最大位置差約7.1e−15px。実際のブラウザ描画三角形から復元した全482点も最大約1.62e−5pxで、0.01px基準内。UV・ID・トポロジー・素材・配置・カメラを維持し、005と同定義の18数値基準に合格。髪幅・縦曲率・裾曲率・加速度・ジャークも独立検査で005と同等。詳しい値はJSONを正本とする。

同じsoftware rendererを使う補助出力240PNGは005と全枚バイト一致。Canvas GUIの240PNGは保存・再読込で全枚一致するが、005と画素一致しない。カメラ比較はcanvas CSS676×396、既存padding18、scale1、stage640×360領域を採取。透過Canvasを005既存software renderer背景#eef0f3に合成する（モデルstage宣言色とは異なる既存renderer既定色）。元のGUI全画面も保存し、正規化と区別する。

GUI playback MP4はGUIを各時刻へシークして採取した240枚の動画化であり、リアルタイム画面録画ではない。連続26秒以上/3回wrapの証拠はloop-00..25実画面とcontinuous-loop-samples.json。GUI検査はAPI成功だけでなく実ブラウザのファイル入力・ボタン・slider・checkbox・download・canvas描画で実施した。

build、公式schema/smoke16/Node183件成功、既存テストの削除・緩和なし。Linux Chromium headless、Node、Python NumPy/Pillow、FFmpegを使用。Windows実機は未実施。005以前のコード・成果物・判定記録は無変更。

## 再現手順

```sh
npm run build
node experiments/006-bake.mjs
node apps/service/dist/cli.js --data-dir "$PWD/work/006-data" --port 5180
# 別terminal（既存モデルのdata dirを使わない）
node apps/service/dist/cli.js --data-dir "$PWD/work/006-fresh-data" --port 5182
# automation依存はworkだけ。既存Chromiumを使用
npm install --cache "$PWD/work/npm-cache" --prefix "$PWD/work/browser" --no-audit --no-fund playwright
node experiments/006-gui.mjs
node experiments/006-capture.mjs
node experiments/006-fresh-session.mjs
node experiments/006-evaluate.mjs
python experiments/006-monitor-verify.py
python experiments/006-image-metrics.py
npm test
node experiments/006-verify.mjs
```

GUI automationは5182、描画採取は5180を使う。これらを同一ポートで並行実行しない。再試行時に同じモデル名でimport完了を誤検出する問題を検査コードで修正し、import buttonのbusy解除まで待つ。初回のnpm cache書込先、シーク刻み、上限丸め、未完了採取の早期検査、import待機の失敗はlogsに保持。成功結果で過去ログを上書きしない。

FFmpegの動画生成コマンドは006-evaluate.mjsとlogsに対応。3列比較は005/GUI採取MP4/補助出力をhstackする。全MP4のprobeと全フレームdecode検査を保存。

## 残件・レビュー依頼

1. 3列比較でGUI Canvasの三角形境界、輪郭・色差が許容できるかユーザー本人が判断。Codexは同等画質の合格を宣言しない。
2. GUI直接MP4ボタンは残件。今回は補助出力の成功として区別する。
3. Windows実機、全身・接続・衝突・任意素材・オンライン物理は未実施／対象外。

追加課金・有料API・SONY素材/サービス・別エンジンの使用なし。main/上流へ変更なし。

既存GUIのGPU（試験版）も単一poseで探索確認し、[画面](gui-screenshots/gpu-check.png)を保存。Canvasの境界線を避けられる可能性があるが、今回はGPUの全240枚・482サンプル・保存復元を検証しておらず、GPU品質合格の根拠にはしない。
