import os
import io
import uuid
from typing import Dict, List, Optional

import pandas as pd
from flask import Flask, request, abort, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# -------------------------
# General config
# -------------------------
ALLOWED_EXTS = {"csv", "json"}
MAX_ROWS_IN_MEMORY = 2_000_000  # safety cap

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FOLDER = os.path.join(BASE_DIR, "datasets")
EXCEL_FILES = ["patients", "services_weekly", "staff", "staff_schedule"]  # base names (without .xlsx)

# Candidate column names (case-insensitive)
PATIENT_ID_COLS = ["patient_id", "id", "patientid"]
STAFF_ID_COLS = ["staff_id", "employee_id", "emp_id", "id"]
NAME_COLS = ["name", "full_name", "patient_name", "staff_name"]
SERVICE_COLS = ["service", "department", "dept", "specialty"]
AGE_COLS = ["age", "patient_age"]
SAT_COLS = ["satisfaction", "rating", "score"]
ROLE_COLS = ["role", "title", "position"]
WEEK_COLS = ["week", "week_code", "weekid"]
PRESENT_COLS = ["present", "is_present", "attendance"]

# -------------------------
# App
# -------------------------
app = Flask(__name__)
CORS(app)

# -------------------------
# Helpers
# -------------------------
def find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cand = {c.lower() for c in candidates}
    for c in df.columns:
        if c.lower() in cand:
            return c
    return None

def to_bool(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    v = str(val).strip().lower()
    if v in {"1", "true", "yes", "y"}:
        return True
    if v in {"0", "false", "no", "n"}:
        return False
    return None

def read_excel_one(path: str, sheet: Optional[str] = None) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet)
    # If multiple sheets returned, pick the first sheet
    if isinstance(df, dict):
        df = df[next(iter(df.keys()))]
    return df

# Cache all four Excel files in memory (lazy load)
EXCEL_CACHE: Dict[str, Optional[pd.DataFrame]] = {name: None for name in EXCEL_FILES}

def load_excel_cache(force: bool = False) -> Dict[str, Optional[pd.DataFrame]]:
    os.makedirs(EXCEL_FOLDER, exist_ok=True)
    for name in EXCEL_FILES:
        if force or (EXCEL_CACHE[name] is None):
            path = os.path.join(EXCEL_FOLDER, f"{name}.xlsx")
            if os.path.exists(path):
                try:
                    EXCEL_CACHE[name] = read_excel_one(path)
                except Exception as e:
                    EXCEL_CACHE[name] = None
            else:
                EXCEL_CACHE[name] = None
    return EXCEL_CACHE

# -------------------------
# Basic health/home
# -------------------------
@app.get("/")
def home():
    return jsonify({
        "message": "Welcome! Your Flask API is alive.",
        "try_these": [
            "/health",
            "/excel/files",
            "/excel/patients?limit=5",
            "/patients?limit=5",
            "/staff?limit=5",
            "/staff_schedule?limit=5",
            "/services_weekly?limit=5"
        ]
    })

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

@app.get("/hello")
def hello():
    return "Hello from Flask!", 200

# -------------------------
# Excel endpoints (READ-ONLY)
# -------------------------
@app.get("/excel/files")
def excel_files():
    out = []
    for name in EXCEL_FILES:
        path = os.path.join(EXCEL_FOLDER, f"{name}.xlsx")
        out.append({"name": name, "filename": f"{name}.xlsx", "exists": os.path.exists(path)})
    return jsonify(out)

@app.get("/excel/reload")
def excel_reload():
    load_excel_cache(force=True)
    # report what actually loaded
    report = {k: (v is not None) for k, v in EXCEL_CACHE.items()}
    report["folder"] = EXCEL_FOLDER
    return jsonify(report)

