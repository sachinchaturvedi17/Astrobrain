"""v1.3.0: real-time 3D NaradVani (avatar3d.js) with the 2D portrait as fallback. Static checks, a node harness for the pure driver
logic and the live.js hand-over, and server checks for the GLB and CSP. stdlib only (node needed for the harness tests)."""
import json
import re
import shutil
import subprocess
import unittest
from datetime import datetime, timezone
from pathlib import Path

import aipandit
from aipandit.orchestrator import Pandit
from aipandit.web import server

ROOT = Path(__file__).resolve().parent.parent
ST = ROOT / "src" / "aipandit" / "web" / "static"
NODE = shutil.which("node")


def read(name):
    return (ST / name).read_text(encoding="utf-8")


def node_json(js, pre=""):
    r = subprocess.run([NODE, "-e", pre + js], capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


AVATAR = "const A=require(%s);" % json.dumps(str(ST / "avatar3d.js"))
# a tiny seeded random so the blink test is repeatable
RAND = "let s=12345;const rand=()=>{s=(s*1664525+1013904223)%4294967296;return s/4294967296};"


class WiringTests(unittest.TestCase):
    def test_page_loads_avatar3d_before_live(self):
        html = read("index.html")
        self.assertLess(html.index("/static/avatar3d.js"), html.index("/static/live.js"))
        self.assertEqual(set(re.findall(r"\?v=([0-9.]+)", html)), {aipandit.__version__})
        self.assertEqual(aipandit.__version__, "1.3.0")

    def test_avatar3d_is_csp_safe(self):
        src = read("avatar3d.js")
        self.assertIsNone(re.search(r"""\son(click|load|error|change)\s*=\s*["']""", src))
        self.assertNotRegex(src, r"\beval\s*\(|new Function|importScripts|document\.write|innerHTML")
        self.assertNotRegex(src, r"https?://")                                   # no network except our own static files
        self.assertIsNone(re.search(r"^\s*import\s", src, re.M))                 # classic script: only dynamic import()
        for spec in re.findall(r"import\(\s*VENDOR\s*\+\s*\"([^\"]+)\"", src):
            self.assertTrue(spec.endswith(".js"), spec)
        self.assertIn('VENDOR = "/static/vendor/"', src)                         # absolute path, no bare specifiers

    def test_live_keeps_2d_fallback(self):
        live = read("live.js")
        self.assertIn("L.three", live)
        self.assertIn("onFail", live)
        self.assertIn("canvas.style.display", live)
        self.assertIn("is3d", live)

    def test_css_and_gitignore(self):
        self.assertIn(".portrait canvas.nv3d", read("v11.css"))
        self.assertIn("naradvani_mp.glb", (ROOT / ".gitignore").read_text())      # private test avatar never committed
        self.assertIn("assets_src/private/", (ROOT / ".gitignore").read_text())

    def test_shipped_glb_is_a_glb_within_budget(self):
        g = ST / "vendor" / "naradvani.glb"
        data = g.read_bytes()
        self.assertEqual(data[:4], b"glTF")
        self.assertLessEqual(len(data), 8 * 1024 * 1024)


class ServerTests(unittest.TestCase):
    def test_glb_is_served_with_its_type(self):
        app = server.App(Pandit(now=lambda: datetime(2026, 11, 20, tzinfo=timezone.utc)))
        body, ctype = app.static("/static/vendor/naradvani.glb")
        self.assertEqual(ctype, "model/gltf-binary")
        self.assertEqual(body[:4], b"glTF")
        self.assertIsNotNone(app.static("/static/avatar3d.js"))
        self.assertIsNone(app.static("/static/vendor/../app.py"))
        self.assertIsNone(app.static("/static/vendor/sub/x.glb"))                # still no nested paths

    def test_csp_allows_wasm_for_meshopt_but_nothing_else_new(self):
        csp = server.CSP
        self.assertIn("script-src 'self' 'wasm-unsafe-eval'", csp)
        self.assertNotIn("'unsafe-inline'", csp)
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertIn("connect-src 'self' blob:;", csp)                          # GLTFLoader fetches GLB-embedded textures from blob: URLs
        self.assertNotRegex(csp, r"connect-src[^;]*(https?:|\*|data:)")              # still no remote or data: connections
        self.assertIn("frame-ancestors 'none'", csp)


@unittest.skipUnless(NODE, "node not installed")
class DriverTests(unittest.TestCase):
    def test_syntax(self):
        self.assertEqual(subprocess.run([NODE, "--check", str(ST / "avatar3d.js")]).returncode, 0)

    def test_visemes_latin_and_devanagari(self):
        out = node_json(AVATAR + "const v=(t,i)=>{const r=A.visemeFor(t,i);return r&&r.v};"
                        "console.log(JSON.stringify({a:v('a',0),m:v('m',0),b:v('b',0),f:v('f',0),r:v('r',0),sp:v(' ',0),q:v('?',0),eof:v('a',5),"
                        "sh0:v('sh',0),sh1:v('sh',1),th0:v('th',0),ph0:v('ph',0),ch1:v('ch',1),aa:v('आ',0),pa:v('प',0),ka:v('क',0),i:v('ि',0),virama:v('्',0)}))")
        self.assertEqual(out["a"], "aa")
        self.assertEqual((out["m"], out["b"], out["pa"]), ("PP", "PP", "PP"))      # lips closed on labials, Latin and Devanagari
        self.assertEqual(out["f"], "FF")
        self.assertEqual(out["r"], "RR")
        self.assertIsNone(out["sp"]); self.assertIsNone(out["q"]); self.assertIsNone(out["eof"]); self.assertIsNone(out["virama"])
        self.assertEqual((out["sh0"], out["sh1"]), ("CH", "CH"))                   # digraphs
        self.assertEqual(out["th0"], "TH"); self.assertEqual(out["ph0"], "FF"); self.assertEqual(out["ch1"], "CH")
        self.assertEqual(out["aa"], "aa"); self.assertEqual(out["ka"], "kk"); self.assertEqual(out["i"], "I")

    def test_targets_rest_when_paused(self):
        out = node_json(AVATAR + "console.log(JSON.stringify({p:A.targets('aaa',0,true),n:A.targets('aaa',0.5,false),sp:A.targets('   ',0,false)}))")
        self.assertEqual(out["p"], {})
        self.assertGreater(out["n"]["aa"], 0.7)
        self.assertEqual(out["sp"], {})

    def test_mouth_opens_on_vowels_and_closes_on_labials(self):
        js = (RAND + AVATAR + "function run(text){const d=A.createDriver(rand);let o;for(let i=0;i<30;i++)o=d.update(1/60,i/60,{speaking:true,text:text,pos:1,talk:true});return o.morph}"
              "const a=run('aaaa'),m=run('mmmm');console.log(JSON.stringify({aa:a.viseme_aa,aPP:a.viseme_PP,mPP:m.viseme_PP,maa:m.viseme_aa,sil:a.viseme_sil}))")
        out = node_json(js)
        self.assertGreater(out["aa"], 0.6); self.assertLess(out["aPP"], 0.05)
        self.assertGreater(out["mPP"], 0.6); self.assertLess(out["maa"], 0.05)
        self.assertEqual(out["sil"], 0)

    def test_mouth_never_overdriven_and_rests_when_idle(self):
        js = (RAND + AVATAR + "const d=A.createDriver(rand);let worst=0,idleMax=0;"
              "for(let i=0;i<600;i++){const o=d.update(1/60,i/60,{speaking:true,text:'ashoka. namaste! kaise ho?',pos:(i/60)*13,talk:true});"
              "let sum=0;A.VIS.forEach(n=>{sum+=o.morph['viseme_'+n];if(o.morph['viseme_'+n]>1)worst=2});worst=Math.max(worst,sum)}"
              "let o;for(let i=0;i<120;i++){o=d.update(1/60,10+i/60,{speaking:false,talk:true})}"
              "A.VIS.forEach(n=>{idleMax=Math.max(idleMax,o.morph['viseme_'+n])});console.log(JSON.stringify({worst:worst,idle:idleMax}))")
        out = node_json(js)
        self.assertLessEqual(out["worst"], 1.2001)
        self.assertLess(out["idle"], 0.02)

    def test_blinks_happen_at_natural_intervals(self):
        js = (RAND + AVATAR + "const d=A.createDriver(rand);let blinks=0,prev=0,peak=0,end;"
              "for(let i=0;i<60*30;i++){const o=d.update(1/60,i/60,{talk:false});const b=o.morph.eyeBlinkLeft;peak=Math.max(peak,b);if(prev<0.5&&b>=0.5)blinks++;prev=b;end=o.morph.eyeBlinkRight-b}"
              "console.log(JSON.stringify({blinks:blinks,peak:peak,sym:end}))")
        out = node_json(js)
        self.assertGreaterEqual(out["blinks"], 5)            # 30 s: gaps of 2.2-5.5 s plus some doubles
        self.assertLessEqual(out["blinks"], 20)
        self.assertGreater(out["peak"], 0.95)
        self.assertEqual(out["sym"], 0)

    def test_brows_lift_on_question_and_smile_is_light(self):
        js = (RAND + AVATAR + "const d=A.createDriver(rand);let o,q=0;"
              "for(let i=0;i<120;i++){o=d.update(1/60,i/60,{speaking:true,text:'ready? yes',pos:5,talk:true});q=Math.max(q,o.morph.browInnerUp)}"
              "const d2=A.createDriver(rand);let n;for(let i=0;i<300;i++){n=d2.update(1/60,i/60,{talk:false})}"
              "console.log(JSON.stringify({q:q,idle:n.morph.browInnerUp,smile:n.morph.mouthSmileLeft}))")
        out = node_json(js)
        self.assertGreater(out["q"], 0.6)
        self.assertLess(out["idle"], 0.25)
        self.assertGreater(out["smile"], 0.1); self.assertLess(out["smile"], 0.25)

    def test_head_and_eyes_stay_small_and_reduced_motion_is_calmer(self):
        js = (RAND + AVATAR + "function span(red){const d=A.createDriver(rand);let m=0,e=0;"
              "for(let i=0;i<60*40;i++){const o=d.update(1/60,i/60,{speaking:true,text:'namaste '.repeat(50),pos:i/60*13,talk:true,reduced:red});"
              "m=Math.max(m,Math.abs(o.head.x),Math.abs(o.head.y),Math.abs(o.head.z));e=Math.max(e,Math.abs(o.eyes.x),Math.abs(o.eyes.y))}return [m,e]}"
              "const a=span(false),b=span(true);console.log(JSON.stringify({head:a[0],eyes:a[1],headRed:b[0]}))")
        out = node_json(js)
        self.assertLess(out["head"], 0.08); self.assertLess(out["eyes"], 0.15)      # radians: a few degrees
        self.assertLess(out["headRed"], out["head"])

    def test_3d_is_off_without_webgl_and_mount_resolves_false(self):
        js = ("globalThis.location={search:''};" + AVATAR +
              "A.mount({isConnected:true},{}).then(ok=>console.log(JSON.stringify({sup:A.supported(),en:A.enabled(),ok:ok,rep:A.report().active})))")
        out = node_json(js)
        self.assertEqual(out, {"sup": False, "en": False, "ok": False, "rep": False})

    def test_avatar_2d_query_forces_fallback(self):
        out = node_json("globalThis.location={search:'?avatar=2d'};" + AVATAR + "console.log(JSON.stringify({en:A.enabled()}))")
        self.assertFalse(out["en"])


@unittest.skipUnless(NODE, "node not installed")
class HandOverTests(unittest.TestCase):
    PRE = ("global.document={createElement:()=>({getContext:()=>({drawImage(){}}),style:{}})};global.performance={now:()=>0};global.requestAnimationFrame=()=>0;"
           "global.Image=function(){};")

    def run_live(self, ams, check):
        js = (self.PRE + "global.window={AM3D:%s};require(%s);const A=window.AMLive;" % (ams, json.dumps(str(ST / "live.js"))) +
              "const cv={width:0,height:0,style:{display:''},isConnected:true,parentNode:{},getContext:()=>({drawImage(){}})};A.mount(cv,{mode:'chat'});" + check)
        return node_json(js)

    def test_stage_is_handed_to_3d_when_it_loads(self):
        out = self.run_live("{enabled:()=>true,mount:()=>Promise.resolve(true)}",
                            "setTimeout(()=>console.log(JSON.stringify({is3d:A.is3d(),display:cv.style.display})),10)")
        self.assertEqual(out, {"is3d": True, "display": "none"})

    def test_is3d_is_false_once_the_3d_view_has_unmounted(self):
        out = self.run_live("{enabled:()=>true,isActive:()=>global.on,mount:()=>{global.on=true;return Promise.resolve(true)}}",
                            "setTimeout(()=>{const a=A.is3d();global.on=false;console.log(JSON.stringify({mounted:a,afterUnmount:A.is3d()}))},10)")
        self.assertEqual(out, {"mounted": True, "afterUnmount": False})

    def test_portrait_stays_when_3d_cannot_load(self):
        out = self.run_live("{enabled:()=>true,mount:()=>Promise.resolve(false)}",
                            "setTimeout(()=>console.log(JSON.stringify({is3d:A.is3d(),display:cv.style.display})),10)")
        self.assertEqual(out, {"is3d": False, "display": ""})

    def test_portrait_comes_back_if_3d_fails_later(self):
        out = self.run_live("{enabled:()=>true,mount:(h,o)=>{global.fail=o.onFail;return Promise.resolve(true)}}",
                            "setTimeout(()=>{const before=cv.style.display;global.fail('too slow');console.log(JSON.stringify({before:before,is3d:A.is3d(),after:cv.style.display}))},10)")
        self.assertEqual(out, {"before": "none", "is3d": False, "after": ""})

    def test_works_with_no_3d_module_at_all(self):
        js = (self.PRE + "global.window={};require(%s);const A=window.AMLive;" % json.dumps(str(ST / "live.js")) +
              "const cv={width:0,height:0,style:{display:''},isConnected:true,parentNode:{},getContext:()=>({drawImage(){}})};A.mount(cv,{mode:'talk'});"
              "console.log(JSON.stringify({is3d:A.is3d(),api:['mount','setMode','speak','stop','listen','stopListening','micSupported'].every(k=>typeof A[k]==='function')}))")
        self.assertEqual(node_json(js), {"is3d": False, "api": True})


class VendorToolTests(unittest.TestCase):
    def load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("vendor_three", ROOT / "tools" / "vendor_three.py")
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def test_imports_are_rewritten_to_absolute_vendor_paths(self):
        m = self.load()
        src = ("import { Mesh } from 'three';\nimport {\n  toTrianglesDrawMode\n} from '../utils/BufferGeometryUtils.js';\n"
               "import * as T from \"three\";\n")
        out = m.rewrite(src)
        self.assertIn("from '/static/vendor/three.module.js'", out)
        self.assertIn("from '/static/vendor/BufferGeometryUtils.js'", out)
        self.assertEqual(m.leftovers(out), [])
        self.assertEqual(m.leftovers("import x from 'three';"), ["three"])           # a missed bare import is caught
        self.assertEqual(m.leftovers("import x from '../utils/a.js';"), ["../utils/a.js"])
        self.assertIn("from '/static/vendor/SkeletonUtils.js'", m.rewrite("import { clone } from '../utils/SkeletonUtils.js';"))
        doc = "/**\n * import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';\n */\nimport { A } from '/static/vendor/three.module.js';\n"
        self.assertEqual(m.leftovers(doc), [])                                          # examples inside doc comments are not imports

    def test_vendored_files_if_present_are_csp_safe(self):
        m = self.load()
        for name in ("GLTFLoader.js", "BufferGeometryUtils.js", "SkeletonUtils.js"):
            f = ST / "vendor" / name
            if f.exists():
                self.assertEqual(m.leftovers(f.read_text(encoding="utf-8")), [], name)


if __name__ == "__main__":
    unittest.main()
