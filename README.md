# S.T.E.P.
**Scenario-based Tool for Extraction Process**

MySQL からデータを取得し、CSV として書き出すデスクトップアプリです。  
**Mac / Windows 両対応** · Python 3.8 以上で動作します。

---

## 必要なもの

| ツール | バージョン |
|--------|-----------|
| Python | 3.8 以上  |
| pip    | 最新推奨   |

---

## セットアップ（開発・直接実行）

```bash
# 1. 依存パッケージをインストール
pip install -r requirements.txt

# 2. アプリを起動
python main.py
```

---

## 機能一覧

### 接続

- MySQL への直接接続
- SSH トンネル経由接続（秘密鍵 / パスワード認証）
- ジャンプサーバー（踏み台）を経由した多段 SSH 接続
- MySQL SSL/TLS（CA証明書・クライアント証明書・秘密鍵）
- 接続プロファイルの保存・切り替え（パスワードも保存）

### シナリオ

- シナリオ単位で SQL を管理（追加・名前変更・複製・削除）
- 選択中シナリオを単体で実行
- 全シナリオを一括実行し、シナリオ名ごとに CSV を出力
- プリセットファイル（JSON）への書き出し・読み込み

### 変数

- `{変数名}` 形式で SQL 内に変数を埋め込み
- 実行時に全シナリオへ一括適用
- 例：`WHERE created_at >= '{start_date}'`
- 変数はアプリ終了後も自動保存・復元

### CSV 出力

- エンコーディング：UTF-8 (BOM付き) / UTF-8 / Shift-JIS
- 区切り文字：カンマ / タブ / セミコロン

---

## 使い方

### 1. 接続設定

**MySQL タブ**で接続情報を入力します。

| 項目     | 説明                             |
|----------|----------------------------------|
| Host     | MySQL サーバーのホスト名 / IP    |
| Port     | ポート番号（デフォルト: 3306）   |
| User     | ユーザー名                       |
| Password | パスワード                       |
| Database | 接続先データベース名             |

SSH トンネルを使う場合は **SSH タブ**、ジャンプサーバーを経由する場合は **Jump タブ**で設定します。

接続情報は「**保存**」ボタンでプロファイルに名前をつけて保存できます。

### 2. シナリオと SQL

左中列のシナリオ一覧からシナリオを選択すると、右の SQL エディタに切り替わります。  
テーブル一覧からテーブルをクリックすると SQL が自動入力されます。

### 3. 変数

変数パネルで `{変数名} = 値` を設定すると、実行する全シナリオの SQL に一括で適用されます。

```sql
-- 例
SELECT * FROM orders
WHERE created_at >= '{start_date}'
  AND user_id = {user_id};
```

### 4. プリセットの書き出し・読み込み

シナリオパネル右上の **↑ 書き出し** / **↓ 読み込み** ボタンで、シナリオと変数をまとめた JSON ファイルを共有できます。

読み込み時は「置き換え」または「追加」を選択できます。

### 5. CSV エクスポート

- **▶ 選択を実行**：選択中のシナリオのみ実行、保存先を指定
- **▶▶ 全シナリオ実行**：全シナリオを順次実行、出力フォルダを1回指定するだけで `シナリオ名.csv` として個別に保存

---

## ビルド（アプリとしてパッケージング）

Python なしで起動できる単体アプリを作成できます。  
ビルドは **それぞれの OS 上で実行する必要があります**（Mac で `.app`、Windows で `.exe`）。

### Mac (.app)

```bash
bash build.sh
```

完了すると `dist/STEP.app` が生成されます。  
`/Applications` にドラッグ＆ドロップすれば Launchpad からも起動できます。

**初回起動時のセキュリティ警告について**

Apple の署名がないため、初回は警告が表示されます。

```
"STEP.app" は開発元を確認できないため開けません
```

回避方法：**右クリック → 開く → 開く** を選択するか、以下のコマンドを実行します：

```bash
xattr -cr dist/STEP.app
```

### Windows (.exe)

`build.bat` をダブルクリックするか、コマンドプロンプトで実行します。

```bat
build.bat
```

完了すると `dist\STEP\STEP.exe` が生成されます。

### spec ファイルを使ったビルド（上級者向け）

`STEP.spec` を直接使うと細かい設定を変えた再ビルドが高速に行えます。

```bash
pyinstaller STEP.spec
```

---

## ファイル構成

```
S.T.E.P./
├── main.py          # メインアプリ
├── requirements.txt # 依存パッケージ
├── build.sh         # Mac 用ビルドスクリプト
├── build.bat        # Windows 用ビルドスクリプト
├── STEP.spec        # PyInstaller spec ファイル
└── README.md        # このファイル
```

設定・プリセットは以下に自動保存されます：

```
~/.step_tool/
├── connections.json  # 接続プロファイル
├── scenarios.json    # シナリオ一覧
└── variables.json    # 変数
```

---

## トラブルシューティング

### `ModuleNotFoundError: No module named 'mysql'`
```bash
pip install mysql-connector-python
```

### SSH 接続エラー `module 'paramiko' has no attribute 'DSSKey'`
paramiko 3.x では DSSKey が削除されています。2.x を使用してください：
```bash
pip install "paramiko>=2.11.0,<3.0.0" --force-reinstall
```

### Windows で日本語が文字化けする
エンコーディングを「UTF-8 (BOM)」または「Shift-JIS」に変更してください。

### Mac でウィンドウが表示されない
Tkinter が不足している場合があります：
```bash
brew install python-tk
```
