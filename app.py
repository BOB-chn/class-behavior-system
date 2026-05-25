"""
704班级行为管理系统 - Flask后端
代理飞书多维表格API，提供REST接口
"""
import os
import time
import json
import csv
from datetime import datetime, timedelta
from io import StringIO
from functools import wraps

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# 配置
FEISHU_APP_ID = "cli_aa9902f04462dcc4"
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
BASE_TOKEN = "MwnabIru0aqK7dsnXYcccI8knZg"

# 表ID
TBL_STUDENTS = "tblpxPK0fKrM2qLT"      # 学生档案
TBL_RECORDS = "tbl5TfujbekzE3rq"       # 行为记录
TBL_HANDOVER = "tblpyHEWQxeE1NRY"     # 值日交接
TBL_REPORTS = "tbleB8oLfHfeQAAR"      # 学生上报

# 学生档案字段ID
FLD_STUDENT_NAME = "fldiJIkQDr"
FLD_STUDENT_ID = "fldFYYmdss"
FLD_PASSWORD = "fldoZNTU2T"
FLD_HOMEWORK = "fldT95h8LW"
FLD_HYGIENE = "fldYzEQV9T"
FLD_DISCIPLINE = "fldEtIs30P"
FLD_SPORTS = "fldu0Qyf8n"
FLD_CIVILIZED = "fld4jDPOT4"
FLD_OTHER = "fldjONkmbH"
FLD_STATUS = "fldwPqE0Lw"
FLD_TOTAL = "fldcwP71ql"

# 行为记录字段ID
FLD_DATE = "fldkORZUWW"
FLD_STUDENT_LINK = "fldcff9j3B"
FLD_CATEGORY = "fldkjIyjVk"
FLD_RULE_CLAUSE = "fldOZVHAAO"
FLD_SCORE = "fldVAYHaAF"
FLD_RECORDER = "fldYayQntF"
FLD_NOTE = "fldf4I1tMZ"

# 学生上报字段ID
FLD_REPORT_DATE = "fldH0T43kU"
FLD_REPORT_STUDENT = "fldiSIcY0N"
FLD_REPORT_CATEGORY = "fldwDOmVbf"
FLD_REPORT_DESC = "fldrj3udWF"
FLD_AUDIT_STATUS = "fldIj8DoOY"
FLD_REPORT_SCORE = "fldQK23nsy"
FLD_AUDITOR = "fldCiRfTmR"

# 值日交接字段ID
FLD_HANDOVER_DATE = "fldrM8VwvW"
FLD_DUTY_MONITOR = "fld8TkGjwd"
FLD_SUMMARY = "fldb8CbV9F"
FLD_PENDING = "fldmPI08Q5"
FLD_REMARK = "fld0tHTkBp"
FLD_HANDOVER_STATUS = "fldwp6Vh1w"

