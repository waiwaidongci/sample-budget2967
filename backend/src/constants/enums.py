ROLES=('admin','analyst','viewer')
# queued/running: 在途计算; published: 当前发布; superseded: 曾被发布后被新版替换;
# stale: 计算完成时事件版本已前进,按约定不得发布为当前结果; failed: 计算失败
RUN_STATES=('queued','running','published','superseded','stale','failed')
EVENT_KINDS=('touch','click')
EVENT_STATES=('active','withdrawn')
QUEUE='attribution-queue'
