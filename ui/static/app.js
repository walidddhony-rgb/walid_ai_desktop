const socket=io();
let cid=null,buf='',ai=null,generating=false;
const $=s=>document.querySelector(s);

function stamp(t){return t?new Date(t).toLocaleTimeString('ar',{hour:'2-digit',minute:'2-digit'}):new Date().toLocaleTimeString('ar',{hour:'2-digit',minute:'2-digit'})}

function setStatus(msg,type='idle'){
    $('#status').textContent='● '+msg;
    $('#status').className='status '+type;
}

function render(txt){
    try{return marked.parse(txt)}catch(e){return txt}
}

function add(role,text='',time='',id=''){
    let d=document.createElement('div');
    d.className='msg '+role;
    d.dataset.id=id;
    let roleIcon = role==='user'?'\ud83d\udc64':'\ud83e\udde0';
    d.innerHTML='<div class="msg-actions">'+
        '<button class="msg-btn" onclick="copyMsg(this)">\u2398</button>'+
        (role==='assistant'?'<button class="msg-btn" onclick="likeMsg(this)">\ud83d\udc4d</button>':'')+
        '</div>'+
        '<div class="role">'+roleIcon+' <span class="time">'+stamp(time)+'</span></div>'+
        '<div class="content">'+render(text)+'</div>';
    $('#msgs').appendChild(d);
    $('#msgs').scrollTop=$('#msgs').scrollHeight;
    return d;
}

function copyMsg(btn){
    let text=btn.closest('.msg').querySelector('.content').textContent;
    navigator.clipboard.writeText(text);
    setStatus('تم النسخ');
}

function likeMsg(btn){
    let id=btn.closest('.msg').dataset.id;
    setStatus('تم التقييم');
}

function sendMsg(){
    let msg=$('#input').value.trim();
    if(!msg||generating)return;
    $('#input').value='';
    if(!cid){cid=crypto.randomUUID();}
    add('user',msg);
    setStatus('جارٍ التحليل...','generating');
    generating=true;
    $('#send').style.display='none';
    $('#stop').style.display='inline-block';
    let frame=add('assistant','');
    ai=frame.querySelector('.content');
    buf='';
    let modes=['quick'];
    socket.emit('chat_message',{message:msg,conversation_id:cid,modes:modes,model:$('#modelSelect').value});
    socket.off('stream_chunk');
    socket.on('stream_chunk',d=>{
        buf+=d.chunk;
        ai.innerHTML=render(buf);
        $('#msgs').scrollTop=$('#msgs').scrollHeight;
    });
    socket.off('response_complete');
    socket.on('response_complete',d=>{
        generating=false;
        $('#send').style.display='inline-block';
        $('#stop').style.display='none';
        setStatus('جاهز');
        loadConvs();
    });
    socket.off('status');
    socket.on('status',d=>{
        if(d.status==='searching')setStatus(d.message,'searching');
        else if(d.status==='generating')setStatus(d.message,'generating');
    });
    socket.off('search_results');
    socket.on('search_results',d=>{
        if(d.web&&d.web.length){
            let h='<div class="search-results"><h4>نتائج الويب:</h4>';
            d.web.forEach((r,i)=>{h+='<div><a href="'+r.url+'" target="_blank">'+r.title+'</a><br><small>'+r.snippet+'</small></div>'});
            h+='</div>';
            ai.innerHTML=render(buf)+h;
        }
    });
}

function stopGen(){
    socket.emit('stop_generation');
    generating=false;
    $('#send').style.display='inline-block';
    $('#stop').style.display='none';
    setStatus('تم الإيقاف','error');
}

function newConv(){
    cid=null;
    let welcome=document.createElement('div');
    welcome.id='welcome';
    welcome.innerHTML='مرحبًا بك في Walid AI<br><small>تحدث أو ارفع ملفات واسأل عن محتواها.</small>';
    $('#msgs').innerHTML='';
    $('#msgs').appendChild(welcome);
    $('#fileList').innerHTML='';
    $('#file-chips').innerHTML='';
    setStatus('جاهز');
}

async function loadConvs(){
    let r=await fetch('/api/conversations');
    let data=await r.json();
    let html='';
    data.forEach(c=>{
        let cls=c.id===cid?'conv active':'conv';
        html+='<div class="'+cls+'" onclick="loadConv(\''+c.id+'\')">'+(c.title||'محادثة')+'</div>';
    });
    $('#convList').innerHTML=html;
}

async function loadConv(id){
    cid=id;
    let r=await fetch('/api/conversations/'+id);
    let msgs=await r.json();
    $('#msgs').innerHTML='';
    msgs.forEach(m=>add(m.role,m.content,m.created_at,m.id));
    loadFiles(id);
    loadConvs();
    setStatus('جاهز');
}

async function loadFiles(id){
    let r=await fetch('/api/conversations/'+id+'/files');
    let files=await r.json();
    let html='';
    files.forEach(f=>{
        html+='<div class="file-card">'+f.filename+'<div class="file-meta">'+f.file_type+' - '+f.size+' bytes</div><span class="file-del" onclick="deleteFile('+f.id+')">x</span></div>';
    });
    $('#fileList').innerHTML=html;
}

async function deleteFile(fid){
    await fetch('/api/files/'+fid,{method:'DELETE'});
    if(cid)loadFiles(cid);
}

function uploadFile(){
    let input=document.createElement('input');
    input.type='file';
    input.multiple=true;
    input.onchange=async()=>{
        for(let f of input.files){
            let fd=new FormData();
            fd.append('file',f);
            fd.append('conversation_id',cid||'');
            let r=await fetch('/api/upload',{method:'POST',body:fd});
            let data=await r.json();
            let chip=document.createElement('span');
            chip.className='chip';
            chip.innerHTML=data.filename+' <span class="x" onclick="this.parentElement.remove()">x</span>';
            $('#file-chips').appendChild(chip);
        }
        if(cid)loadFiles(cid);
    };
    input.click();
}

function searchConv(){
    let q=$('#searchInput').value.trim();
    if(!q){loadConvs();return;}
    fetch('/api/conversations').then(r=>r.json()).then(data=>{
        let filtered=data.filter(c=>(c.title||'').includes(q));
        let html='';
        filtered.forEach(c=>{
            let cls=c.id===cid?'conv active':'conv';
            html+='<div class="'+cls+'" onclick="loadConv(\''+c.id+'\')">'+(c.title||'محادثة')+'</div>';
        });
        $('#convList').innerHTML=html;
    });
}

let recognition=null;
function toggleMic(){
    if(recognition){
        recognition.stop();
        recognition=null;
        return;
    }
    let SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){alert('المتصفح لا يدعم التعرف الصوتي');return;}
    recognition=new SR();
    recognition.lang='ar-SA';
    recognition.continuous=false;
    recognition.onresult=e=>{
        $('#input').value=e.results[0][0].transcript;
        $('#input').focus();
    };
    recognition.onend=()=>{recognition=null};
    recognition.start();
}

$('#input').addEventListener('keydown',e=>{
    if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMsg()}
});

loadConvs();