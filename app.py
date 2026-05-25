"""
704班级行为管理系统 - Flask后端
包含数据缓存层、预计算功能、飞书API调用
"""
import os
import json
import time
import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ==================== 配置 ====================
FEISHU_APP_ID = "cli_aa9902f04462dcc4"
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

# 飞书多维表格配置
BASE_TOKEN = "MwnabIru0aqK7dsnXYcccI8knZg"

# 表ID
TBL_STUDENTS = "tblpxPK0fKrM2qLT"      # 学生档案
TBL_RECORDS = "tbl5TfujbekzE3rq"       # 行为记录
TBL_HANDOVER = "tblpyHEWQxeE1NRY"      # 值日交接
TBL_REPORTS = "tbleB8oLfHfeQAAR"       # 学生上报
TBL_ACCOUNTS = "tblJpml4bflaPJyr"       # 账号管理

# 学生档案字段ID
FLD_STUDENT_NAME = "fldiJIkQDr"        # 姓名
FLD_STUDENT_ID = "fldFYYmdss"           # 学号
FLD_PASSWORD = "fldoZNTU2T"            # 密码
FLD_HOMEWORK = "fldT95h8LW"            # 作业积分
FLD_HYGIENE = "fldYzEQV9T"             # 卫生积分
FLD_DISCIPLINE = "fldEtIs30P"          # 纪律积分
FLD_SPORTS = "fldu0Qyf8n"              # 体育锻炼积分
FLD_CIVILITY = "fld4jDPOT4"            # 文明行为积分
FLD_OTHER = "fldjONkmbH"               # 其他积分
FLD_STATUS = "fldwPqE0Lw"              # 状态标记
FLD_TOTAL = "fldcwP71ql"               # 总积分(公式)
FLD_BEHAVIORS = "fldz818hKn"           # 行为记录(双向关联)

# 行为记录字段ID
FLD_DATE = "fldkORZUWW"                # 日期
FLD_STUDENT = "fldcff9j3B"             # 学生(关联)
FLD_CATEGORY = "fldkjIyjVk"            # 行为类别
FLD_RULE = "fldOZVHAAO"                # 班规条款
FLD_SCORE = "fldVAYHaAF"               # 分值
FLD_RECORDER = "fldYayQntF"            # 记录人
FLD_REMARK = "fldf4I1tMZ"              # 备注

# 值日交接字段ID
FLD_HANDOVER_DATE = "fldrM8VwvW"       # 日期
FLD_DUTY_MONITOR = "fld8TkGjwd"        # 值日班长
FLD_HANDOVER_SUMMARY = "fldb8CbV9F"    # 值日总结
FLD_PENDING = "fldmPI08Q5"             # 未处理事项
FLD_HANDOVER_NOTE = "fld0tHTkBp"       # 交接备注
FLD_HANDOVER_STATUS = "fldwp6Vh1w"    # 状态

# 学生上报字段ID
FLD_REPORT_DATE = "fldH0T43kU"         # 上报日期
FLD_REPORTER = "fldiSIcY0N"            # 学生姓名
FLD_REPORT_CATEGORY = "fldwDOmVbf"     # 行为类别
FLD_REPORT_DESC = "fldrj3udWF"         # 事迹描述
FLD_REVIEW_STATUS = "fldIj8DoOY"       # 审核状态
FLD_REPORT_SCORE = "fldQK23nsy"        # 分值
FLD_REVIEWER = "fldCiRfTmR"            # 审核人

# 账号管理字段ID
FLD_ACCOUNT_NAME = "fldC0Qj4Lc"        # 姓名
FLD_ACCOUNT = "fld6z3M7V9"             # 账号
FLD_ACCOUNT_PWD = "fldo09NIV0"         # 密码
FLD_ROLE = "fldBUxOZEU"                # 角色
FLD_LINK_ID = "fldCnSJp44"             # 关联学号

# 学生名单（39人）
STUDENT_NAMES = [
    "蒋雨函", "张钰晴", "李宇航", "姚明哲", "蔡悦然", "沈逸宸", "魏锦宸", "汪雨萱",
    "丁以萍", "周韩涵", "周陆云逸", "郑宇涵", "徐佐怡", "汤舒婷", "徐梦漪", "张艺通",
    "王以太", "吴宇浩", "孙泽洋", "李成", "金恒仲", "黄佳丞", "傅雨辰", "陈威吉",
    "仇彦媛", "柴逸山", "沈毅赐", "熊启航", "韩宇程", "邵晗", "齐慧妍", "章毅煊",
    "楼智宸", "沈子欣", "厉胡瑾", "邓永琪", "钱奕辰", "阮镱芠", "王胡彬"
]

# 行为类别映射
CATEGORIES = {
    "作业": "fldT95h8LW",
    "卫生": "fldYzEQV9T",
    "纪律": "fldEtIs30P",
    "体育锻炼": "fldu0Qyf8n",
    "文明行为": "fld4jDPOT4",
    "其他": "fldjONkmbH"
}

