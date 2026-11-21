# 榆灯全渠道归因台

同一人收到多个渠道的触达后,一次点击常被各渠道重复认领。本应用录入带编号和时间的触达与点击,在约定时窗内给同一人的事件一对一配对:先让归因的点击最多,再让总等待最短,同分按事件编号定。迟到补报与撤回触发重算并改派原配对;结果按事件版本发布,明细与分渠道首点率同源同版、一次性切换,复盘页可查配对与旧版结果。原生 HTML/CSS/JavaScript 多模块工作席,所有计算由 Python 完成。

## 模拟业务

榆灯研究协作组,12名分析师与业务人员,日常把短信、推送、邮件、广告四个渠道的触达与点击手工抄表对量,一次点击常被多个渠道重复认领。当前三个痛点:重复认领无统一口径、迟到补报与撤回后旧配对无人改派、补报与计算并发时结果版本混乱。上游提供独立合成业务事件流;本应用接管事件登记、归因配对与版本化发布;下游负责人在复盘页核对配对与改派,观察员只读查阅。

核心业务实体:AttributionProject(归因项目,约定时窗与渠道名单)/ TouchClickEvent(触达与点击,带编号、时间与版本)/ AttributionRun(一次基于某事件版本的计算与发布)。源码 model/schema/service/controller/route 与前端 api/store/pages 完成链路,不依赖浏览器本地假数据。

## 功能与方法

- 归因项目登记约定时窗(小时)与渠道名单;触达必须取自名单,点击不带渠道;重名项目、非法时窗明确拒绝。
- 事件录入带编号(项目内同类唯一,撤回不释放)、同一人标识、发生时间(ISO 8601 带时区);支持单条录入与 JSON 批量补报,整批校验、任一非法整批拒绝。
- 配对规则(逐人二分图最小费用最大流,确定性、可复现):
  1. 可配:点击不早于触达,且 点击时间−触达时间 ≤ 约定时窗;一触达一点击。
  2. 先让归因的点击最多(配对数最大);
  3. 再让总等待最短(Σ等待秒最小);
  4. 同分按事件编号定:依次比较配对触达编号总和、配对点击编号总和,小者优先;仍相同由固定增广顺序(节点与边按编号升序)确定,与输入顺序无关。
