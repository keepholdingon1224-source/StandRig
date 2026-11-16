# 未採用・失敗記録

- 髪単純回転/せん断の初期探索：8秒の髪範囲147px以上と全辺0.90〜1.10を同時達成できず。例：分散曲げ0.75・断面回転0.75では辺比0.859385〜1.144136、範囲155.825px。
- 先端151px目標の共同最適化：実範囲150.801858px、辺比0.897893〜1.101269で不合格。`../attempts.json`に最終パラメータ・測定値。`hair-first-opt.py`は当時のscratch依存スナップショットで、単独再現用ではない。正式再現は`../code/005-solve.py`。
- スカート7条件：`../attempts.json`に記録。無平滑化は004境界4.274729px/sで不合格。時間σ2以上は境界を満たす候補もあるが、全時間の加速度・曲率と振幅保持を比較してσ6・空間0.65を採用。
- 初回独立検査：fixtureを再JSON化した末尾改行差で入力バイトハッシュ不一致（数値は合格、証拠整合性は不合格）。`first-verification.json`と`first-independent-verification.log`を保持。元のバイトコピーに修正。
- 初期scratch補助解析はworkディレクトリ未作成でexit2。mkdir後再実行。初期Git取得時はremoteのmain限定fetch設定と複数FETCH_HEADにより配布版を選んだが、既知先端15020757へのfast-forwardで修正し、生成前に指定ブランチを確認。API経由tarball取得403は利用せず通常git fetchで取得した。いずれも成果物の成功検査には算入しない。
- グラフ作成時Fontconfig cache警告は発生。exit0でPNG生成成功。Matplotlibはwork内cacheを明示した。
