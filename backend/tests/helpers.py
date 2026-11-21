from src.models.user import User
from src.utils.security import hash_password
from src.schemas.event import EventInput

def make_user(db,email='admin@demo.local',role='admin'):
    u=db.get(User,1)
    if not u:
        u=User(email=email,role=role,password_hash=hash_password('Research2026!'))
        db.add(u);db.commit()
    return u

def E(kind,no,person,at,channel=''):
    return EventInput(kind=kind,event_no=no,person=person,channel=channel,occurred_at=at)
