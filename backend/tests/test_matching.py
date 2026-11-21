"""配对引擎测试:暴力枚举复核最优性、确定性、编号定序层级。"""
import random
from src.services.matching import attribute,channel_stats,summarize,_match_person

def brute_best(touches,clicks,window):
    """暴力枚举全部配对,返回 (最大配对数, 最小总等待)。"""
    best=(-1,None)
    edges=[[j for j,c in enumerate(clicks) if 0<=c['occurred_ts']-t['occurred_ts']<=window] for t in touches]
    def rec(i,used,cnt,wait):
        nonlocal best
        if i==len(touches):
            if cnt>best[0] or (cnt==best[0] and wait<best[1]): best=(cnt,wait)
            return
        rec(i+1,used,cnt,wait)
        for j in edges[i]:
            if j not in used: rec(i+1,used|{j},cnt+1,wait+clicks[j]['occurred_ts']-touches[i]['occurred_ts'])
    rec(0,set(),0,0)
    return best

def ev(kind,no,person,ts,channel=''):
    return {'kind':kind,'event_no':no,'person':person,'channel':channel,
            'occurred_at':str(ts),'occurred_ts':ts}

def test_greedy_counterexample():
    """最近触达贪心会漏配:引擎必须拿到最大配对数2。"""
    touches=[ev('touch',1,'P',0),ev('touch',2,'P',5)]
    clicks=[ev('click',1,'P',5),ev('click',2,'P',6)]
    pairs=_match_person(touches,clicks,5)
    assert len(pairs)==2
    assert sorted((i,j) for i,j,_ in pairs)==[(0,0),(1,1)]

def test_wait_dominates_touch_number():
    """小编号触达不能让位于更短等待之外:等待优先于编号。"""
    touches=[ev('touch',1,'P',0),ev('touch',2,'P',4)]
    clicks=[ev('click',1,'P',5)]
    pairs=_match_person(touches,clicks,5)
    assert pairs==[(1,0,1)]  # T2 等待1,优于 T1 等待5

def test_tie_break_by_touch_number():
    """等待相同 -> 配对触达编号和小者优先。"""
    touches=[ev('touch',1,'P',0),ev('touch',2,'P',0)]
    clicks=[ev('click',1,'P',5)]
    assert _match_person(touches,clicks,5)==[(0,0,5)]

def test_tie_break_by_click_number():
    touches=[ev('touch',1,'P',0)]
    clicks=[ev('click',1,'P',5),ev('click',2,'P',5)]
    assert _match_person(touches,clicks,5)==[(0,0,5)]

def test_window_and_order_constraints():
    touches=[ev('touch',1,'P',10)]
    clicks=[ev('click',1,'P',9),ev('click',2,'P',11)]  # C1早于触达不可配;C2在窗内
    assert _match_person(touches,clicks,1)==[(0,1,1)]
    assert _match_person(touches,clicks,0)==[]        # 等待0不允许? 允许:0<=wait<=window -> 窗0仅同刻
    clicks2=[ev('click',1,'P',10)]
    assert _match_person(touches,clicks2,0)==[(0,0,0)]

def test_random_against_brute_force():
    rng=random.Random(20261121)
    for case in range(400):
        m,n=rng.randint(0,5),rng.randint(0,5)
        window=rng.choice([0,3,5,10,25])
        touches=sorted([ev('touch',i+1,'P',rng.randint(0,30)) for i in range(m)],
                       key=lambda x:(x['occurred_ts'],x['event_no']))
        clicks=sorted([ev('click',j+1,'P',rng.randint(0,30)) for j in range(n)],
                      key=lambda x:(x['occurred_ts'],x['event_no']))
        pairs=_match_person(touches,clicks,window)
        used_t=[i for i,_,_ in pairs];used_c=[j for _,j,_ in pairs]
        assert len(set(used_t))==len(used_t) and len(set(used_c))==len(used_c)  # 一对一
        for i,j,w in pairs:
            assert w==clicks[j]['occurred_ts']-touches[i]['occurred_ts']
            assert 0<=w<=window
        cnt,wait=brute_best(touches,clicks,window)
        assert len(pairs)==cnt,f'case {case}: 配对数 {len(pairs)} != 最优 {cnt}'
        assert sum(w for *_,w in pairs)==wait,f'case {case}: 总等待非最优'

def test_deterministic_and_order_independent():
    rng=random.Random(7)
    events=[]
    for person in ('P1','P2','P3'):
        for i in range(4):
            events.append(ev('touch',i+1,person,rng.randint(0,50),rng.choice(['短信','邮件'])))
            events.append(ev('click',i+1,person,rng.randint(0,50)))
    a=attribute(events,12)
    b=attribute(list(reversed(events)),12)   # 输入顺序不影响结果
    c=attribute(events,12)
    assert a==b==c
    assert all(x==y for x,y in zip(a,c))

def test_channel_stats_first_click():
    pairs=[
        {'person':'P1','touch_no':1,'click_no':1,'channel':'短信','touch_at':'','click_at':'','touch_ts':0,'click_ts':10,'wait_seconds':10},
        {'person':'P1','touch_no':2,'click_no':2,'channel':'邮件','touch_at':'','click_at':'','touch_ts':0,'click_ts':20,'wait_seconds':20},
        {'person':'P2','touch_no':3,'click_no':1,'channel':'邮件','touch_at':'','click_at':'','touch_ts':0,'click_ts':5,'wait_seconds':5},
    ]
    stats={r['channel']:r for r in channel_stats(pairs)}
    assert stats['短信']['first_clicks']==1 and stats['短信']['first_click_rate']==0.5
    assert stats['邮件']['first_clicks']==1 and stats['邮件']['attributed_clicks']==2
    assert abs(sum(r['first_click_rate'] for r in stats.values())-1)<1e-9

def test_summarize_counts():
    events=[ev('touch',1,'P',0,'短信'),ev('touch',2,'P',0,'短信'),ev('click',1,'P',3),ev('click',2,'Q',1)]
    pairs=attribute(events,5)
    s=summarize(events,pairs,5)
    assert s['pairs']==1 and s['unmatched_touches']==1 and s['unmatched_clicks']==1
    assert s['total_wait_seconds']==3 and s['persons_with_pairs']==1
