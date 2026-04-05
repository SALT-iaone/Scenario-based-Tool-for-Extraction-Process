# MySQL → CSV Exporter

MySQL からデータを取得し、CSV として書き出すデスクトップアプリです。  
**Mac / Windows 両対応** · Python 3.8 以上で動作します。

---

## 必要なもの

| ツール | バージョン |
|--------|-----------|
| Python | 3.8 以上 |
| pip    | 最新推奨   |

---

## セットアップ

```bash
# 1. 依存パッケージをインストール
pip install -r requirements.txt

# 2. アプリを起動
python main.py
```

---

## 使い方

### 1. 接続設定

| 項目 | 説明 |
|------|------|
| Host | MySQL サーバーのホスト名 / IP |
| Port | ポート番号（デフォルト: 3306）|
| User | ユーザー名 |
| Password | パスワード |
| Database | 接続先データベース名 |

「**接続**」ボタンで接続 → 成功するとテーブル一覧が表示されます。

### 2. プロファイル保存

接続情報を名前付きで保存できます（パスワードは保存されません）。  
設定は `~/.mysql_csv_exporter/connections.json` に保存されます。

### 3. テーブル選択

左下の一覧からテーブルをクリックすると、SQL エディタに  
`SELECT * FROM テーブル名 LIMIT 1000;` が自動入力されます。

### 4. SQL 編集

SQL エディタで自由に編集できます。任意の SELECT 文が使えます。

```sql
-- 例: 条件指定
SELECT id, name, email FROM users WHERE created_at > '2024-01-01' ORDER BY id;

-- 例: JOIN
SELECT o.id, u.name, o.total FROM orders o JOIN users u ON o.user_id = u.id;
```

### 5. エクスポート設定

| 設定 | 選択肢 |
|------|--------|
| エンコーディング | UTF-8 (BOM付き) / UTF-8 / Shift-JIS |
| 区切り文字 | カンマ / タブ / セミコロン |

> **Excel で開く場合は「UTF-8 (BOM)」を推奨**  
> BOM なし UTF-8 は文字化けすることがあります。

### 6. CSV 書き出し

「**⬇ CSV エクスポート**」ボタン → 保存先を選択 → 完了！

---

## トラブルシューティング

### `ModuleNotFoundError: No module named 'mysql'`
```bash
pip install mysql-connector-python
```

### Windows で日本語が文字化けする
エンコーディングを「UTF-8 (BOM)」または「Shift-JIS」に変更してください。

### 接続タイムアウトになる
- ホスト・ポートが正しいか確認
- ファイアウォールで 3306 番ポートが開いているか確認
- MySQL の `bind-address` 設定を確認

---

## ファイル構成

```
mysql_csv_exporter/
├── main.py   # メインアプリ
├── requirements.txt  # 依存パッケージ
└── README.md         # このファイル
```

接続プロファイルはホームディレクトリの `~/.mysql_csv_exporter/` に保存されます。
