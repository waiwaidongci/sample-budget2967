"""API 冒烟:认证、RBAC、项目/事件/重算/当前结果/复盘/留痕。"""
from src.services import runs as run_service
from src.config.database import Session

def login(client,email):
    r=client.post('/auth/login',json={'email':email,'password':'Research2026!'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}

def make_project(client,headers,name='API项目'):
    r=client.post('/projects',json={'name':name,'window_hours':72,'channels':['短信','邮件'],'description':''},headers=headers)
    assert r.status_code==200,r.text
    return r.json()['id']

def drain():
    from src.models.run import Run
    from sqlalchemy import select
    with Session() as db:
        ids=[r.id for r in db.scalars(select(Run).where(Run.status.in_(['queued','running'])))]
    for i in ids:
        with Session() as db: run_service.process(db,i)

def test_auth_and_rbac(client,seeded):
    assert client.post('/auth/login',json={'email':'admin@demo.local','password':'wrong'}).status_code==401
    assert client.get('/projects').status_code==401
    viewer=login(client,'viewer@demo.local')
    assert client.post('/projects',json={'name':'X项目','window_hours':72,'channels':['短信']},headers=viewer).status_code==403
    admin=login(client,'admin@demo.local')
    pid=make_project(client,admin)
    assert client.post(f'/projects/{pid}/events',json={'kind':'touch','event_no':1,'person':'U1','channel':'短信','occurred_at':'2026-11-10T09:00:00Z'},headers=viewer).status_code==403
    assert client.post(f'/projects/{pid}/runs',headers=viewer).status_code==403
    assert client.get(f'/projects/{pid}/events',headers=viewer).status_code==200

def test_event_flow_and_current_result(client,seeded):
    admin=login(client,'admin@demo.local')
    pid=make_project(client,admin)
    # 重名项目拒绝
    assert client.post('/projects',json={'name':'API项目','window_hours':72,'channels':['短信']},headers=admin).status_code==409
    touch={'kind':'touch','event_no':1,'person':'U1','channel':'短信','occurred_at':'2026-11-10T09:00:00Z'}
    r=client.post(f'/projects/{pid}/events',json=touch,headers=admin);assert r.status_code==200,r.text
    assert r.json()['version']==1
    # 重号拒绝(含跨状态)
    assert client.post(f'/projects/{pid}/events',json=touch,headers=admin).status_code==409
    # 批量补报:一条点击 + 一条窗口外触达
    r=client.post(f'/projects/{pid}/events/batch',json={'events':[
        {'kind':'click','event_no':1,'person':'U1','occurred_at':'2026-11-10T10:00:00Z'},
        {'kind':'touch','event_no':2,'person':'U2','channel':'邮件','occurred_at':'2026-11-01T09:00:00Z'}]},headers=admin)
    assert r.status_code==200 and r.json()['version']==2
    drain()
    cur=client.get(f'/projects/{pid}/current',headers=admin).json()
    assert cur['run']['status']=='published' and cur['run']['base_version']==2
    assert cur['run']['result']['summary']['pairs']==1
    stats=cur['run']['result']['channel_stats']
    assert stats[0]['channel']=='短信' and stats[0]['first_click_rate']==1
    # 撤回后重算,当前结果一次性切换到 v3
    r=client.post(f'/projects/{pid}/events/withdraw',json={'kind':'touch','event_no':1},headers=admin)
    assert r.json()['version']==3
    drain()
    cur=client.get(f'/projects/{pid}/current',headers=admin).json()
    assert cur['run']['base_version']==3 and cur['run']['result']['summary']['pairs']==0
    # 复盘:三版均可查。v1 计算完成时事件已前进到 v2,按约定过期未发布;v2 被 v3 替换
    versions=client.get(f'/projects/{pid}/runs',headers=admin).json()
    assert [v['status'] for v in versions]==['published','superseded','stale']
    v2=client.get(f"/runs/{versions[1]['id']}",headers=admin).json()
    assert v2['base_version']==2 and v2['result']['summary']['pairs']==1  # v2 的配对仍留档
    v1=client.get(f"/runs/{versions[2]['id']}",headers=admin).json()
    assert v1['status']=='stale' and v1['result']['summary']['pairs']==0  # 过期计算留档但未发布
    # 手动重算去重
    assert client.post(f'/projects/{pid}/runs',headers=admin).json()['deduplicated'] is False
    assert client.post(f'/projects/{pid}/runs',headers=admin).json()['deduplicated'] is True
    drain()
    audits=client.get('/audits',headers=admin).json()
    actions={a['action'] for a in audits}
    assert {'project.create','event.add','event.batch','event.withdraw','run.enqueue','run.publish'}<=actions

def test_health_and_domain(client,seeded):
    assert client.get('/health').json()=={'status':'healthy'}
    admin=login(client,'admin@demo.local')
    d=client.get('/domain',headers=admin).json()
    assert d['slug']=='touch-attribution' and 'stale' in d['states']