# 学生record_id映射
STUDENT_RECORD_MAP = {
    "蒋雨函": "recvkBTZ7KqYYH", "张钰晴": "recvkBTZ7KbncL", "李宇航": "recvkBTZ7KHOmq",
    "姚明哲": "recvkBTZ7K8EIM", "蔡悦然": "recvkBTZ7KJfbf", "沈逸宸": "recvkBTZ7Kcwm4",
    "魏锦宸": "recvkBTZ7Ketxm", "汪雨萱": "recvkBTZ7KdwFc", "丁以萍": "recvkBTZ7KKIjj",
    "周韩涵": "recvkBTZ7KrgBG", "周陆云逸": "recvkBU3vQy5pF", "郑宇涵": "recvkBU3vQ6map",
    "徐佐怡": "recvkBU3vQpra6", "汤舒婷": "recvkBU3vQdi8D", "徐梦漪": "recvkBU3vQcoLl",
    "张艺通": "recvkBU3vQOFUM", "王以太": "recvkBU3vQWIUo", "吴宇浩": "recvkBU3vQ8t30",
    "孙泽洋": "recvkBU3vQG9A6", "李成": "recvkBU3vQMLBw", "金恒仲": "recvkBU6nJBK5a",
    "黄佳丞": "recvkBU6nKOctb", "傅雨辰": "recvkBU6nK5aah", "陈威吉": "recvkBU6nK19AK",
    "仇彦媛": "recvkBU6nKyAK9", "柴逸山": "recvkBU6nKOhyO", "沈毅赐": "recvkBU6nKzQdi",
    "熊启航": "recvkBU6nKqY68", "韩宇程": "recvkBU6nKLggU", "邵晗": "recvkBU6nKHPyY",
    "齐慧妍": "recvkBU9a1YIKN", "章毅煊": "recvkBU9a1UE7j", "楼智宸": "recvkBU9a1FPTK",
    "沈子欣": "recvkBU9a1ffvj", "厉胡瑾": "recvkBU9a19MFI", "邓永琪": "recvkBU9a1vksG",
    "钱奕辰": "recvkBU9a1ByJ2", "阮镱芠": "recvkBU9a1FfPH", "王胡彬": "recvkBU9a1wnSc"
}

# 积分字段映射
SCORE_FIELD_MAP = {
    "作业": FLD_HOMEWORK,
    "卫生": FLD_HYGIENE,
    "纪律": FLD_DISCIPLINE,
    "体育锻炼": FLD_SPORTS,
    "文明行为": FLD_CIVILIZED,
    "其他": FLD_OTHER
}

# tenant_access_token缓存
_token_cache = {"token": None, "expires_at": 0}


def get_token():
    """获取tenant_access_token，带缓存"""
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 300:
        return _token_cache["token"]
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            _token_cache["token"] = result["tenant_access_token"]
            _token_cache["expires_at"] = now + result.get("expire", 7200)
            return _token_cache["token"]
    except Exception as e:
        print(f"获取token失败: {e}")
    
    return None


def feishu_headers():
    """获取飞书API请求头"""
    token = get_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def list_records(table_id, page_token=None, page_size=100):
    """列出表格所有记录（处理分页）"""
    all_records = []
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records"
    params = {"page_size": page_size}
    
    while True:
        if page_token:
            params["page_token"] = page_token
        
        try:
            resp = requests.get(url, headers=feishu_headers(), params=params, timeout=15)
            result = resp.json()
            
            if result.get("code") != 0:
                print(f"API错误: {result}")
                break
            
            items = result.get("data", {}).get("items", [])
            all_records.extend(items)
            
            if result.get("data", {}).get("has_more"):
                page_token = result["data"].get("page_token")
            else:
                break
        except Exception as e:
            print(f"获取记录失败: {e}")
            break
    
    return all_records


def search_records(table_id, filter_conditions, page_size=100):
    """搜索记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records/search"
    headers = feishu_headers()
    
    all_records = []
    page_token = None
    
    while True:
        data = {
            "filter": {"conjunction": "and", "conditions": filter_conditions},
            "page_size": page_size
        }
        if page_token:
            data["page_token"] = page_token
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=15)
            result = resp.json()
            
            if result.get("code") != 0:
                break
            
            items = result.get("data", {}).get("items", [])
            all_records.extend(items)
            
            if result.get("data", {}).get("has_more"):
                page_token = result["data"].get("page_token")
            else:
                break
        except Exception as e:
            print(f"搜索失败: {e}")
            break
    
    return all_records


def create_record(table_id, fields):
    """创建记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records"
    data = {"fields": fields}
    
    try:
        resp = requests.post(url, headers=feishu_headers(), json=data, timeout=15)
        result = resp.json()
        return result.get("code") == 0, result
    except Exception as e:
        print(f"创建记录失败: {e}")
        return False, {"msg": str(e)}


