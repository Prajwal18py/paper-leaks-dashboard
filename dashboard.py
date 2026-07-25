import sys
import json
import pandas as pd
from collections import Counter

IN_CSV = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/paper_leaks.csv"
OUT_HTML = sys.argv[2] if len(sys.argv) > 2 else "/mnt/user-data/outputs/Dashboard.html"

_script_dir = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
with open(_script_dir + "/india_paths.json") as _f:
    INDIA_MAP = json.load(_f)

# ---------------- LOAD ----------------
df = pd.read_csv(IN_CSV)
df["date"] = pd.to_datetime(df["date"])
df["year"] = df["date"].dt.year
N = len(df)

BODY_ALIASES = {
    "Central Board of Secondary Education (CBSE)": "CBSE",
    "Madhya Pradesh Professional Examination Board (Vyapam)": "Vyapam (MPPEB)",
}
df["conducting_body_norm"] = df["conducting_body"].replace(BODY_ALIASES)

STATE_LIST = ["Madhya Pradesh", "Uttar Pradesh", "Rajasthan", "Bihar", "Uttarakhand",
              "Maharashtra", "Haryana", "Jharkhand", "Gujarat", "Punjab", "Chhattisgarh",
              "Himachal Pradesh", "Delhi", "Karnataka", "Assam", "Telangana", "Odisha",
              "West Bengal", "Tamil Nadu", "Andhra Pradesh", "Jammu"]

def first_state(area):
    area = str(area)
    for s in STATE_LIST:
        if s in area:
            return s
    return "Multiple / Other"

df["state"] = df["area"].apply(first_state)
df["period"] = df["era"].apply(lambda e: "2004\u20132014" if "UPA" in str(e) else "2014\u20132026")

# ---------------- headline stats ----------------
total_arrests = int(df["arrests"].sum())
total_convictions = int(df["convictions"].sum())
total_aspirants = int(df["aspirants_affected"].sum())
confirmed_n = int(len(df[df.leak_status == "Confirmed"]))
confirmed_pct = round(100 * confirmed_n / N, 1)
states_affected = int(df[df.state != "Multiple / Other"]["state"].nunique())

upa_years, nda_years = 10.1, round((df["year"].max() - 2014) + 0.6, 1)
upa_count = int((df.period == "2004\u20132014").sum())
nda_count = int((df.period == "2014\u20132026").sum())
upa_rate = round(upa_count / upa_years, 1)
nda_rate = round(nda_count / nda_years, 1)
era_ratio = round(nda_count / max(upa_count, 1), 1)

# ---------------- map data: state -> incident count, aliased to GeoJSON names ----------------
GEOJSON_ALIAS = {"Uttarakhand": "Uttaranchal", "Odisha": "Orissa"}
map_state_counts = Counter()
for a in df["area"].fillna(""):
    for s in STATE_LIST:
        if s in a:
            geo_name = GEOJSON_ALIAS.get(s, s)
            map_state_counts[geo_name] += 1
MAP_COUNTS_JSON = json.dumps(map_state_counts)
map_max = max(map_state_counts.values()) if map_state_counts else 1

state_body_n = int((df.body_type == "State").sum())
central_body_n = int((df.body_type == "Central").sum())

n_with_arrests = int(df["arrests"].notna().sum())
n_with_convictions = int(df["convictions"].notna().sum())
mean_arrests = round(df["arrests"].mean(), 1)
avg_arrests_state = round(df[df.body_type == "State"]["arrests"].mean(), 1)
avg_arrests_central = round(df[df.body_type == "Central"]["arrests"].mean(), 1)

def decompose_action(a):
    a = str(a).lower()
    cats = []
    if "cancelled" in a: cats.append("Exam Cancelled")
    if "retest" in a: cats.append("Retest")
    if "arrest" in a: cats.append("Arrests/FIR")
    if "probe" in a: cats.append("Probe (CBI/SIT)")
    if not cats or a == "none reported":
        cats = ["No Action"]
    return cats

action_counter = Counter()
for a in df["action_taken"]:
    for cat in decompose_action(a):
        action_counter[cat] += 1
action_order = ["Arrests/FIR", "Probe (CBI/SIT)", "Exam Cancelled", "Retest", "No Action"]
action_vals = [action_counter.get(k, 0) for k in action_order]

# ---------------- exam category ----------------
def classify_exam(name):
    n = str(name).lower()
    if any(k in n for k in ["neet", "aipmt", "pmt", "aiims", "mbbs", "bds", "medical"]):
        return "Medical Entrance"
    if any(k in n for k in ["aieee", "jee", "engineering entrance"]):
        return "Engineering Entrance"
    if any(k in n for k in ["tet", "teacher eligibility", "prt", "slst", "contract teacher", "samvida shala"]):
        return "Teaching / TET"
    if any(k in n for k in ["class 10", "class 12", "board exam", "cbse class"]):
        return "School Board"
    if any(k in n for k in ["pcs", "ras (", "hcs", "administrative service", "civil service", "judicial"]):
        return "Civil Services"
    if any(k in n for k in ["ugc-net", "ugc net", "post-graduate", "pg entrance", " net "]):
        return "Postgraduate / UGC"
    if any(k in n for k in ["police", "constable", "sub-inspector", "inspector", "ssc", "rrb", "patwari",
                             "clerk", "junior engineer", "food inspector", "transport", "vpdo", "vdo",
                             "panchayat", "staff selection", "recruitment"]):
        return "Recruitment / Police"
    return "Other"

df["exam_category"] = df["exam_name"].apply(classify_exam)
exam_cat_counts = df["exam_category"].value_counts()

# ---------------- leak mechanism (mined from note) ----------------
def classify_mechanism(note):
    n = str(note).lower()
    if "whatsapp" in n:
        return "WhatsApp / Messaging"
    if "omr" in n or "answer key" in n or "answer-key" in n or "marks" in n or "inflated" in n:
        return "OMR / Marks Manipulation"
    if "impersonat" in n or "solver" in n or "proxy" in n:
        return "Impersonation / Solver"
    if "print" in n or "press" in n:
        return "Print / Press Leak"
    if "mobile" in n or "bluetooth" in n or "photograph" in n:
        return "In-Hall Device Leak"
    if "insider" in n or "employee" in n or "official" in n:
        return "Insider Leak"
    return "Unspecified"

