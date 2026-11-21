from src.services import attribution,runs
# 控制器只编排端点契约,持久化与计算留在服务层。
def overview(db):
    return {'projects':attribution.list_projects(db),'runs':runs.list_runs(db)[:20]}
def create_project(db,data,user): return attribution.create_project(db,data,user)
def list_events(db,id): return attribution.list_events(db,id)
def add_events(db,id,items,user): return attribution.add_events(db,id,items,user)
def withdraw(db,id,data,user): return attribution.withdraw(db,id,data,user)
def create_run(db,id,user): return runs.create_manual(db,id,user)
def project_runs(db,id):
    attribution.require(db,id);return runs.list_runs(db,id)
def current(db,id): return runs.current(db,id)
def get_run(db,id): return runs.get(db,id)
