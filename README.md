##ダウンロード

1. 「[Releases](https://github.com/tube22-ex/YoutubeChatHistoryViewer/releases/latest)」にある「x.x.zip」をダウンロードし解凍

※ Codeタブから個別にダウンロードするとディレクトリ構造を再現する手間がかかるのでおすすめしません。ディレクトリ構造を再現しない限りエラーで動きません。

##チャットデータの用意
1. [Google Takeout](https://takeout.google.com/settings/takeout/custom/youtube
) で「YouTubeのすべてのデータが含まれます」をクリックし「チャット」にのみチェックを入れてエクスポートを作成
2. しばらくするとリンクがメールに届くので適当な場所にダウンロードし解凍
3. 「takeout-xxxxx-000」> 「Takeout」 > 「YouTube と YouTube Music」 > 「チャット」にチャット.csvがあるを確認し、「チャット」までのパスをコピー

##実行
1. 「main.exe」を実行
2. デフォルト設定のブラウザでページが開く。表示されているテキストボックスに「チャットデータの用意 3」で用意したパスを貼り付け（　**ダブルクオーテーション等はいりません**　）
3. 実行ボタンを押すと	csvが読みとられ、チャットフォルダに「chat.csv」「output.json」が生成されます。（コマンドプロント側でプログレスバーが動きます）
4. ブラウザ側に処理が移り、ブラウザ側のプログレスバーが動き始め最後まで到達したら処理完了です。
