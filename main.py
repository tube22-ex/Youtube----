import eel, json
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
import pytz
import pandas as pd
import asyncio
import aiohttp
import orjson # 高速 JSON ライブラリ orjson をインポート

class YoutubeChatHistory:
    def __init__(self, input_folder):
        self.input_folder = Path(input_folder)
        self.output_csv = self.input_folder / 'chat.csv'
        self.output_json = self.input_folder / 'output.json'
        self.cache_file = self.input_folder / 'cache.json'
        self.all_rows = []
        self.json_result = []
        self.cache_data = self.read_cache()
        # self.executor = ThreadPoolExecutor(max_workers=os.cpu_count()) # ThreadPoolExecutor は削除

    def search_files(self):
        csv_files = list(self.input_folder.glob("*.csv"))
        combined_data = []
        header = None
        expected_columns = None

        for file_path in csv_files:
            file_name = file_path.name
            if file_name in ('chat.csv', 'output.json', 'cache.json'):
                continue

            try:
                # 【高速化 1-a, 1-b, 1-c を組み合わせ、データ型と使用列を明示的に指定】
                df = pd.read_csv(
                    file_path,
                    encoding='utf-8',
                    low_memory=False, # low_memory=False を指定 (メモリを多く使うが、高速になる可能性)
                    dtype={ # データ型を明示的に指定 (更なる高速化)
                        '動画 ID': str,
                        'チャット ID': str,
                        'チャット作成タイムスタンプ': str,
                        'チャット テキスト': str,
                        'チャンネル ID': str,
                        '価格': str # 価格も文字列として読み込む例 (必要に応じて適切な型に)
                    },
                    usecols=[ # 使用する列を限定 (不要な列を読み込まない)
                        '動画 ID',
                        'チャット ID',
                        'チャット作成タイムスタンプ',
                        'チャット テキスト',
                        'チャンネル ID',
                        '価格'
                    ]
                )
            except pd.errors.ParserError as e:
                print(f"エラー：CSVファイル {file_path} の解析に失敗しました。ファイル形式を確認してください。\n{e}")
                continue

            current_columns = df.columns.tolist()
            if header is None and not df.empty:
                header = current_columns
                expected_columns = len(header)
            elif expected_columns is not None and len(current_columns) != expected_columns:
                print(f"エラー：CSVファイル {file_path} の列数がヘッダーと一致しません。スキップします。")
                print(f"  - ヘッダー列数: {expected_columns}, ファイル列数: {len(current_columns)}")
                continue

            combined_data.append(df)

        if combined_data:
            combined_df = pd.concat(combined_data, ignore_index=True)
            combined_df = combined_df.dropna(how='all')
            if header:
                self.all_rows = [header] + combined_df.values.tolist()

    def save_csv(self):
        if not self.all_rows:
            print("警告：保存するデータがありません。")
            return

        header_len = len(self.all_rows[0])
        for row in self.all_rows[1:]:
            if len(row) != header_len:
                raise ValueError(f"データ行の列数がヘッダーと一致しません。Header columns: {header_len}, Data row columns: {len(row)}")

        df_output = pd.DataFrame(self.all_rows[1:], columns=self.all_rows[0])
        # 【高速化 2-a: compression='gzip' を指定 (gzip圧縮) 】
        df_output.to_csv(
            self.output_csv,
            index=False,
            encoding='utf-8',
            chunksize=10000,
            compression='gzip' # gzip 圧縮でファイルサイズを削減、IO 速度向上を狙う
        )

    async def async_get_channel_id(self, video_id, session):
        """非同期でチャンネルIDを取得 (キャッシュ利用)"""
        if video_id in self.cache_data:
            return self.cache_data[video_id]

        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        try:
            async with session.get(url, timeout=10) as response: # タイムアウト設定
                if response.status == 200:
                    # 【高速化: JSON パースに orjson を使用 (高速化が期待できる場合) 】
                    # data = await response.json() # 標準 json
                    text = await response.text()
                    data = orjson.loads(text) # orjson を使用
                    channel_url = data.get("author_url", "")
                    if "youtube.com/@" in channel_url:
                        data["author_url"] = channel_url.split("/")[-1]
                    self.cache_data[video_id] = data
                    return data
        except aiohttp.ClientError as e:
            print(f"API request error for video ID {video_id}: {e}")
        except asyncio.TimeoutError:
            print(f"API request timeout for video ID {video_id}")
        return None


    async def organize_data(self):
        """CSVをJSON形式に変換 (非同期APIリクエスト対応)"""
        error_log = []
        video_data = {}

        try:
            # 【高速化 2-a: compression='gzip' を指定 (gzip圧縮) 】
            df = pd.read_csv(self.output_csv, encoding='utf-8', compression='gzip') # save_csv で gzip 圧縮したので、読み込み時にも compression='gzip' を指定
        except FileNotFoundError:
            print(f"エラー：CSVファイル {self.output_csv} が見つかりません。")
            return

        async with aiohttp.ClientSession() as session:
            tasks = []
            # 【iterrows() の代わりに values.tolist() + zip() で高速化 (DataFrame -> List 変換 + zip 処理) 】
            for index, row in tqdm(enumerate(df.values.tolist()), total=len(df), desc="Processing rows", unit="row"): # enumerate を使用
                row_dict = dict(zip(df.columns, row)) #  zip で辞書化
                video_id = row_dict['動画 ID'] if len(row_dict['動画 ID']) == 11 else row_dict['チャット テキスト']
                timestamp = self.convert_utc_to_jst(row_dict['チャット作成タイムスタンプ'])

                if timestamp is None:
                    error_log.append(f"Skipping row {index} due to invalid timestamp.")
                    continue

                if video_id not in video_data:
                    video_data[video_id] = {
                        'date': timestamp,
                        'dougaID': video_id,
                        'chat': [],
                        'channelData': None
                    }
                    tasks.append(self.async_get_channel_id(video_id, session))

                chat_text = row_dict['チャット テキスト'] or ''
                chat_data = {
                    'chatID': row_dict['チャット ID'],
                    'channelID': row_dict['チャンネル ID'],
                    'timeStamp': timestamp,
                    'chat': self.clean_chat_text_sync(chat_text),
                    'type': 'superChat' if pd.notna(row_dict.get('価格')) and int(row_dict.get('価格', 0)) > 0 else 'chat',
                    'superchat': [row_dict['価格'], row_dict['動画 ID']] if pd.notna(row_dict.get('価格')) and int(row_dict.get('価格', 0)) > 0 else []
                }
                video_data[video_id]['chat'].append(chat_data)

            channel_data_results = await asyncio.gather(*tasks)
            video_ids_for_channel_data = list(video_data.keys())
            for video_id, channel_data in zip(video_ids_for_channel_data, channel_data_results):
                if video_id in video_data:
                    video_data[video_id]['channelData'] = channel_data

        # 【高速化 3-a: indent 削除、orjson で JSON 書き出し (最速) 】
        with self.output_json.open('wb') as json_file: # バイナリモードで open
            json_file.write(orjson.dumps(list(video_data.values()))) # orjson.dumps を使用 (indent 削除)

        if error_log:
            print("\n".join(error_log))

        self.json_result = list(video_data.values())
        print(f"JSONファイルが {self.output_json} として保存されました。")


    def clean_chat_text(self, chat_text): # clean_chat_text は削除
        raise NotImplementedError("clean_chat_text は clean_chat_text_sync に置き換えられました。")

    def clean_chat_text_sync(self, chat_text):
        """チャットテキストのクリーニングを同期的に実行"""
        try:
            chat_dict_list = json.loads(f'[{chat_text}]')
            text = ''.join(item.get("text", "") for item in chat_dict_list)
            return ["text", text] # type情報を付与
        except json.JSONDecodeError:
            return ["text", ""] # type情報を付与


    def convert_utc_to_jst(self, utc_time_str):
        """UTCからJSTへの変換 (datetime.fromisoformat を利用) - 最速版を維持"""
        try:
            utc_time = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00")) # fromisoformat が最速
            return utc_time.astimezone(pytz.timezone('Asia/Tokyo')).strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
        except ValueError:
            return None


    def read_cache(self):
        if self.cache_file.exists():
            try:
                with self.cache_file.open('r', encoding='utf-8') as f:
                    cache_list = json.load(f)
                    return {item['id']: item['data'] for item in cache_list}
            except json.JSONDecodeError:
                return {}
        return {}

    def write_cache(self):
        # 【高速化: JSON 書き込みにも orjson を使用 (書き込み頻度が高い場合は効果あり) 】
        cache_list_for_json = [{'id': video_id, 'data': data} for video_id, data in self.cache_data.items()]
        with self.cache_file.open('wb') as json_file: # バイナリモードで open
             json_file.write(orjson.dumps(cache_list_for_json)) # orjson.dumps を使用 (indent 削除)


    def get_channel_id(self, video_id): # get_channel_id は削除
        raise NotImplementedError("get_channel_id は非同期関数 async_get_channel_id に置き換えられました。")


    def jsonExport(self):
        return self.json_result


# --- eel の処理 ---
eel.init('web')

@eel.expose
def python_processor_eel(values):
    """JSから受け取ったパスを処理 (非同期処理対応)"""
    print(values)
    processor = YoutubeChatHistory(values)
    processor.search_files()
    processor.save_csv()
    asyncio.run(processor.organize_data())
    processor.write_cache()
    eel.js_function(processor.jsonExport())

eel.start('index.html', mode='default')