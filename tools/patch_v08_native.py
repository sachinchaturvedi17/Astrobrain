import compileall, re, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "aipandit"
STATIC = SRC / "web" / "static"

# 1. app.js: make palm uploads optional in stepError() and body.palms
app_p = STATIC / "app.js"
app_txt = app_p.read_text(encoding="utf-8")
app_txt = re.sub(r'return\s*\[\s*["\']needPalms["\'][^\]]*\]\s*;', 'return null;', app_txt)
app_txt = app_txt.replace(
    "if (PALMS.left && PALMS.right) body.palms = { left: PALMS.left.b64, right: PALMS.right.b64 };",
    "if (PALMS.left || PALMS.right) body.palms = { left: PALMS.left ? PALMS.left.b64 : null, right: PALMS.right ? PALMS.right.b64 : null };",
)
app_p.write_text(app_txt, encoding="utf-8")

# 2. copy.js: update palmNote across hg, hi, en
copy_p = STATIC / "copy.js"
copy_txt = copy_p.read_text(encoding="utf-8")
for pat, rep in [
    (r'palmNote:\s*"AstroMuni abhi haath nahi padhta[^"]*"', 'palmNote: "Optional — aap palm photos skip kar sakte hain, lekin dono haathon ki saaf photos upload karne se zyada accurate jawab mil paata hai."'),
    (r'palmNote:\s*"AstroMuni अभी हाथ नहीं पढ़ता[^"]*"', 'palmNote: "वैकल्पिक — आप हथेली की फ़ोटो छोड़ भी सकते हैं, लेकिन दोनों हाथों की स्पष्ट फ़ोटो अपलोड करने से अधिक सटीक उत्तर मिल पाता है।"'),
    (r'palmNote:\s*"AstroMuni doesn\'t currently read palms[^"]*"', 'palmNote: "Optional — you can skip uploading palm photos, though adding clear photos of both hands helps us give an answer closer to accurate."'),
]:
    copy_txt = re.sub(pat, rep, copy_txt)
copy_p.write_text(copy_txt, encoding="utf-8")

# 3. Backend: ensure /api/start accepts missing palms
for py in (SRC / "web").rglob("*.py"):
    t = py.read_text(encoding="utf-8")
    t2 = re.sub(r'if\s+not\s+palms\b[^\n]*:\s*\n\s*return[^\n]*', 'if False:\n        pass', t)
    if t2 != t:
        py.write_text(t2, encoding="utf-8")

# 4. index.html: startup language modal + cache-busting
idx_p = STATIC / "index.html"
idx_txt = re.sub(r'\n<!-- AstroMuni v0\.8.*?</body>', '\n</body>', idx_p.read_text(encoding="utf-8"), flags=re.DOTALL)
idx_txt = re.sub(r'(src=["\'][^"\']*(?:copy|app)\.js)(?:\?v=[^"\']*)?(["\'])', r'\1?v=0.8.0\2', idx_txt)

modal = """
<!-- AstroMuni v0.8 Startup Language Modal -->
<div id="amLangModal" style="position:fixed;inset:0;background:rgba(34,22,12,.62);backdrop-filter:blur(4px);display:none;align-items:center;justify-content:center;z-index:99999;padding:16px">
  <div style="background:#fffdf8;border:1px solid #e2cfa8;border-radius:18px;max-width:420px;width:100%;padding:26px 22px;text-align:center;box-shadow:0 20px 48px rgba(34,22,12,.28);color:#3b2310">
    <div style="display:inline-block;font-size:.78rem;font-weight:600;color:#8a5a19;background:#f8eed8;border:1px solid #e6cfa0;border-radius:999px;padding:4px 12px;margin-bottom:10px">AstroMuni</div>
    <h2 style="margin:0 0 6px;font-size:1.25rem;font-weight:700">अपनी भाषा चुनें / Choose Language</h2>
    <p style="margin:0 0 20px;font-size:.92rem;color:#6e5239">Select your preferred language to continue</p>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
      <button type="button" class="am-lc" data-am-lang="hg" style="padding:12px 8px;border-radius:12px;border:1.5px solid #cfa968;background:#fff8eb;color:#3b2310;font-size:.95rem;font-weight:600;cursor:pointer">Hinglish</button>
      <button type="button" class="am-lc" data-am-lang="hi" style="padding:12px 8px;border-radius:12px;border:1.5px solid #cfa968;background:#fff8eb;color:#3b2310;font-size:.95rem;font-weight:600;cursor:pointer">हिन्दी</button>
      <button type="button" class="am-lc" data-am-lang="en" style="padding:12px 8px;border-radius:12px;border:1.5px solid #cfa968;background:#fff8eb;color:#3b2310;font-size:.95rem;font-weight:600;cursor:pointer">English</button>
    </div>
  </div>
</div>
<script>
(function(){
  function pick(c){
    sessionStorage.setItem("am_lang_v08", c);
    var b = document.querySelector('#langSeg button[data-lang="' + c + '"]');
    if (b) b.click();
    var m = document.getElementById("amLangModal");
    if (m) m.style.display = "none";
  }
  function boot(){
    var m = document.getElementById("amLangModal");
    document.querySelectorAll(".am-lc").forEach(function(b){
      b.onclick = function(){ pick(b.getAttribute("data-am-lang") || "hg"); };
    });
    var s = sessionStorage.getItem("am_lang_v08");
    if (!s && m) m.style.display = "flex";
    else if (s) pick(s);
  }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", boot) : boot();
})();
</script>
</body>"""

idx_p.write_text(idx_txt.replace("</body>", modal, 1), encoding="utf-8")

# 5. Compile & package v0.8
ok = compileall.compile_dir(str(SRC), quiet=1)
(ROOT / "dist").mkdir(exist_ok=True)
zp = ROOT / "dist" / "astrobrain-v0.8.zip"
skip = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "knowledge_base"}
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(ROOT.rglob("*")):
        if f.is_file() and f.name != ".DS_Store" and not any(p in skip or p.endswith(".egg-info") for p in f.parts):
            zf.write(f, f"astrobrain-v0.8/{f.relative_to(ROOT)}")
print("v0.8.0 patched, compiled:", ok, "and zipped at:", zp)
