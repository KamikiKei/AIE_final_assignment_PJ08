import matplotlib.pyplot as plt
import io
import base64
from collections import defaultdict
import logging
from sqlalchemy.orm import Session
from app.models import Comment
from sqlalchemy import func
from groq import Groq, AsyncGroq # Groqクライアントをインポート
from app.config import GROQ_API_KEY, GROQ_MODEL_NAME # config.pyからAPIキーとモデル名を読み込む

# 日本語フォントの設定 (既存)
plt.rcParams['font.family'] = 'Meiryo' # Windowsの場合の例
plt.rcParams['axes.unicode_minus'] = False # マイナス記号を正しく表示

# ロガーの設定 (既存)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Groqクライアントの初期化
groq_client = Groq(api_key=GROQ_API_KEY)

# app/analyze.py の get_comments_in_cluster 関数

# コメント詳細表示機能 (D3) に対応する関数
def get_comments_in_cluster(db: Session, cluster_id: int):
    logger.info(f"クラスタID {cluster_id} に属するコメントを取得します。")
    # cluster_id に基づいて、そのクラスタ内のすべてのコメントを取得
    comments_in_cluster = db.query(Comment).filter(
        Comment.cluster_id == cluster_id
    ).order_by(Comment.importance_score.desc(), Comment.id).all() # 重要度順に並べ替え

    # クラスタの代表文を抽出 (今回は重要度スコアが最も高いコメントを代表文とする)
    representative_text = None
    if comments_in_cluster:
        # importance_score が None のコメントがある可能性を考慮
        valid_comments_for_rep = [c for c in comments_in_cluster if c.importance_score is not None]
        if valid_comments_for_rep:
            representative_text = max(valid_comments_for_rep, key=lambda c: c.importance_score).text
        else:
            # 有効なスコアを持つコメントがなくても、少なくとも最初のコメントを代表とする
            representative_text = comments_in_cluster[0].text if comments_in_cluster else "代表コメントなし"
    
    formatted_comments = []
    for c in comments_in_cluster:
        formatted_tags = {}
        if c.tags:
            for tag_name, tag_value in c.tags.items():
                formatted_tags[tag_name] = tag_value 
        
        formatted_comments.append({
            "id": c.id,
            "text": c.text,
            "category": c.category,
            "danger": c.danger,
            "sentiment": c.sentiment,
            "importance_score": c.importance_score if c.importance_score is not None else 'N/A',
            "tags": formatted_tags
        })
    logger.info(f"クラスタID {cluster_id} から {len(formatted_comments)} 件のコメントを取得しました。")

    return {
        "cluster_id": cluster_id,
        "representative_text": representative_text,
        "comments": formatted_comments
    }

