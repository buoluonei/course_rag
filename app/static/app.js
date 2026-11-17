
function newSessionId(){
    if(window.crypto&&typeof window.crypto.randomUUID==="function"){
        return window.crypto.randomUUID();
    }
    return "session-"+Date.now()+"-"+Math.random().toString(36).slice(2);
}
let sessionId=newSessionId();
let historyOffset=0;
const historyLimit=10;
const $=selector=>document.querySelector(selector);

function setStatus(element,message,type=""){
    element.textContent=message;
    element.className=`status ${type}`.trim();
}

async function readJson(response){
    const data=await response.json().catch(()=>({}));
    if(!response.ok){throw new Error(data.detail||`请求失败（${response.status}）`);}
    return data;
}

function addSource(source){
    const card=document.createElement("article");
    card.className="source-card";
    const meta=document.createElement("div");
    meta.className="source-meta";
    const fileName=document.createElement("span");
    fileName.textContent=source.filename||"未知文件";
    const position=document.createElement("span");
    const details=[];
    if(source.section_title){
        details.push(source.section_title);
    }
    if(Number.isInteger(source.chunk_index)){
        details.push(`第 ${source.chunk_index+1} 个片段`);
    }
    position.textContent=details.join(" · ")||"资料片段";
    const score=document.createElement("span");
    score.textContent=typeof source.score==="number"?`相关度 ${source.score.toFixed(3)}`:"资料片段";
    meta.append(fileName,position,score);
    const content=document.createElement("p");
    content.className="source-content";
    content.textContent=source.content||"";
    card.append(meta,content);
    $("#sources").appendChild(card);
}

async function upload(){
    const file=$("#file").files[0];
    const status=$("#uploadStatus");
    if(!file){setStatus(status,"请先选择 TXT、PDF 或 DOCX 文件","error");return;}
    const form=new FormData();
    form.append("upload_file",file);
    $("#uploadButton").disabled=true;
    setStatus(status,"正在上传并处理文档…");
    try{
        let response=await fetch("/documents/upload",{method:"POST",body:form});
        if(response.status===409){
            if(!confirm("同名文件已存在，是否覆盖？")){setStatus(status,"已取消覆盖");return;}
            response=await fetch("/documents/upload?overwrite=true",{method:"POST",body:form});
        }
        const data=await readJson(response);
        setStatus(status,`已上传 ${data.filename}，生成 ${data.chunks_count} 个资料片段`,"success");
        $("#file").value="";
        await loadDocuments();
    }catch(error){setStatus(status,error.message,"error");}
    finally{$("#uploadButton").disabled=false;}
}

async function ask(){
    const input=$("#question");
    const question=input.value.trim();
    if(!question){input.focus();return;}
    const answer=$("#answer");
    $("#copyAnswerButton").hidden=true;
    $("#askButton").disabled=true;
    $("#newConversationButton").disabled=true;
    answer.className="answer-empty";
    answer.textContent="正在生成回答…";
    $("#sources").replaceChildren();
    try{
        const data=await readJson(await fetch("/answers",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question,session_id:sessionId})}));
        answer.className="answer";
        answer.textContent=data.answer||"模型没有返回回答。";
        $("#copyAnswerButton").hidden=false;
        resetCopyButton();
        (data.source||[]).forEach(addSource);
        historyOffset=0;
        await loadHistory();
    }catch(error){answer.className="answer-empty";answer.textContent=error.message;}
    finally{$("#askButton").disabled=false;$("#newConversationButton").disabled=false;}
}

async function exportConversation(){
    try{
        const data=await readJson(await fetch(`/sessions/${encodeURIComponent(sessionId)}`));
        const questions=data.questions||[];
        if(!questions.length){alert("当前会话还没有问答记录");return;}
        const lines=["# 课程问答对话记录",""];
        questions.forEach(function(item){
            lines.push(`## 问：${item.question}`,"");
            lines.push(item.answer||"","");
        });
        const blob=new Blob([lines.join("\n")],{type:"text/markdown;charset=utf-8"});
        const url=URL.createObjectURL(blob);
        const link=document.createElement("a");
        link.href=url;
        link.download=`对话记录-${new Date().toISOString().slice(0,10)}.md`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }catch(error){
        alert(error.message);
    }
}

function resetCopyButton(){
    const button=$("#copyAnswerButton");
    button.classList.remove("copied");
    button.textContent="复制回答";
}

async function copyAnswer(){
    const button=$("#copyAnswerButton");
    const answer=$("#answer");
    if(!answer.textContent||answer.classList.contains("answer-empty")){return;}
    try{
        await navigator.clipboard.writeText(answer.textContent);
        button.classList.add("copied");
        button.textContent="已复制";
    }catch(error){
        button.textContent="复制失败";
    }
    setTimeout(resetCopyButton,1500);
}

