"""Compile UI upgrades (startup language popup + optional palm note) and build Astrobrain v0.8."""
from __future__ import annotations

import compileall
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_PKG = ROOT / "src" / "aipandit"
DIST_DIR = ROOT / "dist"

UI_INJECTION = """
<!-- AstroMuni v0.8 Startup Language Modal & Optional Palm Guidance -->
<div id="amLangModal" class="am-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="amLangTitle">
  <div class="am-modal-card">
    <div class="am-modal-badge">AstroMuni • Vedic Guidance</div>
    <h2 id="amLangTitle">अपनी भाषा चुनें / Choose Language</h2>
    <p class="am-modal-sub">Select your preferred language to begin</p>
    <div class="am-lang-grid">
      <button type="button" class="am-lang-choice" data-am-lang="hg">Hinglish</button>
      <button type="button" class="am-lang-choice" data-am-lang="hi">हिन्दी</button>
      <button type="button" class="am-lang-choice" data-am-lang="en">English</button>
    </div>
  </div>
</div>

<style>
  .am-modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(34, 22, 12, 0.58);
    backdrop-filter: blur(4px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 99999;
    padding: 16px;
  }
  .am-modal-backdrop.is-open {
    display: flex;
  }
  .am-modal-card {
    background: #fffdf8;
    border: 1px solid #e2cfa8;
    border-radius: 18px;
    max-width: 420px;
    width: 100%;
    padding: 26px 22px;
    text-align: center;
    box-shadow: 0 20px 48px rgba(34, 22, 12, 0.24);
    color: #3b2310;
  }
  .am-modal-badge {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: #8a5a19;
    background: #f8eed8;
    border: 1px solid #e6cfa0;
    border-radius: 999px;
    padding: 4px 12px;
    margin-bottom: 12px;
  }
  .am-modal-card h2 {
    margin: 0 0 6px;
    font-size: 1.25rem;
    font-weight: 700;
    color: #3b2310;
  }
  .am-modal-sub {
    margin: 0 0 20px;
    font-size: 0.92rem;
    color: #6e5239;
  }
  .am-lang-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
  }
  .am-lang-choice {
    padding: 12px 8px;
    border-radius: 12px;
    border: 1.5px solid #cfa968;
    background: #fff8eb;
    color: #3b2310;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.16s ease;
  }
  .am-lang-choice:hover {
    background: #4a2c14;
    border-color: #4a2c14;
    color: #fffdf8;
  }
  .am-palm-note {
    margin: 12px 0 6px;
    padding: 10px 12px;
    border-radius: 10px;
    background: #fbf5e8;
    border: 1px solid #e7d5b3;
    color: #5a3c22;
    font-size: 0.84rem;
    line-height: 1.45;
    text-align: left;
  }
</style>

<script>
  (function () {
    const PALM_NOTE_COPY = {
      en: "Optional — you can skip uploading palm photos, though adding clear images of both palms helps us give a more accurate, personalised reading.",
      hg: "Optional — aap palm photos skip kar sakte hain, lekin dono haathon ki saaf photos upload karne se zyada accurate aur personalised jawab milta hai.",
      hi: "वैकल्पिक — आप हथेली की फ़ोटो छोड़ भी सकते हैं, लेकिन दोनों हाथों की स्पष्ट फ़ोटो अपलोड करने से अधिक सटीक और व्यक्तिगत उत्तर मिल पाता है।"
    };

    const LABEL_TO_CODE = {
      "hinglish": "hg",
      "हिन्दी": "hi",
      "hindi": "hi",
      "english": "en"
    };

    function detectActiveLang() {
      const saved = sessionStorage.getItem("am_lang_picked") || localStorage.getItem("astromuni_lang");
      if (saved && PALM_NOTE_COPY[saved]) return saved;
      const activeBtn = Array.from(document.querySelectorAll("button, [role='button']")).find((el) => {
        const txt = (el.textContent || "").trim().toLowerCase();
        return LABEL_TO_CODE[txt] && (el.classList.contains("active") || el.getAttribute("aria-pressed") === "true");
      });
      if (activeBtn) {
        return LABEL_TO_CODE[(activeBtn.textContent || "").trim().toLowerCase()] || "hg";
      }
      return "hg";
    }

    function syncPalmNote(lang) {
      const code = PALM_NOTE_COPY[lang] ? lang : detectActiveLang();
      document.querySelectorAll("input[type='file']").forEach((inp) => {
        inp.removeAttribute("required");
        inp.required = false;
      });

      const fileInputs = Array.from(document.querySelectorAll("input[type='file']"));
      if (!fileInputs.length) return;

      // Find the common container wrapping the left & right palm cards
      let container = fileInputs[0].parentElement;
      while (container && container.parentElement && container.querySelectorAll("input[type='file']").length < 2) {
        if (container.tagName === "FORM" || container.tagName === "BODY") break;
        container = container.parentElement;
      }
      if (!container) return;

      let note = document.getElementById("amPalmOptionalNote");
      if (!note) {
        note = document.createElement("div");
        note.id = "amPalmOptionalNote";
        note.className = "am-palm-note";
        container.insertAdjacentElement("afterend", note);
      }
      note.textContent = PALM_NOTE_COPY[code];
    }

    function selectAppLanguage(code) {
      const lang = PALM_NOTE_COPY[code] ? code : "hg";
      sessionStorage.setItem("am_lang_picked", lang);
      localStorage.setItem("astromuni_lang", lang);

      // Click the matching header language toggle button so the whole UI updates
      const targetLabels = lang === "hi" ? ["हिन्दी", "hindi"] : lang === "en" ? ["english"] : ["hinglish"];
      const headerBtns = Array.from(document.querySelectorAll("button, [role='button']"));
      for (const btn of headerBtns) {
        if (btn.closest("#amLangModal")) continue;
        const txt = (btn.textContent || "").trim().toLowerCase();
        if (targetLabels.includes(txt)) {
          btn.click();
          break;
        }
      }

      syncPalmNote(lang);
      const modal = document.getElementById("amLangModal");
      if (modal) modal.classList.remove("is-open");
    }

    function initAstroMuniV08() {
      const modal = document.getElementById("amLangModal");
      document.querySelectorAll(".am-lang-choice").forEach((btn) => {
        btn.addEventListener("click", () => selectAppLanguage(btn.getAttribute("data-am-lang")));
      });

      // Keep note synced if user clicks header language toggle later
      document.addEventListener("click", (ev) => {
        const btn = ev.target.closest("button, [role='button']");
        if (!btn || btn.closest("#amLangModal")) return;
        const txt = (btn.textContent || "").trim().toLowerCase();
        if (LABEL_TO_CODE[txt]) {
          const code = LABEL_TO_CODE[txt];
          sessionStorage.setItem("am_lang_picked", code);
          localStorage.setItem("astromuni_lang", code);
          setTimeout(() => syncPalmNote(code), 40);
        }
      });

      const pickedThisSession = sessionStorage.getItem("am_lang_picked");
      if (!pickedThisSession && modal) {
        modal.classList.add("is-open");
      } else if (pickedThisSession) {
        selectAppLanguage(pickedThisSession);
      }

      syncPalmNote(detectActiveLang());
      const observer = new MutationObserver(() => syncPalmNote(detectActiveLang()));
      observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initAstroMuniV08);
    } else {
      initAstroMuniV08();
    }
  })();
</script>
"""