def update_record(table_id, record_id, fields):
    """更新记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records/{record_id}"
    data = {"fields": fields}
    
    try:
        resp = requests.put(url, headers=feishu_headers(), json=data, timeout=15)
        result = resp.json()
        return result.get("code") == 0, result
    except Exception as e:
        print(f"更新记录失败: {e}")
        return False, {"msg": str(e)}


def get_student_record_id(student_name):
    """根据学生姓名获取record_id"""
    return STUDENT_RECORD_MAP.get(student_name)


def get_student_by_name(student_name):
    """根据姓名查找学生档案"""
    records = list_records(TBL_STUDENTS)
    for record in records:
        fields = record.get("fields", {})
        name = fields.get(FLD_STUDENT_NAME, "")
        if name == student_name:
            return record
    return None


def update_student_score(student_name, category, score_delta):
    """更新学生积分"""
    record = get_student_by_name(student_name)
    if not record:
        return False, "学生不存在"
    
    record_id = record["record_id"]
    field_id = SCORE_FIELD_MAP.get(category)
    if not field_id:
        return False, "无效的积分类别"
    
    fields = record.get("fields", {})
    current_score = fields.get(field_id, 0) or 0
    new_score = current_score + score_delta
    
    success, result = update_record(TBL_STUDENTS, record_id, {field_id: new_score})
    return success, result


def format_timestamp(ts):
    """格式化时间戳"""
    if not ts:
        return "-"
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000)
        else:
            return str(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return str(ts)


def format_date_str(ts):
    """格式化日期字符串"""
    if not ts:
        return "-"
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except:
        return str(ts)


# ==================== 页面路由 ====================
@app.route("/")
def index():
    return render_template("login.html")


@app.route("/login.html")
def login():
    return render_template("login.html")


@app.route("/student.html")
def student_page():
    return render_template("student.html")


@app.route("/monitor.html")
def monitor_page():
    return render_template("monitor.html")


@app.route("/teacher.html")
def teacher_page():
    return render_template("teacher.html")


# ==================== API路由 ====================
@app.route("/api/health")
def health():
    """健康检查"""
    return jsonify({"code": 0, "msg": "OK"})


# ==================== 学生端API ====================
@app.route("/api/student/profile")
def student_profile():
    """获取学生个人信息"""
    name = request.args.get("name", "")
    if not name:
        return jsonify({"code": 1, "msg": "缺少学生姓名"})
    
    record = get_student_by_name(name)
    if not record:
        return jsonify({"code": 1, "msg": "学生不存在"})
    
    fields = record.get("fields", {})
    
    profile = {
        "name": fields.get(FLD_STUDENT_NAME, ""),
        "studentId": fields.get(FLD_STUDENT_ID, ""),
        "homeworkScore": fields.get(FLD_HOMEWORK, 0) or 0,
        "hygieneScore": fields.get(FLD_HYGIENE, 0) or 0,
        "disciplineScore": fields.get(FLD_DISCIPLINE, 0) or 0,
        "sportsScore": fields.get(FLD_SPORTS, 0) or 0,
        "civilizedScore": fields.get(FLD_CIVILIZED, 0) or 0,
        "otherScore": fields.get(FLD_OTHER, 0) or 0,
        "totalScore": fields.get(FLD_TOTAL, 0) or 0,
        "status": fields.get(FLD_STATUS, "正常")
    }
    
    return jsonify({"code": 0, "data": profile})


@app.route("/api/student/records")
def student_records():
    """获取学生行为记录"""
    name = request.args.get("name", "")
    sort = request.args.get("sort", "desc")
    
    if not name:
        return jsonify({"code": 1, "msg": "缺少学生姓名"})
    
    student_record_id = get_student_record_id(name)
    if not student_record_id:
        return jsonify({"code": 1, "msg": "学生ID不存在"})
    
    # 搜索该学生的行为记录
    records = search_records(TBL_RECORDS, [
        {"field_name": "学生", "operator": "contains", "value": [student_record_id]}
    ])
    
    result = []
    for record in records:
        fields = record.get("fields", {})
        student_link = fields.get(FLD_STUDENT_LINK, [])
        student_text = student_link[0].get("text", "") if student_link else name
        
        result.append({
            "recordId": record.get("record_id"),
            "date": format_timestamp(fields.get(FLD_DATE)),
            "studentName": student_text,
            "category": fields.get(FLD_CATEGORY, ""),
            "ruleClause": fields.get(FLD_RULE_CLAUSE, ""),
            "score": fields.get(FLD_SCORE, 0) or 0,
            "recorder": fields.get(FLD_RECORDER, ""),
            "note": fields.get(FLD_NOTE, "")
        })
    
    # 排序
    result.sort(key=lambda x: x["date"] or "", reverse=(sort == "desc"))
    
    return jsonify({"code": 0, "data": result})


@app.route("/api/student/radar")
def student_radar():
    """获取学生六维度数据"""
    name = request.args.get("name", "")
    if not name:
        return jsonify({"code": 1, "msg": "缺少学生姓名"})
    
    record = get_student_by_name(name)
    if not record:
        return jsonify({"code": 1, "msg": "学生不存在"})
    
    fields = record.get("fields", {})
    
    return jsonify({
        "code": 0,
        "data": {
            "homeworkScore": fields.get(FLD_HOMEWORK, 0) or 0,
            "hygieneScore": fields.get(FLD_HYGIENE, 0) or 0,
            "disciplineScore": fields.get(FLD_DISCIPLINE, 0) or 0,
            "sportsScore": fields.get(FLD_SPORTS, 0) or 0,
            "civilizedScore": fields.get(FLD_CIVILIZED, 0) or 0,
            "otherScore": fields.get(FLD_OTHER, 0) or 0
        }
    })


@app.route("/api/leaderboard")
def leaderboard():
    """获取积分排行榜"""
    records = list_records(TBL_STUDENTS)
    
    students = []
    for record in records:
        fields = record.get("fields", {})
        name = fields.get(FLD_STUDENT_NAME, "")
        if not name:
            continue
        
        students.append({
            "name": name,
            "homeworkScore": fields.get(FLD_HOMEWORK, 0) or 0,
            "hygieneScore": fields.get(FLD_HYGIENE, 0) or 0,
            "disciplineScore": fields.get(FLD_DISCIPLINE, 0) or 0,
            "sportsScore": fields.get(FLD_SPORTS, 0) or 0,
            "civilizedScore": fields.get(FLD_CIVILIZED, 0) or 0,
            "otherScore": fields.get(FLD_OTHER, 0) or 0,
            "totalScore": fields.get(FLD_TOTAL, 0) or 0,
            "status": fields.get(FLD_STATUS, "正常")
        })
    
    # 按总积分排序
    students.sort(key=lambda x: x["totalScore"] or 0, reverse=True)
    
    return jsonify({"code": 0, "data": students})


@app.route("/api/student/report", methods=["POST"])
def submit_report():
    """学生自主上报"""
    data = request.json
    name = data.get("name")
    category = data.get("category")
    description = data.get("description")
    
    if not all([name, category, description]):
        return jsonify({"code": 1, "msg": "缺少必填字段"})
    
    fields = {
        FLD_REPORT_DATE: int(time.time() * 1000),
        FLD_REPORT_STUDENT: name,
        FLD_REPORT_CATEGORY: category,
        FLD_REPORT_DESC: description,
        FLD_AUDIT_STATUS: "待审核"
    }
    
    success, result = create_record(TBL_REPORTS, fields)
    if success:
        return jsonify({"code": 0, "msg": "提交成功"})
    else:
        return jsonify({"code": 1, "msg": result.get("msg", "提交失败")})


# ==================== 值日班长端API ====================
@app.route("/api/monitor/record", methods=["POST"])
def add_record():
    """录入行为记录"""
    data = request.json
    date = data.get("date")
    student_name = data.get("studentName")
    category = data.get("category")
    score = data.get("score", 0)
    rule_clause = data.get("ruleClause", "")
    note = data.get("note", "")
    recorder = data.get("recorder", "")
    
    if not all([date, student_name, category, score]):
        return jsonify({"code": 1, "msg": "缺少必填字段"})
    
    student_record_id = get_student_record_id(student_name)
    if not student_record_id:
        return jsonify({"code": 1, "msg": "学生ID不存在"})
    
    # 1. 创建行为记录
    fields = {
        FLD_DATE: date,
        FLD_STUDENT_LINK: [{"id": student_record_id}],
        FLD_CATEGORY: category,
        FLD_SCORE: int(score),
        FLD_RULE_CLAUSE: rule_clause,
        FLD_NOTE: note,
        FLD_RECORDER: recorder
    }
    
    success, result = create_record(TBL_RECORDS, fields)
    if not success:
        return jsonify({"code": 1, "msg": "创建行为记录失败"})
    
    # 2. 更新学生积分
    success2, result2 = update_student_score(student_name, category, int(score))
    if not success2:
        return jsonify({"code": 1, "msg": "更新积分失败"})
    
    return jsonify({"code": 0, "msg": "录入成功"})


@app.route("/api/monitor/handover", methods=["POST"])
def submit_handover():
    """提交值日交接"""
    data = request.json
    date = data.get("date")
    summary = data.get("summary")
    pending = data.get("pending", "")
    remark = data.get("remark", "")
    recorder = data.get("recorder", "")
    
    if not all([date, summary]):
        return jsonify({"code": 1, "msg": "缺少必填字段"})
    
    fields = {
        FLD_HANDOVER_DATE: date,
        FLD_DUTY_MONITOR: recorder,
        FLD_SUMMARY: summary,
        FLD_PENDING: pending,
        FLD_REMARK: remark,
        FLD_HANDOVER_STATUS: "待处理"
    }
    
    success, result = create_record(TBL_HANDOVER, fields)
    if success:
        return jsonify({"code": 0, "msg": "交接记录已保存"})
    else:
        return jsonify({"code": 1, "msg": result.get("msg", "保存失败")})


@app.route("/api/monitor/pending-reports")
def pending_reports():
    """获取待审核上报"""
    records = search_records(TBL_REPORTS, [
        {"field_name": "审核状态", "operator": "is", "value": ["待审核"]}
    ])
    
    result = []
    for record in records:
        fields = record.get("fields", {})
        result.append({
            "recordId": record.get("record_id"),
            "date": format_timestamp(fields.get(FLD_REPORT_DATE)),
            "studentName": fields.get(FLD_REPORT_STUDENT, ""),
            "category": fields.get(FLD_REPORT_CATEGORY, ""),
            "description": fields.get(FLD_REPORT_DESC, "")
        })
    
    return jsonify({"code": 0, "data": result})


@app.route("/api/monitor/approve-report", methods=["POST"])
def approve_report():
    """审核通过"""
    data = request.json
    report_record_id = data.get("reportRecordId")
    score = data.get("score", 0)
    reviewer = data.get("reviewer", "")
    
    if not all([report_record_id, score]):
        return jsonify({"code": 1, "msg": "缺少必填字段"})
    
    # 1. 获取上报记录
    records = list_records(TBL_REPORTS)
    report_record = None
    for record in records:
        if record.get("record_id") == report_record_id:
            report_record = record
            break
    
    if not report_record:
        return jsonify({"code": 1, "msg": "上报记录不存在"})
    
    fields = report_record.get("fields", {})
    student_name = fields.get(FLD_REPORT_STUDENT, "")
    category = fields.get(FLD_REPORT_CATEGORY, "")
    description = fields.get(FLD_REPORT_DESC, "")
    report_date = format_date_str(fields.get(FLD_REPORT_DATE))
    
    student_record_id = get_student_record_id(student_name)
    if not student_record_id:
        return jsonify({"code": 1, "msg": "学生ID不存在"})
    
    # 2. 更新上报状态
    success1, _ = update_record(TBL_REPORTS, report_record_id, {
        FLD_AUDIT_STATUS: "已通过",
        FLD_REPORT_SCORE: int(score),
        FLD_AUDITOR: reviewer
    })
    
    # 3. 创建行为记录
    record_fields = {
        FLD_DATE: report_date,
        FLD_STUDENT_LINK: [{"id": student_record_id}],
        FLD_CATEGORY: category,
        FLD_SCORE: int(score),
        FLD_RULE_CLAUSE: description,
        FLD_RECORDER: reviewer
    }
    create_record(TBL_RECORDS, record_fields)
    
    # 4. 更新学生积分
    update_student_score(student_name, category, int(score))
    
    return jsonify({"code": 0, "msg": "审核通过"})


@app.route("/api/monitor/reject-report", methods=["POST"])
def reject_report():
    """审核驳回"""
    data = request.json
    report_record_id = data.get("reportRecordId")
    reviewer = data.get("reviewer", "")
    
    success, _ = update_record(TBL_REPORTS, report_record_id, {
        FLD_AUDIT_STATUS: "已驳回",
        FLD_AUDITOR: reviewer
    })
    
    if success:
        return jsonify({"code": 0, "msg": "已驳回"})
    else:
        return jsonify({"code": 1, "msg": "操作失败"})


@app.route("/api/monitor/recent-records")
def recent_records():
    """获取最近行为记录"""
    records = list_records(TBL_RECORDS)
    
    result = []
    for record in records:
        fields = record.get("fields", {})
        student_link = fields.get(FLD_STUDENT_LINK, [])
        student_name = student_link[0].get("text", "") if student_link else "-"
        
        result.append({
            "recordId": record.get("record_id"),
            "date": format_timestamp(fields.get(FLD_DATE)),
            "studentName": student_name,
            "category": fields.get(FLD_CATEGORY, ""),
            "score": fields.get(FLD_SCORE, 0) or 0,
            "ruleClause": fields.get(FLD_RULE_CLAUSE, ""),
            "recorder": fields.get(FLD_RECORDER, "")
        })
    
    # 按日期降序
    result.sort(key=lambda x: x["date"] or "", reverse=True)
    
    # 返回最近50条
    return jsonify({"code": 0, "data": result[:50]})


# ==================== 教师端API ====================
@app.route("/api/teacher/dashboard")
def teacher_dashboard():
    """数据看板"""
    # 获取所有学生
    students = list_records(TBL_STUDENTS)
    # 获取所有行为记录
    records = list_records(TBL_RECORDS)
    
    # 计算指标
    total_students = len(students)
    today = datetime.now().strftime("%Y-%m-%d")
    today_violations = 0
    homework_positive_count = 0
    
    # 积分分布
    distribution = [
        {"range": "<0", "count": 0},
        {"range": "0-10", "count": 0},
        {"range": "11-30", "count": 0},
        {"range": "31-50", "count": 0},
        {"range": ">50", "count": 0}
    ]
    
    # 六维度班级平均
    radar = {
        "homeworkScore": 0, "hygieneScore": 0, "disciplineScore": 0,
        "sportsScore": 0, "civilizedScore": 0, "otherScore": 0
    }
    
    student_list = []
    for record in students:
        fields = record.get("fields", {})
        name = fields.get(FLD_STUDENT_NAME, "")
        if not name:
            continue
        
        homework = fields.get(FLD_HOMEWORK, 0) or 0
        hygiene = fields.get(FLD_HYGIENE, 0) or 0
        discipline = fields.get(FLD_DISCIPLINE, 0) or 0
        sports = fields.get(FLD_SPORTS, 0) or 0
        civilized = fields.get(FLD_CIVILIZED, 0) or 0
        other = fields.get(FLD_OTHER, 0) or 0
        total = fields.get(FLD_TOTAL, 0) or 0
        
        student_list.append({
            "name": name,
            "homeworkScore": homework,
            "hygieneScore": hygiene,
            "disciplineScore": discipline,
            "sportsScore": sports,
            "civilizedScore": civilized,
            "otherScore": other,
            "totalScore": total,
            "status": fields.get(FLD_STATUS, "正常")
        })
        
        # 作业完成率
        if homework > 0:
            homework_positive_count += 1
        
        # 积分分布
        if total < 0:
            distribution[0]["count"] += 1
        elif total <= 10:
            distribution[1]["count"] += 1
        elif total <= 30:
            distribution[2]["count"] += 1
        elif total <= 50:
            distribution[3]["count"] += 1
        else:
            distribution[4]["count"] += 1
        
        # 累计雷达数据
        radar["homeworkScore"] += homework
        radar["hygieneScore"] += hygiene
        radar["disciplineScore"] += discipline
        radar["sportsScore"] += sports
        radar["civilizedScore"] += civilized
        radar["otherScore"] += other
    
    # 计算平均
    if total_students > 0:
        for k in radar:
            radar[k] = round(radar[k] / total_students, 1)
    
    # 计算今日违规
    for record in records:
        fields = record.get("fields", {})
        date_str = format_date_str(fields.get(FLD_DATE))
        score = fields.get(FLD_SCORE, 0) or 0
        if date_str == today and score < 0:
            today_violations += 1
    
    # AI预警统计
    warning_count = len(get_warning_students(students, records))
    
    # 21天趋势
    daily_trend = []
    now = datetime.now()
    for i in range(21, -1, -1):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        positive = 0
        negative = 0
        for record in records:
            fields = record.get("fields", {})
            if format_date_str(fields.get(FLD_DATE)) == date:
                score = fields.get(FLD_SCORE, 0) or 0
                if score > 0:
                    positive += score
                else:
                    negative += score
        daily_trend.append({"date": date, "positive": positive, "negative": negative})
    
    homework_rate = f"{round(homework_positive_count / total_students * 100)}%" if total_students > 0 else "0%"
    
    return jsonify({
        "code": 0,
        "data": {
            "totalStudents": total_students,
            "todayViolations": today_violations,
            "homeworkRate": homework_rate,
            "warningStudents": warning_count,
            "scoreDistribution": distribution,
            "classRadar": radar,
            "dailyTrend": daily_trend,
            "students": student_list
        }
    })


def get_warning_students(students, records):
    """获取预警学生列表（用于AI预警）"""
    warnings = []
    now = datetime.now()
    three_days_ms = 3 * 24 * 60 * 60 * 1000
    
    for student in students:
        fields = student.get("fields", {})
        name = fields.get(FLD_STUDENT_NAME, "")
        if not name:
            continue
        
        # 获取该学生的最近21天记录
        student_records = []
        for record in records:
            r_fields = record.get("fields", {})
            student_link = r_fields.get(FLD_STUDENT_LINK, [])
            if student_link and student_link[0].get("text") == name:
                student_records.append(r_fields)
        
        # 计算每日积分
        daily_scores = {}
        for i in range(21):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_scores[date] = 0
        
        for r in student_records:
            date_str = format_date_str(r.get(FLD_DATE))
            if date_str in daily_scores:
                daily_scores[date_str] += r.get(FLD_SCORE, 0) or 0
        
        # 检查连续3天零分
        dates = sorted(daily_scores.keys(), reverse=True)
        zero_streak = 0
        max_zero = 0
        for d in dates:
            if daily_scores[d] == 0:
                zero_streak += 1
                max_zero = max(max_zero, zero_streak)
            else:
                zero_streak = 0
        
        if max_zero >= 3:
            warnings.append(name)
    
    return warnings


@app.route("/api/teacher/all-records")
def all_records():
    """获取所有行为记录（用于AI分析）"""
    records = list_records(TBL_RECORDS)
    
    result = []
    for record in records:
        fields = record.get("fields", {})
        student_link = fields.get(FLD_STUDENT_LINK, [])
        student_name = student_link[0].get("text", "") if student_link else "-"
        
        result.append({
            "recordId": record.get("record_id"),
            "date": format_date_str(fields.get(FLD_DATE)),
            "studentName": student_name,
            "category": fields.get(FLD_CATEGORY, ""),
            "score": fields.get(FLD_SCORE, 0) or 0
        })
    
    return jsonify({"code": 0, "data": result})


@app.route("/api/teacher/students")
def teacher_students():
    """全班学生列表"""
    records = list_records(TBL_STUDENTS)
    
    students = []
    for record in records:
        fields = record.get("fields", {})
        name = fields.get(FLD_STUDENT_NAME, "")
        if not name:
            continue
        
        students.append({
            "name": name,
            "homeworkScore": fields.get(FLD_HOMEWORK, 0) or 0,
            "hygieneScore": fields.get(FLD_HYGIENE, 0) or 0,
            "disciplineScore": fields.get(FLD_DISCIPLINE, 0) or 0,
            "sportsScore": fields.get(FLD_SPORTS, 0) or 0,
            "civilizedScore": fields.get(FLD_CIVILIZED, 0) or 0,
            "otherScore": fields.get(FLD_OTHER, 0) or 0,
            "totalScore": fields.get(FLD_TOTAL, 0) or 0,
            "status": fields.get(FLD_STATUS, "正常")
        })
    
    students.sort(key=lambda x: x["totalScore"] or 0, reverse=True)
    
    return jsonify({"code": 0, "data": students})


@app.route("/api/teacher/export")
def export_data():
    """导出CSV数据"""
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    
    if not start or not end:
        return jsonify({"code": 1, "msg": "请选择日期范围"})
    
    # 获取数据
    students = list_records(TBL_STUDENTS)
    records = list_records(TBL_RECORDS)
    
    # 过滤日期范围内的记录
    filtered_records = []
    for record in records:
        fields = record.get("fields", {})
        date_str = format_date_str(fields.get(FLD_DATE))
        if start <= date_str <= end:
            student_link = fields.get(FLD_STUDENT_LINK, [])
            filtered_records.append({
                "date": date_str,
                "student": student_link[0].get("text", "") if student_link else "-",
                "category": fields.get(FLD_CATEGORY, ""),
                "score": fields.get(FLD_SCORE, 0) or 0,
                "rule": fields.get(FLD_RULE_CLAUSE, ""),
                "recorder": fields.get(FLD_RECORDER, "")
            })
    
    # 生成CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # 标题
    writer.writerow(["日期", "学生姓名", "行为类别", "分值", "班规条款", "记录人"])
    
    # 数据
    for r in filtered_records:
        writer.writerow([r["date"], r["student"], r["category"], r["score"], r["rule"], r["recorder"]])
    
    # 学生汇总
    writer.writerow([])
    writer.writerow(["学生姓名", "作业", "卫生", "纪律", "体育", "文明", "其他", "总积分", "状态"])
    
    for record in students:
        fields = record.get("fields", {})
        name = fields.get(FLD_STUDENT_NAME, "")
        if not name:
            continue
        writer.writerow([
            name,
            fields.get(FLD_HOMEWORK, 0) or 0,
            fields.get(FLD_HYGIENE, 0) or 0,
            fields.get(FLD_DISCIPLINE, 0) or 0,
            fields.get(FLD_SPORTS, 0) or 0,
            fields.get(FLD_CIVILIZED, 0) or 0,
            fields.get(FLD_OTHER, 0) or 0,
            fields.get(FLD_TOTAL, 0) or 0,
            fields.get(FLD_STATUS, "正常")
        ])
    
    output.seek(0)
    filename = f"班级行为数据_{start}_至_{end}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== 启动 ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
