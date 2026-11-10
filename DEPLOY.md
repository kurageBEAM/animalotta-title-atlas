# サイト公開手順（GitHub Pages）

公開先（2026年11月9日に設定済み）

- リポジトリ: https://github.com/kurageBEAM/animalotta-title-atlas （Public）
- 公開URL: https://kuragebeam.github.io/animalotta-title-atlas/
- 設定: Settings → Pages → Deploy from a branch、`main` / `(root)`。`.nojekyll` を置いているので Jekyll の変換は行われず、ファイルがそのまま配信されます。

## 更新のしかた

このフォルダ（`D:\osu\Mapping\Anima`）はそのままリポジトリのクローンです。サイトを直したら次の手順で反映します。

1. 難易度やUIを変えた場合はビルドします。

```bash
python tools/build_difficulty.py
```

```bash
python tools/assemble_ui.py
```

   獲得状況を新しい画面画像で更新する場合は、先に `tools/snapshots.json` へ日付と新たに名前の出た枠（枠番号: 表示名）を追記し、次を実行してから上の2つを実行します。

```bash
python tools/apply_snapshot.py
```

```bash
python tools/export_assumptions.py
```

2. 変更をコミットしてプッシュします。

```bash
git add -A
```

```bash
git commit -m "変更内容を書く"
```

```bash
git push
```

3. 1〜2分で公開URLに反映されます（反映の状況は GitHub の Actions タブ「pages build and deployment」で確認できます）。

## 注意

- `.claude/` フォルダは `.gitignore` で除外しています（ローカルのプレビュー設定のみ）。
- 個人の獲得チェック・獲得日・手動補正は閲覧者のブラウザ（localStorage）に保存され、リポジトリには含まれません。端末を変えるときはサイトの「セーブデータ」から書き出したJSONを使ってください。
- 公開URLが変わると保存先（オリジン）も変わり、記録は引き継がれません。URLを変える前に必ずセーブデータを書き出してください。
- このサイトは非公式の個人用資料です。出典URLを明記したまま公開してください。
