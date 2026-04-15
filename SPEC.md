# 运维工单录入自动化框架 - 详细设计文档

## 1. 项目概述

### 1.1 项目背景

运维人员在日常工作中需要频繁处理工单，工单相关信息（如截图、错误日志、问题描述）通常通过内部通讯工具（Welink）以群聊形式流转。传统的操作流程是：

1. 收到工单号
2. 在 Welink 中搜索对应工单群
3. 查找群消息中的关键信息
4. 手动将信息填入工单系统

这套流程重复性高、耗时长，亟需自动化改造。

### 1.2 项目目标

构建一个 **运维工单自动化工具**，实现：

- 通过 PyQt5 图形界面管理工单
- 输入工单号，自动在 Welink 中定位对应群
- 自动截图、读取群消息并提取关键信息
- 用户可在界面中挑选要使用的信息
- 自动打开工单系统网页并填充表单

### 1.3 约束与限制

| 约束项 | 说明 |
|--------|------|
| Welink | 桌面客户端，无开放 API，必须使用 Windows UI 自动化 |
| 工单系统 | 华为自研网页系统 |
| 运行平台 | Windows 10/11 |
| 触发方式 | 图形界面操作 |
| 数据存储 | SQLite 本地存储 |

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    PyQt5 GUI (图形界面)                      │
│              工单列表 / 详情 / 收集 / 录单                    │
└─────────────────────┬─────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   Welink 自动化   │     │  工单系统自动化   │
│   (PyWinAuto)   │     │   (Playwright)   │
├─────────────────┤     ├─────────────────┤
│ - WelinkConnector│     │ - TicketBrowser │
│ - WelinkSearch  │     │ - TicketFiller  │
│ - WelinkChat    │     │ - FieldHandlers │
│ - WelinkCollector│    └─────────────────┘
└─────────────────┘
          │
          ▼
┌─────────────────┐
│     SQLite      │
│   (本地存储)     │
├─────────────────┤
│ - workorders   │
│ - screenshots  │
│ - chat_messages│
└─────────────────┘
```

### 2.2 技术栈

| 组件 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| **GUI** | **PyQt5** | >= 5.15 | Python 图形界面 |
| Welink 自动化 | **PyWinAuto** | >= 0.6.8 | Windows UI 自动化 |
| 图像处理 | **Pillow** | >= 10.0 | 截图处理 |
| 工单系统自动化 | **Playwright** | >= 1.40 | Python 异步 API |
| 数据库 | **SQLite** | 内置 | 本地数据存储 |
| 配置管理 | **PyYAML** | >= 6.0 | 配置文件解析 |
| 日志 | **loguru** | >= 3.0 | 现代化日志库 |
| 运行时 | **Python** | 3.10+ | 主语言 |
├─────────────────┤     ├─────────────────┤
│ - 连接Welink窗口 │     │ - 打开工单网页   │
│ - 搜索工单群     │     │ - 定位表单元素   │
│ - 读取群消息     │     │ - 填充文本框     │
│ - 关键字匹配     │     │ - 处理下拉框     │
│ - 消息提取       │     │ - 处理弹窗选择   │
└─────────────────┘     └─────────────────┘
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
            ┌─────────────────┐
            │   配置加载器     │
            │  (keywords.yaml │
            │  field-mapping) │
            └─────────────────┘
```

### 2.2 技术栈

| 组件 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| Welink 自动化 | **PyWinAuto** | >= 0.6.8 | Windows UI 自动化 |
| 图像识别 (备用) | **Tesseract OCR** | - | 当 UI 元素无法定位时使用 |
| 工单系统自动化 | **Playwright** | >= 1.40 | Python 异步 API |
| 配置管理 | **PyYAML** | >= 6.0 | 配置文件解析 |
| 日志 | **loguru** | >= 3.0 | 现代化日志库 |
| 运行时 | **Python** | 3.10+ | 主语言 |

---

## 3. 功能模块设计

### 3.1 配置管理模块

