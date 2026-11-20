# AI Live2D自動制作研究｜実験008 パーツ分離精度改善

2026-11-20 JSTに実行。**完全自動分離は素材1・素材2とも不合格。** 採用候補のBは素材1でスカートだけが合格し、素材2では3部位とも未達だった。正式合格には、独立基準マスクv4に対する両素材・3部位の全6項目で個別にIoU 0.90以上が必要。uncertainを含む全画素で測定した。

## 正式IoU

左右は画像を見る側。太字は0.90以上。丸め前の値で判定した。

| 方式 | 素材1 左毛束 | 素材1 右毛束 | 素材1 スカート | 素材2 左毛束 | 素材2 右毛束 | 素材2 スカート |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 007自動・無改変 | 0.779636 | 0.874592 | **0.986948** | 0.000000 | 0.000000 | 0.000000 |
| A 007既存補助 | **0.909590** | **0.928652** | **0.984607** | 未実施 | 未実施 | 未実施 |
| B 画像処理・素材2適用方式 | 0.882712 | 0.859678 | **0.992826** | 0.010460 | 0.165496 | 0.876402 |
| C MobileSAM | 0.534941 | **0.912921** | **0.987086** | 0.041532 | 0.190732 | **0.970314** |
| D 反転再推論 | 0.822514 | 0.897912 | **0.988020** | 0.038483 | 0.193606 | **0.971070** |
| E 反転＋ミラー形状参照 | 0.797979 | 0.897175 | **0.988020** | 0.038906 | 0.194886 | **0.971070** |

- **A**は007のスクリプトを一時ディレクトリで無改変実行。素材2では原画のSHA-256固定アサーションで停止し、中間マスクも生成されなかった。正式点は空だった3部位を各0として集計した。素材1の既存補助版は根元の手指定2件を含み、隠れスカートを含む既存マスクに4,647画素の重複がある。[素材2停止箇所](logs/asset-02-A-007-auto-stderr.txt)
- **B**は画像の余白から背景を見積もり、対象シルエット上端と下半身中央からLabの色分布を推定する。連結成分の行幅の収束から根元を推定し、GrabCutで局所境界を調整して近傍の暗い輪郭を回収した。素材1の最低IoUは0.859678で、最終比較中の自動方式で最高。素材2では予測した左毛束が先端付近に限られ、根元誤差692.26px、右毛束は巻いた下部を主に抽出し、根元誤差274.19pxだった。銀髪を局所色分布と一続きの連結成分で捉える処理が大きく欠落した。B〜Eの最終出力で主要5分類の重複・未分類は0。[B素材1重畳](overlays/asset-01/B-opencv.png)・[B素材2重畳](overlays/asset-02/B-opencv.png)
- **C**はBから矩形・前景点を自動生成し、MobileSAMの提案をモデルスコアとBとの重なりで選んだ。B比で素材1右毛束は+0.053244、左毛束は−0.347771。素材2スカートは+0.093911で合格した。素材1左毛束の候補は固定部位への過抽出が13,844画素あり、素材2左右毛束は再現率が0.042、0.192にとどまった。SAM、SAM 2、アニメ向け前景抽出モデルを比較候補とし、CPUで実行できるMobileSAM TinyViTを採用。モデルの重み・ライセンス・取得先・実測時間とメモリを保存した。[モデル選択](model-selection.json)・[実測](method-comparison.csv)
- **D**は反転画像から候補検出とAI推論をやり直し、予測を逆反転して左右ラベルを交換した。一致領域とBの近傍にある不一致領域を統合。C比で素材1左毛束+0.287573、右毛束−0.015010。素材2はスカート+0.000756で、左毛束−0.003049、右毛束+0.002874。[素材1反転出力](predictions/asset-01/D-tta/)・[素材2反転出力](predictions/asset-02/D-tta/)
- **E**は左右別に推定した根元、先端、中心線に沿って毛束幅を相対深度で対応付けた。候補をその側の中心線と不一致領域に限定し、幅の整合度が低い場合は適用を控える。D比で素材1左毛束−0.024535、右毛束−0.000737。素材2は微増（左+0.000423、右+0.001280）で依然未達。毛束の試行結果から本採用を見送った。袖・腰・スカート外周・裾飾りの対応推定、および結び目構造の独立した対応評価は未実施。[ミラー記録](predictions/asset-01/E-mirror/run.json)
- 素材1の最初のB〜Eと、根元の幅の収束を利用した改訂版の両方を保存。素材1で全候補を比較し、3部位の最低IoUを優先してBと共通設定を `c0ea3bba6421fe6a7d98546b64cd7dd5493f9d44` に記録。そのコミットで素材2を一度だけ処理した。素材2の事前アクセスは固定基準の技術検査に限定し、視認・方式選択・パラメータ調整は素材2初回推論前に行っていない。両素材は公開リポジトリに存在するため、公開素材を用いた工程分離による適用検査である。[初回適用記録](generalization-report.json)・[初回試行](logs/trial-01/)

