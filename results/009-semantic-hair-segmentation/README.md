# 実験009 意味認識による毛束分離

2026-11-20 JSTに開始。基準マスクv4の独立照合、008のMobileSAM要因診断、保存済み結果の再評価、005〜007の回帰を実施した。その後、009-AでA3改変構成を確立し、009-Bで両素材を評価した。手動介入0回、全6項目中2項目がIoU 0.90以上。[009-B正式結果](009-B/README.md)。

## A 008失敗原因の切り分け

008のMobileSAM重みをピン留めしたコミットから取得し、SHA-256を確認した。元の008パイプラインを再実行し、保存済みの毛束4件と素材2スカートのIoUが一致した。素材1スカートの差は −0.00000233。診断では各素材に同じ条件を使用した。

| 素材 | 008 C再実行 左 / 右 / 裙 | 基準由来プロンプトの部位別最大 左 / 右 / 裙 |
|---|---|---|
| 1 | 0.53494 / 0.91292 / 0.98708 | 0.89151 / 0.93398 / 0.98821 |
| 2 | 0.04153 / 0.19073 / 0.97031 | 0.87823 / 0.81925 / 0.97100 |

部位別最大は複数の診断条件の集計。基準由来の点・矩形は診断専用プロセスに限定した。

- **入力**。素材2左では008点を維持し、基準由来の矩形を使うと、SAM信頼度選択・上側切断なしの条件でIoUが0.05408から0.87823へ上昇。素材2右は基準由来の複数点と矩形でIoU0.81925、Recall 0.91958。
- **候補選択**。素材2右で基準由来の複数点と008矩形を固定すると、上側切断なしで008ランキング0.26270からSAM信頼度ランキング0.78289へ上昇。基準由来の点・矩形の併用では008ランキングの方が高く、プロンプトとの相互作用があった。
- **上側切断**。素材2左で基準矩形・SAM信頼度ランキングを固定すると、上側切断ありのIoU0.11471が、解除で0.87823に上昇。素材2右は複数点・基準矩形・008ランキング固定で0.19714から0.81925に上昇。
- **負例点とモデルの残差**。素材2の固定、ブラウス、スカートから負例点を追加しても、試した条件では左右の最高IoUは上がらなかった。最良条件でも左右とも0.90に未達で、誤抽出・欠落が残った。この試験から判断できるのは、実施したプロンプトと選択規則の範囲まで。
- **計測**。診断時間は素材1 9.10秒、素材2 15.88秒。LinuxのプロセスピークRSSはそれぞれ817,664 KiB、819,316 KiB。[全方式・全部位のCSV](method-comparison.csv) · [素材1](diagnostics/asset-01/metrics.json) · [素材2](diagnostics/asset-02/metrics.json) · [素材2の診断動画](videos/asset-02-mobilesam-ablation.mp4)

## 2026-11-20初回調査時点のB〜F実行状態

| 項目 | 判定 |
|---|---|
| 1. 008失敗原因 | 入力、選択、上側切断の影響を確認 |
| 2. See-through GPU環境 | CloudはGPUなし、Kaggle・ローカルは未アクセス |
| 3. レイヤー分離 | 公式コード調査済み、実画像の出力未取得 |
| 4. NF4・省メモリ | 公式の分岐を確認、速度・VRAM・品質は未測定 |
| 5. 左右構造認識 | 意味レイヤー未取得のため未実施 |
| 6. SAM自動プロンプト | 基準由来の診断を実施、意味モデル由来の自動方式は未実施 |
| 7. 代替比較 | AnimeSeg重みとGrounding DINOのBERT依存取得に403、推論未実施 |
| 8〜9. 素材1・2の完全自動分離 | 全6項目未測定 |
| 10〜12. 補完・リグ・GUI | 009正式分離評価後の工程。007 GUI回帰は13項目合格 |
| 13. 映像品質承認 | 009完成映像未生成 |

See-throughのコードは `fc4440db7c076518e313f378e28b1504e9886a95`。標準はBF16、公式目安は1280で12〜16GB、グループオフロードで約10GB、NF4で約8GB。NF4の公式スクリプトはグループオフロード既定オン、レイヤー1280・深度768。READMEのNF4例の深度720表記との差は、明示的に768を指定して統一した。NF4のCPUオフロード分岐はLayerDiffにあり、NF4 Marigoldは別処理でCUDAとグループオフロードを使う。公式の実行経路は単一CUDAデバイスを指定する。これらの値・設定は公式資料上の確認。 [公式README](https://github.com/shitagaki-lab/see-through/blob/fc4440db7c076518e313f378e28b1504e9886a95/README.md) · [標準スクリプト](https://github.com/shitagaki-lab/see-through/blob/fc4440db7c076518e313f378e28b1504e9886a95/inference/scripts/inference_psd.py) · [NF4スクリプト](https://github.com/shitagaki-lab/see-through/blob/fc4440db7c076518e313f378e28b1504e9886a95/inference/scripts/inference_psd_quantized.py)

公式実装は前髪・後ろ髪、頭部・顔の部位、頭部装飾、衣装などを扱い、推定深度の中央値でPSDの描画順を付与する。追加分割フラグの毛髪処理も前後分割で、左右可動毛束を直接返す分類はコードで確認できなかった。スカートは専用分類ではなく `bottomwear` の検証が必要。透過レイヤーの配置、前後順、中央切り出しは合成PSDで確認した。CloudではCUDAと重み取得が成立せず、Kaggleの割当・無料枠とローカルRTX 3060 Tiの空きVRAMは未確認。[環境判定](environment-report.json) · [モデル選定](model-selection.json) · [外部実行手順](environment/README.md)

## 回帰・再現

固定記録とERRATAに照合し、原画、全PNG、補助分類の部分集合、排他的な5分類、訂正文書4件を独立確認した。005〜008と素材の2,373ファイルの前後SHA-256は一致。008の保存済み予測15方式・素材組合せの評価JSONは再計算と完全一致。npm build、公式Node 183件、005の独立監視、006の保存結果、007変形・標準GUI操作を検証した。007検査は別コピーで再実行し、006検証による再生成物を固定版に戻してから実行した。診断動画は1152×2048、8秒、30fps、240フレームを全デコードした。[独立検査](verification.json) · [正式測定状況](metrics.json) · [自動化状況](automation-report.json)

```bash
python -B experiments/009-verify-reference.py /tmp/009-reference.json
out=results/009-semantic-hair-segmentation
# 既存結果を上書きしない別ディレクトリを指定
python -B experiments/009-diagnose-mobilesam.py source_008/original.png \
  results/008-segmentation-accuracy/reference/asset-02 /path/to/MobileSAM /tmp/009-asset-02
npm run build
npm test
```

MobileSAMはPython 3.12、PyTorch 2.8.0+cpu、torchvision 0.23.0+cpu、timm 0.9.16、OpenCV headless 4.13.0.92、NumPy 2.3.5、SciPy 1.17.0、Pillow 13.0.0で実行した。入力と固定リビジョンは[manifest](manifest.json)を参照。
