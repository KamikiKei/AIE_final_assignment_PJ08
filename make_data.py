import pandas as pd
import random

# コメントのテンプレートと関連情報
comment_templates = [
    {"text": "今日の講義はとても分かりやすかったです。", "category": "講義内容", "sentiment": 1, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":0}},
    {"text": "スライドの文字が小さくて見えにくかったです。", "category": "授業資料", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":1}},
    {"text": "先生の説明が早すぎて理解が追いつきませんでした。", "category": "講義内容", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":2}},
    {"text": "休憩時間が短すぎます。もう少し長くしてください。", "category": "運営", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":1, "インフラ":0, "緊急性":1}},
    {"text": "質問です。この問題の解決策は具体的にどうすればよいですか？", "category": "講義内容", "sentiment": 0, "danger": 0, "tags": {"質問":1, "具体的":1, "インフラ":0, "緊急性":2}},
    {"text": "マイクの調子が悪いのか、音声が途切れて聞き取りづらかったです。", "category": "インフラ", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":1, "緊急性":3}},
    {"text": "素晴らしい授業をありがとうございました！大変参考になりました。", "category": "講義内容", "sentiment": 1, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":0}},
    {"text": "配布資料のURLが間違っているようです。確認お願いします。", "category": "授業資料", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":1, "インフラ":0, "緊急性":3}},
    {"text": "運営側の対応が遅すぎます。改善を求めます。", "category": "運営", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":2}},
    {"text": "チャット機能が使えません。インフラの問題でしょうか？", "category": "インフラ", "sentiment": 0, "danger": 0, "tags": {"質問":1, "具体的":0, "インフラ":1, "緊急性":3}},
    {"text": "次の授業までに、今日の復習をしておきます。", "category": "その他", "sentiment": 1, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":0}},
    {"text": "もう少し例題を多く出していただけると、理解が深まると思います。", "category": "講義内容", "sentiment": 1, "danger": 0, "tags": {"質問":0, "具体的":1, "インフラ":0, "緊急性":1}},
    {"text": "このクソみたいな授業、金を返せ。", "category": "運営", "sentiment": 0, "danger": 1, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":0}},
    {"text": "お前みたいな講師は見たことない。最低だ。", "category": "運営", "sentiment": 0, "danger": 1, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":0}},
    {"text": "接続が不安定で何度も落ちました。何とかしてください。", "category": "インフラ", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":1, "緊急性":3}},
    {"text": "とても面白く、有益な内容でした。ありがとうございます。", "category": "講義内容", "sentiment": 1, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":0}},
    {"text": "資料の誤字脱字が気になりました。", "category": "授業資料", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":1}},
    {"text": "録画のアップロードはいつになりますか？", "category": "運営", "sentiment": 0, "danger": 0, "tags": {"質問":1, "具体的":0, "インフラ":0, "緊急性":1}},
    {"text": "この内容について、別の視点からの解説も聞きたいです。", "category": "講義内容", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":0, "緊急性":0}},
    {"text": "カメラがオフになっていて講師の顔が見えません。", "category": "インフラ", "sentiment": 0, "danger": 0, "tags": {"質問":0, "具体的":0, "インフラ":1, "緊急性":2}},
]

comments_data = []
for i in range(50): # 50件のコメントを生成
    template = random.choice(comment_templates)
    comment_text = template["text"]

    # ほんの少しバリエーションを加える（例：末尾にランダムな文字を追加）
    if random.random() < 0.2: # 20%の確率で少し変える
        comment_text += f" (ID:{i+1})"

    comments_data.append({"comment_text": comment_text})

df_comments = pd.DataFrame(comments_data)

# CSVとしてエクスポート
csv_file_path = "test_comments.csv"
df_comments.to_csv(csv_file_path, index=False, header=False)

print(f"CSVファイル '{csv_file_path}' を生成しました。")
print("ファイルの内容の一部:")
print(df_comments.head())