#### 3.1.1 关键字配置 (keywords.yaml)

```yaml
# 关键字配置
# 支持正则表达式，以 / 开头和结尾

keywords:
  # 问题类型关键词
  problem_types:
    - "/服务器.*故障/"
    - "/网络.*中断/"
    - "/数据库.*异常/"

  # 优先级关键词
  priority:
    - "/P1/"
    - "/P2/"
    - "/紧急/"
    - "/严重/"

  # IP/主机名
  host_patterns:
    - "/\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b/"  # IP 地址
    - "/[A-Z]{2,4}-[A-Z]{2,4}-\\d{2,}/"                    # 主机名格式

  # 工单相关
  ticket_refs:
    - "/工单[：:]\\s*(\\w+)/"
    - "/ITSM-\\d+/"
```

#### 3.1.2 字段映射配置 (field-mapping.yaml)

```yaml
# 工单系统字段映射配置
# field_type: text | dropdown | popup | checkbox

ticket_system:
  url: "http://itsm.company.com"  # 工单系统 URL
  login_required: true            # 是否需要登录

  # 字段映射列表
  fields:
    - name: "工单号"              # 显示名称
      type: "text"                # 字段类型
      selector: "#ticket-id"     # CSS 选择器
      source: "input"             # 数据来源: input=手动输入, extracted=从消息提取

    - name: "问题类型"
      type: "dropdown"
      selector: "#problem-type"
      source: "extracted"
      extract_key: "problem_type" # 从提取结果中取哪个字段

    - name: "服务器IP"
      type: "text"
      selector: "#server-ip"
      source: "extracted"
      extract_key: "host_ips"

    - name: "优先级"
      type: "dropdown"
      selector: "#priority"
      source: "extracted"
      extract_key: "priority"

    - name: "影响范围"
      type: "popup"              # 点击后弹窗选择
      selector: "#impact-scope"
      popup_selector: ".el-dialog__body .el-select"  # 弹窗内的选择器
      source: "extracted"
      extract_key: "impact_scope"

    - name: "问题描述"
      type: "text"
      selector: "#description"
      source: "extracted"
      extract_key: "description"
      multiline: true            # 多行文本框
```

### 3.2 Welink 自动化模块

#### 3.2.1 WelinkConnector

**职责**：连接 Welink 窗口，建立 UI 自动化会话

```python
class WelinkConnector:
    def connect(self) -> bool:
        """连接到 Welink 主窗口"""

    def get_window(self) -> Application:
        """获取 Welink 窗口对象"""

    def is_connected(self) -> bool:
        """检查连接状态"""
```

**关键实现**：
1. 使用 `pywinauto.Application()` 启动或连接 Welink
2. 通过窗口标题 "Welink" 或进程名定位窗口
3. 处理多窗口情况（主窗口、聊天窗口分离）

#### 3.2.2 WelinkSearch

**职责**：在 Welink 中搜索工单群

```python
class WelinkSearch:
    def search_group(self, ticket_no: str) -> bool:
        """搜索工单群"""

    def select_group(self, group_name: str) -> bool:
        """选择并进入群聊"""
```

**关键实现**：
1. 定位搜索框（通过控件类型或图像识别）
2. 输入工单号
3. 在搜索结果中点击工单群

#### 3.2.3 WelinkChat

**职责**：读取群消息并进行关键字匹配

```python
class WelinkChat:
    def scroll_to_top(self):
        """滚动到顶部加载历史消息"""

    def get_messages(self, count: int = 100) -> List[Message]:
        """获取消息列表"""

    def extract_content(self, message: Message) -> dict:
        """从消息中提取结构化信息"""
```

**关键实现**：
1. 定位消息列表控件
2. 滚动加载历史消息
3. 逐条读取消息内容
4. 通过 OCR 或控件文本获取消息文字

#### 3.2.4 WelinkLocator

**职责**：UI 元素定位策略

