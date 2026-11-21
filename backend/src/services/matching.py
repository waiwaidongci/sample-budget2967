"""一对一归因配对引擎。

同一人的触达与点击在约定时窗内配对:点击不早于触达,且 点击时间-触达时间 <= 时窗。
目标按字典序依次优化,结果唯一确定、可复现:
  1. 归因的点击最多(配对数最大);
  2. 总等待最短(Σ(点击时间-触达时间) 最小);
  3. 同分按事件编号定:先比较配对触达编号总和(小者优先),再比较配对点击编号总和,
     仍相同由固定的增广顺序(节点与边均按编号升序)确定,与输入顺序无关。
实现:每人一张二分图的最小费用最大流(逐条最短路增广,Bellman-Ford 严格小于松弛,
遍历顺序固定)。三级目标用大整数权重编码进单一边价,Python 整数无溢出:
  cost = wait*W1 + touch_no*W2 + click_no
  W2 > 任意配对点击编号和; W1 > 任意配对编号代价和,故层级严格。
"""

def _match_person(touches,clicks,window):
    """touches/clicks: 含 event_no、occurred_ts 的 dict,均已按 (occurred_ts,event_no) 排序。
    返回 [(touch_idx,click_idx,wait)]。"""
    m,n=len(touches),len(clicks)
    if not m or not n: return []
    sum_t=sum(t['event_no'] for t in touches)
    sum_c=sum(c['event_no'] for c in clicks)
    W2=sum_c+1
    W1=(sum_t+1)*W2+sum_c+1
    N=2+m+n;S=0;T=N-1
    graph=[[] for _ in range(N)]
    def add(u,v,cost):
        graph[u].append([v,1,cost,len(graph[v])])
        graph[v].append([u,0,-cost,len(graph[u])-1])
    for i in range(m): add(S,1+i,0)
    for j in range(n): add(1+m+j,T,0)
    for i,t in enumerate(touches):
        for j,c in enumerate(clicks):
            wait=c['occurred_ts']-t['occurred_ts']
            if 0<=wait<=window:
                add(1+i,1+m+j,wait*W1+t['event_no']*W2+c['event_no'])
    # 逐条最短路增广:流量最大(配对最多)且总费用最小(等待最短、编号定序)
    while True:
        dist=[None]*N;prev=[None]*N;dist[S]=0
        for _ in range(N):
            moved=False
            for u in range(N):
                du=dist[u]
                if du is None: continue
                for ei,e in enumerate(graph[u]):
                    if e[1]>0 and (dist[e[0]] is None or du+e[2]<dist[e[0]]):
                        dist[e[0]]=du+e[2];prev[e[0]]=(u,ei);moved=True
            if not moved: break
        if dist[T] is None: break
        v=T
        while v!=S:
            u,ei=prev[v];e=graph[u][ei]
            e[1]-=1;graph[v][e[3]][1]+=1;v=u
    pairs=[]
    for i in range(m):
        for e in graph[1+i]:
            if 1+m<=e[0]<1+m+n and e[1]==0:  # 正向边流量用尽 => 该触达已配对
                j=e[0]-(1+m)
                pairs.append((i,j,clicks[j]['occurred_ts']-touches[i]['occurred_ts']))
    return pairs

def attribute(events,window_seconds):
    """对全部在版事件配对。events: dict(kind,event_no,person,channel,occurred_ts)。
    返回配对列表,按 (person,click_no) 排序,每项含双方编号、渠道、时间与等待。"""
    people={}
    for e in events:
        people.setdefault(e['person'],{'touch':[],'click':[]})[e['kind']].append(e)
    pairs=[]
    for person in sorted(people):
        ev=people[person]
        touches=sorted(ev['touch'],key=lambda x:(x['occurred_ts'],x['event_no']))
        clicks=sorted(ev['click'],key=lambda x:(x['occurred_ts'],x['event_no']))
        for i,j,wait in _match_person(touches,clicks,window_seconds):
            t,c=touches[i],clicks[j]
            pairs.append({'person':person,'touch_no':t['event_no'],'click_no':c['event_no'],
                          'channel':t['channel'],'touch_at':t['occurred_at'],'click_at':c['occurred_at'],
                          'touch_ts':t['occurred_ts'],'click_ts':c['occurred_ts'],'wait_seconds':wait})
    pairs.sort(key=lambda p:(p['person'],p['click_no']))
    return pairs

