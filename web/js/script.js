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
        const HTML = `<div id="ALLsummary"><span>１枠最大コメント数： ${data["len"]}件  動画ID： ${data["dougaID"]}</span></div>`
        contents.insertAdjacentHTML('afterbegin', HTML);
    }
    objReturn(){
        const obj = {"len" : this.Maxlen, "dougaID" : this.MaxdougaID}
        return obj;
    }


}

const maxComments = new MaxComments();

send_btn.addEventListener('click', async () => {
    let path = input_text.value;
    contents.innerHTML = '';
    try {
        await eel.python_processor_eel(path)();
    } catch (error) {
        console.error("呼び出し失敗:", error);
    }
});


function createTag(data){
    const data_chat = data["chat"];
    const data_dougaID = data["dougaID"];
    maxComments.compareSize(data_chat.length, data_dougaID);
    let Chat = [];
    for(let i of data_chat){
        let chatText = '';
        if(i["type"] == 'chat'){
            chatText = `<span class="chat">${i["chat"][1]}</span>`
        }else if(i["type"] == "superChat"){
            chatText = `<span class="chat"><span class="superChat">${Number(i["superchat"][0])/1000000}</span><span class="currency">${i["superchat"][1]}</span></span>`
        }

        Chat.push(`
        <div class="comment">
        <span class="timeStamp">${i["timeStamp"]}</span>
        ${chatText}
        </div>
        `
        )
    }

    const template = `
    <div class="content">
    <a href="https://youtu.be/${data_dougaID}">
    <img src="http://img.youtube.com/vi/${data_dougaID}/mqdefault.jpg" class="thumbnail"></img>
    </a>
    <div class="summary">
    <span class="commentLen">${data_chat.length}件<span>
    </div>
    <div class="commentsData">
    ${Chat.reverse().join("")}
    </div>
    </div>
    `
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

eel.expose(js_function)
function js_function(values){
    values.sort((a, b) => new Date(a.date) - new Date(b.date));
    const tagArr = [];
    for(let i of values){
        tagArr.push(createTag(i));
    }
    //指定サイズずつループ
    addTag(tagArr);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
