# 実験009-A Kaggle最小試験 — MUSE回収の生ログ（引き渡し）

MUSEがKaggleカーネル `rindou1224/exp009-seethrough-min`（非公開）から回収した生ログ一式。
正式記録（kaggle-attempts.json、environment-report.json等）はCodexがこの内容とSHA256SUMSを照合して作成する。

## 内訳
- `kaggle-t4-v1/` — v1（2026-11-20 21:43 JST）。ホストPython 3.13のためNotebook冒頭の検査で停止。成果物tarは生成されず、Kaggle実行ログのみ。
- `kaggle-t4-v2/` — v2（21:47開始）。標準・解像度1280・オフロードなし。VAEエンコードでCUDA OOM。`009-kaggle-v2.ipynb` はv3版からの差分復元（CONFIGセルの enable_group_offload と run_label の2値のみ相違。他は同一）。
- `kaggle-t4-v3/` — v3（22:07開始）。標準・1280・グループオフロード有効。SDPAで19.84GiBの確保要求が発生しOOM。`009-kaggle-v3.ipynb` は実際にpushした版そのもの。
- `l4-probe/` — L4確認用プローブ（カーネル `rindou1224/gpu-probe-l4` スクリプト型v2、`rindou1224/gpu-probe-l4-nb` ノートブック型v1）の実行ログ。どちらも machine_shape=NvidiaL4 指定でGPUが割り当てられずCPUセッションになった（torch 2.11.0+cpu、CUDA利用不可）。

## MUSE側の変更点（元Notebookとの差分）
ドライバ側セルのみ変更し、推論コード・固定コミット・重み・seedは不変。
uvでPython 3.12を用意し、推論用venv（/tmp/venv312）を3.12で作成してランナーを実行する形に変えた（KaggleホストのPython 3.13対策）。

## 重みの固定リビジョンとライセンス（MUSE確認済み）
- LayerDiff: `layerdifforg/seethroughv0.0.2_layerdiff3d` @ `4477e6ce529bc6a141732e1a55a4932176db3b89` — openrail++
- Marigold: `24yearsold/seethroughv0.0.1_marigold` @ `4f4ffc46050b6feb764b628859968a26e76e6b6a` — openrail++（See-through追加分はApache-2.0）
各回の `standard-revisions.json` に取得時の照合結果がある。

## SHA256SUMS照合
v2・v3とも、回収時に同梱のSHA256SUMSで全ファイル照合済み（不一致なし）。
`original/src_img.png`（入力画像の複写）はリポジトリ既存の原画と重複するため引き渡しから除外した。
