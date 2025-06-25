import os
from dotenv import load_dotenv 

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# データベース設定
DATABASE_URL = "sqlite:///./comments.db" # SQLite を使用する場合

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) # SQLite の場合のみ connect_args が必要
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# CSVアップロードディレクトリ
UPLOAD_DIR = "uploads"

# Groq APIキー
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY is None:
    # 環境変数にAPIキーが設定されていない場合、警告を出すか、エラーで停止する
    print("警告: 環境変数 'GROQ_API_KEY' が設定されていません。")
    print("API機能は動作しない可能性があります。")
    # raise ValueError("環境変数 'GROQ_API_KEY' が設定されていません。") # 厳密にするなら

GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "meta-llama/llama-4-scout-17b-16e-instruct") 

# Groq APIのベースURL (通常はデフォルトで良いため、設定不要な場合が多いですが、明示的に設定することも可能)
# GROQ_BASE_URL = "https://api.groq.com/openai/v1" 

# Hugging Faceの埋め込みモデル名 (cluster.py で使用)
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

# HDBSCANの最小クラスタサイズ (cluster.py で使用)
MIN_CLUSTER_SIZE = 5

# LLMからJSON形式で返す際のタイムアウト設定（任意）
LLM_TIMEOUT = 60 # 秒