def channel_stats(pairs):
    """分渠道首点率:每人时间最早(同刻取点击编号小者)的已配对点击为其"首点";
    首点率=该渠道赢得的首点人数 / 全部有配对人数,各渠道合计为 1。"""
    first={}
    for p in pairs:
        cur=first.get(p['person'])
        if cur is None or (p['click_ts'],p['click_no'])<(cur['click_ts'],cur['click_no']):
            first[p['person']]=p
    total=len(first)
    stats={}
    for p in pairs:
        s=stats.setdefault(p['channel'],{'channel':p['channel'],'first_clicks':0,'first_click_rate':0,
                                         'attributed_clicks':0,'persons':set(),'total_wait_seconds':0})
        s['attributed_clicks']+=1;s['persons'].add(p['person']);s['total_wait_seconds']+=p['wait_seconds']
    for p in first.values(): stats[p['channel']]['first_clicks']+=1
    rows=[]
    for channel in sorted(stats,key=lambda c:(-stats[c]['first_clicks'],-stats[c]['attributed_clicks'],c)):
        s=stats[channel]
        rows.append({'channel':channel,'first_clicks':s['first_clicks'],
                     'first_click_rate':(s['first_clicks']/total) if total else 0,
                     'attributed_clicks':s['attributed_clicks'],'attributed_persons':len(s['persons']),
                     'avg_wait_seconds':round(s['total_wait_seconds']/s['attributed_clicks'],3)})
    return rows

def summarize(events,pairs,window_seconds):
    touches=[e for e in events if e['kind']=='touch'];clicks=[e for e in events if e['kind']=='click']
    total_wait=sum(p['wait_seconds'] for p in pairs)
    return {'active_touches':len(touches),'active_clicks':len(clicks),'pairs':len(pairs),
            'persons_with_pairs':len({p['person'] for p in pairs}),
            'unmatched_touches':len(touches)-len(pairs),'unmatched_clicks':len(clicks)-len(pairs),
            'total_wait_seconds':total_wait,
            'avg_wait_seconds':round(total_wait/len(pairs),3) if pairs else 0,
            'window_seconds':window_seconds}

def diff_pairs(old,new):
    """新旧两版配对对比,刻画"改派":以 (person,click_no) 为键。
    返回 added/removed/reassigned 三组明细。"""
    def key(p): return (p['person'],p['click_no'])
    oldm={key(p):p for p in old};newm={key(p):p for p in new}
    added=[_brief(p) for k,p in newm.items() if k not in oldm]
    removed=[_brief(p) for k,p in oldm.items() if k not in newm]
    reassigned=[]
    for k in oldm.keys()&newm.keys():
        o,n=oldm[k],newm[k]
        if o['touch_no']!=n['touch_no']:
            reassigned.append({'person':k[0],'click_no':k[1],'old_touch_no':o['touch_no'],
                               'new_touch_no':n['touch_no'],'old_channel':o['channel'],'new_channel':n['channel']})
    keyf=lambda x:(x['person'],x['click_no'])
    return {'added':sorted(added,key=keyf),'removed':sorted(removed,key=keyf),
            'reassigned':sorted(reassigned,key=keyf)}

def _brief(p):
    return {'person':p['person'],'click_no':p['click_no'],'touch_no':p['touch_no'],
            'channel':p['channel'],'wait_seconds':p['wait_seconds']}