```python
class WelinkLocator:
    """定位策略优先级"""
    STRATEGIES = [
        "window_spec",     # pywinauto 窗口规格
        "best_practice",  # 最佳实践（控件类型+文本）
        "image",          # 图像识别（备用）
    ]

    def find_element(self, criteria: dict):
        """根据条件查找元素"""
```

### 3.3 关键字匹配引擎

#### 3.3.1 KeywordMatcher

**职责**：从消息内容中匹配关键字并提取信息

```python
class KeywordMatcher:
    def __init__(self, config: KeywordsConfig):
        """初始化匹配器"""

    def match(self, text: str) -> MatchResult:
        """
        匹配文本
        Returns:
            MatchResult:
                - problem_type: str      # 问题类型
                - priority: str          # 优先级
                - host_ips: List[str]    # IP 列表
                - ticket_refs: List[str] # 引用的工单
                - raw_matches: dict     # 原始匹配结果
        """

    def match_all(self, messages: List[Message]) -> List[MatchResult]:
        """批量匹配消息"""
```

**匹配逻辑**：
1. 遍历所有关键字分类
2. 使用正则表达式匹配
3. 聚合同类型匹配结果
4. 去重和优先级排序

### 3.4 工单系统自动化模块

#### 3.4.1 TicketSystemFiller

**职责**：使用 Playwright 填充工单表单

```python
class TicketSystemFiller:
    def __init__(self, config: FieldMappingConfig):
        """初始化填充器"""

    async def open(self, url: str):
        """打开工单系统页面"""

    async def login(self, username: str, password: str):
        """处理登录（如果需要）"""

    async def fill_field(self, field: FieldConfig, value: any):
        """填充单个字段"""

    async def fill_all(self, data: dict):
        """根据提取的数据填充所有字段"""

    async def submit(self):
        """提交工单"""

    async def close(self):
        """关闭浏览器"""
```

#### 3.4.2 FieldHandlers

**职责**：处理不同类型的表单字段

| 处理类型 | 实现逻辑 |
|----------|----------|
| **text** | 清空文本框 → 输入文本 |
| **dropdown** | 点击下拉框 → 等待选项 → 点击目标选项 |
| **popup** | 点击触发按钮 → 等待弹窗 → 在弹窗内选择 |
| **checkbox** | 点击复选框切换状态 |

### 3.5 数据库模块

#### 3.5.1 Database

**职责**：SQLite 数据库管理，存储工单、截图、聊天记录

```python
class Database:
    # 工单管理
    def create_workorder_simple(self, ticket_no: str, title: str = "") -> int
    def get_workorder(self, ticket_id: int) -> Optional[Dict]
    def get_all_workorders(self, status: Optional[str] = None) -> List[Dict]
    def update_workorder(self, ticket_id: int, **kwargs) -> None
    def update_extracted_data(self, ticket_id: int, data: Dict) -> None

    # 截图管理
    def add_screenshot(self, ticket_id: int, file_path: str, sequence: int) -> int
    def get_screenshots(self, ticket_id: int) -> List[Dict]
    def get_selected_screenshots(self, ticket_id: int) -> List[Dict]

    # 聊天记录管理
    def add_chat_message(self, ticket_id: int, sender: str, content: str, timestamp: str = "") -> int
    def get_chat_messages(self, ticket_id: int) -> List[Dict]
    def get_selected_messages(self, ticket_id: int) -> List[Dict]
```

#### 3.5.2 数据库表结构

| 表名 | 字段 | 说明 |
|------|------|------|
| **workorders** | id, ticket_no, title, status, priority, problem_type, description, host_ips, error_codes, extracted_data, created_at, updated_at | 工单主表 |
| **screenshots** | id, ticket_id, file_path, sequence, selected, note, created_at | 截图表 |
| **chat_messages** | id, ticket_id, sender, content, timestamp, selected, created_at | 聊天记录表 |

### 3.6 GUI 模块

#### 3.6.1 MainWindow

**职责**：主窗口，显示工单列表

