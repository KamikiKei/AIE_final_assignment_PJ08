from sentence_transformers import SentenceTransformer
# from sklearn.cluster import DBSCAN # HDBSCANを使用する場合は不要
import hdbscan # HDBSCANを使用する場合にインポート
import pickle
import logging # ロギングのためのインポート
from sqlalchemy.orm import Session
from app.models import Comment
from app.config import MIN_CLUSTER_SIZE, EMBEDDING_MODEL_NAME # config.py から設定を読み込むことを想定

# ロガーの設定
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Sentence-BERTモデルのロード
# 要件定義書に記載のモデル名を使用
model = SentenceTransformer(EMBEDDING_MODEL_NAME) # 'all-MiniLM-L6-v2' など

async def cluster_comments(db: Session): # ここに async を追加
    logger.info("クラスタリングを開始します。") # main.py との重複を避けるため、cluster.py での開始ログはより詳細に
    comments_to_cluster = db.query(Comment).filter(Comment.sentiment != None).all()
    
    if not comments_to_cluster:
        logger.info("クラスタリングすべきコメントはありません。")
        return

    logger.info(f"{len(comments_to_cluster)} 件のコメントをクラスタリングします。")

    texts = [c.text for c in comments_to_cluster]
    # sentence-transformers の encode メソッドは通常同期的に動作しますが、
    # 大規模なデータセットではI/Oバウンドになり得るため、非同期の実行コンテキストで呼び出すことが推奨される場合もあります。
    # しかし、ここではモデルの推論自体はCPU/GPUバウンドなので、そのまま呼び出します。
    embeddings = model.encode(texts, convert_to_numpy=True)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE, metric='euclidean', cluster_selection_epsilon=0.0)
    labels = clusterer.fit_predict(embeddings)

    noise_count = 0
    clustered_comment_count = 0
    unique_clusters = set()

    for i, (comment, label) in enumerate(zip(comments_to_cluster, labels)):
        comment.cluster_id = int(label)
        comment.embedding = pickle.dumps(embeddings[i])

        if label == -1:
            noise_count += 1
        else:
            clustered_comment_count += 1
            unique_clusters.add(label)
        
        db.add(comment)
        
    try:
        db.commit()
        logger.info(f"コメントのクラスタリングが完了しました。")
        logger.info(f"  総コメント数: {len(comments_to_cluster)}")
        logger.info(f"  生成されたクラスタ数: {len(unique_clusters)}")
        logger.info(f"  ノイズとして分類されたコメント数: {noise_count}")
        logger.info(f"  クラスタリングされたコメント数: {clustered_comment_count}")

    except Exception as e:
        db.rollback()
        logger.error(f"コメントのクラスタリング結果のコミット中にエラーが発生しました: {e}", exc_info=True)