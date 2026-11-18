# 実験007 実キャラクターへの適用

実行日 2026-11-18（JST）。対象は画像左・右の結び目より下の毛束と、1枚のスカートメッシュの左右制御。元画像は [source_007/original.png](../../source_007/original.png)。SHA-256は承認値に一致し、1152×2048、8-bit RGB。実行元は指定ブランチの `13dc02a48f9ace0e2c657dbb751fd7ae865a9138`。

| 段階 | 結果 |
| --- | --- |
| A 自動分離 | 自動版は左側で結び目上部を取り込み、右側で根元を欠落。補助版は目視に基づく分離行を左右各1箇所使用した。独立確認済み基準マスクがないためIoUは未測定。 |
| B 補完・根元 | 補助版で実施。ブラウスを同じ行の端から補間し、スカートの隠れ部分を近傍から転写。背景は外縁の色を使用し、裾の背後に短い脚の延長を追加。Telea法とNavier–Stokes法の比較画像を保存。元画像との静止再合成差分は0ピクセル。 |
| C 変形・出力 | 補助版で005の中心線の区間長保持と空間・時間平滑化を適用。髪左右は別メッシュ。スカートの中心列は共有で、左右の位相は滑らかに混合。原寸の統合PNG240枚と評価用MP4を生成。 |
| D GUI | 006と同じ位相パラメータへのベイク方式を利用。標準GUIの操作13件を実施し、新しいブラウザ・サービスで保存ファイルの再生を確認。モデル内の物理は無効。MP4はソフトウェア補助出力。GUI直接MP4出力は残件。 |
| E 独立検証 | 保存データからメッシュ指標、モデル書き出し、動画の全フレームデコードを再検査。GUI中立姿勢には三角形境界の細線と低アルファ画素があり、補助レンダリングにも左毛束先端付近に暗い断片が残る。ユーザー視覚評価待ち。 |

## 測定値

| 部位 | 水平移動幅 | 基準寸法に対する比率 | 全辺長比 |
| --- | ---: | ---: | ---: |
| 画像左の毛束 | 83.27px | 24.14% | 0.947〜1.053 |
| 画像右の毛束 | 72.10px | 24.12% | 0.959〜1.041 |
| スカート左裾 | 約104px | 10.48% | 0.940〜1.088（連続メッシュ全体） |
| スカート右裾 | 約103px | 10.44% | 同上 |

毛束は中心線先端、裾は左右のマット内で定義した列の最下端を追跡。初回の裾測定はメッシュ下端頂点を使用した。最終評価では衣装上にある点へ置き換え、形状を変更せずに再測定した。測定点とメッシュ頂点の対応、原寸座標と換算値は [測定定義](rigging/measurement-definitions.json)、[数値](metrics.json)、[独立検査](verification.json) に収録。非表示の部位の真の形状は元絵から判定できない。

## 成果物

- [統合8秒・原寸](character-loop.mp4) ／ [24秒・3周期・原寸](three-loops.mp4)
- [A 左毛束](A-left-hair.mp4) ／ [B 右毛束](B-right-hair.mp4) ／ [C スカート](C-skirt.mp4)
- [静止再合成と動きの比較](comparison.mp4) ／ [毛束拡大](hair-closeup.mp4) ／ [裾拡大](skirt-closeup.mp4)
- [自動重畳](segmentation/overlay.png) ／ [補助版重畳](segmentation/assisted/overlay.png) ／ [根元と中央列](rigging/roots-and-controls.png)
- [参照画像マニフェスト](rigging/references/manifest.json) ／ [補完画像](reconstruction/completed-base.png) ／ [静止再合成](reconstruction/static.png) ／ [GUI中立姿勢](reconstruction/gui-neutral.png) ／ [GUI差分6倍](reconstruction/gui-difference-x6.png)
- [モデル](model/character.srig) ／ [モーション](model/character-motion.json) ／ [GUI操作検証](gui-verification.json)
- [マニフェスト](manifest.json) ／ [自動化評価](automation-report.json)

## 再現コマンド

Python 3、NumPy、SciPy、Pillow、OpenCV headless（OpenCVはApache-2.0。別のセグメンテーションモデルは不使用）、FFmpeg、Node 24.22.1、npm 11.9.0、Playwright、Linux Chromiumを使用。GUIはデータディレクトリを2個用意し、ポート5187と5188で起動する。PythonのOpenCVとPlaywrightは作業ディレクトリへ導入した。

```sh
npm ci
npm run build
npm test
python experiments/007-references.py
python experiments/007-segment.py
python experiments/007-rig.py
node experiments/007-bake.mjs
node apps/service/dist/cli.js --data-dir "$PWD/work/007-final-gui-data" --port 5187
# 別シェル
node apps/service/dist/cli.js --data-dir "$PWD/work/007-final-fresh-gui-data" --port 5188
# 別シェル。PLAYWRIGHT_ENTRY はインストール先の絶対パス
PLAYWRIGHT_ENTRY="$PWD/work/browser/node_modules/playwright/index.mjs" node experiments/007-gui.mjs
python experiments/007-verify.py
```

## 未解決

- 独立確認済みの基準マスクを用意し、分離のIoU 90%基準と基準素材版を評価する。今回の補助版のマスクは実装者が補助したもので、独立基準には使っていない。
- 左毛束先端の暗い断片、補完したブラウスの陰影と肌の接続、GUI描画のメッシュ線を確認する。ユーザー本人による視覚承認は保留。
- ChatGPTレビューでは、分離の失敗箇所、左の袖・腰への接続、裾飾りの連続性、GUI差分、次回の独立マスクの作り方を確認してほしい。
