"""
自定义异常模块
"""


class WorkOrderError(Exception):
    """基础异常类"""
    pass


class WelinkConnectionError(WorkOrderError):
    """Welink 连接失败"""
    pass


class WelinkSearchError(WorkOrderError):
    """Welink 搜索失败"""
    pass


class WelinkChatError(WorkOrderError):
    """Welink 聊天消息读取失败"""
    pass


class ElementNotFoundError(WorkOrderError):
    """UI 元素未找到"""
    pass


class ElementOperationError(WorkOrderError):
    """UI 元素操作失败"""
    pass


class ConfigLoadError(WorkOrderError):
    """配置文件加载失败"""
    pass


class MatchError(WorkOrderError):
    """关键字匹配失败"""
    pass


class TicketSystemError(WorkOrderError):
    """工单系统操作失败"""
    pass


class CheckpointError(WorkOrderError):
    """断点保存/恢复失败"""
    pass