@app.get("/excel")
def excel_all():
    limit = int(request.args.get("limit", 5))
    sheet = request.args.get("sheet")
    data = {}
    for name in EXCEL_FILES:
        file_path = os.path.join(EXCEL_FOLDER, f"{name}.xlsx")
        if not os.path.exists(file_path):
            data[f"{name}.xlsx"] = {"error": "file not found"}
            continue
        try:
            df = read_excel_one(file_path, sheet)
            data[f"{name}.xlsx"] = df.head(limit).to_dict(orient="records")
        except Exception as e:
            data[f"{name}.xlsx"] = {"error": str(e)}
    return jsonify(data)

@app.get("/excel/<name>")
def excel_one(name: str):
    limit = int(request.args.get("limit", 50))
    sheet = request.args.get("sheet")
    if name not in EXCEL_FILES:
        abort(404, f"Unknown Excel dataset: {name}. Expected one of {EXCEL_FILES}")
    file_path = os.path.join(EXCEL_FOLDER, f"{name}.xlsx")
    if not os.path.exists(file_path):
        abort(404, f"File not found on disk: {file_path}")
    try:
        df = read_excel_one(file_path, sheet)
        return jsonify(df.head(limit).to_dict(orient="records"))
    except Exception as e:
        abort(500, f"Failed to read Excel: {e}")

# -------------------------
# PART D-style friendly endpoints (operate on the Excel cache)
# -------------------------
@app.before_request
def ensure_excel_loaded():
    # Load once lazily; skip for upload/query endpoints which don't need Excel
    if request.path.startswith("/excel") or request.path in {"/", "/health", "/hello"}:
        return
    load_excel_cache(force=False)

def get_df_or_404(name: str) -> pd.DataFrame:
    df = EXCEL_CACHE.get(name)
    if df is None:
        path = os.path.join(EXCEL_FOLDER, f"{name}.xlsx")
        if not os.path.exists(path):
            abort(404, f"Excel file not found: {path}")
        try:
            df = read_excel_one(path)
            EXCEL_CACHE[name] = df
        except Exception as e:
            abort(500, f"Failed to read {name}.xlsx: {e}")
    return df.copy()

# --- Patients ---
@app.get("/patients")
def patients_list():
    df = get_df_or_404("patients")
    q_service = request.args.get("service")
    q_age_min = request.args.get("age_min")
    q_age_max = request.args.get("age_max")
    q_sat_ge = request.args.get("satisfaction_ge")
    q_name_like = request.args.get("name_like")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    service_col = find_col(df, SERVICE_COLS)
    age_col = find_col(df, AGE_COLS)
    sat_col = find_col(df, SAT_COLS)
    name_col = find_col(df, NAME_COLS)

    if q_service and service_col and service_col in df:
        df = df[df[service_col].astype(str).str.strip().str.lower() == q_service.strip().lower()]

    if q_age_min and age_col and age_col in df:
        df = df[pd.to_numeric(df[age_col], errors="coerce") >= float(q_age_min)]
    if q_age_max and age_col and age_col in df:
        df = df[pd.to_numeric(df[age_col], errors="coerce") <= float(q_age_max)]

    if q_sat_ge and sat_col and sat_col in df:
        df = df[pd.to_numeric(df[sat_col], errors="coerce") >= float(q_sat_ge)]

    if q_name_like and name_col and name_col in df:
        df = df[df[name_col].astype(str).str.contains(q_name_like, case=False, na=False)]

    total = len(df)
    page = df.iloc[offset: offset + limit]
    return jsonify({"total": total, "offset": offset, "limit": limit,
                    "columns": list(page.columns),
                    "data": page.to_dict(orient="records")})

@app.get("/patients/<pid>")
def patients_one(pid: str):
    df = get_df_or_404("patients")
    id_col = find_col(df, PATIENT_ID_COLS)
    if not id_col:
        abort(400, f"Could not find a patient id column. Tried {PATIENT_ID_COLS}")
    rec = df[df[id_col].astype(str) == str(pid)]
    if rec.empty:
        abort(404, f"No patient with id {pid}")
    return jsonify(rec.iloc[0].to_dict())

