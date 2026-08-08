🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

gazette-drouot.com の1つまたは複数のルブリック（記事一覧）ページを監視し、新着または更新された記事があるたびに Windows 通知を表示します——通知をクリックすると既定のブラウザーで開きます。

## 仕組み

- 毎回の実行で、設定された各ルブリックの最初の `MAX_PAGES` ページ分の一覧を完全にスキャンします（「既知」の記事が見つかるまでではありません——このサイトのページ送りは必ずしも時系列順ではないことがテストで判明しており、早期に停止すると本当に新しい記事を見逃す可能性があるためです）。
- 見つかった各記事は、その数値 id と発行日の両方で保存済みの状態（`state/<rubrique-key>.json`）と比較されます。新しい id → 通知します。既知の id だが前回と日付が異なる → 再度通知します（記事が再公開/編集された可能性が高いです）。日付が全く表示されていない記事は一度だけ通知され、以後は二度と確認されません。
- あるルブリックの初回実行では、現在存在する内容を基準として静かに記録するだけです——インストール時に既存の記事で通知が殺到することはありません。
- 1回の実行であるルブリックに `FLOOD_CAP` を超える新着/更新記事が見つかった場合、最初の数件のみが個別に通知され、残りは1件の「他に N 件の新着記事」というまとめ通知に集約されます。

## セットアップ

- 実行中は **VPN をオフにする必要があります**——Cloudflare は自動化では突破できないインタラクティブな認証を VPN の IP に強制します。通常の自宅 IP なら問題なく通過します。
- Microsoft Edge がインストールされている必要があります（Playwright の `channel="msedge"` を通じてシステムの Edge を直接使用するため、別途ブラウザーをダウンロードする必要はありません）。
- `pip install -r requirements.txt`

## 設定

**すべての設定は `gazette_watcher/config.py` という1つのファイルで編集します**：監視するページ、確認頻度、スキャンの深さ、通知の上限、警告のクールダウンなど——各設定には説明コメントが付いています。ここでの変更は次回の実行時に反映されますが、**例外として** `POLL_INTERVAL_MINUTES` を変更した場合は、実際の Windows タスク スケジューラのタスクを更新するために `install_task.ps1` をもう一度実行する必要があります。

## コントロールパネル（GUI）

PowerShell や config.py を直接操作することなく、以下をすべて行えるデスクトップウィンドウです：スケジュールされたタスクのインストール／有効化／無効化／アンインストール、そして設定ファイルを手動で編集する代わりに使える設定パネル（何か問題が起きた場合の「既定値に戻す」機能付き）。旗のアイコンでインターフェースの言語を切り替えられます（英語、中文、Español、हिन्दी、العربية、Português、Русский、Français、日本語、ドイツ語——既定では Windows の表示言語に従い、対応していない場合は英語にフォールバックします）。太陽/月のアイコンでライト/ダークモードを切り替えられます（既定では Windows のテーマに従います）。両方の選択は `gui_prefs.json` に保存されます。

**`.exe` だけをお持ちの場合：** `GazetteDrouotWatcherGUI.exe` をダブルクリックするだけで、他に何もインストールする必要はありません。このファイルは、`gazette_watcher/` や `install_task.ps1` などと同じ、このプロジェクトフォルダーの直下に置いてください。

**代わりにソースから実行する場合：** `gui.pyw` をダブルクリックするか（Windows は `.pyw` ファイルを `pythonw.exe` 経由で実行するため、コンソールウィンドウは表示されません）、次のコマンドを実行してください：
```
pythonw.exe gui.pyw
```

**`.exe` を自分でビルドする場合**（gitignore で除外されているためソースには含まれていません。自分で再ビルドするか、Release からダウンロードしてください）：
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcherGUI --icon icon.ico gui.pyw
```
その後、`dist/GazetteDrouotWatcherGUI.exe` をプロジェクトのルート（`gui.pyw` と同じ場所）にコピーし、残った `build/`、`dist/`、`*.spec` を削除してください。

## 手動実行

```
python -m gazette_watcher.watcher
```

## スケジュール設定

`install_task.ps1` を実行すると、「GazetteDrouotWatcher」というタスクがタスク スケジューラに登録され、ログオン中は `config.py` で設定した間隔で実行されます。すでに登録済みのタスクを更新したい場合（`POLL_INTERVAL_MINUTES` を変更した後など）は、いつでも再実行してください。

```
powershell -ExecutionPolicy Bypass -File install_task.ps1
```

テスト用にすぐ1回だけ実行する場合：
```
powershell -Command "Start-ScheduledTask -TaskName GazetteDrouotWatcher"
```

`uninstall_task.ps1` で削除できます：
```
powershell -ExecutionPolicy Bypass -File uninstall_task.ps1
```

## 問題が発生した場合

問題が長く続いても毎回の実行で通知が殺到しないように、それぞれ `ALERT_COOLDOWN_HOURS`（config.py）につき最大1回に制限された、2種類の異なる警告通知があります：

- **「blocked by Cloudflare」**——サイトのボット対策がリクエストを遮断しました。ほとんどの場合、VPN をオフにすれば解決します。
- **「needs an update」**——ページ自体は正常に読み込まれましたが、その HTML がこのスクリプトの想定と一致しなくなっています。おそらく gazette-drouot.com がページのレイアウトを変更したため、スクレイパーのセレクター（`gazette_watcher/scraper.py`）を合わせて更新する必要があります。

`logs/watcher.log` には毎回の実行の詳細がすべて記録されています——通知が来なくなった場合は、まずここを確認してください。

## 実際のサイトに触れずにテストする

`test/` には、スクレイピング/通知ロジックを実際のサイトに負荷をかけたり最新のコンテンツに依存したりせずに単独でテストできる、小さなローカルの疑似サイトのテスト環境が含まれています。詳しくは `test/README.md` を参照してください。

## 監視するページを追加する

`config.py` の `RUBRIQUES` に新しい項目を追加するだけです——そのページが同じ `div.articleResume` カード構造を使っている限り、他に変更する必要はありません。
