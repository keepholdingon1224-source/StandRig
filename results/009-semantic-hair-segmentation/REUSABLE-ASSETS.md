# 再利用可能な資産

表のリンクは実装または運用記録を指す。指定のない項目の取得元はStandRigのコミット `72c05ea9933591740183709e043f792d56e1a1f8`。このスナップショットには005〜009-Gと素材3の初回予測がそろっている。

| 資産 | 所在 | 再利用条件・検証範囲 |
|---|---|---|
| 髪・裾の変形とループ | [005の拘束ソルバー](../../experiments/005-solve.py)、[007の実素材リグ](../../experiments/007-rig.py)、[007のベイク](../../experiments/007-bake.mjs) | 正しく分離された毛束・裾と支点を入力する。005の合格は合成素材、007の限定合格は分離行と裾位相を手動補助した実素材についてのもの。 |
| StandRigでの再生・保存復元 | [006のベイク](../../experiments/006-bake.mjs)、[GUI操作](../../experiments/006-gui.mjs)、[再読込検査](../../experiments/006-fresh-session.mjs)、[成果物と検証範囲](../006-gui-playback/README.md) | ArtMeshの位相キーに焼き付けた変形を標準GUIで再生する。補助MP4出力とGUI直接MP4出力は区別する。 |
| See-throughローカル実行 | [RTX 3060 Tiの環境手順](environment/rtx-3060-ti-nf4-1024.md)、[A3の成立記録](environment/nf4-intervention/README.md)、[A3推論](../../experiments/009-local-nf4/a3_smoke.py)、[PSDの独立再読込](../../experiments/009-local-nf4/a3_validate.py) | 009-A限定合格のNF4・A3改変構成。GPUをUUIDで固定し、モデル単位でCPU待機・GPU転送する。公式See-throughは `fc4440db7c076518e313f378e28b1504e9886a95`。環境診断とモデル固定だけでA3の転送処理を省略しない。 |
| PSD取り込みと可視所有者 | [レイヤー抽出](../../experiments/009-run-seethrough.py)、[009-Bの取り込み](../../experiments/009-b/predict.py)、[規則](009-B/rules.json) | オフセットと描画順を使って原画座標に復元する。隠れた部分を含む補完RGBAは制作に保存し、可視マスクの採点には可視所有者を使う。想定外の合成モード・座標変換では同一性を確認する。 |
| スカート分離 | [009-Cの可視性・帰属処理](../../experiments/009-c/predict.py)、[C2-C記録](009-C/README.md)、[009-G固定規則](009-G/rules.md) | bottomwearを候補にし、C2-Cの可視所有者で髪との重なりを扱う。009-Gはこのスカートを引き継ぐ。3素材の可視スカートで合格。ほかの衣装・遮蔽条件は別途検証を要する。 |
| 独立評価と成果物保護 | [009-Gの独立評価](../../experiments/009-g/evaluate.py)、[保護照合](../../experiments/009-g/integrity.py)、[初回予測の手順](009-G/holdout-protocol.json)、[入力・実行来歴](holdout-03/provenance.json)、[凍結記録](holdout-03/prediction-lock.json) | 予測コード・条件を先に固定し、基準マスクを予測側から隔離する。実行前後に保護対象を照合し、出力を凍結後、評価担当が受領ハッシュを照合して採点する。009-Gの評価スクリプトは開発2素材用。素材3基準マスクは非公開。 |

## モデルと方式の固定点

- LayerDiff NF4は `96f9311ff449dc86cfaba101ce4dfb4fd4958b80`、Marigold NF4は `e53b344b5aa5beec7c141bd5601decaaff0898c9`。1024、深度768、seed 42、LayerDiff 30ステップ、Marigold既定4ステップの記録を参照する。[実行時の設定・ハッシュ](holdout-03/provenance.json)
- 009-Gの予測器・規則の固定コミットは `38ff2140c8f1358305931276d450040986657973`。素材3用の隔離した入力配置はアダプターのコミット `ca9e315610791b180a362be116b362cb590fcf82` にある。安全判定による009-Cへの復帰は境界編集の退行対策であり、基準方式の認識精度は保証しない。[入力アダプター](holdout-03/input_adapter.py)
