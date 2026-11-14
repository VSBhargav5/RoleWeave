"""Exercise bundled browser assets and local API using a fresh synthetic shelf."""
import http.client
import json
from pathlib import Path
import sys
import ssl
import threading
import time
from runtime_paths import APP_VERSION
from web_server import LocalServer
from web_service import WebService, seed_web_demo


def run_web_self_test(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    report = {"version": APP_VERSION, "frozen": bool(getattr(sys, "frozen", False)), "ok": False}
    server = None
    try:
        context = ssl.create_default_context()
        if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
            raise ValueError("Verified HTTPS context unavailable")
        report['verified_https_context'] = True
        path = destination / "synthetic.db"
        seed_web_demo(path)
        server = LocalServer(("127.0.0.1", 0), WebService(path, demo=True))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def get(path, authorized=True):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
            try:
                connection.request("GET", path, headers={"X-RoleWeave-Token": server.token} if authorized else {})
                response = connection.getresponse()
                payload = response.read()
                if response.status != (401 if not authorized and path.startswith('/api/') else 200):
                    raise ValueError("Bundled route failed")
                return payload
            finally:
                connection.close()
        def post(route,data):
            connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
            try:
                connection.request('POST',route,body=json.dumps(data).encode(),headers={'X-RoleWeave-Token':server.token,'Content-Type':'application/json'})
                response=connection.getresponse();payload=response.read()
                if response.status!=200:raise ValueError('Bundled POST route failed')
                return json.loads(payload)
            finally:connection.close()
        get('/api/bootstrap', False)
        for asset in ('/', '/app.js', '/tailoring.js', '/styles.css', '/document-preview.css', '/icons.js', '/api/browser-helper'):
            if not get(asset): raise ValueError('Bundled asset missing')
        data = json.loads(get('/api/bootstrap'))
        resume = data['resumes'][0]
        record = server.service.store.load_resume(resume['id'])['resume']
        letter = server.service.letter({'job_id': record['job_context']['id'], 'resume_id': resume['id'],
                                        'fact_ids': record['selected_fact_ids'], 'motivation': 'Synthetic runtime check.',
                                        'closing': 'Thank you.', 'confirmed': True})
        if json.loads(get('/api/letter?id='+letter['id']))['text'] != letter['text']:
            raise ValueError('Saved letter unavailable')
        if not json.loads(get('/api/bootstrap'))['letters']['items']:
            raise ValueError('Saved letter catalog unavailable')
        import base64
        service=server.service;profile=service.profile()
        pdf=service.resume({'job_id':record['job_context']['id'],'profile_id':profile['id'],
                            'profile_sha256':profile['snapshot_sha256'],'fact_ids':record['selected_fact_ids'],
                            'confirmed':True},freeze=True)
        preview=service.preview_resume_import({'name':'synthetic.pdf',
                                               'base64':base64.b64encode(service.download('resume',pdf['id'])[0]).decode()})
        service.commit_resume_import({'id':preview['id'],'selected':[{'id':preview['blocks'][0]['id'],'section':'Additional'}],
                                      'confirmed':True})
        report['resume_import']=True
        recovery=service.preview_recovery(get('/api/workspace-bundle'))
        restored=service.restore_recovery({'id':recovery['id'],'sha256':recovery['summary']['sha256'],'confirmed':True})
        if not service.recovery_database({'id':restored['id'],'confirmed':True}).is_file():
            raise ValueError('Managed workspace recovery failed')
        report['managed_recovery']=True
        studio_args={'job_id':record['job_context']['id'],'profile_id':profile['id'],
                     'profile_sha256':profile['snapshot_sha256'],'fact_ids':record['selected_fact_ids'],
                     'label':'Synthetic studio runtime','theme':'slate'}
        preview=service.resume(studio_args)
        studio=service.resume(studio_args|{'confirmed':True,'preview_sha256':preview['preview_sha256']},freeze=True)
        if service.download('resume',studio['id'])[0]!=base64.b64decode(preview['pdf_base64']):
            raise ValueError('Studio preview differs from frozen PDF')
        letter_args={'job_id':record['job_context']['id'],'resume_id':studio['id'],'fact_ids':record['selected_fact_ids'],
                     'motivation':'Synthetic studio runtime.','closing':'Thank you.','include_pdf':True,'confirmed':False}
        letter_preview=service.letter(letter_args,freeze=False)
        studio_letter=service.letter(letter_args|{'confirmed':True,'preview_sha256':letter_preview['preview_sha256']})
        if service.download('letter',studio_letter['id'],'pdf')[0]!=base64.b64decode(letter_preview['pdf_base64']):
            raise ValueError('Letter preview differs from frozen PDF')
        packet=service.packet({'job_id':record['job_context']['id'],'resume_id':studio['id'],'letter_id':studio_letter['id'],
                               'formats':['pdf','letter-pdf'],'confirmed':True})
        if not service.download('packet',packet['id'])[0]:raise ValueError('Studio application kit unavailable')
        report['document_studio']=True
        ai=post('/api/tailoring/preview',{'job_id':record['job_context']['id'],'profile_id':profile['id'],
                 'profile_sha256':profile['snapshot_sha256'],'fact_ids':record['selected_fact_ids'],
                 'instruction':'Synthetic offline runtime check. Preserve project context.'})
        if not ai['offline_demo']:raise ValueError('Self-test must never use a live model')
        post('/api/tailoring/send',{'id':ai['id'],'sha256':ai['sha256'],'key':'','confirmed':True})
        deadline=time.monotonic()+5
        while True:
            result=post('/api/tailoring/status',{'id':ai['id']})
            if result['status']=='completed':break
            if result['status']!='running' or time.monotonic()>deadline:raise ValueError('Offline tailoring task failed')
            time.sleep(.01)
        accepted=post('/api/tailoring/accept',{'id':ai['id'],'result_sha256':result['result_sha256'],
                       'fact_edits':[{'id':record['selected_fact_ids'][0],'text':'Reviewed synthetic runtime application wording.'}],
                       'fields':{'letter_intro':'Reviewed synthetic introduction.'},'confirmed':True})
        saved=json.loads(get('/api/application-draft?id='+accepted['draft_id']))
        if saved['profile']['id']!=accepted['profile']['id'] or json.loads(get('/api/bootstrap'))['profile']['id']!=profile['id']:
            raise ValueError('Reviewed draft changed the master profile')
        from workspace_bundle import inspect_bundle
        if inspect_bundle(service.workspace_bundle())[1]['artifacts'].get('drafts')!=1:raise ValueError('Draft recovery snapshot missing')
        report['ai_tailoring']=True


        # Demo freezes HTML; the core test suite separately covers PDF creation.
        if not get('/api/download?kind=resume&id='+resume['id']+'&format=html'):
            raise ValueError('Frozen resume unavailable')
        get('/api/backup')
        report['ok'] = True
    except Exception:
        report['error'] = 'Synthetic web runtime check failed; no private diagnostics logged.'
    finally:
        if server:
            server.service.tailoring.shutdown()
            server.shutdown()
            server.server_close()
        (destination / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report['ok']
