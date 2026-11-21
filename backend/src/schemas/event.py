from pydantic import BaseModel,Field
class TouchClickEventInput(BaseModel):
    kind:str=Field(pattern='^(touch|click)$')
    event_no:int=Field(gt=0,le=999999999)   # 事件编号,项目内同类唯一
    person:str=Field(min_length=1,max_length=60)
    channel:str=Field(default='',max_length=40)
    occurred_at:str=Field(min_length=10,max_length=40)
class BatchEventsInput(BaseModel):
    events:list[TouchClickEventInput]=Field(min_length=1,max_length=500)
class WithdrawInput(BaseModel):
    kind:str=Field(pattern='^(touch|click)$')
    event_no:int=Field(gt=0,le=999999999)
EventInput=TouchClickEventInput
