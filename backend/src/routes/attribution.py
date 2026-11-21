from fastapi import APIRouter,Depends
from sqlalchemy import select
from src.config.database import get_db
from src.config.domain import DOMAIN
from src.middlewares.auth import current_user,writer
from src.schemas.project import ProjectInput
from src.schemas.event import EventInput,BatchEventsInput,WithdrawInput
from src.controllers import attribution
from src.services import runs as run_service
from src.models.audit import Audit
from src.utils.serializers import record
router=APIRouter()
@router.get('/domain')
def domain(user=Depends(current_user)): return DOMAIN
@router.get('/overview')
def overview(db=Depends(get_db),user=Depends(current_user)): return attribution.overview(db)
@router.get('/projects')
def list_projects(db=Depends(get_db),user=Depends(current_user)): return attribution.list_projects(db)
@router.post('/projects')
def create_project(data:ProjectInput,db=Depends(get_db),user=Depends(writer)): return attribution.create_project(db,data,user)
@router.get('/projects/{id}/events')
def events(id:int,db=Depends(get_db),user=Depends(current_user)): return attribution.list_events(db,id)
@router.post('/projects/{id}/events')
def add_one(id:int,data:EventInput,db=Depends(get_db),user=Depends(writer)): return attribution.add_events(db,id,[data],user)
@router.post('/projects/{id}/events/batch')
def add_batch(id:int,data:BatchEventsInput,db=Depends(get_db),user=Depends(writer)): return attribution.add_events(db,id,data.events,user)
@router.post('/projects/{id}/events/withdraw')
def withdraw(id:int,data:WithdrawInput,db=Depends(get_db),user=Depends(writer)): return attribution.withdraw(db,id,data,user)
@router.post('/projects/{id}/runs')
def recalc(id:int,db=Depends(get_db),user=Depends(writer)): return attribution.create_run(db,id,user)
@router.get('/projects/{id}/runs')
def project_runs(id:int,db=Depends(get_db),user=Depends(current_user)): return attribution.project_runs(db,id)
@router.get('/projects/{id}/current')
def current(id:int,db=Depends(get_db),user=Depends(current_user)): return attribution.current(db,id)
@router.get('/runs')
def all_runs(db=Depends(get_db),user=Depends(current_user)): return run_service.list_runs(db)
@router.get('/runs/{id}')
def get_run(id:int,db=Depends(get_db),user=Depends(current_user)): return attribution.get_run(db,id)
@router.get('/audits')
def audits(db=Depends(get_db),user=Depends(current_user)): return [record(x) for x in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(100))]
