# 704班级行为管理系统 v2

基于飞书多维表格的班级行为管理系统，支持学生自主上报、值日班长审核、教师AI预警等功能。

## 功能特性

### 学生端
- 查看个人积分明细（按日期排序）
- 全班积分排行榜（每日自动刷新）
- 六维度雷达图展示（每周自动生成）
- 自主上报行为事迹

### 值日班长端
- 审核学生自主申报（通过/驳回）
- 录入行为记录（加分/扣分）
- 值日交接记录
- 查看最近记录

### 教师端（AI预警系统）
- **智能预警名单**：21天行为时间序列分析
  - 规则1：连续3天积分为零 → 严重预警（红色高亮）
  - 规则2：连续3天作业未交/扣分 → 关注预警
  - 规则3：同一类行为重复违规≥3次 → 关注预警
- 数据看板：指标卡片、积分分布直方图、六维度班级平均雷达图、21天趋势图
- 全班学生列表：可排序、可筛选状态、点击展开详情
- 一键导出周报/月报CSV

## 技术栈

- **后端**：Flask + requests + flask-cors
- **前端**：HTML + CSS + JavaScript + ECharts
- **数据源**：飞书多维表格（Bitable API）
- **部署**：Render.com 免费层

## 部署到 Render.com

### 1. 准备 GitHub 仓库

将本项目所有文件推送到 GitHub 仓库：
```
class-behavior-system/
├── app.py              # Flask主应用
├── requirements.txt    # 依赖
├── Procfile           # Render启动命令
├── runtime.txt        # Python版本
├── templates/
│   ├── login.html
│   ├── student.html
│   ├── monitor.html
│   └── teacher.html
└── static/
    └── style.css
```

### 2. 创建 Render 应用

1. 登录 [Render.com](https://render.com)
2. 点击 **New +** → **Web Service**
3. 连接到你的 GitHub 仓库
4. 配置如下：
   - **Name**: `class-behavior-system`（或其他名称）
   - **Region**: Singapore（亚太区延迟最低）
   - **Branch**: main
   - **Runtime**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free

### 3. 设置环境变量

在 Render 控制台添加环境变量：

| 变量名 | 值 |
|--------|-----|
| `FEISHU_APP_SECRET` | 你的飞书应用 Secret |

**获取方式**：
1. 打开 [飞书开放平台](https://open.feishu.cn/)
2. 进入你的应用 → 凭证与基础信息
3.复制 App Secret

### 4. 部署

点击 **Create Web Service**，等待构建完成（约1-2分钟）。

部署成功后，访问 `https://你的应用名.onrender.com`

## 本地运行

```bash
# 克隆项目
git clone <你的仓库地址>
cd class-behavior-system

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export FEISHU_APP_SECRET="你的飞书App Secret"

# 运行
python app.py
```

访问 `http://localhost:5000`

## 账号说明

所有账号已硬编码到前端（`login.html`中的`accounts`数组）：

| 角色 | 账号 | 密码 | 说明 |
|------|------|------|------|
| 学生 | 2026001~2026039 | 123 | 学号即账号 |
| 值日班长 | zrbz1, zrbz2, zrbz3 | 123 | - |
| 教师 | jiaoshi, qishuang | 123 | - |

## 飞书多维表格配置

确保你的飞书多维表格包含以下表：

1. **学生档案** - 存储学生信息和积分
2. **行为记录** - 存储所有加减分记录
3. **值日交接** - 存储值日班长交接记录
4. **学生上报** - 存储学生自主上报

字段ID和表ID需要在 `app.py` 中正确配置。

## API 接口

### 通用
- `GET /api/health` - 健康检查

### 学生端
- `GET /api/student/profile?name=xxx` - 获取学生信息
- `GET /api/student/records?name=xxx` - 获取行为记录
- `GET /api/student/radar?name=xxx` - 获取雷达图数据
- `GET /api/leaderboard` - 积分排行榜
- `POST /api/student/report` - 提交上报

### 值日班长端
- `POST /api/monitor/record` - 录入行为记录
- `POST /api/monitor/handover` - 提交交接
- `GET /api/monitor/pending-reports` - 待审核列表
- `POST /api/monitor/approve-report` - 审核通过
- `POST /api/monitor/reject-report` - 审核驳回
- `GET /api/monitor/recent-records` - 最近记录

### 教师端
- `GET /api/teacher/dashboard` - 看板数据
- `GET /api/teacher/students` - 学生列表
- `GET /api/teacher/all-records` - 所有记录
- `GET /api/teacher/export?start=xxx&end=xxx` - 导出CSV

## 注意事项

1. 飞书 API 有频率限制，大批量操作请注意
2. 免费版 Render 休眠后会冷启动，约10-30秒
3. 建议定期检查飞书多维表格的字段ID是否正确
4. datetime字段使用Unix毫秒时间戳

## License

MIT
