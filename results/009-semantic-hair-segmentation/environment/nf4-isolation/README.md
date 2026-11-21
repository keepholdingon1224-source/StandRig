# 実験009-A　RTX 3060 Ti の NF4 単独切り分け

既存の Windows venv（Python 3.12.10、torch 2.8.0+cu128、bitsandbytes 0.49.2、ドライバ610.88）を使用。nvidia-smiで2枚を識別し、前回と同じCUDA_VISIBLE_DEVICESのUUIDで3060 Tiのみに固定した。各演算プロセスで可視GPU数と名前を確認。ロードされたDLLは libbitsandbytes_cuda128.dll。

| 試験 | BF16入力 | 論理重み | 結果 |
|---|---|---|---|
| 通常のPyTorch Linear | 13 × 77 × 768 | BF16、768 × 768 | 3/3合格 |
| Linear4bit、小形状 | 2 × 8 × 64 | 64 × 64をNF4化 | 3/3合格 |
| Linear4bit、CLIP第1層q_proj | 13 × 77 × 768 | 768 × 768、固定チェックポイントのNF4重み・量子化状態・バイアス | 3/3合格 |

## 方法と証拠

固定LayerDiff3Dリビジョン 96f9311ff449dc86cfaba101ce4dfb4fd4958b80 の text_encoder/model.safetensors から対象層を読み出した。前回スタックが示したv3のBodyタグ13個、77トークン、先頭エンコーダーの幅768を再現。入力値はseed 42の合成BF16テンソル。各試行は新規Pythonプロセスで同期実行し、出力形状・dtype・全要素の有限性を確認した。数値精度の参照値比較は実施していない。

再現には既存venvのPythonを用い、前回のGPU UUIDをCUDA_VISIBLE_DEVICESに設定し、各回で python -B -m bitsandbytes を実行後、別プロセスで experiments/009-local-nf4/isolate.py に control、small、clip のいずれかを渡す。clipには --model で上記safetensorsを指定する。これを各条件3回繰り返した。各試行の *-bnb.txt にCLI診断、各演算の .txt にプロセスID・ロードDLL・演算直前の空き/総メモリ・割当/予約バイト数・入出力・終了コードを記録。summary.jsonに各試行の結果を収録した。

## 判別と停止

全9試行が成功。前回失敗した層の実重みと同じ入力形状・dtypeでも、単独演算ではエラーを再現できなかった。次の切り分け対象は統合時のモデルロード、グループオフロード、デバイス移動時の量子化状態やメモリの扱い。今回の単独試験では根本原因を特定できていない。

全条件成功時の指示に従い第1段階で停止。第2段階の別venv比較、第3段階のSee-through再診断・素材1の最小試験、PSD出力、009-Bは未実施。ローカルNF4・1024構成の成立は未確認。