```python
class MainWindow(QMainWindow):
    def _refresh_table(self)  # 刷新工单列表
    def _on_add_workorder(self)  # 新建工单
    def _open_workorder_detail(self, ticket_id: int)  # 打开工单详情
```

#### 3.6.2 WorkorderDetailDialog

**职责**：工单详情对话框，显示和编辑工单信息

```python
class WorkorderDetailDialog(QDialog):
    def _load_data(self)  # 加载工单数据
    def _load_screenshots(self)  # 加载截图列表
    def _load_chat_messages(self)  # 加载聊天记录
    def _on_auto_collect(self)  # 自动收集
    def _on_auto_fill(self)  # 自动录单
```

#### 3.6.3 CollectionDialog

**职责**：自动收集对话框，收集 Welink 截图和聊天记录

```python
class CollectionDialog(QDialog):
    def _on_start_collect(self)  # 开始收集
    def _on_screenshots_ready(self, paths: List[str])  # 截图就绪
    def _on_messages_ready(self, messages: List[dict])  # 消息就绪
    def _on_save(self)  # 保存选择的内容
```

#### 3.6.4 AutoFillDialog

**职责**：自动录单对话框，填充工单系统

```python
class AutoFillDialog(QDialog):
    def _load_data(self)  # 加载提取的数据
    def _on_start_fill(self)  # 开始自动录单
```

### 3.7 日志模块

#### 3.7.1 日志配置

```python
# 使用 loguru
logger.add(
    "logs/run_{time}.log",
    rotation="00:00",      # 每天零点轮转
    retention="7 days",    # 保留 7 天
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)
```

#### 3.7.2 日志等级

| 等级 | 用途 |
|------|------|
| DEBUG | 详细流程信息、UI 控件信息 |
| INFO | 主要步骤、匹配结果 |
| WARNING | 无法识别的元素、匹配结果为空 |
| ERROR | 操作失败、需要人工介入 |

---

## 4. 用户交互流程

### 4.1 图形界面操作

```
1. [启动] 运行 python src/gui/app.py 启动 GUI
         │
2. [主界面] 查看工单列表
         │
3. [新建] 点击"新建工单"，输入工单号
         │
4. [收集] 在工单详情页点击"自动收集"
         │    - 连接 Welink
         │    - 搜索工单群
         │    - 截图并显示
         │    - 读取聊天记录
         │    - 用户勾选要保存的内容
         │
5. [保存] 点击"保存选择"，数据存入 SQLite
         │
6. [录单] 点击"自动录单"，自动填充工单系统
         │
7. [完成] 状态更新为 submitted/completed
```

### 4.2 命令行接口（备用）

```bash
# 基本用法
python main.py --ticket-no ITSM-2024-00123

# 指定配置文件
python main.py --ticket-no ITSM-2024-00123 --config ./config

# 仅提取信息（不填充工单系统）
python main.py --ticket-no ITSM-2024-00123 --extract-only

# 调试模式
python main.py --ticket-no ITSM-2024-00123 --debug
```

---

## 5. 错误处理与恢复

### 5.1 错误类型

| 错误类型 | 处理策略 |
|----------|----------|
| Welink 未启动 | 自动尝试启动 Welink |
| 找不到工单群 | 提示用户手动选择，记忆选择结果 |
| 消息读取超时 | 重试 3 次，失败后提示用户 |
| 工单系统无法访问 | 检查网络，提示重试 |
| 表单元素定位失败 | 截图记录，提示用户手动填写该字段 |

### 5.2 断点恢复

```
保存检查点：
- Welink 连接成功 → checkpoint_welink_connected.json
- 进入工单群成功 → checkpoint_group_entered.json
- 消息提取完成   → checkpoint_messages_extracted.json

重启后检测检查点，询问用户是否从断点继续
```

---

## 6. 项目结构

