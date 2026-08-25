from pathlib import Path
import sqlite3,json,uuid,io
from datetime import datetime
from flask import Flask,render_template,request,jsonify,send_file
from flask_socketio import SocketIO,emit
from werkzeug.utils import secure_filename
import requests,subprocess,os as oss
try:
 from pypdf import PdfReader
except ImportError: PdfReader=None
try:
 from docx import Document
except ImportError: Document=None
BASE=Path(__file__).parent;DB_PATH=BASE/'data'/'walid_ai.db';UPLOADS=BASE/'uploads';UPLOADS.mkdir(exist_ok=True);ALLOWED={'pdf','txt','md','docx','wav','webm','mp3'};stop_flags={}
app=Flask(__name__,template_folder=str(BASE/'ui/templates'),static_folder=str(BASE/'ui/static'));app.config['SECRET_KEY']='walid-ai';app.config['MAX_CONTENT_LENGTH']=50*1024*1024;socketio=SocketIO(app,cors_allowed_origins='*',async_mode='threading')
def db():c=sqlite3.connect(DB_PATH);c.row_factory=sqlite3.Row;return c
def init():
 c=db();c.executescript("""CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT,created_at TEXT,updated_at TEXT);CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,conversation_id TEXT,role TEXT,content TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS uploaded_files(id INTEGER PRIMARY KEY,conversation_id TEXT,filename TEXT,path TEXT,file_type TEXT,size INTEGER,extracted_text TEXT,created_at TEXT);""");c.commit();c.close()
init()
def extract(path,ext):
 try:
  if ext in ('txt','md'):return path.read_text(encoding='utf-8',errors='ignore')[:15000]
  if ext=='pdf' and PdfReader:return '\n'.join(p.extract_text() or '' for p in PdfReader(str(path)).pages)[:15000]
  if ext=='docx' and Document:return '\n'.join(p.text for p in Document(str(path)).paragraphs)[:15000]
  if ext in ('wav','webm','mp3'):return '[ملف صوتي: استخدم Whisper لتحويله إلى نص]'
 except Exception as e:return f'[خطأ: {e}]'
 return ''
def transcribe_audio(path):
 try:
  with open(path,'rb') as f:
   files={'file':f}
   r=requests.post('http://localhost:11434/api/generate',json={'model':'whisper','prompt':f.read().decode('latin-1')},timeout=120)
   return r.json().get('response','')
 except Exception as e:return f'[تعذر تحويل الصوت: {e}]'
def tts(text):
 try:
  out=BASE/'voices'/f'{uuid.uuid4().hex}.wav'
  subprocess.run(['piper','-m','voices/en_US-lessac-medium.onnx','-o',str(out)],input=text.encode(),check=True,timeout=30)
  return str(out)
 except Exception:return None
@app.get('/')
def home():return render_template('index.html')
@app.get('/api/conversations')
def convs():
 c=db();x=[dict(r) for r in c.execute('SELECT * FROM conversations ORDER BY updated_at DESC')];c.close();return jsonify(x)
@app.get('/api/conversations/<cid>')
def conv(cid):
 c=db();x=[dict(r) for r in c.execute('SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id',(cid,))];c.close();return jsonify(x)
@app.get('/api/conversations/<cid>/files')
def files(cid):
 c=db();x=[dict(r) for r in c.execute('SELECT id,filename,file_type,size,created_at FROM uploaded_files WHERE conversation_id=? ORDER BY id DESC',(cid,))];c.close();return jsonify(x)
@app.post('/api/upload')
def upload():
 f=request.files.get('file');cid=request.form.get('conversation_id','')
 if not f or not f.filename:return jsonify(error='لم يتم اختيار ملف'),400
 ext=f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else ''
 if ext not in ALLOWED:return jsonify(error='نوع غير مدعوم'),400
 name=secure_filename(f.filename);path=UPLOADS/(uuid.uuid4().hex[:8]+'_'+name);f.save(path);text=transcribe_audio(path) if ext in ('wav','webm','mp3') else extract(path,ext)
 c=db();cur=c.execute('INSERT INTO uploaded_files(conversation_id,filename,path,file_type,size,extracted_text,created_at) VALUES(?,?,?,?,?,?,?)',(cid or None,f.filename,str(path),ext,path.stat().st_size,text,datetime.now().isoformat()));fid=cur.lastrowid;c.commit();c.close();return jsonify(id=fid,filename=f.filename,file_type=ext,size=path.stat().st_size,text_length=len(text) if text else 0)
@app.delete('/api/files/<int:fid>')
def delete_file(fid):
 c=db();row=c.execute('SELECT path FROM uploaded_files WHERE id=?',(fid,)).fetchone();c.execute('DELETE FROM uploaded_files WHERE id=?',(fid,));c.commit();c.close()
 if row:
  try:Path(row['path']).unlink(missing_ok=True)
  except Exception:pass
 return jsonify(ok=True)
@app.get('/api/tts/<path:filename>')
def serve_tts(filename):
 return send_file(BASE/'voices'/filename,as_attachment=False)
@socketio.on('stop_generation')
def stop():
 stop_flags[request.sid]=True;emit('generation_stopped')
@socketio.on('chat_message')
def chat(d):
 stop_flags[request.sid]=False;msg=d.get('message','');cid=d.get('conversation_id') or str(uuid.uuid4());model={'fast':'qwen2.5:7b','smart':'qwen2.5:14b','code':'qwen2.5-coder:14b'}.get(d.get('model','fast'),'qwen2.5:7b');now=datetime.now().isoformat();c=db()
 if not c.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone():c.execute('INSERT INTO conversations VALUES(?,?,?,?)',(cid,msg[:55] or 'محادثة جديدة',now,now));emit('conversation_created',{'id':cid})
 c.execute('INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)',(cid,'user',msg,now));c.commit();rows=c.execute('SELECT filename,extracted_text FROM uploaded_files WHERE conversation_id=? ORDER BY id DESC LIMIT 3',(cid,)).fetchall();ctx='\n\n'.join(f'ملف: {r["filename"]}\n{r["extracted_text"][:7000]}' for r in rows if r['extracted_text']);prompt='أنت Walid AI. أجب بالعربية بإيجاز.'+ ('\nمحتوى الملفات:\n'+ctx if ctx else '')
 emit('status',{'status':'generating','message':'جارٍ توليد الإجابة...' });text=''
 try:
  r=requests.post('http://127.0.0.1:11434/api/chat',json={'model':model,'stream':True,'messages':[{'role':'system','content':prompt},{'role':'user','content':msg}]},stream=True,timeout=300);r.raise_for_status()
  for line in r.iter_lines(decode_unicode=True):
   if stop_flags.get(request.sid):break
   if line:
    x=json.loads(line);chunk=x.get('message',{}).get('content','');text+=chunk;emit('stream_chunk',{'chunk':chunk})
 except Exception as e:text=f'خطأ: {e}';emit('stream_chunk',{'chunk':text})
 if text:c.execute('INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)',(cid,'assistant',text,now));mid=c.execute('SELECT last_insert_rowid()').fetchone()[0];c.execute('UPDATE conversations SET updated_at=? WHERE id=?',(now,cid));c.commit();tts_path=tts(text)
 else:mid=None;tts_path=None
 c.close();emit('response_complete',{'conversation_id':cid,'message_id':mid,'tts':tts_path})
if __name__=='__main__':socketio.run(app,host='0.0.0.0',port=5000,debug=True)