## 基準マスクと独立検査

両原画とマスク16枚は固定記録のSHA-256と一致した。各素材の既存 `verify-reference.py` を一時コピーに対して実行し、1152×2048、8bitグレースケール、画素値0/255、重複・未分類ゼロ、補助マスクの部分集合条件を確認した。PNGのビット深度と色タイプは追加でIHDRを直接検査した。正式IoUをNumPyの集合演算で算出し、Pillowの濃淡演算とヒストグラムでも全45値が一致した。

固定記録に記載されている両素材の `manifest.json` と `annotation-notes.md` のSHA-256は、各v3文書に対応している。現在の4ファイルはv4固定元・承認コミットとバイト一致する。基準マスクのPNGと原画は技術検査に合格し、文書索引の照合は4件不一致として保存した。基準ディレクトリは書き換えていない。実験前後で005〜007のコード・成果物・承認記録、両原画、基準ディレクトリを含む2,054ファイルのSHA-256はすべて一致した。[固定記録](reference/REVIEW-AND-FREEZE.md)・[独立検査](verification.json)・[不一致4件の照合](logs/reference-document-discrepancies.json)

根元近傍IoUは評価開始前に半径32pxの基準根元中心の円と定義。予測根元は各毛束マスクの最上行のx中央値。境界F1は4近傍で侵食した内側輪郭と元マスクの差を境界に使用し、相互のユークリッド距離1・2・4pxで測定した。補助分類は裾飾り包含率やブラウス巻き込みの診断に使った。実行時間は各方式の測定範囲をrun.jsonに記録し、ピークRSSはプロセスの高水位を示す。Cはモデル読み込みを含み、DとEはCからの累積。測定の詳細は[metrics.json](metrics.json)。

## 補完・変形・GUI

| 検査 | 判定 |
| --- | --- |
| 素材1の完全自動分離 | 不合格 |
| 素材2の完全自動分離 | 不合格 |
| AI分離の改善 | 部位ごとに改善と悪化。採用せず |
| 反転推論の改善 | 左右で改善と悪化。採用せず |
| ミラー形状参照の改善 | 素材1で悪化、素材2の改善は小幅。採用せず |
| 008隠れ領域補完・生成比較 | 正式分離未達のため未実施 |
| 008自動リギング・変形 | 正式分離未達のため未実施 |
| 008モデルのStandRig標準GUI接続 | 未実施 |
| ユーザーによる008映像品質承認 | 未実施 |

007補助版の既存成果物を別ディレクトリに複製し、標準GUIで読み込み・再生・一時停止・停止・シーク・3周期ループ・書き出し・新規セッションでの再読み込みを再実行して13項目合格。独立変形検査も合格し、全辺長比は左0.946779〜1.053221、右0.959169〜1.040831、スカート0.939652〜1.088075。髪の中心線長比は両側とも約1.0、可動範囲は左24.14%、右24.12%、左右裾10.48%・10.44%、三角形反転・縮退0。髪240px・スカート200px換算で、最大根元変位は0.000000270px、位置・60Hz同位相速度差は0、30fps最大速度段差0.316393px/s。上記の元画像座標の対応最大値は0.000000335px、0、0、0.849720px/s。既存MP4全8本は全フレームデコードに成功。008の補完、リギングおよび007左毛束先端の暗い断片の新規映像確認は未実施。008の比較用MP4は可視分離診断であり、GUI直接出力・ベイクしたキャラクターアニメーションは含まない。[007回帰検査](logs/regression-007-verification.json)・[GUI操作](gui-screenshots/regression-007/)・[008診断動画の全フレーム検査](logs/diagnostic-video-decode.json)