```
workorder-automation/
├── SPEC.md                    # 本文档
├── README.md                  # 使用说明
├── requirements.txt           # Python 依赖
│
├── config/                    # 配置文件
│   ├── keywords.yaml          # 关键字配置
│   ├── field-mapping.yaml     # 字段映射配置
│   └── settings.yaml          # 全局设置
│
├── src/                       # 源代码
│   ├── __init__.py
│   ├── main.py                # 命令行入口（备用）
│   │
│   ├── gui/                   # PyQt5 图形界面
│   │   ├── __init__.py
│   │   ├── app.py            # GUI 入口
│   │   ├── main_window.py    # 主窗口（工单列表）
│   │   ├── collection_dialog.py  # 自动收集对话框
│   │   └── fill_dialog.py    # 自动录单对话框
│   │
│   ├── welink/                # Welink 自动化模块
│   │   ├── __init__.py
│   │   ├── connector.py       # Welink 连接器
│   │   ├── search.py          # 搜索功能
│   │   ├── chat.py            # 聊天消息读取
│   │   ├── locator.py         # UI 元素定位
│   │   └── collector.py       # 数据收集器（截图+消息）
│   │
│   ├── workorder/             # 工单系统自动化
│   │   ├── __init__.py
│   │   ├── browser.py         # Playwright 封装
│   │   ├── filler.py          # 表单填充
│   │   ├── handlers.py        # 字段类型处理器
│   │   └── exporter.py        # 数据导出
│   │
│   ├── core/                  # 核心组件
│   │   ├── __init__.py
│   │   ├── config_loader.py    # 配置加载
│   │   ├── keyword_matcher.py  # 关键字匹配引擎
│   │   ├── logger.py           # 日志配置
│   │   ├── checkpoint.py       # 断点保存/恢复
│   │   └── exceptions.py       # 自定义异常
│   │
│   └── database.py             # SQLite 数据库管理
│
├── logs/                      # 日志目录
├── checkpoints/               # 断点目录
├── data/                      # 数据目录
│   ├── workorder.db          # SQLite 数据库
│   └── screenshots/          # 截图存储
│
└── tests/                     # 测试目录
    ├── __init__.py
    ├── test_keyword_matcher.py
    ├── test_config_loader.py
    └── test_welink_locator.py
```

---

## 7. 验收标准

### 7.1 功能验收

| 功能点 | 验收条件 |
|--------|----------|
| Welink 连接 | 能在 10 秒内连接 Welink 窗口 |
| 群搜索 | 输入工单号能定位到对应群 |
| 消息读取 | 能读取至少最近 100 条消息 |
| 关键字匹配 | 能正确匹配配置中的关键字 |
| 工单填充 | 能自动填充文本框、下拉框 |
| 配置加载 | 能正确解析 YAML 配置文件 |

### 7.2 非功能验收

| 指标 | 要求 |
|------|------|
| 执行时间 | 单工单处理 ≤ 2 分钟 |
| 成功率 | 正常情况下 ≥ 90% |
| 日志完整性 | 全程操作可追溯 |
| 配置灵活性 | 无需修改代码即可调整关键字和字段映射 |

---

## 8. 后续迭代方向

| 优先级 | 迭代内容 |
|--------|----------|
| P1 | 支持批量工单处理 |
| P1 | 图像识别定位（备用定位方案） |
| P2 | 定时任务模式 |
| P2 | 历史工单数据复用 |
| P3 | 可视化界面 |

---

## 9. 附录

### 9.1 Welink UI 控件分析（待补充）

需要在实际环境中使用 Spy++ 或 Inspect 分析 Welink 的窗口结构：

- 主窗口类名
- 搜索框控件类型和 ID
- 消息列表控件结构
- 发送消息框控件

### 9.2 依赖安装

```bash
pip install pywinauto playwright pyyaml loguru
playwright install chromium
```

### 9.3 参考资料

- PyWinAuto 文档: https://pywinauto.readthedocs.io/
- Playwright Python: https://playwright.dev/python/
- Loguru: https://loguru.readthedocs.io/
