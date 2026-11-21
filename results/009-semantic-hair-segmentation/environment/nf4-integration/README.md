# 実験009-A　CLIP統合切り分け

最小の観測済み再現条件は固定NF4 CLIPペアへのDiffusersブロック単位グループオフロード（1グループ1ブロック）。公式Pipelineの他のモデルをロードする前に、先頭CLIP第1層のq_projで以前のCUBLAS_STATUS_ALLOC_FAILEDを再現した。厳密に最小のモジュール数は未探索。

| 段階・条件 | 層別観測なし | 層別観測あり | 観測 |
|---|---:|---:|---|
| A1 GPU常駐 | 3/3成功 | 3/3成功 | CLIP 12層＋32層、Body埋め込みを生成 |
| A2 グループオフロード | 0/3成功 | 0/3成功 | 最初のq_proj、完了0層 |
| A3 CPU待機・エンコーダー単位のGPU往復 | 3/3成功 | 3/3成功 | 全44層、A1とビット単位で同一の出力 |
| B1–B4 | 未実施 | 未実施 | A2で再現、A全成功の開始条件を満たさず |
| C | 未実施 | 未実施 | Bでの異常確認を前提とする追加試験。量子化状態の手動修正なし |
| D 素材1事前診断 | 未実施 | 0/3成功 | 公式グループオフロードでcache_tag_embeds内のq_projが失敗、Body未到達 |

## 入力と観測

既存Windows venv Python 3.12.10、torch 2.8.0+cu128、bitsandbytes 0.49.2、ドライバ610.88。RTX 3060 TiをCUDA_VISIBLE_DEVICESのUUIDで固定し、各プロセスでGPU名・可視数を確認。GTX 1650も物理GPU一覧に記録。公式See-through fc4440db7c076518e313f378e28b1504e9886a95、LayerDiff3D 96f9311ff449dc86cfaba101ce4dfb4fd4958b80。固定ファイルは読み取りのみ。

公式v3のBodyタグ13個を両トークナイザーへ同じ順序で渡し、max_length=77、padding=max_length、truncation=True、int64で生成。トークンID全件・ハッシュはAログのtokensイベントに保存。各エンコーダーの最後から2番目の隠れ状態を連結し、第2エンコーダーのpooled出力も記録。A1/A3の全12成功試行でBF16のBody埋め込み [13,77,2048] とpooled [13,1280] は有限かつハッシュ一致。ハッシュ対象は形状をログに併記した連続CPUテンソルの生バイト。これはBodyタグの試験で、Headタグは対象外。

Aの各試行は新規プロセスで integration.py を実行。plainは層・matmulフックなし（境界での同期と出力検証あり）。traceは層の前後、4bit matmul後にも同期し、CPU/GPUとdtypeを記録。すべての試行で異常後のCUDA再照会は実施していない。成功時のallocated、reserved、mem_get_infoの前後差をsummary.jsonに保存。失敗時の事後値は未測定。

## 失敗箇所と判別

A2の観測3試行とも、matmul_4bit入口で入力BF16と圧縮重みuint8はcuda:0、一方quant_state.absmaxとcodeはともにCPUのfloat32。A1/A3では同じ入口で4テンソルともcuda:0。A2では層入口での同期を通過し、その後dequantize_4bitを含むlinearでcublasCreate(handle)の例外。エラーが報告された呼び出しと、最初に不正となったCUDA命令の位置は区別する必要がある。メモリ不足や特定のCUDA命令を根本原因と断定する証拠はない。グループ転送時の量子化状態の配置不整合が有力。手動補正による因果確認は未実施。今回は最小条件で明示的なillegal memory accessのメッセージを観測せず、Compute Sanitizerは実行していない。

## 素材1の再確認

A2で統合条件を特定できたため、Dは同一の公式構成で事前診断まで再実行。integration_body_gate.pyから公式CLIを呼び、cache_tag_embedsと最初のBody forwardに外部フックを装着。素材 source_007/original.png、NF4、1024、深度768、seed 42、30ステップ、グループオフロード、PSD指定。3回ともcache_tag_embedsで停止。ロード完了時点のpeak allocated/reservedを各Dログに保存。Body・Head・深度段階のピークは未測定。最小本試験0回、PSDなし、構成成立は未確認。009-B未実施。