CATEGORY_EMOJI = {
    "作业": "📚",
    "卫生": "🧹",
    "纪律": "📏",
    "体育锻炼": "⚽",
    "文明行为": "🌟",
    "其他": "📋"
}

# 字段ID到中文字段名的映射（用于get_field_value读取兼容）
FIELD_ID_TO_NAME = {
    FLD_STUDENT_NAME: "姓名",
    FLD_STUDENT_ID: "学号",
    FLD_PASSWORD: "密码",
    FLD_HOMEWORK: "作业积分",
    FLD_HYGIENE: "卫生积分",
    FLD_DISCIPLINE: "纪律积分",
    FLD_SPORTS: "体育锻炼积分",
    FLD_CIVILITY: "文明行为积分",
    FLD_OTHER: "其他积分",
    FLD_STATUS: "状态标记",
    FLD_TOTAL: "总积分",
    FLD_BEHAVIORS: "行为记录",
    FLD_DATE: "日期",
    FLD_STUDENT: "学生",
    FLD_CATEGORY: "行为类别",
    FLD_RULE: "班规条款",
    FLD_SCORE: "分值",
    FLD_RECORDER: "记录人",
    FLD_REMARK: "备注",
    FLD_HANDOVER_DATE: "日期",
    FLD_DUTY_MONITOR: "值日班长",
    FLD_HANDOVER_SUMMARY: "值日总结",
    FLD_PENDING: "未处理事项",
    FLD_HANDOVER_NOTE: "交接备注",
    FLD_HANDOVER_STATUS: "状态",
    FLD_REPORT_DATE: "上报日期",
    FLD_REPORTER: "学生姓名",
    FLD_REPORT_CATEGORY: "行为类别",
    FLD_REPORT_DESC: "事迹描述",
    FLD_REVIEW_STATUS: "审核状态",
    FLD_REPORT_SCORE: "分值",
    FLD_REVIEWER: "审核人",
    FLD_ACCOUNT_NAME: "姓名",
    FLD_ACCOUNT: "账号",
    FLD_ACCOUNT_PWD: "密码",
    FLD_ROLE: "角色",
    FLD_LINK_ID: "关联学号",
}

def convert_field_ids_to_names(fields_dict):
    """将fields字典中的field_id key转为field_name key（用于写入飞书API）"""
    result = {}
    for key, value in fields_dict.items():
        # 如果key已经是中文字段名，直接保留
        if key not in FIELD_ID_TO_NAME.values():
            field_name = FIELD_ID_TO_NAME.get(key, key)
        else:
            field_name = key
        result[field_name] = value
    return result

# ==================== 缓存数据结构 ====================
class DataCache:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_refresh = None
        self.is_refreshing = False
        
        # 学生数据缓存
        self.students = {}           # {record_id: student_data}
        self.students_by_name = {}   # {name: record_id}
        self.record_id_to_name = {}  # {record_id: name}
        
        # 行为记录缓存
        self.behavior_records = []   # 所有行为记录
        
        # 预计算结果缓存
        self.leaderboard = []        # 排行榜
        self.radar_data = {}         # {name: radar_data}
        self.warnings = []           # 预警名单
        self.trend_data = {}         # {name: [21天积分列表]}
        self.teacher_stats = {}      # 教师看板统计
        
        # token缓存
        self.tenant_token = None
        self.token_expires_at = 0

cache = DataCache()

# ==================== 飞书API工具函数 ====================
def get_tenant_token():
    """获取tenant_access_token，缓存2小时"""
    now = time.time()
    if cache.tenant_token and cache.token_expires_at > now + 300:
        return cache.tenant_token
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        result = resp.json()
        if result.get("code") == 0:
            cache.tenant_token = result["tenant_access_token"]
            cache.token_expires_at = now + result.get("expire", 7200)
            return cache.tenant_token
    except Exception as e:
        print(f"获取token失败: {e}")
    return None

def feishu_headers():
    """获取飞书API请求头"""
    token = get_tenant_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def get_records(table_id, page_size=500, filter_conditions=None):
    """分页获取表格所有记录"""
    all_records = []
    page_token = None
    
    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records"
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        if filter_conditions:
            params["filter"] = filter_conditions
        
        try:
            resp = requests.get(url, headers=feishu_headers(), params=params, timeout=30)
            result = resp.json()
            
            if result.get("code") != 0:
                print(f"获取记录失败: {result}")
                break
            
            items = result.get("data", {}).get("items", [])
            all_records.extend(items)
            
            if not result.get("data", {}).get("has_more"):
                break
            page_token = result.get("data", {}).get("page_token")
            
        except Exception as e:
            print(f"获取记录异常: {e}")
            break
    
    return all_records