# --- Staff ---
@app.get("/staff")
def staff_list():
    df = get_df_or_404("staff")
    q_role = request.args.get("role")
    q_service = request.args.get("service")
    q_name_like = request.args.get("name_like")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    role_col = find_col(df, ROLE_COLS)
    service_col = find_col(df, SERVICE_COLS)
    name_col = find_col(df, NAME_COLS)

    if q_role and role_col and role_col in df:
        df = df[df[role_col].astype(str).str.lower() == q_role.strip().lower()]
    if q_service and service_col and service_col in df:
        df = df[df[service_col].astype(str).str.lower() == q_service.strip().lower()]
    if q_name_like and name_col and name_col in df:
        df = df[df[name_col].astype(str).str.contains(q_name_like, case=False, na=False)]

    total = len(df)
    page = df.iloc[offset: offset + limit]
    return jsonify({"total": total, "offset": offset, "limit": limit,
                    "columns": list(page.columns),
                    "data": page.to_dict(orient="records")})

@app.get("/staff/<sid>")
def staff_one(sid: str):
    df = get_df_or_404("staff")
    id_col = find_col(df, STAFF_ID_COLS)
    if not id_col:
        abort(400, f"Could not find a staff id column. Tried {STAFF_ID_COLS}")
    rec = df[df[id_col].astype(str) == str(sid)]
    if rec.empty:
        abort(404, f"No staff with id {sid}")
    return jsonify(rec.iloc[0].to_dict())

# --- Staff Schedule ---
@app.get("/staff_schedule")
def schedule_list():
    df = get_df_or_404("staff_schedule")
    q_week = request.args.get("week")
    q_service = request.args.get("service")
    q_present = to_bool(request.args.get("present"))
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    week_col = find_col(df, WEEK_COLS)
    service_col = find_col(df, SERVICE_COLS)
    present_col = find_col(df, PRESENT_COLS)

    if q_week and week_col and week_col in df:
        df = df[df[week_col].astype(str) == str(q_week)]
    if q_service and service_col and service_col in df:
        df = df[df[service_col].astype(str).str.lower() == q_service.strip().lower()]
    if (q_present is not None) and present_col and present_col in df:
        # Treat truthy as True; else False
        df = df[df[present_col].astype(str).str.lower().isin(
            {"true", "1", "yes", "y"} if q_present else {"false", "0", "no", "n"})]

    total = len(df)
    page = df.iloc[offset: offset + limit]
    return jsonify({"total": total, "offset": offset, "limit": limit,
                    "columns": list(page.columns),
                    "data": page.to_dict(orient="records")})

# --- Services weekly ---
@app.get("/services_weekly")
def services_weekly_list():
    df = get_df_or_404("services_weekly")
    q_service = request.args.get("service")
    q_week_like = request.args.get("week_like")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    service_col = find_col(df, SERVICE_COLS)
    week_col = find_col(df, WEEK_COLS)

    if q_service and service_col and service_col in df:
        df = df[df[service_col].astype(str).str.lower() == q_service.strip().lower()]
    if q_week_like and week_col and week_col in df:
        df = df[df[week_col].astype(str).str.contains(q_week_like, case=False, na=False)]

    total = len(df)
    page = df.iloc[offset: offset + limit]
    return jsonify({"total": total, "offset": offset, "limit": limit,
                    "columns": list(page.columns),
                    "data": page.to_dict(orient="records")})

