const API="";
const state={products:[],product:null};

const $=id=>document.getElementById(id);
const money=v=>v==null||Number.isNaN(Number(v))?"—":new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format(Number(v));
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));

let paymentPoller = null;

function startPaymentPolling(negotiationId) {
    if (paymentPoller) {
        clearInterval(paymentPoller);
    }

    paymentPoller = setInterval(async () => {
        try {
            const response = await fetch(
                `${API}/negotiations/${negotiationId}`
            );

            if (!response.ok) {
                return;
            }

            const negotiation = await response.json();

            // Update the UI with the latest database state
            renderResult(negotiation);

            // Stop polling once payment is completed
            if (negotiation.payment_status === "paid") {
                clearInterval(paymentPoller);
                paymentPoller = null;

                $("round").textContent = "PAID";
            }

        } catch (error) {
            console.log("Payment status check failed:", error);
        }
    }, 3000);
}

function renderProduct(p){
 state.product=p;
 $("productInfo").innerHTML=`
 <div class="stat"><small>List Price</small><b>${money(p.list_price)}</b></div>
 <div class="stat"><small>Hard Floor</small><b>${money(p.floor_price)}</b></div>
 <div class="stat"><small>Inventory</small><b>${p.current_inventory??"—"}</b></div>
 <div class="stat"><small>Weeks Left</small><b>${p.weeks_remaining??"—"}</b></div>`;
 $("merchantSummary").textContent=`Floor ${money(p.floor_price)} · List ${money(p.list_price)}`;
 $("merchantData").innerHTML=`
 <div class="metric"><small>List Price</small><b>${money(p.list_price)}</b></div>
 <div class="metric"><small>Hard Floor</small><b>${money(p.floor_price)}</b></div>
 <div class="metric"><small>Inventory</small><b>${p.current_inventory??"—"}</b></div>
 <div class="metric"><small>Weeks Remaining</small><b>${p.weeks_remaining??"—"}</b></div>
 <div class="metric"><small>Beginning Inventory</small><b>${p.beginning_inventory??"—"}</b></div>
 <div class="metric"><small>Product</small><b>${esc(p.name)}</b></div>`;
 $("factors").innerHTML=["Historical sales","Inventory pressure","Sales velocity","Hard floor constraint"].map((x,i)=>`
 <div class="factor"><div class="factor-head"><span>${x}</span><span>${i===3?money(p.floor_price):"Enabled"}</span></div>
 <div class="bar"><div class="fill" style="width:${[72,85,65,100][i]}%"></div></div></div>`).join("");
}

async function loadProducts(){
 const r=await fetch(API+"/products/");
 if(!r.ok)throw Error("Could not load products.");
 state.products=await r.json();
 $("product").innerHTML=state.products.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join("");
 if(state.products.length)renderProduct(state.products[0]);
}

$("product").onchange=()=>renderProduct(state.products.find(p=>p.id==$("product").value));
function buyerSummary(){$("buyerSummary").textContent=`Target ${money($("target").value)} · Budget ${money($("budget").value)}`}
$("target").oninput=buyerSummary;$("budget").oninput=buyerSummary;

function renderRounds(rounds){
 const box=$("transcript");box.classList.remove("empty");
 if(!rounds.length){box.innerHTML="<div class='empty-result'>No transcript entries returned.</div>";return}
 box.innerHTML=rounds.map(r=>{
   const buyer=String(r.actor||"").toLowerCase().includes("buyer");
   return `<div class="message ${buyer?"buyer":"merchant"}"><div class="bubble">
   <div class="meta"><span>${buyer?"Buyer Agent":"Merchant Agent"}</span><span>Round ${r.round_no}</span></div>
   <div class="reason">${esc(r.reasoning||r.action)}</div>
   ${r.offer_amount!=null?`<div class="offer">${money(r.offer_amount)}</div>`:""}</div></div>`;
 }).join("");
 box.scrollTop=box.scrollHeight;
}

