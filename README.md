# 运维工单录入自动化框架

自动化运维工单录入流程，从 Welink 群消息中提取关键信息并填入工单系统。

## 功能特性

- **Welink 群消息获取**: 自动连接 Welink 桌面客户端，搜索工单群，读取历史消息
- **关键字智能匹配**: 支持正则表达式配置，自动识别问题类型、优先级、IP 地址、错误码等
- **工单系统自动填充**: 支持文本框、下拉框、弹窗选择等多种表单字段类型
- **配置化管理**: 关键字和字段映射均通过 YAML 配置文件管理，无需修改代码
- **断点恢复**: 支持断点保存和恢复，中断后可继续执行
- **日志完整**: 全程操作可追溯

## 环境要求

- Windows 10/11
- Python 3.10+
- Welink 桌面客户端
- 网络可访问工单系统

## 安装

```bash
# 克隆或下载项目

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

## 配置

### 1. 关键字配置 (config/keywords.yaml)

```yaml
keywords:
  problem_types:
    - "/服务器.*故障/"
    - "/网络.*中断/"

  priority:
    - "/P1/"
    - "/P2/"
    - "/紧急/"

  host_patterns:
    - "/\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b/"
```

### 2. 字段映射配置 (config/field-mapping.yaml)

```yaml
ticket_system:
  url: "http://itsm.company.com"

  fields:
    - name: "问题类型"
      type: "dropdown"
      selector: "#problem-type"
      source: "extracted"
      extract_key: "problem_type"
```

### 3. 全局设置 (config/settings.yaml)

```yaml
welink:
  window_title: "Welink"
  executable_path: "C:\\Program Files\\Welink\\Welink.exe"

workorder:
  confirm_before_fill: true
```

## 使用方法

### 基本用法

```bash
python main.py --ticket-no ITSM-2024-00123
```

### 仅提取信息（不填充工单系统）

```bash
python main.py --ticket-no ITSM-2024-00123 --extract-only
```

### 跳过确认步骤

```bash
python main.py --ticket-no ITSM-2024-00123 --yes
```

### 调试模式

```bash
python main.py --ticket-no ITSM-2024-00123 --debug
```

## 项目结构

```
workorder-automation/
├── config/                    # 配置文件
│   ├── keywords.yaml          # 关键字配置
│   ├── field-mapping.yaml     # 字段映射配置
│   └── settings.yaml          # 全局设置
├── src/                       # 源代码
│   ├── main.py                # 入口
│   ├── core/                  # 核心组件
│   │   ├── config_loader.py
│   │   ├── keyword_matcher.py
│   │   ├── checkpoint.py
│   │   └── logger.py
│   ├── welink/                # Welink 自动化
│   │   ├── connector.py
│   │   ├── search.py
│   │   ├── chat.py
│   │   └── locator.py
│   └── workorder/             # 工单系统自动化
│       ├── browser.py
│       ├── filler.py
│       ├── handlers.py
│       └── exporter.py
├── logs/                      # 日志目录
├── checkpoints/               # 断点目录
├── data/                      # 导出数据目录
└── requirements.txt
```

## 字段类型说明

| 类型 | 说明 | 配置示例 |
|------|------|----------|
| `text` | 文本框 | `selector: "#field-id"` |
| `dropdown` | 下拉框 | `selector: "#dropdown-id"` |
| `popup` | 弹窗选择 | `selector: "#trigger-btn", popup_selector: ".el-dialog .el-select"` |
| `checkbox` | 复选框 | `selector: "#checkbox-id"` |

## 数据来源

| 来源 | 说明 |
|------|------|
| `input` | 使用配置的默认值 |
| `extracted` | 从 Welink 消息中提取 |

## 注意事项

1. **Welink UI 结构**: 实际使用前需要使用 Spy++ 或 Inspect 工具分析 Welink 的窗口控件结构
2. **工单系统适配**: 需要根据实际工单系统调整 `field-mapping.yaml` 中的选择器
3. **首次运行**: 建议先使用 `--extract-only` 测试关键字匹配效果

## License

MIT
