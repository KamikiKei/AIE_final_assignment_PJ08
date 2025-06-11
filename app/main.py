from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os, shutil, pandas as pd
from sqlalchemy.orm import Session
from app.config import SessionLocal, UPLOAD_DIR, engine
from app.models import Comment, Base, AnalysisSession
from app.crud import save_comments_from_csv
from app.llm import label_comments
from app.cluster import cluster_comments
from app.scoring import calculate_importance_scores
from app.analyze import generate_pn_charts, get_top_clusters_and_comments, get_comments_in_cluster, generate_ai_analysis_comment
import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict

# スキーマのインポートを追加
from app.schemas import (
    AnalysisResult,
    AiAnalysisCommentResult,
    ClusterCommentDetail,
    TimeSeriesDataResult,
    AnalysisSessionListItem,
    PnChartsResult,
    ClusterDetailsResponse, TopClusterResult,
    )

from typing import List, Dict, Optional, Any # 念のため Dict, Any も確認
from collections import defaultdict

logger = logging.getLogger(__name__)

if logging.root.handlers:
    for handler in logging.root.handlers:
        handler.setLevel(logging.DEBUG)
    logging.root.setLevel(logging.DEBUG)
else:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    
app = FastAPI()
templates = Jinja2Templates(directory="templates")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="templates"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def handle_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSVファイルのみアップロード可能です。")

    filepath = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイルの保存中にエラーが発生しました: {e}")

    try:
        df = pd.read_csv(filepath)
        if df.empty or df.iloc[:, 0].isnull().all():
            raise HTTPException(status_code=400, detail="CSVファイルが空であるか、コメントデータが含まれていません。")
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSVファイルが空です。")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSVファイルの読み込み中にエラーが発生しました。フォーマットを確認してください: {e}")

    try:
        saved_count = save_comments_from_csv(db, df)
        
        logger.info("LLMによるラベル付けを開始します。")
        await label_comments(db)
        logger.info("LLMによるラベル付けが完了しました。")

        logger.info("コメントのクラスタリングを開始します。")
        logger.debug(f"cluster_comments の型: {type(cluster_comments)}")
        await cluster_comments(db)
        logger.info("コメントのクラスタリングが完了しました。")

        logger.debug("calculate_importance_scores を呼び出す直前です。")
        await calculate_importance_scores(db) 
        logger.info("重要度スコアの計算が完了しました。")

        # --- 分析結果を取得し、AnalysisSession に保存するロジック ---
        logger.info("分析結果の最終取得と保存を開始します。")
        
        # PN比グラフデータを取得
        # generate_pn_chartsは同期関数だが、Pydanticスキーマに合うように辞書を構築
        pn_charts_data_raw = generate_pn_charts(db)
        
        # 重要度ランキングデータを取得
        top_clusters_ranking_raw = await get_top_clusters_and_comments(db)
        
        # AI分析コメントを取得
        ai_analysis_comment_text = await generate_ai_analysis_comment(db)

        # 総コメント数を取得
        total_comments_count = db.query(Comment).count()
        
        # 全体PN比のパーセンテージを計算 (時系列グラフ用)
        total_pos = db.query(Comment).filter(Comment.sentiment == 1).count()
        total_neg = db.query(Comment).filter(Comment.sentiment == 0).count()
        overall_pos_percent = (total_pos / total_comments_count * 100) if total_comments_count > 0 else 0.0
        overall_neg_percent = (total_neg / total_comments_count * 100) if total_comments_count > 0 else 0.0

        # カテゴリ別PN比のパーセンテージを計算 (時系列グラフ用)
        category_sentiment_percents = {}
        categories = db.query(Comment.category).distinct().filter(Comment.category != None).all()
        for category_tuple in categories:
            category = category_tuple.category
            cat_total = db.query(Comment).filter(Comment.category == category).count()
            cat_pos = db.query(Comment).filter(Comment.sentiment == 1, Comment.category == category).count()
            cat_pos_percent = (cat_pos / cat_total * 100) if cat_total > 0 else 0.0
            category_sentiment_percents[category] = cat_pos_percent # カテゴリ別のポジティブ比率のみを保存

        # 危険コメント数を取得
        dangerous_comment_count = db.query(Comment).filter(Comment.danger == True).count()

        # AnalysisSession オブジェクトを作成し、データベースに保存
        new_analysis_session = AnalysisSession(
            csv_filename=file.filename,
            total_comments=total_comments_count,
            total_pn_chart_base64=pn_charts_data_raw["total_pn_chart"],
            category_pn_charts_base64=pn_charts_data_raw["category_pn_charts"],
            top_clusters_data=top_clusters_ranking_raw,
            ai_analysis_comment=ai_analysis_comment_text,
            overall_positive_percent=overall_pos_percent,
            overall_negative_percent=overall_neg_percent,
            category_sentiment_percents=category_sentiment_percents,
            dangerous_comment_count=dangerous_comment_count
        )
        db.add(new_analysis_session)
        db.commit()
        logger.info(f"分析セッションID {new_analysis_session.id} をデータベースに保存しました。")

    except TypeError as te:
        logger.error(f"分析パイプライン実行中にTypeErrorが発生しました: {te}. 関数が非同期関数として認識されていない可能性があります。", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析パイプライン実行中にエラーが発生しました: {te}")
    except Exception as e:
        logger.error(f"分析パイプライン実行中に予期せぬエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"コメントの処理中にエラーが発生しました: {e}")
    
    return RedirectResponse(url="/", status_code=303)

# --- 分析結果提供用のAPIエンドポイント ---
# response_model を追加して、スキーマに準拠したレスポンスを強制する
@app.get("/api/analysis_results", response_model=AnalysisResult)
async def get_analysis_results(session_id: int | None = None, db: Session = Depends(get_db)):
    logger.info(f"API: /api/analysis_results が呼び出されました。Session ID: {session_id}")
    try:
        # 特定のセッションIDが指定された場合、その履歴データを取得
        if session_id is not None:
            analysis_session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if not analysis_session:
                raise HTTPException(status_code=404, detail="Analysis session not found")
            
            # Pydanticスキーマに合うようにデータを整形して返す
            return AnalysisResult(
                pn_charts=PnChartsResult(
                    total_pn_chart=analysis_session.total_pn_chart_base64,
                    category_pn_charts=analysis_session.category_pn_charts_base64
                ),
                top_clusters=analysis_session.top_clusters_data # ORMモードで自動変換されることを期待
            )
        else:
            # 最新の分析結果を取得 (履歴から取得)
            latest_session = db.query(AnalysisSession).order_by(AnalysisSession.created_at.desc()).first()
            if not latest_session:
                raise HTTPException(status_code=404, detail="No analysis results found. Please upload a CSV first.")
            
            return AnalysisResult(
                pn_charts=PnChartsResult(
                    total_pn_chart=latest_session.total_pn_chart_base64,
                    category_pn_charts=latest_session.category_pn_charts_base64
                ),
                top_clusters=latest_session.top_clusters_data # ORMモードで自動変換されることを期待
            )
    except Exception as e:
        logger.error(f"API /api/analysis_results 処理中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析結果の取得中にエラーが発生しました: {e}")

@app.get("/api/cluster_details/{cluster_id}", response_model=ClusterDetailsResponse) # response_model を新しいスキーマに変更
async def get_cluster_details_api(cluster_id: int, session_id: int | None = None, db: Session = Depends(get_db)):
    logger.info(f"API: /api/cluster_details/{cluster_id} が呼び出されました。Session ID: {session_id}")
    try:
        # get_comments_in_cluster は既に辞書を返します
        details = get_comments_in_cluster(db, cluster_id)
        
        # ClusterDetailsResponse スキーマのインスタンスとして返す
        return ClusterDetailsResponse(**details) # ここで辞書をスキーマに変換
    except Exception as e:
        logger.error(f"API /api/cluster_details/{cluster_id} 処理中にエラーが発生しました: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"クラスタ詳細の取得中にエラーが発生しました: {e}")

@app.get("/api/ai_analysis_comment", response_model=AiAnalysisCommentResult)
async def get_ai_analysis_comment_api(session_id: int | None = None, db: Session = Depends(get_db)):
    logger.info(f"API: /api/ai_analysis_comment が呼び出されました。Session ID: {session_id}")
    try:
        if session_id is not None:
            analysis_session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if not analysis_session:
                raise HTTPException(status_code=404, detail="Analysis session not found")
            return AiAnalysisCommentResult(comment=analysis_session.ai_analysis_comment)
        else:
            latest_session = db.query(AnalysisSession).order_by(AnalysisSession.created_at.desc()).first()
            if not latest_session:
                raise HTTPException(status_code=404, detail="No analysis results found. Please upload a CSV first.")
            return AiAnalysisCommentResult(comment=latest_session.ai_analysis_comment)
    except Exception as e:
        logger.error(f"API /api/ai_analysis_comment 処理中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI分析コメントの取得中にエラーが発生しました: {e}")

# 新規追加APIエンドポイント: 履歴リスト取得
@app.get("/api/analysis_sessions", response_model=List[AnalysisSessionListItem])
async def get_analysis_sessions_list(db: Session = Depends(get_db)):
    logger.info("API: /api/analysis_sessions が呼び出されました。")
    try:
        sessions = db.query(AnalysisSession).order_by(AnalysisSession.created_at.desc()).all()
        # ORMモードが有効なため、直接リストを返すことでPydanticが自動変換する
        return sessions 
    except Exception as e:
        logger.error(f"API /api/analysis_sessions 処理中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析セッション履歴の取得中にエラーが発生しました: {e}")

# 新規追加APIエンドポイント: 時系列データ取得
@app.get("/api/time_series_data", response_model=TimeSeriesDataResult)
async def get_time_series_data(db: Session = Depends(get_db)):
    logger.info("API: /api/time_series_data が呼び出されました。")
    try:
        sessions = db.query(AnalysisSession).order_by(AnalysisSession.created_at.asc()).all()

        dates = []
        overall_positive_percents = []
        category_positive_percents: Dict[str, List[Dict[str, Any]]] = defaultdict(list) # 型ヒントを追加

        for s in sessions:
            dates.append(s.created_at.isoformat())
            overall_positive_percents.append(round(s.overall_positive_percent, 1))
            
            if s.category_sentiment_percents:
                # category_sentiment_percents は DBからJSONとしてロードされるので、辞書として直接アクセス可能
                for category, percent in s.category_sentiment_percents.items():
                    category_positive_percents[category].append({"date": s.created_at.isoformat(), "percent": round(percent, 1)})

        return TimeSeriesDataResult(
            dates=dates,
            overall_positive_percents=overall_positive_percents,
            category_positive_percents=category_positive_percents
        )
    except Exception as e:
        logger.error(f"API /api/time_series_data 処理中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"時系列データの取得中にエラーが発生しました: {e}")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)