def create_record(table_id, fields):
    """创建单条记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records"
    # 将field_id转为field_name（飞书写入API需要中文字段名）
    fields_converted = convert_field_ids_to_names(fields.get("fields", fields))
    data = {"fields": fields_converted}
    
    try:
        resp = requests.post(url, headers=feishu_headers(), json=data, timeout=30)
        result = resp.json()
        return result.get("code") == 0, result
    except Exception as e:
        print(f"创建记录失败: {e}")
        return False, {"msg": str(e)}

def batch_create_records(table_id, records):
    """批量创建记录，每批不超过10条"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records/batch_create"
    
    results = []
    for i in range(0, len(records), 10):
        batch = records[i:i+10]
        try:
            resp = requests.post(url, headers=feishu_headers(), json={"records": batch}, timeout=30)
            result = resp.json()
            if result.get("code") == 0:
                results.extend(result.get("data", {}).get("records", []))
            else:
                print(f"批量创建失败: {result}")
        except Exception as e:
            print(f"批量创建异常: {e}")
    
    return results

def update_record(table_id, record_id, fields):
    """更新记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records/{record_id}"
    # 将field_id转为field_name（飞书写入API需要中文字段名）
    fields_converted = convert_field_ids_to_names(fields)
    data = {"fields": fields_converted}
    
    try:
        resp = requests.put(url, headers=feishu_headers(), json=data, timeout=30)
        result = resp.json()
        return result.get("code") == 0, result
    except Exception as e:
        print(f"更新记录失败: {e}")
        return False, {"msg": str(e)}

def batch_update_records(table_id, record_ids, fields):
    """批量更新记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_TOKEN}/tables/{table_id}/records/batch_update"
    # 将field_id转为field_name（飞书写入API需要中文字段名）
    fields_converted = convert_field_ids_to_names(fields)
    data = {
        "record_id_list": record_ids,
        "fields": fields_converted
    }
    
    try:
        resp = requests.patch(url, headers=feishu_headers(), json=data, timeout=30)
        result = resp.json()
        return result.get("code") == 0, result
    except Exception as e:
        print(f"批量更新失败: {e}")
        return False, {"msg": str(e)}

# ==================== 数据处理工具函数 ====================
def parse_timestamp(val):
    """解析飞书时间戳为日期字符串"""
    if not val:
        return None
    try:
        # 飞书datetime是Unix毫秒时间戳
        ts = int(val) / 1000
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except:
        return val

def get_field_value(record, field_id):
    """安全获取字段值，自动兼容field_id和field_name两种key，自动解包数组"""
    fields = record.get("fields", {})
    
    # 1. 优先尝试直接用field_id作为key（某些API调用可能返回ID为key）
    val = fields.get(field_id)
    if val is not None:
        # 自动解包单元素数组（飞书单选/下拉字段返回["值"]格式）
        if isinstance(val, list) and len(val) == 1:
            return val[0]
        return val
    
    # 2. 再尝试用field_name作为key（默认API返回name为key）
    field_name = FIELD_ID_TO_NAME.get(field_id, "")
    if field_name:
        val = fields.get(field_name)
        if val is not None:
            # 自动解包单元素数组
            if isinstance(val, list) and len(val) == 1:
                return val[0]
    
    return val if val is not None else None

def get_linked_name(record_id):
    """通过record_id获取学生姓名"""
    return cache.record_id_to_name.get(record_id, "未知")

def parse_linked_records(val):
    """解析关联字段，返回record_id列表"""
    if isinstance(val, list):
        return [item.get("record_id") for item in val if isinstance(item, dict)]
    return []

# ==================== 预计算函数 ====================
def calculate_leaderboard():
    """计算排行榜"""
    students = []
    for record_id, student in cache.students.items():
        total = get_field_value(student, FLD_TOTAL) or 0
        students.append({
            "record_id": record_id,
            "name": student.get("name", ""),
            "total": float(total),
            "homework": float(get_field_value(student, FLD_HOMEWORK) or 0),
            "hygiene": float(get_field_value(student, FLD_HYGIENE) or 0),
            "discipline": float(get_field_value(student, FLD_DISCIPLINE) or 0),
            "sports": float(get_field_value(student, FLD_SPORTS) or 0),
            "civil": float(get_field_value(student, FLD_CIVILITY) or 0),
            "other": float(get_field_value(student, FLD_OTHER) or 0),
            "status": get_field_value(student, FLD_STATUS) or "正常"
        })
    
    # 按总积分排序
    students.sort(key=lambda x: x["total"], reverse=True)
    
    # 添加排名
    for i, s in enumerate(students):
        s["rank"] = i + 1
    
    return students