## 成果物

| 内容 | ファイル |
| --- | --- |
| 条件・環境・実行順 | [manifest.json](manifest.json) |
| 部位別測定と方式比較 | [metrics.json](metrics.json)・[method-comparison.csv](method-comparison.csv)・[automation-report.json](automation-report.json) |
| 初回適用とモデル固定 | [generalization-report.json](generalization-report.json)・[model-selection.json](model-selection.json) |
| マスク・重畳・差分・根元と中心線 | [predictions](predictions/)・[overlays](overlays/)・[errors](errors/)・[landmarks](landmarks/) |
| 分離の比較診断 | [素材1](videos/asset-01-comparison.mp4)・[素材2](videos/asset-02-comparison.mp4)・[素材1根元拡大](videos/asset-01-roots-closeup.mp4)・[素材2根元拡大](videos/asset-02-roots-closeup.mp4)・[3周期版](videos/) |
| 生成工程の実施状態 | [completion](completion/)・[model](model/) |
| 独立・回帰検査 | [verification.json](verification.json)・[logs](logs/) |

## 再現コマンド

Linux x86_64、Python 3.12.14、Node v24.22.1、npm 11.9.0、Chromium、FFmpeg。OpenCV 5.1.0.95、NumPy 2.5.5、SciPy 1.18.1、Pillow 13.0.0、PyTorch 2.15.0+cpu、torchvision 0.29.2+cpu、timm 0.9.16。完全なPython環境は [logs/python-packages.txt](logs/python-packages.txt)。MobileSAMは別作業領域にクローンし、[指定コミット](https://github.com/ChaoningZhang/MobileSAM/tree/f706ad9c4eb7f219c00d9050e46328518ffb65d2) をチェックアウトする。モデル重みは取得元に配置され、StandRigへ同梱していない。

以下の `r` は成果物ディレクトリ、`mobile_sam` はピン留め済みモデルの作業パス。記録済み初回成果物の再現時は別チェックアウトと別出力先を使用する。素材1の試行履歴は上記の初回試行に保存。

```bash
r=results/008-segmentation-accuracy
mobile_sam=/path/to/pinned/MobileSAM
npm ci
npm run build
npm test
python experiments/008-verify-reference.py "$r/logs/reference-before.json"
# 上の検査は文書索引の既知の4件不一致を含めて非ゼロ終了する。
python experiments/008-baseline.py source_007/original.png "$r/predictions/asset-01"
python experiments/008-segment.py source_007/original.png "$r/predictions/asset-01" --mobile-sam "$mobile_sam"
python experiments/008-evaluate.py source_007/original.png "$r/reference/asset-01" "$r/predictions/asset-01" "$r"
# 素材1の方式をコミットし、固定SHAを記録してから素材2を実行
python experiments/008-segment.py source_008/original.png "$r/predictions/asset-02" --mobile-sam "$mobile_sam"
python experiments/008-baseline.py source_008/original.png "$r/predictions/asset-02"
python experiments/008-evaluate.py source_008/original.png "$r/reference/asset-02" "$r/predictions/asset-02" "$r"
python experiments/008-comparison-video.py "$r"
python experiments/008-verify-reference.py "$r/logs/reference-after.json"
python experiments/008-report.py
```

007の回帰検査はNode/Python依存を共有し、書き込みを伴う007成果物は複製して実行した。標準GUIの独立した2サービスは5187/5188で起動し、元の `007-gui.mjs` と `007-verify.py` を使用。手順は[007の再現記録](../007-character-application/README.md)。
