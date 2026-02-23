const form=document.getElementById("form");
const bar=document.getElementById("bar");

form.onsubmit=async(e)=>{
e.preventDefault();
bar.value=0;
const data=new FormData(form);

const response = await fetch("/start",{method:"POST",body:data});
const result = await response.json();

if (response.status === 400 && result.status === "duplicate") {
    alert("⚠️ " + result.message);
    return;
}

const t=setInterval(async()=>{
const r=await fetch("/progress");
const j=await r.json();
bar.value=j.value;
if(j.value>=100){
    clearInterval(t);
    alert("✅ Download complete! Check the Downloads page.");
    window.location.href="/downloads";
}
},500);
};

