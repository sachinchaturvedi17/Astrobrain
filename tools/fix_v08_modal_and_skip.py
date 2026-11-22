import compileall
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "aipandit"
STATIC = SRC / "web" / "static"

# 1. Find the stylesheet linked in index.html
idx_p = STATIC / "index.html"
idx_txt = idx_p.read_text(encoding="utf-8")
css_match = re.search(r'<link[^>]+href=["\']/?([^"\'?]+\.css)', idx_txt)
css_name = css_match.group(1) if css_match else "styles.css"
css_p = STATIC / css_name
if not css_p.exists():
    css_candidates = list(STATIC.glob("*.css"))
    css_p = css_candidates[0] if css_candidates else STATIC / "styles.css"

# 2. Append CSP-safe centered modal & skip button CSS to stylesheet
css_txt = css_p.read_text(encoding="utf-8") if css_p.exists() else ""
css_txt = re.sub(r"/\* AstroMuni v0\.8 Modal \*/.*$", "", css_txt, flags=re.DOTALL)
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
.am-lang-backdrop[hidden] {
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
print(f"[OK] Added modal CSS to {css_p.name}")

# 3. Update index.html: clean CSP-compliant modal markup + Skip button on Step 3 + cache-busting
idx_txt = re.sub(r"\n<!-- AstroMuni v0\.8.*?</body>", "\n</body>", idx_txt, flags=re.DOTALL)
idx_txt = re.sub(r'<button[^>]*id="skipPalmStep"[^>]*>.*?</button>', "", idx_txt)

# Add Skip button right before #nextStep inside .ob-nav
idx_txt = idx_txt.replace(
    '<button type="submit" class="btn" id="nextStep"',
    '<button type="button" class="btn ghost" id="skipPalmStep" hidden>Skip</button>\n          <button type="submit" class="btn" id="nextStep"',
    1,
)

# Cache-bust CSS & JS files so browser loads fresh assets
idx_txt = re.sub(r'((?:href|src)=["\'][^"\']*\.(?:css|js))(?:\?v=[^"\']*)?(["\'])', r'\1?v=0.8.2\2', idx_txt)

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
print("[OK] Updated index.html with CSP-clean centered modal and #skipPalmStep button")

# 4. Update app.js: handle centered language modal + Step 3 Skip button + zero mandatory palm check
app_p = STATIC / "app.js"
app_txt = app_p.read_text(encoding="utf-8")
app_txt = re.sub(r"\n// === AstroMuni v0\.8 Modal & Skip Logic ===.*$", "", app_txt, flags=re.DOTALL)

# Ensure stepError never requires palms
app_txt = re.sub(r'if\s*\([^\n]*PALMS[^\n]*\)\s*return\s*\[[^\]]*\]\s*;', '// palms optional', app_txt)
app_txt = re.sub(r'return\s*\[\s*["\']needPalms["\'][^\]]*\]\s*;', 'return null;', app_txt)

app_txt += """
// === AstroMuni v0.8 Modal & Skip Logic ===
(function () {
  var SKIP_LABELS = { hg: "Skip", hi: "छोड़ें", en: "Skip" };

  function syncSkipButton() {
    var skipBtn = document.getElementById("skipPalmStep");
    if (!skipBtn) return;
    var isStep3 = (typeof STEP !== "undefined" && STEP === 3);
    skipBtn.hidden = !isStep3;
    var activeLang = (document.querySelector('#langSeg button[aria-pressed="true"]') || {}).dataset?.lang || "hg";
    skipBtn.textContent = SKIP_LABELS[activeLang] || "Skip";
  }

  function applyStartupLang(code) {
    sessionStorage.setItem("am_lang_chosen_v082", code);
    var topBtn = document.querySelector('#langSeg button[data-lang="' + code + '"]');
    if (topBtn) topBtn.click();
    var modal = document.getElementById("amLangModal");
    if (modal) modal.hidden = true;
    syncSkipButton();
  }

  function wireV08() {
    var modal = document.getElementById("amLangModal");
    document.querySelectorAll(".am-lang-opt").forEach(function (btn) {
      btn.addEventListener("click", function () {
        applyStartupLang(btn.getAttribute("data-am-lang") || "hg");
      });
    });

    // Show centered language modal immediately if not chosen yet in this tab/session
    var chosen = sessionStorage.getItem("am_lang_chosen_v082");
    if (!chosen) {
      if (modal) modal.hidden = false;
    } else {
      if (modal) modal.hidden = true;
      var topBtn = document.querySelector('#langSeg button[data-lang="' + chosen + '"]');
      if (topBtn) topBtn.click();
    }

    // Wire Skip button on Step 3 (Palm Photos)
    var skipBtn = document.getElementById("skipPalmStep");
    if (skipBtn) {
      skipBtn.addEventListener("click", function () {
        if (typeof PALMS !== "undefined") {
          PALMS.left = null;
          PALMS.right = null;
        }
        var form = document.querySelector("#v-onboard form");
        if (form) {
          form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        }
      });
    }

    // Keep Skip button visibility and language synced on every step/language change
    document.addEventListener("click", function () {
      setTimeout(syncSkipButton, 20);
    });
    syncSkipButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireV08);
  } else {
    wireV08();
  }
})();
"""
app_p.write_text(app_txt, encoding="utf-8")
print("[OK] Updated app.js with centered modal logic and Step 3 Skip handler")

# 5. Recompile & update dist/astrobrain-v0.8.zip
ok = compileall.compile_dir(str(SRC), quiet=1)
(ROOT / "dist").mkdir(exist_ok=True)
zp = ROOT / "dist" / "astrobrain-v0.8.zip"
skip = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "knowledge_base"}
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(ROOT.rglob("*")):
        if f.is_file() and f.name != ".DS_Store" and not any(p in skip or p.endswith(".egg-info") for p in f.parts):
            zf.write(f, f"astrobrain-v0.8/{f.relative_to(ROOT)}")
print(f"[OK] Compiled ({ok}) and rebuilt {zp}")
