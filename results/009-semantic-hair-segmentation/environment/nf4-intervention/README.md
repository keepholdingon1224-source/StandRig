# 009-A　量子化状態の配置介入とA3モデル単位転送

## Gate 1

Windows実機、Python 3.12.10、torch 2.8.0+cu128、bitsandbytes 0.49.2、ドライバ610.88。全プロセスでCUDA_VISIBLE_DEVICESにRTX 3060 TiのUUIDを指定し、可視デバイス名と台数を検査した。判定条件は誤差許容なしのビット一致。Bodyタグ13個×77トークンを使用し、A3-Reference → A2-Fix → A2-Controlの順に3周、すべて新規プロセスで実行した。

| 条件 | 全44層完走 | 出力比較 |
|---|---:|---|
| A2-Control | 0/3 | 補正解除後の3回とも最初のq_projで事前配置検査が拒否。今回の試行でカーネルは呼び出していない |
| A2-Fix | 3/3 | Bodyとpooledの両方が同一セッションのA3および既報のA1に完全一致 |
| A3-Reference | 3/3 | 前回の参照ハッシュと一致 |

3条件で同じ観測・配置検査を使用した。A2-Fixのみ、GPU上の圧縮重みとCPU上の量子化状態を検出したときに、bitsandbytes 0.49.2のQuantState.to(weight.device)を呼んだ。インストール済みfunctional.pyの593–600行を確認した。このメソッドは状態をin-placeで更新し、code・absmaxに加え、nestedのときはoffset・state2.absmax・state2.codeも転送する。全状態テンソルを再帰的に列挙して同一デバイスを確認後、CUDA同期して元の演算に委譲した。固定NF4 CLIPには入れ子状態はなく、入れ子の実モデルでの動作は未試験。

Fix各試行で264演算、状態転送44,646,912バイト。各呼び出しの圧縮重みSHA-256は補正前後で一致した。Body [13,77,2048]、pooled [13,1280] はともに有限BF16。各成功試行で参照との差は0。gate1.jsonにハッシュ、プロセスID、完了層数、ピークを集約した。テキストログのplacementおよびメモリイベントに全演算の前後状態、割当・予約・空きメモリを保存した。fixed-files.jsonで両固定スナップショットの40ファイルを前回のSHA-256と照合した。

判定は配置不整合の因果的関与を強く支持。未補正のCUDAエラーそのものの根拠は、前回コミット f63382d の nf4-integration/A2-trace-{1,2,3}.txt とA2-plainの記録である。今回、補正解除後に再現を確認したのは配置異常まで。カーネル内部で最初に失敗した命令は未特定。後半は補正フックを取り外し、A3のモデル単位転送を使った。

## Gate 3

素材1は source_007/original.png。a3_body.py は公式 fc4440db の固定チェックポイントを使用し、ブロックオフロードを使わず、CLIPを1本ずつオンロードしてBody/Head計24タグの埋め込みをCPU側に保存した。次に画像VAEと透明VAEのエンコーダーを使用して条件潜在を作り、CPUへ退避してからUNet全体を3060 Tiへ移した。演算パラメータはNF4、Body解像度1024、seed 42、30ステップ。Gate 3は初回Body forwardの完走を外部フックで検知し、終了コード42で意図終了する。ここでの42はプローブの成功。

独立プロセス3/3成功。各回のBody初回forwardピークはallocated 5,106,815,488バイト、reserved 6,780,092,416バイト。各回の実Q/K/Vの6組すべてでProfilerのEfficient Attentionを確認した。Q/K/Vの寸法・ストライド・dtype・適合候補・実選択と演算イベントはbody-*-real.jsonlに記録。gate3.jsonはキャッシュファイルのハッシュも含む。画像準備、UNet、初回forwardなどのピークは個別ログで参照できる。

### 再現に使った入口

全実行で既存venvのPythonとローカルの固定スナップショットを使い、HF_HUB_OFFLINE=1、HF_HOMEを既存hfディレクトリ、CUDA_VISIBLE_DEVICESをgpus.csvの3060 Ti UUIDとした。以下の山括弧内は実際のパスまたは条件名で置換する。Gate 3以降は固定See-throughのルートを作業ディレクトリ、同リポジトリのcommonをPYTHONPATHとする。各試行に別ディレクトリを使う。診断が指定のゲートを通過した場合のみ次へ進める。

~~~text
python -B <experiment>/quantstate_gate.py <LayerDiff snapshot> <reference|fix|control>
NF4_PROBE=probe, NF4_DIAG_DIR=<trial directory> をプロセス環境に設定
python -B <experiment>/a3_body.py <LayerDiff snapshot> <source_007/original.png> <trial directory>/cache.safetensors
python -B <experiment>/a3_smoke.py <LayerDiff snapshot> <Marigold snapshot> <source_007/original.png> <verified cache.safetensors> <new output directory>
python -B <experiment>/a3_validate.py <source_007/original.png> <output directory> <validation.json>
~~~

2回目の本推論終了後、Windowsの監視側printがcp932に変換できず例外となった。子プロセスの終了コード0と推論ログは例外前に保存済み。既存PSDを独立に再読込してGate 5を検証し、監視側をUTF-8で再開した。2回目の推論の再実行は行っていない。

## Gate 4・5

A3改変構成の素材1最小試験を3つの独立プロセスで実行。各回ともa3_body.pyで作った同一の固定CLIPキャッシュを再利用し、補正フックとブロックオフロードを外した。a3_smoke.pyから公式run_layerdiff、run_marigold、further_extrを呼び、画像エンコード、各UNet、デコードでモデル単位に転送した。LayerDiffのみ30ステップ（BodyとHeadそれぞれ）、Marigoldは公式既定4ステップ、深度768。素材1の最小推論は3/3成功。CUDAピークは各ログ・run.jsonに実測値を収録。ラベルはリセット間の計測区間であり、Head image encode区間には直前のBodyデコードも含む。

Gate 5は3/3成功。a3_validate.pyで独立にPSDを開き、カラー・深度の各16レイヤーについてメタデータとの対応、並び順、オフセット、キャンバス内の境界、画像のデコードを検証。カラーでは各レイヤーのアルファ>10の全画素も切り出し前の画像と照合した。24個の中間パーツ画像と23個の対応深度画像を確認した。headは顔領域の切り出し用の中間画像。空の部位など、公式書き出し条件でPSDから除かれるものは各gate5記録のraw欄に残した。

元画像1152×2048を左右448ピクセルずつパディングし、2048角から1024角に面積補間する独立計算が保存済みsrc_img.pngと全画素一致。ピクセル境界座標をPSDから原画へ戻す式は x_original = 2*x_psd - 448、y_original = 2*y_psd。各レイヤーの原画座標もgate5記録に保存した。この検証は出力の完全性と配置を対象とし、パーツの正解マスクとのIoUは未計測。

判定：素材1と指定パラメータでローカルNF4・1024（A3改変構成）は成立。公式ブロックオフロード構成の過去の失敗記録は継続する。カラー・深度PSDと中間出力はWindowsのLive2D_009A/a3-smoke-{1,2,3}/に保存。個別ファイルのSHA-256とサイズはrun.jsonに収録した。GPU/RAM外部サンプルは1回目のHead処理途中から取得したため、1回目の全過程はカバーしていない。
