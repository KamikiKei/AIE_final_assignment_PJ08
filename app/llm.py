import json
import logging
import asyncio
from sqlalchemy.orm import Session
from app.models import Comment
from app.config import GROQ_API_KEY , GROQ_MODEL_NAME 
from groq import Groq # Groqクライアントライブラリをインポート

# ロガーの設定
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Groqクライアントの初期化
# GROQ_API_KEY は環境変数 'GROQ_API_KEY' から自動的に読み込まれるか、
# client = Groq(api_key=GROQ_API_KEY) のように明示的に渡す
client = Groq(api_key=GROQ_API_KEY)

async def label_comments(db: Session):
    comments_to_process = db.query(Comment).filter(Comment.category == None).all()
    
    if not comments_to_process:
        logger.info("処理すべき新規コメントはありません。")
        return

    logger.info(f"{len(comments_to_process)} 件のコメントをLLMでラベル付けします。")

    # Groqで利用可能なモデル名に置き換える必要があります。
    # 例: "gemma2-9b-it", "llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768" など
    # GroqCloudのウェブサイトで利用可能なモデルリストを確認してください。
    
    for comment in comments_to_process:
        await asyncio.sleep(3) 
        prompt = f"""
        以下のオンライン授業コメントを分類し、追加のタグを付与してください。必ずJSON形式で出力してください。
        カテゴリ、危険性、感情、質問、具体的、インフラ、緊急性の全てのフィールドに、定義されたルールに従って値を割り当ててください。

        カテゴリ: 以下の厳密に4つのカテゴリのいずれかを選択してください。
        - 講義内容: 講義の進め方、内容そのものに関するコメント。
        - 授業資料: スライド、配布資料、教科書などに関するコメント。
        - 運営: 授業の進行、受講者への連絡、システム利用など、講義内容や資料以外の運営全般に関するコメント。
        - その他: 上記のカテゴリに該当しない、または判断が難しいコメント。

        危険性: コメントが攻撃的、ハラスメント、暴言などを含む不適切な内容である場合は true、それ以外は false。
        
        感情: コメントがポジティブな表現を含んでいれば 1、ネガティブな表現を含んでいれば 0。感情が判断できない場合は 0 を返してください。

        タグ: 以下のタグをワンホットエンコーディング形式 (0/1) で付与してください。緊急性は0〜3の数値で評価してください。
        - 質問: 質問・疑問点の提示を含んでいれば 1、そうでなければ 0。
        - 具体的: 具体的な改善提案や事例を含んでいれば 1、そうでなければ 0。
        - インフラ: 通信・マイク・カメラなどの技術的問題に関する内容であれば 1、そうでなければ 0。
        - 緊急性: 今すぐ対処すべき内容の緊急度を0（低）から3（高）の数値で評価してください。判断できない場合は0を返してください。

        ---
        コメント: {comment.text}
        ---
        出力例:
        {{
            "カテゴリ": "講義内容",
            "危険性": false,
            "感情": 1,
            "質問": 0,
            "具体的": 1,
            "インフラ": 0,
            "緊急性": 2
        }}
        """
        
        llm_output_str = "" 
        
        for attempt in range(3): # 3回までリトライ
            try:
                # Groqクライアントを使用してAPIを呼び出す
                # stream=True を指定し、チャンクを受け取る
                completion = client.chat.completions.create(
                    model=GROQ_MODEL_NAME, 
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=256,
                    response_format={"type": "json_object"},
                    stream=True # ここでストリーミングを有効にする
                )
                
                # ストリーミングされたチャンクを処理し、完全なレスポンスを構築する
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        llm_output_str += chunk.choices[0].delta.content

                logger.info(f"LLMからの生レスポンス (コメントID {comment.id}): {llm_output_str}")
                
                result = json.loads(llm_output_str) # 完全なJSON文字列をパース
                
                if result.get('カテゴリ') is None:
                    logger.warning(f"コメントID {comment.id} のカテゴリ判定結果がNoneです。デフォルト値'その他'を設定します。")
                    comment.category = 'その他' # デフォルト値を設定
                else:
                    comment.category = result.get('カテゴリ')

                # 危険性、感情のNoneチェックと型変換
                if result.get('危険性') is None:
                    logger.warning(f"コメントID {comment.id} の危険性判定結果がNoneです。デフォルト値Falseを設定します。")
                    comment.danger = False
                else:
                    comment.danger = bool(result.get('危険性'))

                if result.get('感情') is None:
                    logger.warning(f"コメントID {comment.id} の感情分類結果がNoneです。デフォルト値0を設定します。")
                    comment.sentiment = 0 # Noneの場合は0をデフォルトとする
                else:
                    try:
                        comment.sentiment = int(result.get('感情'))
                    except ValueError:
                        logger.warning(f"コメントID {comment.id} の感情分類結果が予期せぬ値です: {result.get('感情')}。デフォルト値0を設定します。")
                        comment.sentiment = 0 
                
                # タグのパースと保存
                tags_data = {}
                # get() を使ってキーが存在しない場合もエラーにならないようにデフォルト値を設定
                tags_data['質問'] = int(result.get('質問', 0)) #
                tags_data['具体的'] = int(result.get('具体的', 0)) #
                tags_data['インフラ'] = int(result.get('インフラ', 0)) #
                tags_data['緊急性'] = int(result.get('緊急性', 0)) #
                comment.tags = tags_data # JSON型カラムに辞書を保存 [cite: 35]
                
                db.add(comment)
                break # 成功したらループを抜ける
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"コメントID {comment.id} のLLMレスポンスパースエラー (試行 {attempt+1}/{3}): {e} - レスポンス: '{llm_output_str}'")
                if attempt < 2:
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"コメントID {comment.id} のGroq API処理中に予期せぬエラーが発生しました (試行 {attempt+1}/{3}): {e} - レスポンス: '{llm_output_str}'", exc_info=True)
                if attempt < 2:
                    await asyncio.sleep(10)
        else: # リトライ回数を使い果たした場合
            logger.error(f"コメントID {comment.id} のLLM処理が複数回失敗したためスキップします。最終レスポンス: '{llm_output_str}'")
            
    try:
        db.commit()
        logger.info("LLMによるコメントのラベル付けが完了しました。")
    except Exception as e:
        db.rollback()
        logger.error(f"コメントのLLMラベル付け結果のコミット中にエラーが発生しました: {e}", exc_info=True)
