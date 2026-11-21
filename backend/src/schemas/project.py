from pydantic import BaseModel,Field
class AttributionProjectInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    window_hours:float=Field(gt=0,le=720)          # 约定时窗(小时)
    channels:list[str]=Field(min_length=1,max_length=12)
    description:str=Field(default='',max_length=2000)
ProjectInput=AttributionProjectInput
