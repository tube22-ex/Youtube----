import eel, os, csv, json
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
import pytz
import requests

#nuitka --onefile --standalone main.py
class YoutubeChatHistory:
    def __init__(self, input_folder):
        self.input_folder = Path(input_folder)
        self.output_csv = os.path.join(self.input_folder ,'chat.csv')
        self.output_json = os.path.join(self.input_folder ,'output.json')
        self.all_rows = []
        self.json_result = []

    def search_files(self):
        """指定されたフォルダ内のCSVファイルを検索し、データを集める"""
        dir_g = self.input_folder.iterdir()
        for x in dir_g:
            file_name = x.name
            if file_name == 'chat.csv' or file_name == 'output.json':
                continue  # "chat.csv" と "output.json" をスキップ

            # それ以外のファイルに対する処理
            with open(self.input_folder / file_name, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                header = next(reader)  # ヘッダーは最初に読み込んでおく
                if not self.all_rows:
                    self.all_rows.append(header)  # 最初のCSVファイルからヘッダーを追加
                for row in reader:
                    # 空の要素を削除
                    cleaned_row = [element for element in row if element.strip() != '']
                    self.all_rows.append(cleaned_row)  # 各ファイルのデータ行を追加

    def save_csv(self):
        """収集したデータをCSVファイルに保存"""
        with open(self.output_csv, 'w', newline='', encoding='utf-8') as output_csv:
            writer = csv.writer(output_csv)
            all = self.all_rows
            filtered_list = list(filter(None, all))
            writer.writerows(filtered_list)

    def organize_data(self):
        """csvをjson形式に変換"""
        result = []
        errorResult = []

        with open(self.output_csv, 'r', encoding='utf-8') as file:
            # 最初に行数を数える
            total_lines = sum(1 for _ in file)
            
            # ファイルを最初に戻してからDictReaderを使用
            file.seek(0)

            reader = csv.DictReader(file)
            
            cnt = 0
            video_data = {}

            for row in tqdm(reader, desc="Processing rows", unit="row", total=total_lines-1):  # ヘッダー行を引くために1を引く
                cnt += 1
                
                video_id = row['チャット テキスト'] if len(row['動画 ID']) < 11 else row['動画 ID']
                #11桁じゃない場合チャットテキストに入っているのでそれを採用
                timestamp = self.convert_utc_to_jst(row['チャット作成タイムスタンプ'])

                if timestamp is None:  # 変換できない場合はスキップ
                    errorResult.append(f"Skipping row {cnt} due to invalid timestamp.")
                    continue

                if video_id not in video_data:
                    video_data[video_id] = {'date': timestamp, 'dougaID': video_id, 'chat': [], 'channelData' : self.get_channel_id(video_id)}
                
                chat_text = row['チャット テキスト']
                # print(row)
                

                # 正しい形式なら分割処理を実行
                if chat_text is None or chat_text == '':
                    continue

                if chat_text.startswith('{"text":') and chat_text.endswith('}'):
                    try:
                        # chat_text を JSON としてパース
                        text = self.clean_chat_text(chat_text)
                        chat_data = {
                            'chatID': row['チャット ID'],
                            'channelID': row['チャンネル ID'],
                            'timeStamp': timestamp,
                            'chat': ["text", text],
                            'type':'chat',
                            'currency': []
                        }
                        video_data[video_id]['chat'].append(chat_data)
                    except json.JSONDecodeError:
                        errorResult.append(f"Warning: JSONデコードエラーが発生しました (chatテキスト: {chat_text})")
                    except KeyError:
                        errorResult.append(f"Warning: 'text' フィールドが見つかりません (chatテキスト: {chat_text})")
                else:
                    if(int(row['価格']) > 0):
                        chat_data = {
                            'chatID': row['チャット ID'],
                            'channelID': row['チャンネル ID'],
                            'timeStamp': timestamp,
                            'chat': ["text", ''],
                            'type':'superChat',
                            'superchat': [row['価格'], row['動画 ID']]
                        }
                        video_data[video_id]['chat'].append(chat_data)
                    else:
                        errorResult.append(f"Warning: 不正な形式のチャットテキストがあります (chatテキスト: {chat_text}){cnt}")

            # video_data をリスト形式に変換
            result = list(video_data.values())

        # JSON形式で出力
        with open(self.output_json, 'w', encoding='utf-8') as json_file:
            json.dump(result, json_file, ensure_ascii=False, indent=4)

        print("\n".join(errorResult))#エラーログをまとめて最後に出力してプログレス分割を回避

        print(f"JSONファイルが {self.output_json} として保存されました。")
        self.json_result = result  # グローバル変数に結果を格納

    def clean_chat_text(self, chat_text):
        chat_text = f'[{chat_text}]'  # 最初と最後に '[]' を追加
        chat_dict = json.loads(chat_text)
        text = ''
        for i in chat_dict:
            text += i.get("text", "")
        #絵文字が使われていると分割されるので複数のtextをつなげる
        return text

    def convert_utc_to_jst(self, utc_time_str):
        """UTCのdatetimeオブジェクトに変換"""
        try:
            utc_time = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))  # 'Z' を '+00:00' に置き換え
        except ValueError as e:
            print(f"タイムスタンプのフォーマットがおかしいよ: {utc_time_str} - Error: {e}")
            return None

        # JST (日本標準時) に変換
        jst = pytz.timezone('Asia/Tokyo')
        jst_time = utc_time.astimezone(jst)

        # 指定された形式でフォーマット
        formatted_time = jst_time.strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]  # 小数点以下3桁に切り捨て

        return formatted_time

    def get_channel_id(self, video_id):
        
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(url)
    
        if response.status_code == 200:
            data = response.json()
            channel_url = data.get("author_url", "")
            if "youtube.com/@" in channel_url:
                channel_id = channel_url.split("/")[-1]
                data["author_url"] = channel_id ##@の先からに書き換え
                return data
            else:
                return None
        else:
            #print("Error:", response.status_code)
            #404が帰ってきた場合、手元にある動画IDを配列にセットしておき、そこから探索することによって消えたチャンネルでも特定できるようにする（仮）
            #Archive_dougaID = [{dougaID: xx, channel_id : xx, channelName : xx}]
            return None
    

    def jsonExport(self):
        return self.json_result



#ここからeel
eel.init('web')

@eel.expose
def python_processor_eel(values):
    """JS側の実行ボタンで実行。inputに貼り付けた絶対パスを受け取る。"""
    print(values)
    processor = YoutubeChatHistory(
        input_folder=values
    )

    processor.search_files()
    processor.save_csv()
    processor.organize_data()
    result = processor.jsonExport()
    eel.js_function(result)  # グローバル変数を渡す

eel.start(
    'index.html',
    mode='default'
)

