# 実装調査と採用方式

基準コミット: `9b8b4ca5751cd370fc71068957f975f2d3bb5796`。開始時ローカルはクリーンな `work/c3166aa`。`git ls-remote` とfetchで指定Forkのブランチを確認後、SHAを明示して実験ブランチへ移動した。FETCH_HEADにmainも含まれていたため、最初のブランチ作成ではmainを選んだが、実験作成前に修正。mainへの書き込みなし。

README.md、AGENTS.md、AI_OPERATING_GUIDE.md、docs/MCP.md、docs/MOTION.md、docs/API.md、docs/RIG-FEATURES.md、docs/DEFORM.mdと、以下の実装を照合した。

| 対象 | 実装で確認した内容 |
|---|---|
| Core ArtMesh | `artMesh.ts` の単一parameter bindingは任意長keysを線形補間。キー/パラメータ総数の明示上限なし。generator行列は1..16、頂点ID一意・UV0..1・有限座標・三角形index/面積・offsetの頂点参照を検証。基準の153頂点/256三角形をそのまま使用 |
| Blend Shape | `artMeshBlendShape.ts` はneutral→targetのclamp weightと補間曲線でoffsetを加算。今回は多数shape/parameterより、1つの位相に482キーを持つ既存ArtMesh bindingが簡潔で無損失 |
| 複数parameter | `parameterGrid.ts` は2..8軸の多重線形補間。今回不要 |
| モーション | `core/motion.ts` でduration>0..3600、track1..256、各1..4096keys・合計50000keys、有限値・単調時間・ID/値域を検証。今回は8秒・1track・2keys |
| Runtime | `MotionController.seek`→parameter→`resolveArtMesh`。StandRigPlayerは同じ評価をCanvas/WebGL描画へ渡す。モデルのphysics.enabled=false/chains=[]、旧Blend Shape削除により二重適用なし |
| Preview | `main.ts`/`modelFile.ts`でbundle/packed読み込み、transaction import、play/pause/stop/seek/loop、portableモデルとmotion JSONのdownloadを実施。既存のseek slider刻みは0.01秒。精密検証だけstep=anyをDOMに設定し、実際のchange/inputハンドラーを使用 |
| Service | `modelingRoutes`/`portableBundle`/`playback`/`httpBody`経由でimport・保存・playback・export。モデル上限384MiB。motion HTTP/Preview実装上限16MiB（UIはenvelope余裕1024bytes）。docs/MOTION.mdの1MiB記述は現実装と不一致。wire/展開後の両方を制限 |
| 動画 | 標準GUIにMP4出力ボタン/APIなし。GUIからdownloadしたモデル・motionを入力に、既存Core software rendererとFFmpegを使う補助書き出し。005動画のコピーではない |

本体ソース・スキーマ・公開APIは変更していない。新規adapter、物理演算、平滑化、基底圧縮も不要だった。ベイクモデルは画像埋め込みの既存standrig-bundle、GUI exportは既存standrig-packed内包bundle。13件のwarningはrootと標準顔parameter未定義で、合成2パーツ実験に対する既存警告。エラー0。

位相parameter範囲0..481/60。モデルに0..8と追加1/60の482サンプルを保持し、通常motionは0..8だけを駆動する。動画はt=0..239/30の240枚。停止でphase=0へ復元し、物理状態に依存しない。同時刻間は既存線形補間であり、元の60Hzサンプル間に新しいシミュレーションを行わない。

精密GUI検査は主canvasのdrawImage直前の実際のDOMMatrixを読み取る。各フレーム512三角形×3頂点を元UVで投影し、既存padding18と固定パーツtransformを引いて005と比較する。描画や頂点評価の置換はしていない。Canvas内部行列のfloat精度差も含めて判定する。追加sampleだけHTML数値文字列の上限丸めを避け481/60−1e−12秒をparameterスライダーから入力（誤差をそのまま計測）。

取得証拠のうち大きなCanvas描画行列JSONは、全値を保つgzipで保存する（`.json.gz`）。検査コードはgzip/非圧縮の両方を読める。これは証拠ファイルの圧縮であり、モデル頂点データの量子化ではない。