def calculate_radar_data():
    """计算每个学生的六维度雷达图数据
    基线为50（等边六边形），加分>50，减分<50，越减分越靠近中心
    """
    radar_data = {}
    
    for record_id, student in cache.students.items():
        name = student.get("name", "")
        if not name:
            continue
        
        # 原始积分值
        homework = float(get_field_value(student, FLD_HOMEWORK) or 0)
        hygiene = float(get_field_value(student, FLD_HYGIENE) or 0)
        discipline = float(get_field_value(student, FLD_DISCIPLINE) or 0)
        sports = float(get_field_value(student, FLD_SPORTS) or 0)
        civil = float(get_field_value(student, FLD_CIVILITY) or 0)
        other = float(get_field_value(student, FLD_OTHER) or 0)
        
        # 映射到0-100，基线50：原始分+50，clamp到0-100
        radar_data[name] = {
            "homework": max(0, min(100, 50 + homework)),
            "hygiene": max(0, min(100, 50 + hygiene)),
            "discipline": max(0, min(100, 50 + discipline)),
            "sports": max(0, min(100, 50 + sports)),
            "civil": max(0, min(100, 50 + civil)),
            "other": max(0, min(100, 50 + other)),
            "raw_homework": homework,
            "raw_hygiene": hygiene,
            "raw_discipline": discipline,
            "raw_sports": sports,
            "raw_civil": civil,
            "raw_other": other,
            "total": homework + hygiene + discipline + sports + civil + other
        }
    
    return radar_data

def calculate_warnings():
    """计算AI预警名单
    1. 直接读取飞书中的状态标记（预警/关注）→ 加入预警名单
    2. 按行为记录计算连续3天零分、作业连续扣分、同类违规≥3次
    """
    warnings = []
    today = datetime.now()
    twenty_one_days_ago = (today - timedelta(days=21)).strftime("%Y-%m-%d")
    
    for record_id, student in cache.students.items():
        name = student.get("name", "")
        if not name:
            continue
        
        status = get_field_value(student, FLD_STATUS) or "正常"
        
        # 获取学生各维度原始积分
        total = float(get_field_value(student, FLD_TOTAL) or 0)
        
        # ========== 规则0: 直接从状态标记读取 ==========
        if status == "预警":
            # 检查是否已添加过
            existing = [w for w in warnings if w["student"] == name]
            if not existing:
                warnings.append({
                    "type": "red",
                    "level": "🔴 红色预警",
                    "student": name,
                    "reason": f"总积分{total}分，已被标记为预警状态"
                })
            continue  # 预警学生不再重复检查
        
        if status == "关注":
            existing = [w for w in warnings if w["student"] == name]
            if not existing:
                warnings.append({
                    "type": "orange",
                    "level": "🟠 橙色关注",
                    "student": name,
                    "reason": f"总积分{total}分，已被标记为关注状态"
                })
            continue  # 关注学生不再重复检查
        
        # ========== 规则1: 连续3天总积分为0 ==========
        # 从今天往前连续查，有记录天数为0或无记录都算
        student_rid = cache.students_by_name.get(name)
        student_records = [
            r for r in cache.behavior_records
            if student_rid and student_rid in parse_linked_records(get_field_value(r, FLD_STUDENT))
        ]
        
        # 按日期分组（最近21天）
        daily_records = {}
        for r in student_records:
            date = parse_timestamp(get_field_value(r, FLD_DATE))
            if date and date >= twenty_one_days_ago:
                if date not in daily_records:
                    daily_records[date] = []
                daily_records[date].append(r)
        
        # 从今天往前数连续3天
        zero_days = 0
        for i in range(7):
            check_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            day_records = daily_records.get(check_date, [])
            day_total = sum(float(get_field_value(r, FLD_SCORE) or 0) for r in day_records)
            if day_total <= 0:
                zero_days += 1
            else:
                break
        
        if zero_days >= 3:
            warnings.append({
                "type": "red",
                "level": "🔴 红色预警",
                "student": name,
                "reason": f"连续{zero_days}天无正向积分",
                "days": zero_days
            })
            continue
        
        # ========== 规则2: 连续3天作业扣分 ==========
        homework_days = 0
        for i in range(7):
            check_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            day_records = daily_records.get(check_date, [])
            hw_records = [r for r in day_records if get_field_value(r, FLD_CATEGORY) == "作业"]
            if hw_records:
                has_negative = any(float(get_field_value(r, FLD_SCORE) or 0) < 0 for r in hw_records)
                if has_negative:
                    homework_days += 1
                else:
                    break
            else:
                homework_days += 1
        
        if homework_days >= 3:
            warnings.append({
                "type": "orange",
                "level": "🟠 橙色预警",
                "student": name,
                "reason": f"连续{homework_days}天作业扣分或无记录",
                "days": homework_days
            })
            continue
        
        # ========== 规则3: 同类行为重复违规≥3次 ==========
        category_violations = {}
        for r in student_records:
            category = get_field_value(r, FLD_CATEGORY)
            score = float(get_field_value(r, FLD_SCORE) or 0)
            if score < 0 and category:
                if category not in category_violations:
                    category_violations[category] = 0
                category_violations[category] += 1
        
        for cat, count in category_violations.items():
            if count >= 3:
                warnings.append({
                    "type": "orange",
                    "level": "🟠 橙色预警",
                    "student": name,
                    "reason": f"近21天{count}次{cat}类违规(扣分)",
                    "count": count
                })
    
    return warnings

