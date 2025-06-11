from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, create_engine, LargeBinary, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func as sa_func # SQLAlchemyのfuncをインポートし、名前が衝突しないように別名をつける

Base = declarative_base()

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, nullable=False)
    category = Column(String)
    danger = Column(Boolean)
    sentiment = Column(Integer)
    embedding = Column(LargeBinary)
    cluster_id = Column(Integer)
    tags = Column(JSON)
    importance_score = Column(Float)

# ★★★ ここから新しいモデルを追加 ★★★
class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 分析を行ったCSVファイル名（参照用）
    csv_filename = Column(String, nullable=False)
    # 分析実行日時
    created_at = Column(DateTime, server_default=sa_func.now())
    # 関連するコメントの総数
    total_comments = Column(Integer)
    # 全体PN比グラフのBase64文字列
    total_pn_chart_base64 = Column(String)
    # カテゴリ別PN比グラフのBase64文字列 (JSON形式で辞書として保存)
    category_pn_charts_base64 = Column(JSON)
    # 重要度上位クラスタのデータ (JSON形式でリストとして保存)
    top_clusters_data = Column(JSON)
    # AI分析コメント
    ai_analysis_comment = Column(String)
    # ポジティブ、ネガティブのパーセンテージを数値で保存 (時系列グラフ用)
    overall_positive_percent = Column(Float)
    overall_negative_percent = Column(Float)
    # カテゴリ別PN比を数値で保存 (時系列グラフ用、JSON形式で辞書として保存)
    category_sentiment_percents = Column(JSON)
    # その他の概要情報 (例: 危険コメント数など、必要に応じて追加)
    dangerous_comment_count = Column(Integer)
