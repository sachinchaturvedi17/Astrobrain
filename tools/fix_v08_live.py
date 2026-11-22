import compileall
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "aipandit"
STATIC = SRC / "web" / "static"

# 1. CSS: centered modal visible by default until user picks a language
css_p = STATIC / "app.css"
css_txt = re.sub(r"/\* AstroMuni v0\.8 Modal \*/.*$", "", css_p.read_text(encoding="utf-8"), flags=re.DOTALL)
css_txt += """
/* AstroMuni v0.8 Modal */
.am-lang-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(30, 19, 10, 0.65);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 99999;
  padding: 16px;
}
.am-lang-backdrop.is-hidden {
  display: none !important;
}
.am-lang-dialog {
  background: #fffdf8;
  border: 1px solid #dfc89e;
  border-radius: 20px;
  max-width: 420px;
  width: 100%;
  padding: 28px 24px;
  text-align: center;
  box-shadow: 0 24px 60px rgba(24, 15, 7, 0.32);
  color: #3b2310;
}
.am-lang-pill {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #8a5a19;
  background: #f8eed8;
  border: 1px solid #e6cfa0;
  border-radius: 999px;
  padding: 4px 12px;
  margin-bottom: 12px;
}
.am-lang-dialog h2 {
  margin: 0 0 8px;
  font-size: 1.3rem;
  font-weight: 700;
  color: #3b2310;
}
.am-lang-dialog p {
  margin: 0 0 22px;
  font-size: 0.94rem;
  color: #6e5239;
}
.am-lang-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.am-lang-opt {
  padding: 13px 8px;
  border-radius: 12px;
  border: 1.5px solid #cfa968;
  background: #fff8eb;
  color: #3b2310;
  font-size: 0.96rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease, border-color 0.16s ease;
}
.am-lang-opt:hover,
.am-lang-opt:focus {
  background: #4a2c14;
  border-color: #4a2c14;
  color: #fffdf8;
  outline: none;
}
#skipPalmStep[hidden] {
  display: none !important;
}
"""
css_p.write_text(css_txt, encoding="utf-8")

# 2. HTML: centered modal open on page load + cache-bust v0.8.3
idx_p = STATIC / "index.html"
idx_txt = re.sub(r"\n<!-- AstroMuni v0\.8.*?</body>", "\n</body>", idx_p.read_text(encoding="utf-8"), flags=re.DOTALL)
idx_txt = re.sub(r'((?:href|src)=["\'][^"\']*\.(?:css|js))(?:\?v=[^"\']*)?(["\'])', r'\1?v=0.8.3\2', idx_txt)

modal_html = """
<!-- AstroMuni v0.8 Centered Language Modal -->
<div id="amLangModal" class="am-lang-backdrop" role="dialog" aria-modal="true" aria-labelledby="amLangHeading">
  <div class="am-lang-dialog">
    <div class="am-lang-pill">AstroMuni</div>
    <h2 id="amLangHeading">अपनी भाषा चुनें / Choose Language</h2>
    <p>Select your preferred language to begin</p>
    <div class="am-lang-options">
      <button type="button" class="am-lang-opt" data-am-lang="hg">Hinglish</button>
      <button type="button" class="am-lang-opt" data-am-lang="hi">हिन्दी</button>
      <button type="button" class="am-lang-opt" data-am-lang="en">English</button>
    </div>
  </div>
</div>
</body>"""
idx_p.write_text(idx_txt.replace("</body>", modal_html, 1), encoding="utf-8")

# 3. JS: delegated click handlers for language modal & Step 3 Skip button
app_p = STATIC / "app.js"
app_txt = re.sub(r"\n// === AstroMuni v0\.8 Modal & Skip Logic ===.*$", "", app_p.read_text(encoding="utf-8"), flags=re.DOTALL)
app_txt += """
// === AstroMuni v0.8 Modal & Skip Logic ===
(function () {
  var SKIP_LABELS = { hg: "Skip", hi: "छोड़ें", en: "Skip" };

  function syncSkipButton() {
    var skipBtn = document.getElementById("skipPalmStep");
    if (!skipBtn) return;
    var isStep3 = (typeof STEP !== "undefined" && STEP === 3);
    skipBtn.hidden = !isStep3;
    var pressed = document.querySelector('#langSeg button[aria-pressed="true"]');
    var activeLang = pressed ? pressed.getAttribute("data-lang") : "hg";
    skipBtn.textContent = SKIP_LABELS[activeLang] || "Skip";
  }

  document.addEventListener("click", function (ev) {
    var langBtn = ev.target.closest(".am-lang-opt");
    if (langBtn) {
      var code = langBtn.getAttribute("data-am-lang") || "hg";
      var topBtn = document.querySelector('#langSeg button[data-lang="' + code + '"]');
      if (topBtn) topBtn.click();
      var modal = document.getElementById("amLangModal");
      if (modal) modal.classList.add("is-hidden");
      setTimeout(syncSkipButton, 20);
      return;
    }

    var skipBtn = ev.target.closest("#skipPalmStep");
    if (skipBtn) {
      if (typeof PALMS !== "undefined") {
        PALMS.left = null;
        PALMS.right = null;
      }
      var form = document.querySelector("#v-onboard form");
      if (form) {
        if (form.requestSubmit) form.requestSubmit();
        else form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      }
      return;
    }

    setTimeout(syncSkipButton, 20);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncSkipButton);
  } else {
    syncSkipButton();
  }
})();
"""
app_p.write_text(app_txt, encoding="utf-8")
compileall.compile_dir(str(SRC), quiet=1)
print("[OK] Updated app.css, index.html, and app.js")