function addDocument(documentInfo){
    const row=document.createElement("div");row.className="document-row";
    const info=document.createElement("div");
    const name=document.createElement("div");name.className="document-name";name.textContent=documentInfo.filename;
    const date=document.createElement("div");date.className="document-date";date.textContent=documentInfo.created_at?new Date(documentInfo.created_at).toLocaleString():"";
    info.append(name,date);
    const button=document.createElement("button");button.className="delete-button";button.type="button";button.textContent="删除";button.title=`删除 ${documentInfo.filename}`;
    button.addEventListener("click",()=>removeDocument(documentInfo.id,documentInfo.filename));
    row.append(info,button);$("#documents").appendChild(row);
}

async function loadDocuments(){
    const box=$("#documents");
    try{const data=await readJson(await fetch("/documents"));box.replaceChildren();if(!data.documents.length){const empty=document.createElement("p");empty.className="list-empty";empty.textContent="资料库还是空的。";box.appendChild(empty);return;}data.documents.forEach(addDocument);}
    catch(error){box.replaceChildren();const empty=document.createElement("p");empty.className="list-empty";empty.textContent=error.message;box.appendChild(empty);}
}

async function removeDocument(id,filename){
    if(!confirm(`确定删除“${filename}”吗？`)){return;}
    try{await readJson(await fetch(`/documents/${id}`,{method:"DELETE"}));await loadDocuments();}
    catch(error){setStatus($("#uploadStatus"),error.message,"error");}
}

function addHistory(item){
    const row=document.createElement("article");row.className="history-row";
    const content=document.createElement("div");content.className="history-content";
    const question=document.createElement("p");question.className="history-question";question.textContent=item.question;
    const answer=document.createElement("p");answer.className="history-answer";answer.textContent=item.answer;
    const button=document.createElement("button");
    button.className="delete-button history-delete";button.type="button";button.textContent="删除";
    button.setAttribute("aria-label","删除这条问答记录");
    button.addEventListener("click",()=>removeHistory(item.id,button));
    content.append(question,answer);
    row.append(content,button);$("#history").appendChild(row);
}

async function removeHistory(id,button){
    if(!confirm("确定删除这条问答记录吗？")){return;}
    button.disabled=true;
    try{
        await readJson(await fetch(`/questions/${encodeURIComponent(id)}`,{method:"DELETE"}));
        await loadHistory();
    }catch(error){
        button.disabled=false;
        alert(`删除失败：${error.message}`);
    }
}

async function loadHistory(){
    const box=$("#history");
    try{
        const data=await readJson(await fetch(`/questions?limit=${historyLimit}&offset=${historyOffset}`));
        const total=data.total||0;
        if(historyOffset>0&&historyOffset>=total){
            historyOffset=total===0?0:Math.floor((total-1)/historyLimit)*historyLimit;
            return await loadHistory();
        }
        box.replaceChildren();
        if(!data.questions.length){
            const empty=document.createElement("p");empty.className="list-empty";empty.textContent="还没有问答记录。";box.appendChild(empty);
        }else{
            data.questions.forEach(addHistory);
        }
        const totalPages=Math.max(1,Math.ceil(total/historyLimit));
        const currentPage=Math.floor(historyOffset/historyLimit)+1;
        $("#historyPageInfo").textContent=`第 ${currentPage} / ${totalPages} 页，共 ${total} 条`;
        $("#historyPrevButton").disabled=historyOffset===0;
        $("#historyNextButton").disabled=historyOffset+historyLimit>=total;
    }
    catch(error){box.replaceChildren();const empty=document.createElement("p");empty.className="list-empty";empty.textContent=error.message;box.appendChild(empty);}
}

function newConversation(){
    sessionId=newSessionId();
    $("#sessionLabel").textContent="已开启新对话";
    $("#answer").className="answer-empty";
    $("#answer").textContent="回答会显示在这里。";
    $("#copyAnswerButton").hidden=true;
    resetCopyButton();
    $("#sources").replaceChildren();
    $("#question").focus();
}

$("#uploadButton").addEventListener("click",upload);
$("#askButton").addEventListener("click",ask);
$("#copyAnswerButton").addEventListener("click",copyAnswer);
$("#exportButton").addEventListener("click",exportConversation);
$("#newConversationButton").addEventListener("click",newConversation);
$("#refreshHistoryButton").addEventListener("click",loadHistory);
$("#historyPrevButton").addEventListener("click",()=>{historyOffset=Math.max(0,historyOffset-historyLimit);loadHistory();});
$("#historyNextButton").addEventListener("click",()=>{historyOffset+=historyLimit;loadHistory();});
$("#question").addEventListener("keydown",event=>{if(event.key==="Enter"){event.preventDefault();ask();}});
loadDocuments();loadHistory();

