const form=document.getElementById("form");
const bar=document.getElementById("bar");
const statusMessage=document.getElementById("statusMessage");
const submitBtn=document.getElementById("submitBtn");

function setStatus(message, isError=false) {
    statusMessage.textContent = message;
    statusMessage.style.color = isError ? "#b22222" : "#0b5fff";
}

form.onsubmit=async(e)=>{
    e.preventDefault();
    bar.value=0;
    submitBtn.disabled = true;
    submitBtn.textContent = "Downloading...";
    setStatus("Download started. Please wait...");

    const data=new FormData(form);

    try {
        const response = await fetch("/start",{method:"POST",body:data});
        const result = await response.json();

        if (response.status === 400 && result.status === "duplicate") {
            const shouldOverride = confirm("⚠️ This URL already exists in downloads. Do you want to override and download it again?");
            if (!shouldOverride) {
                setStatus("⚠️ " + result.message, true);
                submitBtn.disabled = false;
                submitBtn.textContent = "Download";
                return;
            }

            const overrideData = new FormData(form);
            overrideData.set("override", "true");
            const overrideResponse = await fetch("/start", { method: "POST", body: overrideData });
            const overrideResult = await overrideResponse.json();

            if (overrideResponse.status === 400 && overrideResult.status === "duplicate") {
                setStatus("⚠️ " + overrideResult.message, true);
                submitBtn.disabled = false;
                submitBtn.textContent = "Download";
                return;
            }

            if (!overrideResponse.ok) {
                setStatus("⚠️ Download could not start after override. Please try again.", true);
                submitBtn.disabled = false;
                submitBtn.textContent = "Download";
                return;
            }

            const t2 = setInterval(async()=>{
                const r=await fetch("/progress");
                const j=await r.json();
                bar.value=j.value;
                if(j.value>=100){
                    clearInterval(t2);
                    const skipped = overrideResult.skipped || [];
                    let message = "✅ Download complete! Check the Downloads page.";
                    if (skipped.length > 0) {
                        const firstReasons = skipped.slice(0, 3).map(item => item.reason || "unknown reason");
                        message = `✅ Download complete. ${skipped.length} video(s) were skipped: ${firstReasons.join("; ")}`;
                    }
                    setStatus(message);
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Download";
                    alert(message);
                    window.location.href="/downloads";
                }
            },500);
            return;
        }

        if (!response.ok) {
            setStatus("⚠️ Download could not start. Please try again.", true);
            submitBtn.disabled = false;
            submitBtn.textContent = "Download";
            return;
        }

        const t=setInterval(async()=>{
            const r=await fetch("/progress");
            const j=await r.json();
            bar.value=j.value;
            if(j.value>=100){
                clearInterval(t);
                const skipped = result.skipped || [];
                let message = "✅ Download complete! Check the Downloads page.";
                if (skipped.length > 0) {
                    const firstReasons = skipped.slice(0, 3).map(item => item.reason || "unknown reason");
                    const details = firstReasons.join("; ");
                    message = `✅ Download complete. ${skipped.length} video(s) were skipped: ${details}`;
                }
                setStatus(message);
                submitBtn.disabled = false;
                submitBtn.textContent = "Download";
                alert(message);
                window.location.href="/downloads";
            }
        },500);
    } catch (error) {
        setStatus("⚠️ Network error while starting the download.", true);
        submitBtn.disabled = false;
        submitBtn.textContent = "Download";
    }
};

