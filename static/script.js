let reportCount = 1;

/* TAB SWITCH */
function openReport(index) {
  document.querySelectorAll('.report').forEach((r, i) => {
    r.classList.toggle('active', i === index);
  });

  document.querySelectorAll('.tab').forEach((t, i) => {
    t.classList.toggle('active', i === index);
  });
}

/* ADD REPORT */
function addReport() {
  reportCount++;

  const tabs = document.querySelector('.tabs');
  const form = document.getElementById('serviceForm');
  const status = document.getElementById('status');

  const newTab = document.createElement('button');
  newTab.className = 'tab';
  newTab.innerText = `Report ${reportCount}`;
  newTab.onclick = () => openReport(reportCount - 1);

  tabs.insertBefore(newTab, tabs.lastElementChild);

  const report = document.querySelector('.report').cloneNode(true);
  report.classList.remove('active');

  /* CLEAR VALUES */
  report.querySelectorAll('input, textarea, select').forEach(f => {
    if (f.type === "checkbox") f.checked = false;
    else if (f.tagName === "SELECT") f.selectedIndex = 0;
    else f.value = "";
  });

  form.insertBefore(report, status);
}

/* 🔥 FIXED DATA COLLECTION */
function collectData() {
  let data = "";

  document.querySelectorAll('.report').forEach((r, i) => {
    data += `Report ${i + 1}\n------------------\n`;

    r.querySelectorAll('input, textarea, select').forEach(f => {

      if (f.type === "checkbox") {
        if (f.checked) {
          data += f.parentElement.innerText.trim() + "\n";
        }
      }

      else if (f.value && f.value.trim() !== "") {
        data += f.value.trim() + "\n";
      }

    });

    data += "\n";
  });

  return data.trim();
}

/* 🔥 FIXED SAVE */
async function saveReport() {
  const status = document.getElementById("status");

  const data = collectData();

  console.log("DATA:", data); // DEBUG

  if (!data || data === "") {
    alert("Form is empty!");
    return;
  }

  status.innerText = "Saving...";

  try {
    const res = await fetch("/save-report", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        title: "Report " + new Date().toLocaleString(),
        reportData: data
      })
    });

    const msg = await res.text();
    status.innerText = msg;

  } catch (err) {
    console.error(err);
    status.innerText = "Save Failed ❌";
  }
}

/* EMAIL (UNCHANGED) */
async function sendEmail() {
  const res = await fetch("/send-email", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ reportData: collectData() })
  });

  alert(await res.text());
}

/* PDF (UNCHANGED) */
function downloadPDF() {
  html2pdf().from(document.getElementById("serviceForm")).save();
}

/* SMOOTH SCROLL */
document.addEventListener("click", () => {
  document.body.style.scrollBehavior = "smooth";
});
