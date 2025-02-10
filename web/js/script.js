const contents = document.getElementById('contents');
const input_text = document.getElementById('input_text');
const send_btn = document.getElementById('send_btn');
const progress = document.getElementById('progress');

class MaxComments {
    constructor() {
        this.Maxlen = 0;
        this.MaxdougaID = '';
    }

    compareSize(len, dougaID){
        if(len > this.Maxlen){
            this.Maxlen = len;
            this.MaxdougaID = dougaID;
        }
    }

    show(){
        const data = this.objReturn()
        const HTML = `<div id="ALLsummary"><span>1枠最大コメント数：${data["len"]}件</span><span>動画ID：${data["dougaID"]}</span></div>`
        contents.insertAdjacentHTML('afterbegin', HTML);
    }
    objReturn(){
        const obj = {"len" : this.Maxlen, "dougaID" : this.MaxdougaID}
        return obj;
    }


}

const maxComments = new MaxComments();

const fetchComments = async (path) => {
    contents.innerHTML = '';
    try {
        await eel.python_processor_eel(path)();
    } catch (error) {
        console.error("呼び出し失敗:", error);
    }
};


send_btn.addEventListener('click', () => fetchComments(input_text.value));


function createTag(data) {
    const { chat: data_chat, dougaID: data_dougaID, channelData: data_channelData } = data;

    // コメントサイズの比較
    maxComments.compareSize(data_chat.length, data_dougaID);

    // チャットのテンプレート作成
    const Chat = data_chat.map(i => {
        let chatText = '';
        if (i["type"] === 'chat') {
            chatText = `<span class="chat">${i["chat"][1]}</span>`;
        } else if (i["type"] === "superChat") {
            chatText = `<span class="chat"><span class="superChat">${Number(i["superchat"][0]) / 1000000}</span><span class="currency">${i["superchat"][1]}</span></span>`;
        }

        return `
        <div class="comment">
            <span class="timeStamp">${i["timeStamp"]}</span>
            ${chatText}
        </div>
        `;
    }).reverse().join("");  // 逆順にして一度にjoinで結合

    // チャンネルデータがあれば詳細な表示
    let template = `
    <div class="content">
        <a href="https://youtu.be/${data_dougaID}">
            <img src="http://img.youtube.com/vi/${data_dougaID}/mqdefault.jpg" class="thumbnail" />
        </a>
        <div class="summary">
            <span class="commentLen">コメント数：${data_chat.length}件</span>
            <span class="videoID">動画ID：${data_dougaID}</span>
        </div>
        <div class="commentsData">
            ${Chat}
        </div>
        ${data_channelData ? `
        <div class="Data">
            <div class="data_title">動画タイトル：${data_channelData["title"]}</div>
            <div class="author_name">チャンネル名：${data_channelData["author_name"]}</div>
            <div class="author_url">アカウント：${data_channelData["author_url"]}</div>
        </div>
        ` : ''}
    </div>
    `;
    return template;
}


async function addTag(tag){
    const tagArr = tag;
    const size = 5;
    let cnt = 0;
    let prog = 0;

    for (let l = 0; l < tagArr.length - (tagArr.length % size); l += size) {
        for(let i = 0; i  < size; i++){
            const index = i + l;
            Adjacent(tagArr[index]);
            cnt = index;
        }
        await sleep(50);
    }

    function Adjacent(t){
        contents.insertAdjacentHTML('beforeend', t);
        prog = (((cnt + 1) / (tagArr.length - 1)))
        progress.value = prog;

    }
    maxComments.show();
}

eel.expose(js_function);
function js_function(values) {
    values.sort((a, b) => new Date(a.date) - new Date(b.date));
    const tagArr = values.map(i => createTag(i));
    console.log(values);
    addTag(tagArr);
}
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