# --- Joined view: staffing vs outcomes ---
@app.get("/service_week_overview")
def service_week_overview():
    """Join staff presence (aggregated) with weekly outcomes by service+week."""
    sched = get_df_or_404("staff_schedule")
    weekly = get_df_or_404("services_weekly")

    service_col_s = find_col(sched, SERVICE_COLS)
    week_col_s = find_col(sched, WEEK_COLS)
    present_col = find_col(sched, PRESENT_COLS)

    service_col_w = find_col(weekly, SERVICE_COLS)
    week_col_w = find_col(weekly, WEEK_COLS)

    missing = []
    for nm, ok in {
        "staff_schedule.service": bool(service_col_s),
        "staff_schedule.week": bool(week_col_s),
        "staff_schedule.present": bool(present_col),
        "services_weekly.service": bool(service_col_w),
        "services_weekly.week": bool(week_col_w),
    }.items():
        if not ok: missing.append(nm)
    if missing:
        abort(400, f"Missing required columns for join: {missing}")

    # Normalize present to boolean-ish 1/0
    pres = sched.copy()
    pres["_present_num"] = pres[present_col].astype(str).str.lower().isin({"true", "1", "yes", "y"}).astype(int)

    # Aggregate presence by service+week
    agg = pres.groupby([service_col_s, week_col_s], dropna=False)["_present_num"].sum().reset_index()
    agg = agg.rename(columns={
        service_col_s: "service",
        week_col_s: "week",
        "_present_num": "present_count"
    })

    # Prepare weekly and rename keys for join
    wk = weekly.rename(columns={service_col_w: "service", week_col_w: "week"})

    # Optional filters
    q_service = request.args.get("service")
    q_week_like = request.args.get("week_like")
    if q_service:
        agg = agg[agg["service"].astype(str).str.lower() == q_service.strip().lower()]
        wk = wk[wk["service"].astype(str).str.lower() == q_service.strip().lower()]
    if q_week_like:
        agg = agg[agg["week"].astype(str).str.contains(q_week_like, case=False, na=False)]
        wk = wk[wk["week"].astype(str).str.contains(q_week_like, case=False, na=False)]

    # Join
    merged = pd.merge(wk, agg, on=["service", "week"], how="left")
    merged["present_count"] = merged["present_count"].fillna(0).astype(int)

    limit = int(request.args.get("limit", 200))
    offset = int(request.args.get("offset", 0))
    total = len(merged)
    page = merged.iloc[offset: offset + limit]

    return jsonify({
        "total": total,
        "offset": offset,
        "limit": limit,
        "columns": list(page.columns),
        "data": page.to_dict(orient="records")
    })

# -------------------------
# Upload & in-memory CSV/JSON API (your original endpoints)
# -------------------------
DATASETS: Dict[str, Dict] = {}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS

@app.route("/upload", methods=["POST"])
def upload():
    """
    Upload one file at a time (CSV or JSON).
    form-data:
      - file=<yourfile.csv|json>
      - name=<optional label like 'patients'>
    Returns a dataset_id.
    """
    if "file" not in request.files:
        abort(400, "No file part in request")

    f = request.files["file"]
    if f.filename == "":
        abort(400, "No selected file")
    if not allowed_file(f.filename):
        abort(400, f"Unsupported extension. Allowed: {sorted(ALLOWED_EXTS)}")

    filename = secure_filename(f.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    raw = f.read()

    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(raw))
        else:
            try:
                df = pd.read_json(io.BytesIO(raw), orient="records")
            except ValueError:
                df = pd.read_json(io.BytesIO(raw), lines=True)
    except Exception as e:
        abort(400, f"Failed to parse file: {e}")

    if len(df) > MAX_ROWS_IN_MEMORY:
        abort(413, f"Dataset too large (> {MAX_ROWS_IN_MEMORY} rows)")

    dataset_id = str(uuid.uuid4())
    label = request.form.get("name") or filename
    DATASETS[dataset_id] = {
        "name": label,
        "df": df,
        "columns": list(df.columns),
        "rows": len(df),
    }
    return jsonify({"dataset_id": dataset_id, "name": label, "rows": len(df), "columns": list(df.columns)})

@app.route("/datasets", methods=["GET"])
def list_datasets():
    out = []
    for ds_id, meta in DATASETS.items():
        out.append({"dataset_id": ds_id, "name": meta["name"], "rows": meta["rows"], "columns": meta["columns"]})
    return jsonify(out)

@app.route("/datasets/<dataset_id>/head", methods=["GET"])
def head(dataset_id):
    meta = DATASETS.get(dataset_id)
    if not meta:
        abort(404, "Unknown dataset_id")
    n = int(request.args.get("n", 5))
    return meta["df"].head(n).to_json(orient="records")

