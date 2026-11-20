# Experiment 008 — Reference review and freeze

## 2026-11-20 JST / ChatGPT technical approval
**v4 frozen as the evaluation reference for experiment 008.** User approved the experimental design and both source assets; final Codex execution authorization remains pending. Do not start implementation until final user approval.

Frozen source snapshot: `ca383315a73c0f5e0621f15b9a943d6b67f87d23` (asset-01 revision e1b9d66, asset-02 revision ca38331). Branch: `experiment/rigging-validation-20261115`.

Reviewed actual v4 overlay images, both auxiliary blouse overlays, saved reference-verification.json and verify-reference.py. Prior visual reviews covered roots, tips, sleeves, waist and trim. Both saved independent verification reports pass: original hashes match; 1152x2048 mode L binary masks; primary overlap/unclassified and auxiliary subset violations all zero. ChatGPT did not separately execute pixel verification. Codex must recheck actual PNG bytes and hashes before testing, in a temporary directory, without writing into reference/.

The references are operational annotations, not perfect semantic truth. Minor boundary uncertainty and auxiliary blouse omissions (notably asset-02 shoulder) are retained; no further edits required before 008. Primary official IoU remains >=0.90 separately for hair-left, hair-right, skirt on both images, including uncertain pixels. Auxiliary masks and landmarks are diagnostics only. Hidden pixels are excluded from visible reference labels. No changes to reference data during model selection or testing.

Asset-01 is development; asset-02 is held out from development/adjustment, but publicly accessible, not genuinely blind. Freeze code/model/config before evaluation on asset-02; record accessed files and first-run outputs. Reference masks/landmarks/annotation scripts must never enter automatic prediction inputs. Evaluation-only use; assisted downstream runs separate. 005–007 immutable, no extra cost, SONY separation.

## Frozen references and recorded SHA-256

### asset-01
- [Independent validation](asset-01/reference-verification.json) (Git blob `22144eba3bfb2410c243d5d259307f7d4243e0aa`)
- Original SHA-256: `a1388c37f35c19278d346ab4491c8bcc919e1f375b07f312a70ab7e87bbcbcea`

| File | SHA-256 |
|---|---|
| background.png | `94854a565e316ff1e938d3a242c598b2bf9e36c2745c1744570660a41204dcd3` |
| hair-left.png | `0103b9c33036913b3cffa0d1655c13c362ea09d7eca4dc466c84994ebaa595bd` |
| hair-right.png | `7e7e280ac1df1f690de3d1b975a6b67901892b835902f34e47304fd786cb4f6c` |
| skirt.png | `cb615a5a926d3ac997a65a4285c8451ffe5c8d7b3fdfda05a12b065613a6c388` |
| fixed.png | `8df2f1cf20d6367f1eb0bcfe8c43442ceeca46ad703d7361734adbbdf5a76329` |
| blouse-visible.png | `1d25c51b3431506f34a92fb15578611e765b1efa6f7c683a5f8eeb8e995bd995` |
| hem-trim.png | `d14c2055592bec8e569abaea9b179287aedb842b43e2e906d2679c1ec747939a` |
| uncertain.png | `432ce0a4b6b970e9da152767f5cc4d53b334a183c09bd9d8d9c8c9d0fc42d149` |
| landmarks.json | `9cad80872d8211472a4da34f4b0c4d728ca955bd95ba5968bc92ea241e9745d1` |
| manifest.json | `4c93e1ee235effc3439df8f0ab0f82d3371e3326329be587a58417d01ca07b4c` |
| annotation-notes.md | `d3851da974958d8d83965eed4f867a90904cffa7404ea1ea6e6243221c78d9a2` |
| annotation-v3.py | `c8772d1cd113254f73f0c45bdac3dff63c9317c6fc3469988cbf5caa0ae586a3` |

All other annotation evidence, verification scripts and overlays are also pinned by the full source commit above; any later reference revision requires explicit review, a new reference version and separate results, not silent replacement.

### asset-02
- [Independent validation](asset-02/reference-verification.json) (Git blob `58e21b979ee80bb2124e5f1eaee91f4adeb93195`)
- Original SHA-256: `ee3f4481c7d3259844659ee49d54899920a9c9698eddf8d0b93b951501701728`

| File | SHA-256 |
|---|---|
| background.png | `8a680c939f2c2bcd563f827cc7b43feb75a48742b1997fa7e48a4293d27fe938` |
| hair-left.png | `9b250fdc42eb0a573d70ae9795234f87f0761915403085e209a3e81bd398978c` |
| hair-right.png | `00695c819c10baa543ce737c85f68b4300d301e9e3f8b10e73980a84cf2d1aea` |
| skirt.png | `076e26117dc5a3dad9957b4301575933dc632036715485724d365a609a7c5497` |
| fixed.png | `d8c02c3afa8e7c4f9184065726dd6be27341faf46b945cc7153180ea3563e28e` |
| blouse-visible.png | `bcb4a60a55a35230347dfee999365a4354909440f9be7f957ba55c8bc604dd8d` |
| hem-trim.png | `76a5fc670be9230d7d62ad54c54035e50de47e4010471514f8de76f919257966` |
| uncertain.png | `0063a79bfacbf1e66271a669f956aa0df1016fb5c39ae536a000691b05aa8cb9` |
| landmarks.json | `7d89ab9f10e22e89928c1c2e0838f4d0dc23bd7b394b55228d343014ed835fdb` |
| manifest.json | `932df0f03586284d2233fa0de2fe07fcd09ab70298e54d45bf9a70d3a66d4268` |
| annotation-notes.md | `32e35c17fb22c544030921c4056b291e3810aad200e18936e4139fc2f6bc942b` |
| annotation-v3.py | `7ea830ec1da817a443e287ec91b59e0c5875f5d33b63e44e83f6d76fef0532c9` |

All other annotation evidence, verification scripts and overlays are also pinned by the full source commit above; any later reference revision requires explicit review, a new reference version and separate results, not silent replacement.