function renderResult(n){
 if(String(n.status).toLowerCase()==="agreed"&&n.agreed_price!=null){
   const savings=Math.max(0,(state.product?.list_price||n.agreed_price)-n.agreed_price);
   $("result").innerHTML=`<div class="deal"><div class="check">✓</div><div class="deal-label">DEAL AGREED</div>
   <div class="deal-price">${money(n.agreed_price)}</div><div class="deal-sub">Buyer saves ${money(savings)} from list price</div>
   ${n.payment_link_url?`<a class="pay" href="${n.payment_link_url}" target="_blank">Pay with Razorpay →</a>`:"<div class='deal-sub'>Payment link unavailable</div>"}
   <div class="deal-sub" style="margin-top:9px">Payment status: ${esc(n.payment_status)}</div></div>`;
 }else $("result").innerHTML=`<div class="empty-result"><span style="color:var(--red);font-size:24px">×</span><br>Negotiation did not reach an agreement.</div>`;
}

$("start").onclick=async()=>{
 $("error").textContent="";
 const target=Number($("target").value),budget=Number($("budget").value);
 if(!target||!budget){$("error").textContent="Enter target and budget.";return}
 if(target>budget){$("error").textContent="Target cannot exceed budget.";return}
 $("start").disabled=true;$("start").textContent="Agents negotiating…";$("round").textContent="RUNNING";
 $("transcript").classList.remove("empty");$("transcript").innerHTML="<div class='empty-result'>Buyer Agent and Merchant Agent are analyzing the negotiation…</div>";
 try{
  const r=await fetch(API+"/negotiations/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
   product_id:state.product.id,buyer_target:target,buyer_budget:budget,persona:$("persona").value,max_rounds:Number($("rounds").value)
  })});
  const data=await r.json();if(!r.ok)throw Error(data.detail||"Negotiation failed.");
  let detail=data;const d=await fetch(API+"/negotiations/"+data.id);if(d.ok)detail=await d.json();
  $("round").textContent=String(detail.status||"COMPLETE").toUpperCase();
  renderRounds(detail.rounds || []);
renderResult(detail);
loadHistory();

if (
    detail.status === "agreed" &&
    detail.payment_link_url &&
    detail.payment_status !== "paid"
) {
    startPaymentPolling(detail.id);
}
 }catch(e){$("error").textContent=e.message;$("round").textContent="ERROR";$("transcript").innerHTML="<div class='empty-result'>Backend unavailable or negotiation failed.</div>"}
 finally{$("start").disabled=false;$("start").innerHTML="Start AI Negotiation <b>→</b>"}
};

async function loadHistory(){
 const r=await fetch(API+"/negotiations/");if(!r.ok)return;
 const list=await r.json();
 $("historyBody").innerHTML=list.length?list.map(n=>{
  const p=state.products.find(x=>x.id===n.product_id);const s=String(n.status||"unknown").toLowerCase();
  const cls=s==="agreed"?"green":s==="rejected"?"red":"blue";
  return `<tr><td>#${n.id}</td><td>${esc(p?.name||("Product "+n.product_id))}</td><td>${esc(n.persona)}</td><td>${n.max_rounds}</td><td>${money(n.agreed_price)}</td><td><span class="badge ${cls}">${s}</span></td><td>${esc(n.payment_status)}</td></tr>`;
 }).join(""):"<tr><td colspan='7' style='text-align:center;color:var(--muted)'>No negotiations yet.</td></tr>";
}
$("refresh").onclick=loadHistory;
document.querySelectorAll(".nav").forEach(b=>b.onclick=async()=>{document.querySelectorAll(".nav").forEach(x=>x.classList.remove("active"));b.classList.add("active");$("dashboard").classList.toggle("hidden",b.dataset.page!=="dashboard");$("history").classList.toggle("hidden",b.dataset.page==="dashboard");if(b.dataset.page==="history")await loadHistory()});

(async()=>{try{await loadProducts();await loadHistory()}catch(e){$("error").textContent=e.message}})();