- 迟到记录(发生时间早于在版事件的补报)与撤回都会递进事件版本并自动排队重算,新发布版相对上一发布版给出改派/新增/移除明细。
- 补报与计算并发时,旧计算不得发布为当前结果:计算完成时锁定项目行校验事件版本,版本已前进则该计算标记"过期未发布"并留档。
- 明细与分渠道首点率由同一次计算产出、存于同一结果,随项目的当前发布指针在同一事务一次性切换;读侧永远看到同一版事件的同一套结果。
- 分渠道首点率:每人时间最早(同刻取点击编号小者)的已配对点击为其"首点";渠道首点率 = 该渠道赢得的首点人数 ÷ 全部有配对人数,各渠道合计为 1。
- 复盘页按版本留档:当前发布、历史已发布(superseded)、过期未发布(stale)均可查对配对与首点率;审计记录登录、项目创建、事件录入/补报/撤回、排队、发布与过期;240请求/分钟限流、全局可恢复错误。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```

访问 http://localhost:18244 ,API http://localhost:19244/docs 。数据库映射 17744。无需Node构建。可以从中文和带空格目录启动。清理 `docker compose down -v --remove-orphans` 会删除本题演示数据卷。

|角色|账号|密码|权限与典型动作|
|---|---|---|---|
|admin 负责人|admin@demo.local|Research2026!|全部读写、创建项目、录入/撤回、重算|
|analyst 分析师|analyst@demo.local|Research2026!|同负责人读写;不能修改角色|
|viewer 观察员|viewer@demo.local|Research2026!|只读:总览、当前结果、复盘、留痕|

## 一天的工作剧本

1. 09:00 admin登录,总览看到种子项目"榆灯·冬季全渠道归因"(约定时窗72小时)及其四个版本:v1基础、v2迟到补报改派、v3撤回改派、v4补报并发(一次手动计算过期未发布)。
2. 09:10 analyst在事件录入页核对在版事件与各自录入版本,确认一条重复上报的触达已撤回。
3. 09:20 打开当前结果页:分渠道首点率与配对明细同版同窗(短信首点率 3/6),核对 SHA256 与事件版本 v4。
4. 09:30 批量补报一批迟到的点击,事件版本递进为 v5,系统自动排队重算;当前结果页提示"新计算在途",2秒后一次性切换到 v5。
5. 09:35 在复盘页对比 v4 与 v5 的配对,查看补报引起的改派/新增明细;过期未发布的计算也留档可查。
6. 09:40 viewer在操作留痕页核对登录、补报、撤回、发布与过期记录。

seed剧情:U101 先后被短信、推送触达,一次点击只配对等待更短的推送;随后迟到的广告触达(更接近点击)补报,点击改派广告。U106 的邮件触达系重复上报,撤回后点击改派短信。U107 的短信触达迟到一天,补报后补上配对。v3 上一个手动重算排队期间又有补报,该计算完成时版本已前进,按约定过期未发布。

## 技术与目录

|部分|实现|
|---|---|
|前端|原生ES modules、HTML/CSS、Nginx1.27,无前端框架|
|API|Python3.11、FastAPI0.115、SQLAlchemy2、JWT、PBKDF2密码|
|计算|逐人二分图最小费用最大流(纯Python大整数权重编码三级目标)|
|数据库|PostgreSQL16(本地测试用SQLite)|
|任务|Redis7持久队列,Python独立worker,心跳healthcheck|

`frontend/src/`分api、stores、types、components/common、hooks、pages、router、utils、constants;`backend/src/`分config、models、schemas、services、controllers、routes、middlewares、utils、constants;`backend/scripts/seed_demo.py`自然键插入、重复不覆盖修改;`backend/tests/`为配对引擎、版本守卫与API的pytest测试;`backend/migrations/README.md`说明schema版本。

环境变量 `.env.example`:COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、DB_PASSWORD、JWT_SECRET、SEED_DEMO。开发时在本地venv安装backend/requirements.txt,设置DATABASE_URL、REDIS_URL、JWT_SECRET再运行uvicorn;前端开发经Nginx代理 `/api/` 到不带前缀的API。

共享枚举:角色admin/analyst/viewer;运行状态queued/running/published/superseded/stale/failed;事件touch/click与active/withdrawn。后端`src/constants/enums.py`、认证与worker使用相同值;前端`src/types/enums.js`、状态与角色界面使用相同值。Google Fonts:Noto Serif SC + IBM Plex Mono;断网使用serif/monospace回退。

## 版本、并发与复现

- 每次录入/补报/撤回使项目事件版本 +1(行内原子递进),事件记录录入版本与撤回版本;任意历史版本的在版事件可精确重建,旧版结果可复算。
- 计算任务记录 base_version 与事件快照 SHA256;同版本重算结果逐字节一致(确定性配对)。
- 发布守卫:计算完成时 `SELECT ... FOR UPDATE` 锁定项目行,仅当事件版本仍等于 base_version 才发布;否则标记过期未发布。发布与版本递进互斥,杜绝"旧计算覆盖新结果"。
- 一次性切换:配对明细与分渠道首点率存于同一运行结果,项目当前指针在同一事务内翻转;旧版同时转为 superseded。
- 独立oracle:`backend/tests/`用暴力枚举复核400组随机案例的配对数与总等待,并验证确定性、编号定序、撤回改派、守卫与API。

已知边界:小型本地研究应用,使用合成数据,不含企业SSO与外发邮件;单worker顺序消费,崩溃后在途任务重启恢复;数据库与Redis间未采用分布式事务(先入队失败即整体回滚,入队后失败由重启恢复兜底);单项目事件上限2000条、单批补报500条;SQLite仅用于本地测试,生产PostgreSQL提供行锁保证。以当前测试目录TESTING.md记录实际验证结果。

MIT License。
