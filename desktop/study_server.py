"""Loopback-only reader and shared progress. Tk mutations run on its main thread."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from queue import Queue,Empty
from threading import Thread,Event
from urllib.parse import urlsplit,unquote
import json,mimetypes,time,urllib.error
from study_sync import SharedProgress,GitHub

class StudyServer:
    def __init__(self,model,auto_sync=True):
        self.model=model;self.shared=SharedProgress(model);self.github=GitHub();self.queue=Queue();self.stopped=Event();self.sync_status='동기화 준비';self.auto_sync=auto_sync
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,status,data,kind='application/json'):
                raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode() if kind=='application/json' else data
                self.send_response(status);self.send_header('Content-Type',kind+('; charset=utf-8' if kind.startswith('text/') or kind=='application/json' else ''));self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def handle_request(self):
                host=f'127.0.0.1:{owner.http.server_port}'
                if self.headers.get('Host')!=host:return self.reply(403,{'error':'Invalid host'})
                origin=self.headers.get('Origin')
                if origin and origin!='http://'+host:return self.reply(403,{'error':'Invalid origin'})
                path=urlsplit(self.path).path
                try:
                    body=None
                    if self.command in ('POST','PUT'):
                        length=int(self.headers.get('Content-Length','0'))
                        if not 0<length<=8_000_000:raise ValueError('요청 크기 오류')
                        body=json.loads(self.rfile.read(length))
                    if path=='/api/state':
                        if self.command=='GET':result=owner.call(owner.shared.capture)
                        elif self.command=='POST':result=owner.call(lambda:owner.shared.apply(body))
                        else:return self.reply(405,{'error':'method'})
                        return self.reply(200,result)
                    if path.startswith('/api/github'):
                        remote=path[len('/api/github'):]
                        query=urlsplit(self.path).query
                        if query:remote+='?'+query
                        result=owner.github.request(remote,self.command,body);return self.reply(200,result)
                    if self.command!='GET':return self.reply(405,{'error':'method'})
                    web=owner.model.root/'web'
                    if not web.exists():web=owner.model.root.parent
                    relative=unquote(path).lstrip('/') or 'index.html';target=(web/relative).resolve()
                    allowed={'index.html','app.js','progress.js','lesson_scope.js','reader.css','styles.css','course.html','lessons.html','original.pdf','full_guide.pdf','study_schedule.json','manifest.webmanifest','sw.js'}
                    if relative not in allowed and not relative.startswith(('original-pages/','assets/')):return self.reply(404,{'error':'not found'})
                    if not target.is_relative_to(web.resolve()) or not target.is_file():return self.reply(404,{'error':'not found'})
                    return self.reply(200,target.read_bytes(),mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
                except urllib.error.HTTPError as e:self.reply(e.code,{'error':'GitHub request failed'})
                except Exception as e:self.reply(400,{'error':str(e)})
            do_GET=handle_request;do_POST=handle_request;do_PUT=handle_request
        self.http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        Thread(target=self.http.serve_forever,daemon=True).start()
        if auto_sync:Thread(target=self.sync_loop,daemon=True).start()
    def url(self,day,part='read'):return f'http://127.0.0.1:{self.http.server_port}/?day={day.isoformat()}#{part}'
    def call(self,fn):
        event=Event();result=[];self.queue.put((fn,event,result))
        if not event.wait(50):raise TimeoutError('위젯 응답을 기다리는 중입니다.')
        if isinstance(result[0],Exception):raise result[0]
        return result[0]
    def drain(self):
        changed=False
        while True:
            try:fn,event,result=self.queue.get_nowait()
            except Empty:break
            before=self.model.state
            try:result.append(fn());changed|=before!=self.model.state
            except Exception as e:result.append(e)
            event.set()
        return changed
    def sync_loop(self):
        while not self.stopped.is_set():
            try:
                local=self.call(self.shared.capture);merged=self.github.sync(local);self.call(lambda:self.shared.apply(merged));self.sync_status='GitHub 동기화 완료'
            except Exception as e:self.sync_status='동기화 대기 · '+str(e)
            self.stopped.wait(30)
    def close(self):
        self.shared.capture();self.stopped.set();Thread(target=self.http.shutdown,daemon=True).start()

if __name__=='__main__':
    from study_widget_core import StudyModel
    import webbrowser
    server=StudyServer(StudyModel())
    print(server.url(server.model.current_stage()),flush=True)
    webbrowser.open(server.url(server.model.current_stage()))
    try:
        while True:server.drain();time.sleep(.1)
    except KeyboardInterrupt:server.close()
