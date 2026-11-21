import {DOMAIN} from './constants/domain.js';
import {post} from './api/client.js';
import {store,load,pending} from './stores/attribution.js';
import {pages} from './router/index.js';
import {bindForm} from './hooks/forms.js';
import {esc} from './utils/format.js';
const app=document.getElementById('app');let active=false;
function login(){app.innerHTML=`<div class="login"><section><div class="eyebrow">${DOMAIN.slug.toUpperCase()} / ATTRIBUTION LEDGER</div><h1>${DOMAIN.title}</h1><p class="lead">${DOMAIN.scenario}</p><div class="method-note">${DOMAIN.note}</div><small>合成数据归因演示 · ${DOMAIN.id} · Python 实算</small></section><form id="login-form"><h2>进入归因工作席</h2><label>账号<input name="email" type="email" value="admin@demo.local" required></label><label>密码<input name="password" type="password" value="Research2026!" required></label><button type="submit">登录 →</button><p>负责人 admin / 分析师 analyst / 观察员 viewer<br>后缀 @demo.local · 密码 Research2026!</p><div id="notice" role="alert"></div></form></div>`;bindForm('login-form',async data=>{const x=await post('/auth/login',data);localStorage.setItem('research-token',x.token);localStorage.setItem('research-role',x.role);localStorage.setItem('research-email',x.email);await boot();});}
async function render(){if(active)return;active=true;try{const [key='overview',id]=location.hash.slice(1).split('/'),page=pages[key]||pages.overview;app.innerHTML=`<header><a class="brand" href="#overview">${DOMAIN.title.slice(0,2)} <span>${DOMAIN.slug}</span></a><nav>${[['overview','归因总览'],['events','事件录入'],['runs','归因计算'],['results','当前结果'],['review','复盘'],['audit','操作留痕']].map(([k,v])=>`<a class="${key===k?'active':''}" href="#${k}">${v}</a>`).join('')}</nav><button id="logout" class="text">${esc(localStorage.getItem('research-role'))} · 退出</button></header><main id="content"><p>读取业务数据…</p></main><footer>ATTRIBUTION LEDGER / ${DOMAIN.id} <span>合成数据 · 版本化事件 · 守卫式发布</span></footer><div id="notice" role="alert"></div>`;document.getElementById('content').innerHTML=await page.render(id);page.bind(()=>render());document.getElementById('logout').onclick=()=>{localStorage.clear();login();};}catch(e){document.getElementById('notice').textContent=e.message;}finally{active=false;}}
async function boot(){if(!localStorage.getItem('research-token'))return login();try{await load();await render();}catch(e){login();document.getElementById('notice').textContent=e.message;}}
window.addEventListener('hashchange',()=>render());
setInterval(async()=>{if(localStorage.getItem('research-token')&&pending()){await load();await render();}},2000);
boot();
