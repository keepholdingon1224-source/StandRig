# See-through 無料GPUでの最小試験

009-Aの最新判定と次の実行手順は[構成別環境判定](environment-report.json)と[RTX 3060 Ti NF4・1024手順](rtx-3060-ti-nf4-1024.md)を参照。以下は初回試験時の手順。

まず既存のKaggle無料GPU枠で素材1を1回試す。[Notebook](../notebooks/009-kaggle.ipynb) をインポートし、AcceleratorをGPUにしてInternetを有効にする。無料残量とセッション上限はKaggle画面で確認し、実行記録に転記する。GPUは1枚を指定する。T4などのネイティブBF16対応状況を記録し、公式BF16処理が失敗した場合はログで確認する。複数GPUのVRAMは合算しない。

## 既存PCで実行する場合

Python 3.12環境で実行する。Windowsは既存のCUDA対応環境でのみ試行する。実行前に `nvidia-smi` でドライバーと空きVRAMを確認する。ローカル8GBはNF4・1024から試す。

```text
git clone https://github.com/shitagaki-lab/see-through.git
git -C see-through checkout --detach fc4440db7c076518e313f378e28b1504e9886a95
cd see-through
python -m pip install torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt -r requirements-inference-bnb.txt psutil==7.2.2
cd ..
python StandRig/experiments/009-run-seethrough.py see-through StandRig/source_007/original.png run-nf4 revisions.json --mode nf4 --resolution 1024
```

標準1280は末尾を `--mode standard --resolution 1280` に置き換える。標準グループオフロードには `--group-offload` を追加する。依存は公式リポジトリの固定コミットの指定を使用し、実行環境の解決済み全バージョンは `python -m pip freeze` で記録する。既存環境への影響を避けるため専用venvを使用する。

`revisions.json` は公式モデルIDをキー、レビュー済み40桁リビジョンを値とする。Notebookの調査セルで取得したSHAと、そのSHA上のREADME・LICENSE・NOTICEを確認し、JSONを固定してから推論を開始する。標準の2件とNF4の2件はNotebook参照。コードはApache-2.0。公式モデルカードによるとSee-throughの追加部分はApache-2.0で、LayerDiffにはSDXL系、MarigoldにはMarigoldとSD2系のOpen RAIL条件が継承される。重みを回収物やGitに含めない。 [標準LayerDiff](https://huggingface.co/layerdifforg/seethroughv0.0.2_layerdiff3d) · [標準Marigold](https://huggingface.co/layerdifforg/seethroughv0.0.1_marigold) · [NF4 LayerDiff](https://huggingface.co/24yearsold/seethroughv0.0.2_layerdiff3d_nf4) · [NF4 Marigold](https://huggingface.co/24yearsold/seethroughv0.0.1_marigold_nf4)

出力ディレクトリ全体を回収し、別の作業先で `sha256sum -c SHA256SUMS` を実行する。素材1のSHA-256は `a1388c37f35c19278d346ab4491c8bcc919e1f375b07f312a70ab7e87bbcbcea`。成功条件は `run.json` の `layer_smoke_pass`、PSDと分類別マスクの読み込み、1152×2048座標への復元、無料枠内での完走。失敗時は `run.json`、`inference.txt`、GPU/RAMログを回収する。GPUメモリは1秒サンプルのデバイス使用量で他プロセスも含む。RAMは1秒サンプルの推論プロセスツリーRSS合計。短時間のピークはサンプル間で見逃し得る。

レイヤー座標は、PSDに記録されたオフセットで正方形キャンバスへ配置し、元画像の長辺まで拡大して中央パディングを切り落とす。アルファ128以上を上位レイヤーから前面所有として割り当て、補完済みRGBAは別に保存する。正式評価にはプレビューと元画像の位置合わせ確認、および共通ルールによる左右可動毛束・スカートの割り当てが必要。