df["mechanism"] = df["note"].apply(classify_mechanism)
mechanism_order = ["OMR / Marks Manipulation", "Impersonation / Solver", "Print / Press Leak",
                    "WhatsApp / Messaging", "In-Hall Device Leak", "Insider Leak", "Unspecified"]
mechanism_counts = df["mechanism"].value_counts()
mechanism_vals = [int(mechanism_counts.get(k, 0)) for k in mechanism_order]

# ---------------- biggest incidents by aspirants affected ----------------
big_incidents = df.dropna(subset=["aspirants_affected"]).nlargest(8, "aspirants_affected")
big_rows_html = ""
for _, r in big_incidents.iterrows():
    aff = int(r["aspirants_affected"])
    aff_str = f"{aff/1e6:.2f}M" if aff >= 1e6 else f"{aff:,}"
    big_rows_html += (f'<tr><td>{r["exam_name"][:48]}{"&hellip;" if len(str(r["exam_name"]))>48 else ""}</td>'
                       f'<td>{r["year"]}</td><td class="num-cell">{aff_str}</td></tr>\n')

# ---------------- sourcing / outlets ----------------
import re as _re
def normalize_source(s):
    return _re.sub(r"\s*\(.*?\)\s*$", "", str(s)).strip()

df["source_norm"] = df["source_name"].apply(normalize_source)
unique_sources = int(df["source_norm"].nunique())
top_sources = df["source_norm"].value_counts().head(8)
top_source_pct = round(100 * top_sources.iloc[0] / N, 0) if len(top_sources) else 0

top_bodies = df["conducting_body_norm"].value_counts().head(8)
body_rows_html = ""
for i, (name, cnt) in enumerate(top_bodies.items()):
    body_rows_html += f'<tr><td class="tag">#{i+1:02d}</td><td>{name}</td><td class="num-cell">{cnt}</td></tr>\n'

cancel_pre = df[(df.period == "2004\u20132014") & (df.action_taken.str.contains("cancel", case=False, na=False))].shape[0]
cancel_post = df[(df.period == "2014\u20132026") & (df.action_taken.str.contains("cancel", case=False, na=False))].shape[0]
cancel_pre_pct = round(100 * cancel_pre / upa_count, 0)
cancel_post_pct = round(100 * cancel_post / nda_count, 0)

year_counts = df["year"].value_counts().sort_values(ascending=False)
peak_years = [(int(y), int(c)) for y, c in year_counts.head(4).items()]
peak_years_str = ", ".join(str(y) for y, c in sorted(peak_years, key=lambda x: x[0]))
peak_counts_str = ", ".join(str(c) for y, c in sorted(peak_years, key=lambda x: x[0]))

missing_pct = {
    "arrests": round(100 * df["arrests"].isna().sum() / N, 0),
    "convictions": round(100 * df["convictions"].isna().sum() / N, 0),
    "aspirants_affected": round(100 * df["aspirants_affected"].isna().sum() / N, 0),
    "linked_deaths": round(100 * df["linked_deaths"].isna().sum() / N, 0),
}

# ---------------- records for the interactive widget ----------------
records = []
for _, r in df.iterrows():
    records.append({
        "year": int(r["year"]),
        "period": r["period"],
        "state": r["state"],
        "exam_category": r["exam_category"],
        "body_type": r["body_type"],
        "leak_status": r["leak_status"],
        "confidence": r["confidence"],
    })
RECORDS_JSON = json.dumps(records)

PERIODS = sorted(df["period"].unique().tolist())
BODY_TYPES = sorted(df["body_type"].unique().tolist())
STATUSES = sorted(df["leak_status"].unique().tolist())
CONFIDENCES = ["High", "Medium", "Low"]

def chips(values):
    return "".join(f'<button class="chip" data-val="{v}">{v}</button>' for v in values)

# build the <path> elements for the India map (fill set by JS after load, based on MAP_COUNTS)
map_paths_svg = ""
for name, d_attr in INDIA_MAP["paths"].items():
    cnt = map_state_counts.get(name, 0)
    map_paths_svg += f'<path class="state-path" data-state="{name}" data-count="{cnt}" d="{d_attr}"></path>\n'

top_map_states = sorted(map_state_counts.items(), key=lambda x: -x[1])[:3]
top_map_states_str = ", ".join(f"{n} ({c})" for n, c in top_map_states)