@app.route("/datasets/<dataset_id>/stats", methods=["GET"])
def stats(dataset_id):
    meta = DATASETS.get(dataset_id)
    if not meta:
        abort(404, "Unknown dataset_id")
    desc = meta["df"].describe(include="all", datetime_is_numeric=True).fillna("").to_dict()
    return jsonify(desc)

def apply_filters(df: pd.DataFrame, filters: List[dict]) -> pd.DataFrame:
    ops = {"eq", "ne", "gt", "ge", "lt", "le", "contains", "startswith", "endswith", "isin"}
    for flt in filters:
        col = flt.get("col")
        op = flt.get("op")
        val = flt.get("val")
        if col not in df.columns:
            abort(400, f"Unknown column: {col}")
        if op not in ops:
            abort(400, f"Unsupported op: {op}")

        s = df[col]
        if op in {"contains", "startswith", "endswith"}:
            mask = s.astype(str).str.get(op)(str(val), na=False)
        elif op == "isin":
            if not isinstance(val, list):
                abort(400, "isin requires list value")
            mask = s.isin(val)
        else:
            try:
                mask = getattr(s, op)(val)
            except Exception:
                try:
                    mask = getattr(pd.to_numeric(s, errors="coerce"), op)(
                        pd.to_numeric(pd.Series([val]).repeat(len(s)), errors="coerce").values
                    )
                except Exception as e:
                    abort(400, f"Comparison failed on {col}: {e}")
        df = df[mask]
    return df

@app.route("/datasets/<dataset_id>/query", methods=["GET", "POST"])
def query(dataset_id):
    """
    GET simple filters:
      /query?col=service&op=eq&val=Cardiology&select=patient_id,name,age&limit=20
    POST complex filters:
      {
        "filters":[{"col":"service","op":"eq","val":"Cardiology"}],
        "select":["patient_id","name","age"],
        "sort":[{"col":"age","asc":false}],
        "limit":20,"offset":0
      }
    """
    meta = DATASETS.get(dataset_id)
    if not meta:
        abort(404, "Unknown dataset_id")
    df = meta["df"]

    if request.method == "GET":
        cols = request.args.getlist("col")
        ops_ = request.args.getlist("op")
        vals = request.args.getlist("val")
        if cols or ops_ or vals:
            if not (len(cols) == len(ops_) == len(vals)):
                abort(400, "col/op/val counts must match")
            filters = [{"col": c, "op": o, "val": v} for c, o, v in zip(cols, ops_, vals)]
            df = apply_filters(df, filters)
        select = request.args.get("select")
        select = [c.strip() for c in select.split(",")] if select else None
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
        sort = request.args.get("sort")  # e.g., "age,-satisfaction"
        if sort:
            by, ascending = [], []
            for s in [s.strip() for s in sort.split(",")]:
                if s.startswith("-"):
                    by.append(s[1:]); ascending.append(False)
                else:
                    by.append(s); ascending.append(True)
            df = df.sort_values(by=by, ascending=ascending)
    else:
        body = request.get_json(silent=True) or {}
        filters = body.get("filters", [])
        if filters:
            df = apply_filters(df, filters)
        select = body.get("select")
        limit = int(body.get("limit", 100))
        offset = int(body.get("offset", 0))
        sort_spec = body.get("sort", [])
        if sort_spec:
            by = [s["col"] for s in sort_spec]
            ascending = [bool(s.get("asc", True)) for s in sort_spec]
            df = df.sort_values(by=by, ascending=ascending)

    if select:
        missing = [c for c in select if c not in df.columns]
        if missing:
            abort(400, f"Unknown columns in select: {missing}")
        df = df[select]

    total = len(df)
    page = df.iloc[offset: offset + limit]
    return jsonify({
        "total": total,
        "offset": offset,
        "limit": limit,
        "columns": list(page.columns),
        "data": page.to_dict(orient="records"),
    })

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    print(f"[Excel folder] {EXCEL_FOLDER}")
    load_excel_cache(force=False)  # prime cache if files exist
    app.run(host="0.0.0.0", port=8000, debug=True)
