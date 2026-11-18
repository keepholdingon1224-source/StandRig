# 実験006 正式総合合格（2026-11-18 JST）

## 判定
**総合合格（対象範囲限定）**。ユーザー本人が2026-11-18に comparison-005-gui-export.mp4 を目視し「合格とします」と判断。GUI Canvasの三角形境界・輪郭・色差を許容する旨をMUSEが中継した。ChatGPTはGitHubのREADME、metrics.json、verification.json、gui-verification.json、進捗記録を照合し、合格を確定する。ChatGPT自身による動画直接視聴ではない。

## 根拠
- 実行完了時点の報告コミット：ee853b1（MUSE確認による）。
- [技術報告](README.md)
- [数値](metrics.json) / [独立検査](verification.json) / [GUI操作](gui-verification.json)
- [ユーザー確認動画](comparison-005-gui-export.mp4)
- [005正式合格記録](../005-spatiotemporal-constraints/FINAL-ACCEPTANCE.md)
- [固定基準ハッシュ](baseline-hashes.json)
- 独立検査18項目、従来数値基準18項目、GUI操作13項目すべてpass。公式schema/smoke16/Node183成功。
- 全482サンプルのモデル評価最大誤差7.105427357601002e-15px、実GUI描画からの最大誤差0.000016158029857098344px（0.01px以内）。
- software renderer補助出力240PNGは005と全枚バイト一致。GUI保存・復元前後も240PNG一致。005の固定基準ファイルはハッシュ一致、変更なし。
- 既存ArtMesh位相キーと標準モーションを用い、本体ソースの変更なし。

## 合格範囲
合成素材の005ベイク済みモデル・モーションの標準StandRig GUI（Linux Chromium headless）による読み込み、再生、停止、シーク、ループ、モデル・モーション保存、別セッション復元、補助MP4書き出し。Canvas描画差は今回のユーザー承認の範囲で許容する。GUI直接MP4は未実装であり、補助書き出しで代替した範囲の合格とする。

元のverification.jsonのtechnicalAcceptance=false、visual=pending user review、READMEの保留表記は実験完了時点の証拠として保存する。本記録はその後のユーザー視覚承認と範囲限定の最終判定を追記するもので、元の検査結果を改変しない。

## 残件
- GUI直接MP4ボタン未実装。
- Windows実機未確認。
- GPU描画は単一姿勢の探索のみで全周期未検証。
- 髪幅縮小、縦曲率、裾辺長比の005からの監視課題を継続。
- 任意画像のパーツ分離、隠れ領域補完、人体接続・衝突、全身制作、リアルタイム物理は未実証。

## 次段階（提案のみ）
007は実際のオリジナルキャラクター画像への段階的適用を第一候補とする。まず髪1束・裾1区画と固定された身体側の接続を対象とし、素材分離・根元推定・変形・描画・GUI再生を切り分ける。次に実素材で顕在化した品質問題を改善する。005/006は回帰基準として固定し、数値基準を無断緩和しない。素材の公開権利と対象範囲はユーザー判断を要する。

007は未承認・未開始。SONY ELF-MN1とは完全分離、追加課金なし。
