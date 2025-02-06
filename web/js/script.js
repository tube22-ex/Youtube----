const contents = document.getElementById('contents');
const input_text = document.getElementById('input_text');
const send_btn = document.getElementById('send_btn');
const progress = document.getElementById('progress');


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
    let Chat = [];
    for(let i of data["chat"]){
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
    <a href="https://youtu.be/${data["dougaID"]}">
    <img src="http://img.youtube.com/vi/${data["dougaID"]}/mqdefault.jpg" class="thumbnail"></img>
    </a>
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
        Adjacent(tagArr[l]);
        cnt= l;
        await sleep(50);
    }
    // 余りの処理
    for (let j=(tagArr.length - size) + 1; j < tagArr.length; j++) {
        Adjacent(tagArr[j]);
        cnt= j;
    }

    function Adjacent(t){
        contents.insertAdjacentHTML('beforeend', t);
        prog = (((cnt + 1) / (tagArr.length - 1)))
        progress.value = prog;

    }
}

eel.expose(js_function)
function js_function(values){
    values.sort((a, b) => new Date(a.date) - new Date(b.date));
    const tagArr = [];
    for(let i of values){
        tagArr.push(createTag(i));
    }
    //指定サイズずつループ、最後のループのみ１つずつ。

    console.log(tagArr) 
    addTag(tagArr);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
