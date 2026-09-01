(() => {
  const base = (window.CLOUDCOST_CONFIG?.API_BASE_URL || "").replace(/\/$/, "");
  if (!base) return;
  const money = (v) => `$${Number(v || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const get = async (path) => { const r = await fetch(`${base}${path}`, { headers: { Accept: "application/json" } }); if (!r.ok) throw new Error(`API ${r.status}`); return r.json(); };

  async function dashboard() {
    const data = await get("/api/dashboard");
    const cards = document.querySelectorAll(".kpi-card");
    if (cards[0]) cards[0].querySelector(".kpi-value").textContent = money(data.total_cost);
    if (cards[1]) cards[1].querySelector(".kpi-value").textContent = money(data.forecast_cost);
    if (cards[2]) { cards[2].querySelector(".kpi-value").textContent = money(data.budget?.limit); const n=cards[2].querySelector(".kpi-note"); if(n)n.textContent=`${Number(data.budget_used_percent||0).toFixed(1)}% used`; }
    const change=Number(data.month_change_percent||0), note=cards[0]?.querySelector(".kpi-note");
    if(note){note.textContent=`${change>=0?"↗":"↘"} ${Math.abs(change).toFixed(1)}% vs last month`;note.className=`kpi-note ${change<=0?"trend-up":"trend-down"}`;}
    const rows=document.querySelectorAll(".legend-row"); (data.services||[]).slice(0,rows.length).forEach((s,i)=>{const row=rows[i], spans=row.querySelectorAll("span"), strong=row.querySelector("strong"); if(spans[1])spans[1].textContent=s.service.replace(/^Amazon /,""); if(strong)strong.childNodes[0].textContent=money(s.cost)+" ";});
    const updated=document.getElementById("updated-time"); if(updated)updated.textContent="just now";
    const month=document.getElementById("current-month"); if(month)month.textContent=new Date().toLocaleString("en-US",{month:"long",year:"numeric"});
  }

  async function resources(){
    const data=await get("/api/resources"), rows=document.querySelectorAll(".data-table tbody tr");
    data.slice(0,rows.length).forEach((x,i)=>{const c=rows[i].querySelectorAll("td"); if(c.length>=5){c[0].textContent=x.name||"-";c[1].textContent=x.type||"-";c[2].textContent=x.region||"-";c[3].textContent=x.status||"-";}});
  }

  async function monitoring(){
    const d=await get("/api/monitoring"), metrics=document.querySelectorAll(".metric strong");
    if(metrics[0])metrics[0].textContent=`${Number(d.ec2_cpu||0).toFixed(1)}%`;
    if(metrics[1])metrics[1].textContent=`${Number(d.rds_cpu||0).toFixed(1)}%`;
  }

  async function security(){
    const d=await get("/api/security"), metrics=document.querySelectorAll(".metric strong");
    if(metrics[0])metrics[0].textContent=d.cloudtrail?.some(x=>x.is_logging)?"Enabled":"Check";
    if(metrics[1])metrics[1].textContent=d.waf_acls?"Protected":"Not configured";
    if(metrics[2])metrics[2].textContent=String(d.iam_roles||0);
  }

  async function budgets(){
    const data=await get("/api/budgets"), rows=document.querySelectorAll(".data-table tbody tr");
    data.slice(0,rows.length).forEach((b,i)=>{const c=rows[i].querySelectorAll("td");if(c.length>=4){c[0].textContent=b.name||"AWS Budget";c[1].textContent=money(b.actual);c[2].textContent=money(b.forecast);c[3].textContent=b.limit?`${(b.actual/b.limit*100).toFixed(1)}%`:"-";}});
  }

  async function sync(){
    const route=location.hash.replace(/^#/,"")||"dashboard";
    try { if(route==="dashboard"||route==="cost-explorer"||route==="cost-by-service") await dashboard(); else if(route==="resources") await resources(); else if(route==="monitoring") await monitoring(); else if(route==="security") await security(); else if(route==="budgets-alerts") await budgets(); }
    catch(e){ console.warn("CloudCost AWS API unavailable; preview data remains visible.",e); const u=document.getElementById("updated-time");if(u)u.textContent="preview mode"; }
  }

  document.addEventListener("DOMContentLoaded",()=>{sync();document.getElementById("refresh-btn")?.addEventListener("click",sync);window.addEventListener("hashchange",()=>setTimeout(sync,80));});
})();
