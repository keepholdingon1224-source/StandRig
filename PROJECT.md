# AI Live2D自動制作研究 | StandRig

## 共通名称
**AI Live2D自動制作研究**（Codex・ChatGPT・GitHubでこの表記に統一）

## 目的
オリジナルの2Dキャラクター素材から、AIによるパーツ処理・リギング・髪と衣装の物理揺れ・ループ動画出力をできる限り自動化する。『放置少女』の映像表現を品質参考にするが、既存キャラクター素材は利用しない。

## スコープ・ルール
- SONY ELF-MN1共同プロジェクトと完全に独立。素材・コード・認証・作業ログを混ぜない。
- 追加課金なし。外部有料APIを使わない。
- 実験は `experiment/rigging-validation-20261115` で進め、`main` や作者の上流リポジトリを変更しない。
- **Codex** は実装・テスト・結果保存と `PROGRESS.md` 更新。
- **ChatGPT** は公開された検証結果のレビュー・次の課題選定。レビュー未実施なら明記する。
- 毎回、実行環境、コマンド、コミット、合否、動画/画像、失敗、未解決事項を残す。

## 現在地（2026-11-17 JST確認）
- 001: MCP編集・曲げ・描画・復元の基本試験完了。
- 002: GitHub共有構成と実験ログ準備完了。
- 003: 髪1束とスカート裾1枚の合成素材で8秒/30fps/240フレームのMP4を生成。数値検証は成功。
- **重要な限界（003）**: メッシュ辺長の比率0.7496〜1.2294（縮み・伸びが大きい）。自然な見た目と実キャラ同一性、身体との接続・衝突は未合格／未検証。003は画像からの汎用自動パーツ推定ではなく、既知形状の専用コード実験。

- 004: 同一素材・物理入力のまま髪の長さ保持と裾の距離拘束を実装。公式183件・証拠整合性10項目成功。**総合不合格**: 髪辺長比0.798870〜1.201133、30fps境界速度差は髪2.947091/裾4.274729px/s。髪中心線長比1.000000、裾辺長比0.955130〜1.052548に改善。004の視覚品質は2026-11-17にユーザーが「いいよ」と暫定承認。追加要望はスカートの波打ちの柔らかさ。数値・総合不合格は維持。Windows実機・新方式GUI統合は未実施。

- 005: **数値合格＋ユーザー本人の動画視覚承認により2026-11-17総合合格（合成素材の8秒オフライン生成に限定）**。髪の全辺比0.901536〜1.098376、中心線1.000000〜1.019090、先端147.978px。裾辺比0.947091〜1.058099、先端66.800px。30fps境界速度差は髪1.419529/裾0.750531px/s。公式183件・独立検査20項目成功。裾の曲率急変・加速度・ジャークが改善。一方、髪縦曲率・幅保持、裾の辺長比は悪化（許容内）。オフライン実験コードのみ、GUI未統合。新規の裾方向物理波伝播は未実装。改善・悪化と失敗を[005報告](results/005-spatiotemporal-constraints/README.md)に記録。

- 006: **実行済み・最終合格保留**。既存ArtMesh位相キーへ005を無損失ベイクし、標準GUI操作・3周期ループ・portableモデル/モーション書出し・新session復元・補助MP4出力を検証。本体変更なし。全482サンプルのCore最大差約7.1e−15px、実GUI描画採取約1.62e−5px。software出力240PNGは005と全枚一致。Canvas描画差（境界細線等）のユーザー審査待ち、GUI直接MP4は未実装。[006報告](results/006-gui-playback/README.md)。Windows実機未実施。

## 正本リンク
- [006 GUI再生・保存・補助動画出力](results/006-gui-playback/README.md)
- [005 正式総合合格記録](results/005-spatiotemporal-constraints/FINAL-ACCEPTANCE.md)\n- [005 実験報告・全成果物](results/005-spatiotemporal-constraints/README.md)
- [003・004・005比較](results/005-spatiotemporal-constraints/comparison-003-004-005.mp4) / [004・005裾拡大](results/005-spatiotemporal-constraints/hem-closeup-004-005.mp4)
- [作業履歴と状態](PROGRESS.md)
- [004 実験報告・成果物・不合格項目](results/004-deformation-constraints/README.md)
- [004 左右比較動画](results/004-deformation-constraints/comparison.mp4)
- [004 独立検査](results/004-deformation-constraints/verification.json)
- [003 実験報告](results/003-secondary-loop/README.md)
- [003 MP4](results/003-secondary-loop/hair-skirt-loop.mp4)
- [003 GIF](results/003-secondary-loop/preview.gif)
- [003 数値](results/003-secondary-loop/metrics.json)
- [調査](research/README.md) / [実験](experiments/README.md) / [成果物](results/README.md)

## 次の検証（推奨順）
1. **005のユーザー視覚審査は完了・合格**。[正式判定](results/005-spatiotemporal-constraints/FINAL-ACCEPTANCE.md)を以後の品質基準として固定。006は2026-11-17承認に基づき実行済み。
2. **006のレビューと残件判断**。Canvas描画と005の比較、およびGUI直接MP4を検討。005のオフライン周期全体平滑化をリアルタイム処理と同一視しない。005成果物の回帰検査を維持。\n3. 髪の可動範囲147px以上と全辺長許容を保ちながら、縦曲率・幅変化を改善。
4. 裾の新規物理波伝播・慣性の実装を検討。005の全周期平滑化はオンライン時間積分ではない。
5. 身体接続・衝突、任意素材の汎用化は別工程。

**合格の原則**: 自動テスト合格だけでは画質合格にしない。視覚的品質と変形指標の両方で判断する。
