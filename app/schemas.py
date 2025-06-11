from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime

# Comment モデルのPydanticスキーマ（部分的な表示用）
class CommentBase(BaseModel):
    id: int
    text: str
    category: Optional[str] = None
    danger: Optional[bool] = None
    sentiment: Optional[int] = None
    importance_score: Optional[float] = None
    tags: Optional[Dict[str, Any]] = None # ここは既に Dict[str, Any] でOK

    class Config:
        orm_mode = True
# クラスタ内のコメント詳細表示用
class ClusterCommentDetail(BaseModel):
    id: int
    text: str
    category: Optional[str] = None
    danger: Optional[bool] = None
    sentiment: Optional[int] = None
    importance_score: Optional[float] = None
    tags: Optional[Dict[str, Any]] = None # ここも既に Dict[str, Any] でOK

    class Config:
        orm_mode = True

# 重要度ランキングのクラスタデータ用
# 重要度ランキングのクラスタデータ用
class TopClusterResult(BaseModel):
    cluster_id: int
    score: float
    representative_text: str
    tags: Optional[Dict[str, Any]] = None # List[str] から Optional[Dict[str, Any]] に変更
    comment_count: int
    comments_examples: List[ClusterCommentDetail]

    class Config:
        orm_mode = True # ORMモデルのインスタンスを直接扱う場合
# PN比グラフのBase64文字列用
class PnChartsResult(BaseModel):
    total_pn_chart: str
    category_pn_charts: Dict[str, str]

# AnalysisSession モデルのPydanticスキーマ
class AnalysisSessionBase(BaseModel):
    id: int
    csv_filename: str
    created_at: datetime
    total_comments: int
    overall_positive_percent: float
    overall_negative_percent: float
    category_sentiment_percents: Optional[Dict[str, float]] = None
    dangerous_comment_count: int

    class Config:
        orm_mode = True

# APIから返される分析結果全体
class AnalysisResult(BaseModel):
    pn_charts: PnChartsResult
    top_clusters: List[TopClusterResult]

# APIから返されるAI分析コメント
class AiAnalysisCommentResult(BaseModel):
    comment: str

# APIから返される時系列データ
class TimeSeriesDataResult(BaseModel):
    dates: List[str]
    overall_positive_percents: List[float]
    category_positive_percents: Dict[str, List[Dict[str, Any]]] # {category: [{date: "...", percent: X.X}, ...]}

# APIから返される履歴リストの各項目
class AnalysisSessionListItem(BaseModel):
    id: int
    csv_filename: str
    created_at: datetime
    total_comments: int
    overall_positive_percent: float
    overall_negative_percent: float
    dangerous_comment_count: int

    class Config:
        orm_mode = True
        
class ClusterDetailsResponse(BaseModel):
    cluster_id: int
    representative_text: str
    comments: List[ClusterCommentDetail] # ClusterCommentDetail は既に定義済み

    class Config:
        orm_mode = True # ORMモデルのインスタンスを直接扱う場合