def calculate_trend_data():
    """计算21天行为趋势数据"""
    trend_data = {}
    today = datetime.now()
    
    for record_id, student in cache.students.items():
        name = student.get("name", "")
        if not name:
            continue
        
        # 生成21天日期列表
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(20, -1, -1)]
        
        # 筛选该学生的记录（用record_id匹配关联字段）
        student_rid = cache.students_by_name.get(name)
        student_records = [
            r for r in cache.behavior_records
            if student_rid and student_rid in parse_linked_records(get_field_value(r, FLD_STUDENT))
        ]
        
        # 按日期汇总积分
        daily_scores = {}
        for r in student_records:
            date = parse_timestamp(get_field_value(r, FLD_DATE))
            if date:
                score = float(get_field_value(r, FLD_SCORE) or 0)
                daily_scores[date] = daily_scores.get(date, 0) + score
        
        # 构建21天数据（含累计积分）
        cumulative = 0
        daily_list = []
        for date in dates:
            score = daily_scores.get(date, 0)
            cumulative += score
            daily_list.append({
                "date": date[5:],  # MM-DD格式
                "score": score,
                "cumulative": cumulative
            })
        
        trend_data[name] = daily_list
    
    return trend_data

def calculate_teacher_stats():
    """计算教师看板统计"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 当日违规统计
    today_records = [r for r in cache.behavior_records if parse_timestamp(get_field_value(r, FLD_DATE)) == today]
    today_violations = [r for r in today_records if float(get_field_value(r, FLD_SCORE) or 0) < 0]
    
    # 积分分布
    all_totals = [float(get_field_value(s, FLD_TOTAL) or 0) for s in cache.students.values()]
    all_totals.sort(reverse=True)
    
    # 分段统计（更细致的区间，让饼图更明显）
    ranges = {
        "≤-20": 0, "-19~-10": 0, "-9~0": 0, "1~10": 0, "11~20": 0,
        "21~30": 0, "31~40": 0, "41~50": 0, "51~60": 0, "61~70": 0,
        "71~80": 0, ">80": 0
    }
    for t in all_totals:
        if t <= -20:
            ranges["≤-20"] += 1
        elif t <= -10:
            ranges["-19~-10"] += 1
        elif t <= 0:
            ranges["-9~0"] += 1
        elif t <= 10:
            ranges["1~10"] += 1
        elif t <= 20:
            ranges["11~20"] += 1
        elif t <= 30:
            ranges["21~30"] += 1
        elif t <= 40:
            ranges["31~40"] += 1
        elif t <= 50:
            ranges["41~50"] += 1
        elif t <= 60:
            ranges["51~60"] += 1
        elif t <= 70:
            ranges["61~70"] += 1
        elif t <= 80:
            ranges["71~80"] += 1
        else:
            ranges[">80"] += 1
    
    # 行为类别统计（今日）
    category_today = {}
    for r in today_records:
        cat = get_field_value(r, FLD_CATEGORY) or "其他"
        score = float(get_field_value(r, FLD_SCORE) or 0)
        if cat not in category_today:
            category_today[cat] = {"count": 0, "positive": 0, "negative": 0}
        category_today[cat]["count"] += 1
        if score > 0:
            category_today[cat]["positive"] += score
        else:
            category_today[cat]["negative"] += abs(score)
    
    return {
        "today_violations": len(today_violations),
        "today_total_records": len(today_records),
        "total_students": len(cache.students),
        "average_score": sum(all_totals) / len(all_totals) if all_totals else 0,
        "top_score": all_totals[0] if all_totals else 0,
        "low_score": all_totals[-1] if all_totals else 0,
        "score_distribution": ranges,
        "category_today": category_today
    }

# ==================== 缓存刷新主函数 ====================
def refresh_cache():
    """刷新所有缓存数据"""
    if cache.is_refreshing:
        return False
    
    cache.is_refreshing = True
    
    try:
        print("开始刷新缓存...")
        
        # 1. 加载学生档案
        print("加载学生档案...")
        student_records = get_records(TBL_STUDENTS)
        cache.students = {}
        cache.students_by_name = {}
        cache.record_id_to_name = {}
        
        for record in student_records:
            fields = record.get("fields", {})
            name = get_field_value(record, FLD_STUDENT_NAME) or ""
            record_id = record.get("record_id", "")
            
            student_data = {
                "record_id": record_id,
                "name": name,
                "fields": fields
            }
            cache.students[record_id] = student_data
            if name:
                cache.students_by_name[name] = record_id
                cache.record_id_to_name[record_id] = name
        
        print(f"加载了 {len(cache.students)} 名学生")
        
        # 2. 加载行为记录
        print("加载行为记录...")
        cache.behavior_records = get_records(TBL_RECORDS)
        print(f"加载了 {len(cache.behavior_records)} 条行为记录")
        
        # 3. 预计算所有分析数据
        print("预计算排行榜...")
        cache.leaderboard = calculate_leaderboard()
        
        print("预计算雷达图数据...")
        cache.radar_data = calculate_radar_data()
        
        print("计算预警名单...")
        cache.warnings = calculate_warnings()
        
        print("计算趋势数据...")
        cache.trend_data = calculate_trend_data()
        
        print("计算教师统计...")
        cache.teacher_stats = calculate_teacher_stats()
        
        cache.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"缓存刷新完成! 时间: {cache.last_refresh}")
        
        return True
        
    except Exception as e:
        print(f"刷新缓存失败: {e}")
        return False
    
    finally:
        cache.is_refreshing = False

# ==================== 后台刷新线程 ====================
def background_refresh():
    """后台刷新线程，每10分钟执行一次"""
    def run():
        while True:
            time.sleep(600)  # 10分钟
            refresh_cache()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

# ==================== 登录验证 ====================
def verify_login(username, password):
    """验证登录"""
    # 教师账号
    if username == "jiaoshi" and password == "123":
        return {"role": "teacher", "name": "教师"}
    if username == "qishuang" and password == "123":
        return {"role": "teacher", "name": "祁爽"}
    
    # 值日班长账号
    if username in ["zrbz1", "zrbz2", "zrbz3"] and password == "123":
        return {"role": "monitor", "name": f"值日班长{username[-1]}"}
    
    # 学生账号（学号2026001-2026039）
    if username.startswith("2026") and len(username) == 7:
        # 在学生档案中查找
        for record_id, student in cache.students.items():
            student_id = str(get_field_value(student, FLD_STUDENT_ID) or "")
            if student_id == username and password == "123":
                return {"role": "student", "name": student.get("name", "")}
    
    return None

# ==================== API路由 ====================
@app.route("/")
def index():
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

@app.route("/api/health")
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "last_refresh": cache.last_refresh,
        "is_refreshing": cache.is_refreshing,
        "students_count": len(cache.students),
        "records_count": len(cache.behavior_records)
    })

@app.route("/api/refresh")
def manual_refresh():
    """手动刷新缓存"""
    if cache.is_refreshing:
        return jsonify({"success": False, "message": "正在刷新中..."})
    
    success = refresh_cache()
    return jsonify({"success": success, "message": "刷新成功" if success else "刷新失败"})

@app.route("/api/login", methods=["POST"])
def login():
    """登录验证"""
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    result = verify_login(username, password)
    if result:
        return jsonify({"success": True, **result})
    else:
        return jsonify({"success": False, "message": "账号或密码错误"})

@app.route("/api/student/profile")
def student_profile():
    """获取学生信息+积分+排名"""
    name = request.args.get("name", "")
    if not name:
        return jsonify({"error": "缺少name参数"})
    
    # 从排行榜获取排名信息
    rank_info = None
    for item in cache.leaderboard:
        if item["name"] == name:
            rank_info = item
            break
    
    if not rank_info:
        return jsonify({"error": "学生不存在"})
    
    # 获取雷达图数据
    radar = cache.radar_data.get(name, {})
    
    # 获取预警状态
    warning = None
    for w in cache.warnings:
        if w["student"] == name:
            warning = w
            break
    
    return jsonify({
        "name": name,
        "rank": rank_info["rank"],
        "total": rank_info["total"],
        "homework": rank_info["homework"],
        "hygiene": rank_info["hygiene"],
        "discipline": rank_info["discipline"],
        "sports": rank_info["sports"],
        "civil": rank_info["civil"],
        "other": rank_info["other"],
        "status": rank_info["status"],
        "radar": radar,
        "warning": warning,
        "total_students": len(cache.leaderboard)
    })

@app.route("/api/student/records")
def student_records():
    """获取学生行为记录明细"""
    name = request.args.get("name", "")
    if not name:
        return jsonify({"error": "缺少name参数"})
    
    # 筛选该学生的记录
    records = []
    for r in cache.behavior_records:
        linked_ids = parse_linked_records(get_field_value(r, FLD_STUDENT))
        if name in [cache.record_id_to_name.get(rid, "") for rid in linked_ids]:
            records.append({
                "date": parse_timestamp(get_field_value(r, FLD_DATE)),
                "category": get_field_value(r, FLD_CATEGORY),
                "rule": get_field_value(r, FLD_RULE) or "",
                "score": float(get_field_value(r, FLD_SCORE) or 0),
                "recorder": get_field_value(r, FLD_RECORDER) or "",
                "remark": get_field_value(r, FLD_REMARK) or ""
            })
    
    # 按日期排序
    records.sort(key=lambda x: x["date"] or "", reverse=True)
    
    return jsonify({"records": records[:50]})  # 最多返回50条

@app.route("/api/student/radar")
def student_radar():
    """获取六维度雷达图数据"""
    name = request.args.get("name", "")
    if not name:
        return jsonify({"error": "缺少name参数"})
    
    radar = cache.radar_data.get(name, {})
    return jsonify(radar)

@app.route("/api/leaderboard")
def leaderboard():
    """获取全班排行榜"""
    return jsonify({"leaderboard": cache.leaderboard})

@app.route("/api/student/report", methods=["POST"])
def submit_report():
    """提交上报"""
    data = request.get_json()
    reporter = data.get("reporter", "")
    category = data.get("category", "")
    description = data.get("description", "")
    score = float(data.get("score", 0))
    
    # 获取当前日期
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 创建上报记录
    fields = {
        FLD_REPORT_DATE: int(time.time() * 1000),  # 毫秒时间戳
        FLD_REPORTER: reporter,
        FLD_REPORT_CATEGORY: category,
        FLD_REPORT_DESC: description,
        FLD_REVIEW_STATUS: "待审核",
        FLD_REPORT_SCORE: score,
        FLD_REVIEWER: ""
    }
    
    success, result = create_record(TBL_REPORTS, {"fields": fields})
    
    if success:
        return jsonify({"success": True, "message": "上报成功，等待值日班长审核"})
    else:
        return jsonify({"success": False, "message": f"上报失败: {result.get('msg', '未知错误')}"})

@app.route("/api/monitor/pending-reports")
def pending_reports():
    """获取待审核列表"""
    records = get_records(TBL_REPORTS)
    pending = []
    
    for r in records:
        status = get_field_value(r, FLD_REVIEW_STATUS)
        if status == "待审核":
            pending.append({
                "record_id": r.get("record_id", ""),
                "date": parse_timestamp(get_field_value(r, FLD_REPORT_DATE)),
                "reporter": get_field_value(r, FLD_REPORTER),
                "category": get_field_value(r, FLD_REPORT_CATEGORY),
                "description": get_field_value(r, FLD_REPORT_DESC),
                "score": float(get_field_value(r, FLD_REPORT_SCORE) or 0)
            })
    
    # 按日期倒序
    pending.sort(key=lambda x: x["date"] or "", reverse=True)
    
    return jsonify({"pending": pending})

@app.route("/api/monitor/approve-report", methods=["POST"])
def approve_report():
    """审核通过 - 联动创建行为记录+更新积分"""
    data = request.get_json()
    report_record_id = data.get("report_record_id", "")
    reviewer = data.get("reviewer", "")
    
    # 1. 更新上报状态
    success1, _ = update_record(TBL_REPORTS, report_record_id, {
        FLD_REVIEW_STATUS: "已通过",
        FLD_REVIEWER: reviewer
    })
    
    if not success1:
        return jsonify({"success": False, "message": "更新上报状态失败"})
    
    # 2. 获取上报详情
    records = get_records(TBL_REPORTS)
    report_record = None
    for r in records:
        if r.get("record_id") == report_record_id:
            report_record = r
            break
    
    if not report_record:
        return jsonify({"success": False, "message": "未找到上报记录"})
    
    reporter = get_field_value(report_record, FLD_REPORTER)
    category = get_field_value(report_record, FLD_REPORT_CATEGORY)
    description = get_field_value(report_record, FLD_REPORT_DESC)
    score = float(get_field_value(report_record, FLD_REPORT_SCORE) or 0)
    
    # 3. 获取学生record_id
    student_record_id = cache.students_by_name.get(reporter)
    if not student_record_id:
        return jsonify({"success": False, "message": f"未找到学生: {reporter}"})
    
    # 4. 创建行为记录
    today = int(time.time() * 1000)
    behavior_fields = {
        FLD_DATE: today,
        FLD_STUDENT: [{"record_id": student_record_id}],  # 关联字段格式
        FLD_CATEGORY: category,
        FLD_RULE: description,
        FLD_SCORE: score,
        FLD_RECORDER: reviewer,
        FLD_REMARK: "学生自主上报"
    }
    
    success2, _ = create_record(TBL_RECORDS, {"fields": behavior_fields})
    
    if not success2:
        return jsonify({"success": False, "message": "创建行为记录失败"})
    
    # 5. 刷新缓存
    refresh_cache()
    
    return jsonify({"success": True, "message": f"已通过 {reporter} 的 {category} 上报"})

@app.route("/api/monitor/reject-report", methods=["POST"])
def reject_report():
    """审核驳回"""
    data = request.get_json()
    report_record_id = data.get("report_record_id", "")
    reviewer = data.get("reviewer", "")
    
    success, _ = update_record(TBL_REPORTS, report_record_id, {
        FLD_REVIEW_STATUS: "已驳回",
        FLD_REVIEWER: reviewer
    })
    
    return jsonify({"success": success, "message": "已驳回" if success else "操作失败"})

@app.route("/api/monitor/record", methods=["POST"])
def add_record():
    """录入行为记录"""
    data = request.get_json()
    student_name = data.get("student_name", "")
    category = data.get("category", "")
    rule = data.get("rule", "")
    score = float(data.get("score", 0))
    recorder = data.get("recorder", "")
    remark = data.get("remark", "")
    
    # 获取学生record_id
    student_record_id = cache.students_by_name.get(student_name)
    if not student_record_id:
        return jsonify({"success": False, "message": f"未找到学生: {student_name}"})
    
    today = int(time.time() * 1000)
    fields = {
        FLD_DATE: today,
        FLD_STUDENT: [{"record_id": student_record_id}],
        FLD_CATEGORY: category,
        FLD_RULE: rule,
        FLD_SCORE: score,
        FLD_RECORDER: recorder,
        FLD_REMARK: remark
    }
    
    success, _ = create_record(TBL_RECORDS, {"fields": fields})
    
    if success:
        refresh_cache()
        return jsonify({"success": True, "message": "录入成功"})
    else:
        return jsonify({"success": False, "message": "录入失败"})

@app.route("/api/monitor/handover", methods=["POST"])
def submit_handover():
    """值日交接"""
    data = request.get_json()
    duty_monitor = data.get("duty_monitor", "")
    summary = data.get("summary", "")
    pending = data.get("pending", "")
    note = data.get("note", "")
    
    today = int(time.time() * 1000)
    fields = {
        FLD_HANDOVER_DATE: today,
        FLD_DUTY_MONITOR: duty_monitor,
        FLD_HANDOVER_SUMMARY: summary,
        FLD_PENDING: pending,
        FLD_HANDOVER_NOTE: note,
        FLD_HANDOVER_STATUS: "已处理"
    }
    
    success, _ = create_record(TBL_HANDOVER, {"fields": fields})
    
    return jsonify({"success": success, "message": "交接完成" if success else "交接失败"})

@app.route("/api/teacher/dashboard")
def teacher_dashboard():
    """教师看板"""
    return jsonify({
        "stats": cache.teacher_stats,
        "warnings": cache.warnings,
        "leaderboard_top10": cache.leaderboard[:10]
    })

@app.route("/api/teacher/warnings")
def get_warnings():
    """预警名单详情"""
    return jsonify({"warnings": cache.warnings})

@app.route("/api/teacher/student-detail")
def student_detail():
    """单个学生21天详情"""
    name = request.args.get("name", "")
    if not name:
        return jsonify({"error": "缺少name参数"})
    
    trend = cache.trend_data.get(name, [])
    radar = cache.radar_data.get(name, {})
    
    return jsonify({
        "name": name,
        "trend": trend,
        "radar": radar
    })

@app.route("/api/teacher/score-trend")
def score_trend():
    """全班近21天加扣分趋势"""
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(20, -1, -1)]
    
    daily_positive = {}
    daily_negative = {}
    for d in dates:
        daily_positive[d] = 0
        daily_negative[d] = 0
    
    for r in cache.behavior_records:
        date = parse_timestamp(get_field_value(r, FLD_DATE))
        if date and date in daily_positive:
            score = float(get_field_value(r, FLD_SCORE) or 0)
            if score > 0:
                daily_positive[date] += score
            elif score < 0:
                daily_negative[date] += abs(score)
    
    result = []
    for d in dates:
        result.append({
            "date": d[5:],  # MM-DD
            "positive": daily_positive[d],
            "negative": daily_negative[d]
        })
    
    return jsonify({"trend": result})

@app.route("/api/teacher/export")
def export_csv():
    """导出CSV"""
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    
    # 构建CSV内容
    lines = ["学号,姓名,总积分,作业,卫生,纪律,体育,文明,其他,状态"]
    for item in cache.leaderboard:
        record_id = item["record_id"]
        student = cache.students.get(record_id, {})
        fields = student.get("fields", {})
        student_id = fields.get(FLD_STUDENT_ID, "")
        
        lines.append(f"{student_id},{item['name']},{item['total']},{item['homework']},{item['hygiene']},{item['discipline']},{item['sports']},{item['civil']},{item['other']},{item['status']}")
    
    csv_content = "\n".join(lines)
    
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=class_scores_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# ==================== 启动 ====================
if __name__ == "__main__":
    print("正在初始化数据缓存...")
    refresh_cache()
    print("启动后台刷新线程...")
    background_refresh()
    print("启动Flask服务...")
    app.run(host="0.0.0.0", port=5000, debug=True)
