# 実験009-A　RTX 3060 Ti / NF4 / 1024
2026-11-21 JSTのWindows実機診断。小テンソル合格、素材1での実入力事前診断は不通過。本推論の起動回数は0、PSDは未生成、009-Bは未実施。
## 環境・入力
StandRig起点9640dc74b4459db6b1d1e7ed17fb2e486d3c7a60、指定手順書のblobはprovenance.json。See-through固定fc4440db7c076518e313f378e28b1504e9886a95、追跡ソース差分なし。Python 3.12.10、torch 2.8.0+cu128、bitsandbytes 0.49.2、driver 610.88。pip check合格。GPU 0は3060 Ti 8192 MiB、GPU 1はGTX 1650 4096 MiB。CUDA_VISIBLE_DEVICESに3060 TiのUUIDを設定し、各診断プロセスで可視GPU1台、cuda:0の名前・CC 8.6・BF16ネイティブ対応を確認した。
## NF4実ファイル
LayerDiff3D 96f9311ff449dc86cfaba101ce4dfb4fd4958b80 は24ファイル 3,764,506,934バイト。Marigold e53b344b5aa5beec7c141bd5601decaaff0898c9 は16ファイル 1,928,813,115バイト。両スナップショットの全40ファイルのバイト数とSHA-256を記録、公開LFS SHA-256のある8ファイルは全件一致。各固定版のREADME、LICENSE、NOTICEを同梱。
## Attentionと停止理由
BF16 Q/K/V [1,4,64,64] でFlash/Efficient/cuDNN/Mathの有効フラグはすべてtrue。実装の適合性はFlash=false、Efficient=true、cuDNN=true。Profilerは aten::_scaled_dot_product_efficient_attention と aten::_efficient_attention_forward を観測した。
素材1を渡した診断は通常条件で2回（初回サンドボックス、再確認はホスト環境）とも、cache_tag_embeds中のNF4テキストエンコーダーで cublasCreate(handle) の CUBLAS_STATUS_ALLOC_FAILED。ホスト診断では例外処理時にCUDA illegal memory accessも報告。切り分け用のCUDA_LAUNCH_BLOCKING=1では bitsandbytes/csrc/ops.cu:81 で illegal memory access を報告して終了した。この追加試行は診断専用。根本原因および単純なVRAM不足の確定には至っていない。
通常ホスト診断の約1秒サンプルで、対象GPU全体の最大使用4,065 MiB、プロセスツリーRSS最大4,524,449,792バイト。瞬間ピークはこの周期では測れない。Bodyの最初のSDPA到達前のため実Q/K/V、can_use_*の実形状判定、実モデルのバックエンドおよびVAE/Body/Head/Marigoldの本推論ピークは未測定。候補全不適合という判定も行えない。事前診断が通らず最小試験を起動していない。
## 証拠
run-nf4-preflight 配下にrun.json、small.jsonl、diagnostic-2-3.txt、blocking-diagnostic、GPU/RAM時系列、pip-freeze.txt、実測重みマニフェスト、SHA256SUMSを保存。inference.txtは未起動理由の記録。Git共有版ではローカルパスを一部置換し、共有版のファイルに対して別途SHA256SUMSを生成。原本ログと導入ログはWindows作業先のrun-nf4-preflightに保存した。