# ... (generate_pn_charts 関数は変更なし) ...
def generate_pn_charts(db: Session): # db セッションを引数で受け取るように変更
    logger.info("PN比グラフの生成を開始します。")
    comments = db.query(Comment).filter(Comment.sentiment != None).all()

    if not comments:
        logger.warning("コメントデータがありません。PN比グラフは生成されません。")
        return {
            "total_pn_chart": "",
            "category_pn_charts": {}
        }

    # 全体PN比の計算
    total_pos = sum(1 for c in comments if c.sentiment == 1)
    total_neg = sum(1 for c in comments if c.sentiment == 0)

    charts_data = {}

    # 1. 全体PN比グラフの生成
    if total_pos + total_neg > 0:
        fig_total, ax_total = plt.subplots(figsize=(6, 6))
        ax_total.pie([total_pos, total_neg], labels=["Positive", "Negative"], autopct="%1.1f%%", startangle=90, colors=['skyblue', 'lightcoral']) # 色をマイルドに
        ax_total.set_title("全体コメントPN比")
        buf_total = io.BytesIO()
        plt.savefig(buf_total, format="png", bbox_inches='tight')
        plt.close(fig_total) # 図をクローズ
        buf_total.seek(0)
        charts_data["total_pn_chart"] = base64.b64encode(buf_total.read()).decode()
        logger.info("全体PN比グラフを生成しました。")
    else:
        charts_data["total_pn_chart"] = ""
        logger.info("ポジティブ・ネガティブコメントがないため、全体PN比グラフは生成されませんでした。")

    # 2. カテゴリ別PN比グラフの生成 
    category_sentiment_counts = defaultdict(lambda: {"positive": 0, "negative": 0})
    for comment in comments:
        if comment.category and comment.sentiment is not None:
            if comment.sentiment == 1:
                category_sentiment_counts[comment.category]["positive"] += 1
            else:
                category_sentiment_counts[comment.category]["negative"] += 1
    
    charts_data["category_pn_charts"] = {}
    for category, counts in category_sentiment_counts.items():
        if counts["positive"] + counts["negative"] > 0:
            fig_cat, ax_cat = plt.subplots(figsize=(6, 6))
            ax_cat.pie([counts["positive"], counts["negative"]], labels=["Positive", "Negative"], autopct="%1.1f%%", startangle=90, colors=['skyblue', 'lightcoral']) # 色をマイルドに
            ax_cat.set_title(f"カテゴリ: {category} PN比")
            buf_cat = io.BytesIO()
            plt.savefig(buf_cat, format="png", bbox_inches='tight')
            plt.close(fig_cat) # 図をクローズ
            buf_cat.seek(0)
            charts_data["category_pn_charts"][category] = base64.b64encode(buf_cat.read()).decode()
            logger.info(f"カテゴリ '{category}' のPN比グラフを生成しました。")
        else:
            charts_data["category_pn_charts"][category] = ""
            logger.info(f"カテゴリ '{category}' にポジティブ・ネガティブコメントがないため、グラフは生成されませんでした。")

    return charts_data # 全体とカテゴリ別の両方のグラフデータを返す


# ... (get_top_clusters_and_comments 関数は変更なし) ...
async def get_top_clusters_and_comments(db: Session, top_n_clusters=5, comments_per_cluster=3): # ここに async を追加
    logger.info(f"上位 {top_n_clusters} の重要度クラスタを取得します。")
    
    cluster_scores = db.query(
        Comment.cluster_id,
        func.avg(Comment.importance_score).label('avg_score'), 
        func.count(Comment.id).label('comment_count')
    ).filter(
        Comment.importance_score != None,
        Comment.cluster_id != None,
        Comment.cluster_id != -1 
    ).group_by(Comment.cluster_id).order_by(func.avg(Comment.importance_score).desc()).limit(top_n_clusters).all()

    top_clusters_data = []
    for cluster_id, avg_score, comment_count in cluster_scores:
        cluster_comments = db.query(Comment).filter(
            Comment.cluster_id == cluster_id,
            Comment.importance_score != None
        ).order_by(Comment.importance_score.desc()).limit(comments_per_cluster).all()

        representative_text = "代表コメントなし"
        if  cluster_comments:
            valid_comments_for_rep = [c for c in cluster_comments if c.importance_score is not None]
            if valid_comments_for_rep:
                representative_text = max(valid_comments_for_rep, key=lambda c: c.importance_score).text
            else:
                representative_text = cluster_comments[0].text
        
        all_tags_in_cluster = set()
        merged_tags_in_cluster = {}
        for c in db.query(Comment).filter(Comment.cluster_id == cluster_id).all():
            if c.tags:
                merged_tags_in_cluster.update(c.tags) # 辞書を結合・上書き

        top_clusters_data.append({
            "cluster_id": cluster_id,
            "score": round(avg_score, 2),
            "representative_text": representative_text,
            "tags": merged_tags_in_cluster, # ★ここを修正: List[str] ではなく Dict[str, Any] を渡す★
            "comment_count": comment_count,
            "comments_examples": [{"id": c.id, "text": c.text, "importance_score": c.importance_score} for c in cluster_comments]
        })
        logger.info(f"クラスタID {cluster_id} のデータを取得しました。スコア: {round(avg_score, 2)}")

    return top_clusters_data

