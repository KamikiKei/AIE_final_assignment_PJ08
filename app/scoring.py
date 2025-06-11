import logging
from sqlalchemy.orm import Session
from app.models import Comment

# ロガーの設定
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def calculate_importance_scores(db: Session):
    """
    データベース内のコメントに対して重要度スコアを計算し、保存する。
    重要度 = 緊急性 × (質問 + インフラ + 具体的)
    """
    logger.info("重要度スコアの計算を開始します。")

    # タグが設定されている（または設定されるべき）コメントを取得
    # LLM処理が完了したコメントを対象とします。
    comments_to_score = db.query(Comment).filter(Comment.sentiment != None).all()

    if not comments_to_score:
        logger.info("スコアを計算すべきコメントがありません。")
        return

    updated_count = 0
    for comment in comments_to_score:
        if comment.tags: # tagsカラムにデータがある場合
            try:
                # tags は JSON タイプとして定義されているため、Pythonの辞書としてアクセス可能
                tags_data = comment.tags
                logger.info(f"コメントID {comment.id} のタグデータ: {tags_data}") # 追加: タグデータを確認

                # 各タグの値を取得。get() を使ってキーが存在しない場合もエラーにならないようにデフォルト値を設定
                urgency = int(tags_data.get('緊急性', 0))
                question = int(tags_data.get('質問', 0))
                infrastructure = int(tags_data.get('インフラ', 0))
                concrete = int(tags_data.get('具体的', 0))

                logger.debug(f"コメントID {comment.id} のタグ値: 緊急性={urgency}, 質問={question}, インフラ={infrastructure}, 具体的={concrete}") # DEBUGレベルで詳細ログ

                # 重要度スコアの計算式: 緊急性 × (質問 + インフラ + 具体的)
                # 要件定義書に記載された式に基づきます [cite: 9, 30]
                importance_score = float(urgency * (question + infrastructure + concrete))
                
                comment.importance_score = importance_score
                db.add(comment) # 更新されたコメントオブジェクトをセッションに追加
                updated_count += 1
            except Exception as e:
                logger.error(f"コメントID {comment.id} の重要度スコア計算中にエラーが発生しました: {e}", exc_info=True)
                # エラーが発生したコメントのスコアはNoneのままにするか、0に設定するなど、適切なフォールバックを検討
                comment.importance_score = 0.0 # エラー時は0に設定する例
                db.add(comment)
        else:
            # tagsがない、またはNoneの場合はスコアを0とする
            comment.importance_score = 0.0
            db.add(comment)
            logger.warning(f"コメントID {comment.id} にタグデータがないため、重要度スコアを0に設定しました。")

    try:
        db.commit() # すべての更新をまとめてコミット
        logger.info(f"重要度スコアの計算が完了しました。{updated_count} 件のコメントが更新されました。")
    except Exception as e:
        db.rollback() # コミット中にエラーが発生したらロールバック
        logger.error(f"重要度スコア結果のコミット中にエラーが発生しました: {e}", exc_info=True)