from sqlalchemy.orm import Session # Session をインポート
from app.models import Comment
import pandas as pd
# from app.config import SessionLocal # 依存性注入を使うので不要になる

def save_comments_from_csv(db: Session, df) -> int: # セッションを引数で受け取り、int を返すように変更
    comments_to_add = []
    saved_count = 0
    for index, row in df.iterrows():
        try:
            # 要件定義書に従い、1列目がコメント文であることを想定し、iloc を使用
            comment_text = row.iloc[0]
            if pd.isna(comment_text): # コメントがNaNの場合をスキップ
                continue
            
            comment = Comment(text=str(comment_text)) # textカラムはString型なので文字列に変換
            comments_to_add.append(comment)
            saved_count += 1
        except IndexError:
            # CSVの行に1列目が存在しない場合など
            print(f"警告: CSVの行 {index+1} にコメントデータが見つかりませんでした。スキップします。")
            continue
        except Exception as e:
            print(f"警告: CSVの行 {index+1} の処理中にエラーが発生しました: {e}。スキップします。")
            continue

    if comments_to_add: # 追加するコメントがある場合のみ処理
        db.add_all(comments_to_add) # add_all で一括挿入
        db.commit()
        # commit()後に各オブジェクトはDBから最新の状態に更新される
        # 必要であれば、db.refresh(comment) をコメントオブジェクトに対して実行
    
    return saved_count # 保存件数を返す