# ★★★ 新規追加関数: AI分析コメント生成 ★★★
async def generate_ai_analysis_comment(db: Session) -> str:
    logger.info("AI分析コメントの生成を開始します。")

    # ここで AsyncGroq クライアントをインスタンス化
    groq_client = AsyncGroq(api_key=GROQ_API_KEY) # ai_groq_client ではなく groq_client に変更

    # 全体PN比の取得
    total_pos = db.query(Comment).filter(Comment.sentiment == 1).count()
    total_neg = db.query(Comment).filter(Comment.sentiment == 0).count()
    total_comments = total_pos + total_neg

    pn_ratio_str = "コメントデータがありません。"
    if total_comments > 0:
        pos_percent = (total_pos / total_comments) * 100
        neg_percent = (total_neg / total_comments) * 100
        pn_ratio_str = f"全体コメントの約{pos_percent:.1f}%がポジティブ、約{neg_percent:.1f}%がネガティブです。"

    # カテゴリ別PN比の取得
    category_sentiment_counts = defaultdict(lambda: {"positive": 0, "negative": 0, "total": 0})
    categories = db.query(Comment.category).distinct().filter(Comment.category != None).all()
    for category_tuple in categories:
        category = category_tuple.category
        cat_pos = db.query(Comment).filter(Comment.sentiment == 1, Comment.category == category).count()
        cat_neg = db.query(Comment).filter(Comment.sentiment == 0, Comment.category == category).count()
        cat_total = cat_pos + cat_neg
        if cat_total > 0:
            category_sentiment_counts[category]["positive"] = cat_pos
            category_sentiment_counts[category]["negative"] = cat_neg
            category_sentiment_counts[category]["total"] = cat_total

    category_summary_str = "カテゴリ別のコメント傾向は見られません。"
    if category_sentiment_counts:
        cat_summaries = []
        for category, counts in category_sentiment_counts.items():
            if counts["total"] > 0:
                cat_pos_percent = (counts["positive"] / counts["total"]) * 100
                cat_neg_percent = (counts["negative"] / counts["total"]) * 100
                cat_summaries.append(f"「{category}」カテゴリでは、ポジティブが{cat_pos_percent:.1f}%、ネガティブが{cat_neg_percent:.1f}%です。")
        if cat_summaries:
            category_summary_str = " ".join(cat_summaries)

    # 重要度上位クラスタの取得 (代表文とスコア、タグ)
    top_clusters = await get_top_clusters_and_comments(db, top_n_clusters=3) # 上位3つのクラスタを見る
    cluster_summary_str = "重要度が高いコメントは特定されませんでした。"
    if top_clusters:
        cluster_summaries = []
        for cluster in top_clusters:
            tags_str = ", ".join(cluster["tags"]) if cluster["tags"] else "なし"
            cluster_summaries.append(
                f"スコア {cluster['score']:.2f} のクラスタ（代表コメント:「{cluster['representative_text']}」、タグ: {tags_str}）"
            )
        if cluster_summaries:
            cluster_summary_str = "重要度が高いコメント群がいくつか見つかりました。" + " ".join(cluster_summaries)

    # LLMへのプロンプト作成
    prompt = f"""
    オンライン授業の受講者コメントの分析結果に基づき、以下の情報から総合的な分析コメントを作成してください。
    ユーザーが改善点や傾向を素早く把握できるよう、要点をまとめて具体的に記述してください。また、ユーザが次に
    行うべきことをタスクとして出力してください。

    ---
    分析データ:
    全体PN比: {pn_ratio_str}
    カテゴリ別PN比: {category_summary_str}
    重要度が高いコメント群: {cluster_summary_str}
    ---

    分析コメント:
    """

    ai_analysis_comment = "分析コメントの生成に失敗しました。"
    try:
        # AsyncGroqクライアントを使用してAPIを呼び出す
        # 'await' と 'async for' が正しく使える
        completion = await groq_client.chat.completions.create( # await を使用
            model=GROQ_MODEL_NAME, 
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            stream=True # ストリーミングを有効にする
        )
        
        full_response_content = ""
        # 非同期イテレーターには 'async for' を使用
        async for chunk in completion: # ここを async for に変更
            if chunk.choices[0].delta.content:
                full_response_content += chunk.choices[0].delta.content
        ai_analysis_comment = full_response_content
        logger.info("AI分析コメントの生成が完了しました。")

    except Exception as e:
        logger.error(f"AI分析コメント生成中にエラーが発生しました: {e}", exc_info=True)
        ai_analysis_comment = "AI分析コメントの生成に失敗しました。詳細についてはログを確認してください。"

    return ai_analysis_comment