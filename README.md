# 講義アンケート　コメントピックアップアプリ PoC

## 概要
本プロジェクトは、オンライン授業中に収集された受講者コメント（CSV形式）を自動分類・分析し、改善に役立つ洞察を抽出・可視化する概念実証（PoC）システムです。

## 機能
- CSVファイルからのコメントアップロード
- 大規模言語モデル（LLM）によるコメントの自動分類（カテゴリ、危険性、感情）
- 文ベクトルとクラスタリングによるコメントの集約と代表文抽出
- タグ付けと重要度スコアの自動算出
- PN比グラフ（全体・カテゴリ別）の可視化
- 重要度ランキング形式での表示とコメント詳細閲覧
- AIによる分析コメントの生成
- 分析結果の履歴保存と過去の分析結果の閲覧
- 授業評価の変遷（時系列折れ線グラフ）表示

## 使用技術
- バックエンド: Python (FastAPI, SQLAlchemy, pandas, scikit-learn, sentence-transformers, groq)
- データベース: SQLite (PoC用)
- フロントエンド: React.js (CDN経由), Chart.js, Bootstrap 5

## セットアップ方法

1.  **リポジトリをクローンする**:
    ```bash
    git clone [https://github.com/あなたのGitHubユーザー名/あなたのリポジトリ名.git](https://github.com/あなたのGitHubユーザー名/あなたのリポジトリ名.git)
    cd あなたのリポジトリ名
    ```

2.  **仮想環境の作成とアクティベート**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **依存ライブラリのインストール**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **APIキーの設定**:
    Groq APIを使用します。`GROQ_API_KEY` 環境変数を設定してください。
    ```bash
    # Windows PowerShell (一時的)
    $env:GROQ_API_KEY="あなたのGroq APIキー"
    # macOS/Linux/Git Bash (一時的)
    export GROQ_API_KEY="あなたのGroq APIキー"
    # または、環境変数に永続的に設定
    ```
    `app/config.py` 内で `GROQ_MODEL_NAME` も確認してください。

## 実行方法

1.  **Uvicornサーバーを起動する**:
    ```bash
    uvicorn app.main:app --reload
    ```
2.  **ブラウザでアクセスする**:
    `http://127.0.0.1:8000/` にアクセスしてください。

## 使い方
1.  「CSVアップロード」セクションで、コメントが1列目にあるCSVファイルを選択し、「アップロード & 分析」ボタンをクリックします。
2.  分析が完了すると、自動的にホーム画面（時系列グラフ）が表示されます。
3.  サイドバーのナビゲーションリンクを使って、各分析結果（PN比グラフ、重要度ランキング、AI分析コメント）を切り替えて閲覧できます。
4.  「分析履歴」ページでは、過去の分析セッション一覧を確認し、クリックすることでその時点の分析結果を再表示できます。

## 今後の拡張（PoC終了後）
- 認証機能の追加
- 危険性の高いコメントの表示
- APIにお金をかけてリクエストを低遅延にする
- 重要度スコアの妥当性検証
- AIによるクラスタリングの妥当性検証
- より高度な分析機能（単語頻度分析、トピックモデリングなど）
- UI/UXの改善