# ============================================================
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CASE FILE :: EXAM LEAKS {df['year'].min()}-{df['year'].max()}</title>
<link href="https://fonts.googleapis.com/css2?family=Special+Elite&family=IBM+Plex+Sans:wght@400;500;600;700&family=Courier+Prime:wght@400;700&family=Caveat:wght@500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
:root{{
  --paper:#EAE2C8; --paper-alt:#DFD5AF; --paper-dark:#D2C69A;
  --ink:#211D15; --ink-soft:#4A4437; --red:#A31621; --red-dark:#6E0E17;
  --redact:#131110; --old:#8a7f57; --line:#B8AC80;
}}
*{{box-sizing:border-box; margin:0; padding:0;}}
html{{scroll-behavior:smooth;}}
body{{
  background:var(--paper);
  background-image:
    radial-gradient(circle at 20% 10%, rgba(0,0,0,0.035), transparent 45%),
    radial-gradient(circle at 85% 40%, rgba(0,0,0,0.03), transparent 40%),
    radial-gradient(circle at 50% 90%, rgba(0,0,0,0.04), transparent 50%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
  color:var(--ink); font-family:'IBM Plex Sans',sans-serif; padding:0 0 90px;
  position:relative; overflow-x:hidden;
}}
.watermark{{
  position:fixed; inset:0; pointer-events:none; z-index:0;
  display:flex; flex-wrap:wrap; align-content:space-around; justify-content:space-around;
  transform:rotate(-28deg) scale(1.4); opacity:0.05;
}}
.watermark span{{ font-family:'Special Elite',monospace; font-size:13px; letter-spacing:.25em; color:var(--red-dark); white-space:nowrap; margin:26px 34px; }}
.wrap{{max-width:1150px; margin:0 auto; padding:0 22px; position:relative; z-index:1;}}
.torn-top{{
  height:26px; background:var(--red-dark);
  clip-path:polygon(0% 0%,100% 0%,100% 60%,97% 100%,94% 55%,91% 100%,88% 55%,85% 100%,82% 55%,79% 100%,76% 55%,73% 100%,70% 55%,67% 100%,64% 55%,61% 100%,58% 55%,55% 100%,52% 55%,49% 100%,46% 55%,43% 100%,40% 55%,37% 100%,34% 55%,31% 100%,28% 55%,25% 100%,22% 55%,19% 100%,16% 55%,13% 100%,10% 55%,7% 100%,4% 55%,1% 100%,0 55%);
}}
header{{
  background:var(--paper-alt); border-left:1px solid var(--line); border-right:1px solid var(--line);
  border-bottom:1px solid var(--line); padding:40px 40px 34px; position:relative;
  box-shadow:0 18px 40px -20px rgba(0,0,0,0.35);
  margin-bottom:46px;
}}
.case-no{{ font-family:'Courier Prime',monospace; font-size:13.5px; color:var(--ink-soft); letter-spacing:.08em; margin-bottom:14px; display:flex; gap:18px; flex-wrap:wrap; }}
.case-no b{{color:var(--red);}}
h1{{ font-family:'Special Elite',monospace; font-size:clamp(30px,5vw,54px); line-height:1.15; color:var(--ink); letter-spacing:-0.01em; }}
h1 .word{{position:relative; display:inline-block; overflow:hidden; margin-right:0.28em;}}
h1 .bar{{ position:absolute; inset:0; background:var(--redact); animation:lift 0.55s cubic-bezier(.7,0,.3,1) forwards; animation-delay:var(--d,0s); transform-origin:left; }}
@keyframes lift{{ to{{ transform:scaleX(0); }} }}
h1 .accent{{color:var(--red);}}
.stamp{{
  position:absolute; top:26px; right:34px; border:3px solid var(--red); color:var(--red);
  font-family:'Special Elite',monospace; font-size:15px; letter-spacing:.14em; padding:8px 14px;
  border-radius:4px; transform:rotate(9deg); opacity:0.88; mix-blend-mode:multiply;
}}
.stamp::after{{ content:''; position:absolute; inset:-4px; border:1px solid var(--red); border-radius:6px; opacity:.6; }}
.sub{{ color:var(--ink-soft); font-size:14.5px; max-width:640px; line-height:1.6; margin-top:16px; }}
.sub code{{font-family:'Courier Prime',monospace; background:var(--paper-dark); padding:1px 6px; border-radius:3px; color:var(--red-dark);}}

.stats{{ display:grid; grid-template-columns:repeat(5,1fr); gap:16px; margin:34px 0 40px; }}
.tag{{ background:var(--paper-alt); border:1px solid var(--line); padding:16px 14px 14px; position:relative; box-shadow:2px 4px 10px -4px rgba(0,0,0,0.25); }}
.tag::before{{ content:''; position:absolute; top:-6px; left:50%; transform:translateX(-50%); width:12px; height:12px; border-radius:50%; background:radial-gradient(circle at 35% 30%, #d6cfa0, var(--ink-soft) 70%); box-shadow:0 2px 3px rgba(0,0,0,0.4); }}
.tag .num{{font-family:'Courier Prime',monospace; font-weight:700; font-size:25px; color:var(--ink);}}
.tag .num.red{{color:var(--red);}}
.tag .lbl{{font-size:12px; color:var(--ink-soft); text-transform:uppercase; letter-spacing:.05em; margin-top:5px;}}

.exhibit{{margin-bottom:40px;}}
.ex-head{{display:flex; align-items:baseline; gap:12px; margin-bottom:14px; flex-wrap:wrap;}}
.ex-num{{ font-family:'Courier Prime',monospace; background:var(--ink); color:var(--paper); font-size:11px; padding:3px 9px; letter-spacing:.08em; }}
.ex-head h2{{font-family:'Special Elite',monospace; font-size:20px; color:var(--ink);}}
.ex-note{{font-family:'Courier Prime',monospace; font-size:13px; color:var(--ink-soft); margin-left:auto;}}
.plain-head{{margin-bottom:14px;}}
.plain-head h2{{font-family:'Special Elite',monospace; font-size:20px; color:var(--ink);}}

.card{{ background:var(--paper-alt); border:1px solid var(--line); padding:22px; box-shadow:0 10px 26px -18px rgba(0,0,0,0.4); position:relative; }}
.card::before{{ content:''; position:absolute; top:0; left:24px; width:46px; height:14px; background:linear-gradient(180deg, rgba(200,180,120,0.55), rgba(200,180,120,0.15)); border:1px solid rgba(0,0,0,0.08); transform:translateY(-7px) rotate(-2deg); }}
.grid2{{display:grid; grid-template-columns:1.4fr 1fr; gap:20px;}}
@media(max-width:760px){{ .grid2{{grid-template-columns:1fr;}} .stats{{grid-template-columns:repeat(2,1fr);}} header{{padding:32px 22px 28px;}} .stamp{{position:static; display:inline-block; margin-top:14px; transform:rotate(-2deg);}} }}
canvas{{max-height:320px;}}

.note{{ font-family:'Caveat',cursive; font-size:19px; color:var(--red-dark); line-height:1.4; margin-top:14px; padding-top:12px; border-top:1px dashed var(--line); transform:rotate(-0.3deg); }}
.note b{{font-weight:700;}}

table{{width:100%; border-collapse:collapse; font-family:'Courier Prime',monospace; font-size:13.5px;}}
th{{text-align:left; color:var(--ink-soft); font-weight:700; padding:9px 10px; border-bottom:2px solid var(--ink); text-transform:uppercase; font-size:11.5px; letter-spacing:.05em;}}
td{{padding:9px 10px; border-bottom:1px solid var(--line); color:var(--ink);}}
td.tag{{background:none; border:none; box-shadow:none; padding:9px 10px; color:var(--red); font-weight:700;}}
td.num-cell{{text-align:right; font-weight:700;}}
tr:last-child td{{border-bottom:none;}}

.controls-top{{display:flex; align-items:baseline; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:16px;}}
.controls-top h2{{font-family:'Special Elite',monospace; font-size:19px;}}
.hint{{font-family:'Courier Prime',monospace; font-size:13px; color:var(--ink-soft);}}

.groupby-row{{display:flex; gap:6px; margin:16px 0 18px; flex-wrap:wrap;}}
.gb-btn{{
  font-family:'Courier Prime',monospace; font-size:12.5px; letter-spacing:.04em;
  background:var(--paper); border:1px solid var(--line); color:var(--ink-soft);
  padding:7px 15px; cursor:pointer; border-radius:2px; text-transform:uppercase;
  transition:all .15s;
}}
.gb-btn.active{{background:var(--ink); color:var(--paper); border-color:var(--ink);}}
.gb-btn:hover:not(.active){{border-color:var(--ink);}}

.filter-block{{display:flex; flex-wrap:wrap; gap:24px; padding:14px 0; border-top:1px dashed var(--line); border-bottom:1px dashed var(--line); margin-bottom:14px;}}
.filter-group{{display:flex; flex-direction:column; gap:6px;}}
.filter-label{{font-family:'Courier Prime',monospace; font-size:11.5px; color:var(--ink-soft); text-transform:uppercase; letter-spacing:.08em;}}
.chip-row{{display:flex; gap:6px; flex-wrap:wrap;}}
.chip{{
  font-family:'Courier Prime',monospace; font-size:12.5px;
  background:var(--paper); border:1px solid var(--line); color:var(--ink);
  padding:5px 12px; border-radius:14px; cursor:pointer; transition:all .15s;
}}
.chip.active{{background:var(--red); color:var(--paper); border-color:var(--red-dark);}}
.chip:hover:not(.active){{border-color:var(--red);}}

.showing-row{{display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:10px;}}
.showing{{font-family:'Courier Prime',monospace; font-size:13.5px; color:var(--ink-soft);}}
.showing b{{color:var(--red); font-size:14px;}}
.view-toggle{{
  font-family:'Courier Prime',monospace; font-size:12.5px; text-transform:uppercase; letter-spacing:.05em;
  background:var(--paper); border:1px solid var(--ink); color:var(--ink); padding:7px 14px; cursor:pointer;
}}
.view-toggle:hover{{background:var(--ink); color:var(--paper);}}

.legend-row{{display:flex; gap:18px; font-family:'Courier Prime',monospace; font-size:13px; color:var(--ink-soft); margin-bottom:8px;}}
.legend-row span{{display:inline-flex; align-items:center; gap:6px;}}
.legend-dot{{width:10px; height:10px; display:inline-block; border-radius:2px;}}

#tableView{{display:none;}}
#tableView table th, #tableView table td{{text-align:right;}}
#tableView table th:first-child, #tableView table td:first-child{{text-align:left;}}
.bar-cell{{display:flex; align-items:center; justify-content:flex-end; gap:8px;}}
.bar-track{{flex:1; max-width:180px; height:9px; background:rgba(0,0,0,0.06); border-radius:2px; overflow:hidden;}}
.bar-fill{{height:100%; border-radius:2px;}}
.bar-fill.old{{background:var(--old);}}
.bar-fill.new{{background:var(--red);}}
.bar-num{{min-width:26px; text-align:right;}}
#dataTable tr.total-row td{{border-top:2px solid var(--ink); font-weight:700;}}

/* ratio banner */
.ratio-banner{{
  background:var(--ink); color:var(--paper);
  padding:18px 24px; margin:24px 0 36px;
  font-family:'Special Elite',monospace; font-size:17px; line-height:1.5;
  border-left:6px solid var(--red);
  box-shadow:0 10px 26px -18px rgba(0,0,0,0.5);
}}
.ratio-banner b{{color:var(--red); font-size:1.3em;}}

/* map */
.map-wrap{{display:flex; gap:24px; flex-wrap:wrap; align-items:flex-start;}}
.map-svg-box{{flex:1; min-width:280px; max-width:420px;}}
.map-svg-box svg{{width:100%; height:auto;}}
.state-path{{ stroke:var(--paper-alt); stroke-width:0.8; cursor:pointer; transition:opacity .15s; }}
.state-path:hover{{opacity:0.75; stroke:var(--ink); stroke-width:1.4;}}
.map-legend{{display:flex; align-items:center; gap:8px; margin-top:12px; font-family:'Courier Prime',monospace; font-size:12px; color:var(--ink-soft);}}
.map-legend-scale{{display:flex; height:10px; width:140px; border-radius:2px; overflow:hidden;}}
.map-side{{flex:1; min-width:220px;}}
.map-tooltip{{
  font-family:'Courier Prime',monospace; font-size:13.5px; color:var(--ink);
  background:var(--paper); border:1px solid var(--line); padding:12px 14px; border-radius:2px;
  min-height:52px; margin-bottom:14px;
}}
.map-tooltip b{{color:var(--red);}}

/* takeaways */
.takeaway-box{{
  background:var(--paper-alt); border:2px solid var(--ink); padding:26px 28px; position:relative; margin-top:6px;
}}
.takeaway-box::before{{
  content:'CASE SUMMARY'; position:absolute; top:-13px; left:24px; background:var(--red); color:var(--paper);
  font-family:'Courier Prime',monospace; font-size:11px; letter-spacing:.1em; padding:4px 12px;
}}
.takeaway-list{{list-style:none; margin-top:6px;}}
.takeaway-list li{{
  font-size:15px; line-height:1.7; padding:10px 0 10px 30px; position:relative; border-bottom:1px dashed var(--line);
}}
.takeaway-list li:last-child{{border-bottom:none;}}
.takeaway-list li::before{{
  content:'\\2022'; position:absolute; left:0; top:9px; color:var(--red); font-size:22px; line-height:1;
}}

/* methodology */
.method-box{{background:var(--paper); border:1px dashed var(--ink-soft); padding:20px 22px;}}
.method-box h3{{font-family:'Courier Prime',monospace; font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-soft); margin-bottom:12px;}}
.method-grid{{display:grid; grid-template-columns:1fr 1fr; gap:14px 28px;}}
.method-term{{font-size:14px; line-height:1.6;}}
.method-term b{{color:var(--red-dark); font-family:'Courier Prime',monospace;}}
@media(max-width:640px){{ .method-grid{{grid-template-columns:1fr;}} }}

footer{{ text-align:center; font-family:'Courier Prime',monospace; font-size:12.5px; color:var(--ink-soft); padding-top:24px; margin-top:10px; border-top:1px solid var(--line); }}
</style>
</head>
<body>

<div class="watermark">
  {"".join('<span>CLASSIFIED &middot; DECLASSIFIED FOR REVIEW &middot; </span>' for _ in range(40))}
</div>

<div class="wrap">
  <div class="torn-top"></div>
  <header>
    <div class="case-no">CASE NO. <b>{df['year'].max()}-EDU-{N}</b> &nbsp;|&nbsp; STATUS: <b>OPEN</b> &nbsp;|&nbsp; ROWS ANALYZED: <b>{N}</b> &nbsp;|&nbsp; RANGE: <b>{df['year'].min()}&ndash;{df['year'].max()}</b></div>
    <h1>
      <span class="word" style="--d:0.1s">India<span class="bar"></span></span>
      <span class="word" style="--d:0.22s">Exam<span class="bar"></span></span>
      <span class="word accent" style="--d:0.34s">Paper<span class="bar"></span></span>
      <span class="word accent" style="--d:0.46s">Leaks<span class="bar"></span></span>
      <br>
      <span class="word" style="--d:0.58s; font-size:0.5em; color:var(--ink-soft);">the&nbsp;full&nbsp;case&nbsp;file<span class="bar"></span></span>
    </h1>
    <div class="stamp">EXPOSED</div>
    <p class="sub">{N} documented incidents pulled from <code>paper_leaks.csv</code>, {df['year'].min()}&ndash;{df['year'].max()}, computed live with pandas. A structural read of the evidence &mdash; distributions, timeline, accountability gap &mdash; not a causal or political verdict.</p>
  </header>

  <div class="ratio-banner">
    &#9888; <b>{PERIODS[1]} has {era_ratio}&times; more incidents than {PERIODS[0]}</b> &mdash; {nda_count} cases vs {upa_count}, or ~{nda_rate}/yr vs ~{upa_rate}/yr. See the caveat box below before reading this as a pure trend.
  </div>

  <div class="exhibit">
    <div class="controls-top">
      <h2>{PERIODS[0]} vs {PERIODS[1]} &mdash; total incidents</h2>
      <span class="hint">Click a bar or a chip to slice the evidence.</span>
    </div>

    <div class="card">
      <div class="groupby-row" id="groupByRow">
        <button class="gb-btn active" data-gb="period">Period</button>
        <button class="gb-btn" data-gb="state">State</button>
        <button class="gb-btn" data-gb="body_type">Body</button>
        <button class="gb-btn" data-gb="exam_category">Exam Type</button>
        <button class="gb-btn" data-gb="year">Year</button>
        <button class="gb-btn" data-gb="leak_status">Status</button>
      </div>

      <div class="filter-block">
        <div class="filter-group">
          <span class="filter-label">Period</span>
          <div class="chip-row" data-filter="period">{chips(PERIODS)}</div>
        </div>
        <div class="filter-group">
          <span class="filter-label">Body Type</span>
          <div class="chip-row" data-filter="body_type">{chips(BODY_TYPES)}</div>
        </div>
        <div class="filter-group">
          <span class="filter-label">Leak Status</span>
          <div class="chip-row" data-filter="leak_status">{chips(STATUSES)}</div>
        </div>
        <div class="filter-group">
          <span class="filter-label">Confidence</span>
          <div class="chip-row" data-filter="confidence">{chips(CONFIDENCES)}</div>
        </div>
      </div>

      <div class="showing-row">
        <div class="showing">Showing <b id="showCount">{N}</b> of {N} incidents</div>
        <button class="view-toggle" id="viewToggle">Table view</button>
      </div>

      <div class="legend-row">
        <span><i class="legend-dot" style="background:var(--old)"></i> {PERIODS[0]}</span>
        <span><i class="legend-dot" style="background:var(--red)"></i> {PERIODS[1]}</span>
      </div>

      <div id="chartView"><canvas id="mainChart"></canvas></div>
      <div id="tableView">
        <table id="dataTable"><thead><tr><th id="groupColHead">Group</th><th>{PERIODS[0]}</th><th>{PERIODS[1]}</th><th>Total</th></tr></thead><tbody></tbody></table>
      </div>
    </div>
  </div>

  <div class="stats">
    <div class="tag"><div class="num red">{N}</div><div class="lbl">Incidents on file</div></div>
    <div class="tag"><div class="num">{upa_count}</div><div class="lbl">{PERIODS[0]}</div></div>
    <div class="tag"><div class="num red">{nda_count}</div><div class="lbl">{PERIODS[1]}</div></div>
    <div class="tag"><div class="num">~{upa_rate} / ~{nda_rate}</div><div class="lbl">Incidents per year</div></div>
    <div class="tag"><div class="num red">{state_body_n} / {central_body_n}</div><div class="lbl">State- vs central-body</div></div>
    <div class="tag"><div class="num">{confirmed_n}</div><div class="lbl">Coded "Confirmed"</div></div>
    <div class="tag"><div class="num red">{states_affected}</div><div class="lbl">States / UTs affected</div></div>
  </div>

  <div class="exhibit">
    <div class="plain-head"><h2>Patterns</h2></div>
    <div class="card">
      <div style="font-size:14px; line-height:1.85; color:var(--ink);">
        <p style="margin-bottom:12px;"><b>State recruitment exams are the epicentre.</b> ~{round(100*state_body_n/N)}% of all incidents are state-conducted (public service commissions, subordinate boards, state police) &mdash; {top_bodies.index[0] if len(top_bodies) else ''} recurs most, alongside repeat cases in UP, Rajasthan and Bihar. National exams (NEET, SSC, CBSE) get the headlines, but state-level exams are the bulk. Because most exams are run by state governments of many different parties, these counts shouldn't be read as a verdict on any single government.</p>
        <p style="margin-bottom:12px;"><b>Response has hardened over time.</b> Exams cancelled in response to a leak rose from ~{cancel_pre_pct:.0f}% of incidents in {PERIODS[0]} to ~{cancel_post_pct:.0f}% in {PERIODS[1]} &mdash; institutions increasingly choose to scrap the paper rather than risk a compromised result standing.</p>
        <p><b>Convictions are rare and slow.</b> The recurring pattern is arrests and CBI/SIT probes, with convictions &mdash; where they come at all &mdash; arriving years later. Only {n_with_convictions} of {n_with_arrests} incidents with reported arrests also report a conviction outcome.</p>
      </div>
    </div>
  </div>

  <div class="exhibit">
    <div class="plain-head"><h2>Peak years</h2></div>
    <div class="card">
      <p style="font-size:14px; line-height:1.8;">Incidents cluster hard in <b>{peak_years_str}</b> ({peak_counts_str} incidents respectively) &mdash; the window in which paper leaks became a front-line political and street-protest issue in India, driven by cases like NEET-UG, UKSSSC, RRB-NTPC and various state SSC exams.</p>
    </div>
  </div>

  <div class="exhibit">
    <div class="plain-head"><h2>&#9888; Big caveat &mdash; read before comparing periods</h2></div>
    <div class="card">
      <p style="font-size:14px; line-height:1.8; margin-bottom:12px;">The raw counts for the two periods are shaped by a real <b>reporting &amp; digitisation bias</b>, and several forces all push the same way &mdash; fewer early incidents <i>recorded</i>, not necessarily fewer occurring:</p>
      <ol style="font-size:14px; line-height:1.9; padding-left:20px; margin-bottom:12px;">
        <li><b>Digitisation &amp; the smartphone.</b> Pre-2012 news is sparsely archived online, and WhatsApp &mdash; which both causes modern leaks and documents them virally &mdash; barely existed in the earlier period.</li>
        <li><b>Missingness is heavy on outcome fields.</b> arrests {missing_pct['arrests']:.0f}% missing, convictions {missing_pct['convictions']:.0f}% missing, aspirants_affected {missing_pct['aspirants_affected']:.0f}% missing, linked_deaths {missing_pct['linked_deaths']:.0f}% missing. Treat these as "not reported," not zero.</li>
        <li><b>Unit inconsistency.</b> aspirants_affected mixes registered-candidate counts with retest-only counts across rows &mdash; sum with caution.</li>
      </ol>
      <p style="font-size:14px; line-height:1.8;">Read the patterns above as the trustworthy signal; weight rows by their <code style="background:var(--paper-dark); padding:1px 6px; border-radius:3px;">confidence</code> and <code style="background:var(--paper-dark); padding:1px 6px; border-radius:3px;">leak_status</code> fields when aggregating further. This is a record of <i>reported</i> incidents, not a complete census.</p>
    </div>
  </div>

  <div class="exhibit">
    <div class="plain-head"><h2>Methodology &amp; terms</h2></div>
    <div class="method-box">
      <h3>What the fields on this file mean</h3>
      <div class="method-grid">
        <div class="method-term"><b>Confirmed</b> &mdash; the leak was acknowledged by the conducting body, investigating agency, or court, or is backed by multiple independent reports.</div>
        <div class="method-term"><b>Alleged</b> &mdash; credibly reported by press or aspirants, but not yet acknowledged by an official body.</div>
        <div class="method-term"><b>Denied</b> &mdash; the conducting body has publicly denied a leak took place, despite reports.</div>
        <div class="method-term"><b>Suspected</b> &mdash; pattern (e.g. abnormal scores, viral content pre-exam) suggests a leak, without confirmation either way.</div>
        <div class="method-term"><b>Confidence</b> &mdash; how solid the sourcing is: High (multiple reputable outlets / official statement), Medium (single reputable source), Low (single or unverified source).</div>
        <div class="method-term"><b>Arrests vs. convictions</b> &mdash; an arrest means someone was detained in connection with the case; a conviction means a court found someone guilty. Most cases here show the former without the latter, often because the case is still pending, not because no one was guilty.</div>
      </div>
    </div>
  </div>

  <div class="exhibit">
    <div class="ex-head"><span class="ex-num">EXHIBIT 02</span><h2>Geography of the Leak</h2><span class="ex-note">shaded by total incidents, {df['year'].min()}&ndash;{df['year'].max()}</span></div>
    <div class="card">
      <div class="map-wrap">
        <div class="map-svg-box">
          <svg id="indiaMap" viewBox="0 0 {INDIA_MAP['width']} {INDIA_MAP['height']}" xmlns="http://www.w3.org/2000/svg">
            {map_paths_svg}
          </svg>
          <div class="map-legend">
            <span>0</span>
            <div class="map-legend-scale" style="background:linear-gradient(90deg, #DFD5AF, #A31621);"></div>
            <span>{map_max}+</span>
          </div>
        </div>
        <div class="map-side">
          <div class="map-tooltip" id="mapTooltip">Hover or tap a state to see its incident count.</div>
          <div class="note" style="margin-top:0; padding-top:0; border-top:none;">
            &uarr; Top states by mentions: <b>{top_map_states_str}</b>. Darker fill = more incidents. States with zero recorded incidents in this dataset are left unshaded &mdash; that means no case in <code style="background:var(--paper-dark); padding:1px 6px; border-radius:3px;">paper_leaks.csv</code> mentions them, not that none occurred.
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="exhibit">
    <div class="ex-head"><span class="ex-num">EXHIBIT 03</span><h2>The Accountability Gap</h2><span class="ex-note">arrests in {n_with_arrests} rows, convictions in only {n_with_convictions}</span></div>
    <div class="card">
      <canvas id="accountChart"></canvas>
      <div class="note">&uarr; <b>{total_arrests:,} arrests</b> across {n_with_arrests} cases (mean ~{mean_arrests}/case) vs just <b>{total_convictions} convictions</b> across {n_with_convictions}. State bodies average <b>~{avg_arrests_state}</b> arrests/case vs <b>~{avg_arrests_central}</b> for central bodies.</div>
    </div>
  </div>

  <div class="exhibit">
    <div class="ex-head"><span class="ex-num">EXHIBIT 04</span><h2>Institutional Response</h2><span class="ex-note">action_taken, decomposed</span></div>
    <div class="card">
      <canvas id="actionChart"></canvas>
      <div class="note">&uarr; Cancelling the exam outright ({action_counter.get('Exam Cancelled',0)}) is nearly as common as ordering a retest ({action_counter.get('Retest',0)}).</div>
    </div>
  </div>

  <div class="exhibit">
    <div class="ex-head"><span class="ex-num">EXHIBIT 05</span><h2>How the Paper Actually Got Out</h2><span class="ex-note">mechanism, mined from the case notes</span></div>
    <div class="card">
      <canvas id="mechanismChart"></canvas>
      <div class="note">&uarr; <b>{mechanism_counts.get('OMR / Marks Manipulation',0)}</b> cases are marks/OMR rigging rather than a classic pre-exam leak &mdash; worth separating from the "paper leak" label. Mechanism is inferred from free-text case notes with simple keyword matching, so treat it as directional, not exact.</div>
    </div>
  </div>

  <div class="exhibit">
    <div class="ex-head"><span class="ex-num">EXHIBIT 06</span><h2>Repeat Offenders</h2><span class="ex-note">conducting bodies, name-normalized</span></div>
    <div class="card">
      <table>
        <tr><th>Rank</th><th>Conducting body</th><th style="text-align:right">Cases</th></tr>
        {body_rows_html}
      </table>
      <div class="note">&uarr; "CBSE" and Vyapam's two name forms were merged before ranking &mdash; raw strings undercount repeats.</div>
    </div>
  </div>

  <div class="exhibit">
    <div class="ex-head"><span class="ex-num">EXHIBIT 07</span><h2>Biggest Incidents</h2><span class="ex-note">ranked by aspirants affected</span></div>
    <div class="card">
      <table>
        <tr><th>Exam</th><th>Year</th><th style="text-align:right">Aspirants affected</th></tr>
        {big_rows_html}
      </table>
      <div class="note">&uarr; Units aren't always apples-to-apples &mdash; some rows count all registered candidates, others only those who sat a retest. Read this as "scale of disruption," not a precise headcount.</div>
    </div>
  </div>

  <div class="exhibit">
    <div class="ex-head"><span class="ex-num">EXHIBIT 08</span><h2>Sourcing</h2><span class="ex-note">{unique_sources} unique outlets across {N} rows</span></div>
    <div class="card">
      <canvas id="sourceChart"></canvas>
      <div class="note">&uarr; No single outlet dominates the record &mdash; the top source accounts for only <b>~{top_source_pct:.0f}%</b> of rows. Outlet name variants (e.g. "The Tribune" vs "The Tribune (PTI)") were merged before counting.</div>
    </div>
  </div>

  <div class="exhibit">
    <div class="plain-head"><h2>Bottom line</h2></div>
    <div class="takeaway-box">
      <ul class="takeaway-list">
        <li><b>Incidents are up {era_ratio}&times;</b> since 2014, largely concentrated in state-run recruitment exams in {top_map_states[0][0] if top_map_states else 'a handful of states'} and its neighbors &mdash; but treat the rise with caution: better digital reporting and RTI coverage in the later period inflate the raw comparison.</li>
        <li><b>Punishment lags detection badly.</b> {total_arrests:,} people have been arrested across {n_with_arrests} cases, but only {total_convictions} convictions are on record &mdash; roughly 1 in {round(n_with_arrests/max(n_with_convictions,1))} arrest-cases shows a completed conviction in this dataset.</li>
        <li><b>Institutions increasingly cancel rather than retest</b> &mdash; {action_counter.get('Exam Cancelled',0)} exams were scrapped outright vs {action_counter.get('Retest',0)} retests, suggesting a preference for a clean restart over patching a compromised paper.</li>
      </ul>
    </div>
  </div>

  <footer>{N} incidents &middot; each individually sourced &middot; {df['year'].min()}&ndash;{df['year'].max()}</footer>
</div>

<script>
const RECORDS = {RECORDS_JSON};
const MAP_COUNTS = {MAP_COUNTS_JSON};
const MAP_MAX = {map_max};

function shadeForCount(c) {{
  if (c === 0) return '#DFD5AF';
  const t = Math.min(1, c / MAP_MAX);
  // interpolate paper-alt (#DFD5AF) -> red (#A31621)
  const c1 = [223,213,175], c2 = [163,22,33];
  const rgb = c1.map((v,i) => Math.round(v + (c2[i]-v)*t));
  return `rgb(${{rgb[0]}},${{rgb[1]}},${{rgb[2]}})`;
}}

document.querySelectorAll('.state-path').forEach(path => {{
  const cnt = parseInt(path.dataset.count, 10) || 0;
  path.style.fill = shadeForCount(cnt);
  path.addEventListener('mouseenter', () => {{
    const name = path.dataset.state;
    document.getElementById('mapTooltip').innerHTML = `<b>${{name}}</b> &mdash; ${{cnt}} incident${{cnt === 1 ? '' : 's'}} on file`;
  }});
  path.addEventListener('click', () => {{
    const name = path.dataset.state;
    document.getElementById('mapTooltip').innerHTML = `<b>${{name}}</b> &mdash; ${{cnt}} incident${{cnt === 1 ? '' : 's'}} on file`;
  }});
}});
const PERIODS = {json.dumps(PERIODS)};
const OLD_COLOR = '#8a7f57', NEW_COLOR = '#A31621', INK='#211D15';

let state = {{
  groupBy: 'period',
  filters: {{ period:new Set(), body_type:new Set(), leak_status:new Set(), confidence:new Set() }}
}};
let mainChart = null;
let tableMode = false;

function applyFilters(records) {{
  return records.filter(r => {{
    for (const key of Object.keys(state.filters)) {{
      const set = state.filters[key];
      if (set.size > 0 && !set.has(r[key])) return false;
    }}
    return true;
  }});
}}

function groupData(records, groupBy) {{
  const groups = {{}};
  records.forEach(r => {{
    const g = String(r[groupBy]);
    if (!groups[g]) groups[g] = {{}};
    groups[g][r.period] = (groups[g][r.period] || 0) + 1;
  }});
  let labels = Object.keys(groups);
  if (groupBy === 'year') {{
    labels.sort((a,b) => a-b);
  }} else {{
    labels.sort((a,b) => {{
      const ta = Object.values(groups[a]).reduce((x,y)=>x+y,0);
      const tb = Object.values(groups[b]).reduce((x,y)=>x+y,0);
      return tb - ta;
    }});
  }}
  const oldData = labels.map(l => groups[l][PERIODS[0]] || 0);
  const newData = labels.map(l => groups[l][PERIODS[1]] || 0);
  return {{ labels, oldData, newData }};
}}

function render() {{
  const filtered = applyFilters(RECORDS);
  document.getElementById('showCount').textContent = filtered.length;
  const {{ labels, oldData, newData }} = groupData(filtered, state.groupBy);

  if (tableMode) {{
    renderTable(labels, oldData, newData);
  }} else {{
    renderChart(labels, oldData, newData);
  }}
}}

function renderChart(labels, oldData, newData) {{
  const ctx = document.getElementById('mainChart');
  const horizontal = state.groupBy === 'state';
  if (mainChart) mainChart.destroy();
  mainChart = new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels,
      datasets: [
        {{ label: PERIODS[0], data: oldData, backgroundColor: OLD_COLOR, stack:'s' }},
        {{ label: PERIODS[1], data: newData, backgroundColor: NEW_COLOR, stack:'s' }}
      ]
    }},
    options: {{
      responsive:true,
      indexAxis: horizontal ? 'y' : 'x',
      plugins: {{ legend:{{display:false}} }},
      scales: {{
        x: {{ stacked:true, grid:{{color:'#B8AC80'}}, ticks:{{color:'#4A4437', font:{{family:"'Courier Prime',monospace", size:11}} }} }},
        y: {{ stacked:true, grid:{{color:'#B8AC80'}}, ticks:{{color:'#4A4437', font:{{family:"'Courier Prime',monospace", size:11}} }}, beginAtZero:true }}
      }}
    }}
  }});
}}

