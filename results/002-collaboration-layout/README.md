# 002-collaboration-layout: 共有構成の整備

実施日2026-11-15 UTC。対象ブランチ `experiment/rigging-validation-20261115`、開始時コミット `6b9b5887c521f3c7e5eb5e63d4c9ee67eaa51835`。

作業先はユーザー指定の https://github.com/keepholdingon1224-source/StandRig 。公式リポジトリは参照のみ。追加課金・購入・外部有料API利用なし。SONY共同プロジェクトのコード・素材・サービスを使用していない。

## 成果物

- [進捗・判断・次の作業](../../PROGRESS.md)
- [研究索引](../../research/README.md)、[ChatGPT評価テンプレート](../../research/REVIEW_TEMPLATE.md)
- [実験の実行案内](../../experiments/README.md)、[既存実験への入口](../../experiments/run-baseline.mjs)
- [成果物索引](../README.md)、[第一段階の証拠索引](../001-baseline/README.md)
- [継続作業の記録ルール](../../AGENTS.md)

## 検査

- `node --check experiments/run-baseline.mjs`: 成功。
- `git diff --check`: 成功（今回の追加・編集ファイルが対象）。
- PythonによるMarkdown相対リンク存在検査・PROGRESSの7項目検査・既存PNG存在検査: 成功。Markdown7ファイル・相対リンク44件、2記録の各7項目を確認。
- 既存の製品コードと `validation/` の差分なしを確認。
- 今回は文書と互換入口の追加のみ。npm test、ビルド、MCP・ブラウザ再実験は未実行。過去の183件成功と区別する。
- 新しいPNG・動画は生成していない。

GitHubの反映はローカルコミットをForkの実験ブランチへ通常pushし、リモートのブランチSHAとローカルHEADの一致で確認する。コミットIDは自己参照せずGit履歴・最終ハンドオフを参照。

反映実績: `d58d6e8e4ad6ee63b15d623c48b14d9777213b23` をForkの上記ブランチへpush成功（exit 0）、`git ls-remote` で同じSHAを確認した。公開結果の追記コミットは最終ハンドオフを参照。