def inject_ui() -> int:
    patched_files = 0
    candidates = list(SRC_PKG.rglob("*.html")) + [SRC_PKG / "web.py"]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "amLangModal" in text:
            # Replace existing v0.8 block cleanly on re-runs
            text = re.sub(
                r"\n<!-- AstroMuni v0\.8 Startup Language Modal & Optional Palm Guidance -->.*?</script>\n",
                "\n",
                text,
                flags=re.DOTALL,
            )
        if "</body>" in text:
            text = text.replace("</body>", UI_INJECTION + "\n</body>", 1)
            path.write_text(text, encoding="utf-8")
            patched_files += 1
            print(f"[OK] Patched UI in {path.relative_to(ROOT)}")
    return patched_files


def bump_versions() -> None:
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        pt = pyproject.read_text(encoding="utf-8")
        pt_new = re.sub(r'version\s*=\s*"[^"]+"', 'version = "0.8.0"', pt, count=1)
        pyproject.write_text(pt_new, encoding="utf-8")
        print("[OK] Updated pyproject.toml to version 0.8.0")

    for py_file in SRC_PKG.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        if "0.7-astrobrain" in content:
            py_file.write_text(content.replace("0.7-astrobrain", "0.8-astrobrain"), encoding="utf-8")
            print(f"[OK] Updated version tag in {py_file.relative_to(ROOT)}")


def package_release() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DIST_DIR / "astrobrain-v0.8.zip"
    skip_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "knowledge_base"}
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(ROOT.rglob("*")):
            if any(part in skip_dirs or part.endswith(".egg-info") for part in item.parts):
                continue
            if item.is_file() and item.name != ".DS_Store":
                zf.write(item, arcname=f"astrobrain-v0.8/{item.relative_to(ROOT)}")
    print(f"[OK] Built release archive: {zip_path.relative_to(ROOT)}")
    return zip_path


if __name__ == "__main__":
    count = inject_ui()
    if count == 0:
        print("[Warning] No inline </body> found in web.py or *.html; check template path.")
    bump_versions()
    ok = compileall.compile_dir(str(SRC_PKG), quiet=1)
    print(f"[OK] Python bytecode compile check passed: {ok}")
    package_release()