const GB_LABELS = {{ period:'Period', state:'State', body_type:'Body', exam_category:'Exam Type', year:'Year', leak_status:'Status' }};

function barCell(val, maxVal, cls) {{
  const pct = maxVal > 0 ? Math.max(2, Math.round(100 * val / maxVal)) : 0;
  if (val === 0) return `<div class="bar-cell"><span class="bar-num">0</span></div>`;
  return `<div class="bar-cell"><div class="bar-track"><div class="bar-fill ${{cls}}" style="width:${{pct}}%"></div></div><span class="bar-num">${{val}}</span></div>`;
}}

function renderTable(labels, oldData, newData) {{
  document.getElementById('groupColHead').textContent = GB_LABELS[state.groupBy] || 'Group';
  const tbody = document.querySelector('#dataTable tbody');
  tbody.innerHTML = '';
  const maxVal = Math.max(1, ...oldData, ...newData);
  let sumOld = 0, sumNew = 0;
  labels.forEach((l,i) => {{
    const total = oldData[i] + newData[i];
    sumOld += oldData[i]; sumNew += newData[i];
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${{l}}</td><td>${{barCell(oldData[i], maxVal, 'old')}}</td><td>${{barCell(newData[i], maxVal, 'new')}}</td><td><b>${{total}}</b></td>`;
    tbody.appendChild(tr);
  }});
  const totalRow = document.createElement('tr');
  totalRow.className = 'total-row';
  totalRow.innerHTML = `<td><b>Total</b></td><td>${{sumOld}}</td><td>${{sumNew}}</td><td><b>${{sumOld + sumNew}}</b></td>`;
  tbody.appendChild(totalRow);
}}

document.getElementById('groupByRow').addEventListener('click', e => {{
  const btn = e.target.closest('.gb-btn');
  if (!btn) return;
  document.querySelectorAll('.gb-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  state.groupBy = btn.dataset.gb;
  render();
}});

document.querySelectorAll('.chip-row').forEach(row => {{
  const key = row.dataset.filter;
  row.addEventListener('click', e => {{
    const chip = e.target.closest('.chip');
    if (!chip) return;
    const val = chip.dataset.val;
    chip.classList.toggle('active');
    if (state.filters[key].has(val)) state.filters[key].delete(val);
    else state.filters[key].add(val);
    render();
  }});
}});

document.getElementById('viewToggle').addEventListener('click', () => {{
  tableMode = !tableMode;
  document.getElementById('chartView').style.display = tableMode ? 'none' : 'block';
  document.getElementById('tableView').style.display = tableMode ? 'block' : 'none';
  document.getElementById('viewToggle').textContent = tableMode ? 'Chart view' : 'Table view';
  render();
}});

render();

Chart.defaults.font.family = "'Courier Prime', monospace";
Chart.defaults.font.size = 11;
Chart.defaults.color = '#4A4437';

new Chart(document.getElementById('accountChart'), {{
  type:'bar',
  data:{{ labels:['Arrests (n={n_with_arrests} rows)','Convictions (n={n_with_convictions} rows)'], datasets:[{{ data:[{total_arrests},{total_convictions}], backgroundColor:['#A31621','#211D15'], borderRadius:3, barThickness:56 }}] }},
  options: {{ responsive:true, indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:{{ x:{{grid:{{color:'#B8AC80'}}, beginAtZero:true}}, y:{{grid:{{color:'#B8AC80'}}}} }} }}
}});

new Chart(document.getElementById('actionChart'), {{
  type:'bar',
  data:{{ labels:{json.dumps(action_order)}, datasets:[{{ data:{json.dumps(action_vals)}, backgroundColor:'#211D15', borderRadius:2 }}] }},
  options: {{ responsive:true, plugins:{{legend:{{display:false}}}}, scales:{{ x:{{grid:{{color:'#B8AC80'}}}}, y:{{grid:{{color:'#B8AC80'}}, beginAtZero:true}} }} }}
}});

new Chart(document.getElementById('mechanismChart'), {{
  type:'bar',
  data:{{ labels:{json.dumps(mechanism_order)}, datasets:[{{ data:{json.dumps(mechanism_vals)}, backgroundColor:'#A31621', borderRadius:2 }}] }},
  options: {{ responsive:true, indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:{{ x:{{grid:{{color:'#B8AC80'}}, beginAtZero:true}}, y:{{grid:{{color:'#B8AC80'}}}} }} }}
}});

new Chart(document.getElementById('sourceChart'), {{
  type:'bar',
  data:{{ labels:{json.dumps(top_sources.index.tolist())}, datasets:[{{ data:{json.dumps([int(v) for v in top_sources.values])}, backgroundColor:'#211D15', borderRadius:2 }}] }},
  options: {{ responsive:true, indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:{{ x:{{grid:{{color:'#B8AC80'}}, beginAtZero:true}}, y:{{grid:{{color:'#B8AC80'}}}} }} }}
}});
</script>
</body>
</html>
"""

with open(OUT_HTML, "w") as f:
    f.write(html)

print(f"Wrote {OUT_HTML} ({len(html)} bytes)")