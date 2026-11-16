# StandRig 実験コード

Codexが実装と実行を担当する。リポジトリ直下から起動し、結果はPROGRESS.mdに記録する。

## 既存の第一段階（001-baseline）

- [MCP曲げ・QA・PNG・復元のコード](../validation/probe.mjs)
- [Canvas/WebGL・SSE・モーションのコード](../validation/browser.mjs)
- 入口: `node experiments/run-baseline.mjs`
- 既存コードを保存するため、第一段階の出力先は従来の `validation/artifacts/` のまま。[成果物索引](../results/001-baseline/README.md)

事前に `npm ci` と `npm run build` が必要。ローカルHTTP listenが許可された環境で実行する。`validation/local-data/` は新規の検証専用ディレクトリを前提とし、既存データがあれば別の場所へ退避する。自動削除しない。

ブラウザ検証は `KEEP_SERVICE=1 node experiments/run-baseline.mjs` でサービスを保持し、Chromiumを独立プロファイル・headless・remote-debugging-port=9227で起動して `node validation/browser.mjs` を実行する。probeにSIGTERMを送ると復元して終了する。詳細は[既存報告](../validation/REPORT.ja.md)。

## 新規実験

- [003: 髪1束・裾1枚の自動メッシュ／物理／8秒ループ](../results/003-secondary-loop/README.md): `node experiments/003-secondary-loop.mjs` → `node experiments/003-verify.mjs`。結果とコード保存版は `results/003-secondary-loop/`。

`experiments/<id>/` にコードとREADME、`results/<id>/` に共有可能なログ・設定・画像・動画・結果要約を保存する。実験のREADMEに目的、対象コミット、実行コマンド、環境、素材、合格条件、出力先を明記する。モデルの作業領域は `workspace/` 等のGit除外先を使う。既存の製品コード・検証記録は上書きしない。

- 004: [変形拘束・比較結果・未達項目](../results/004-deformation-constraints/README.md)。髪中心線保持と裾距離拘束、総合不合格・全証拠保存。
