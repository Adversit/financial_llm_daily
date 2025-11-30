"""
时间工具函数
"""
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def get_local_now(naive: bool = False) -> datetime:
    """获取当前时间（默认带时区 Asia/Shanghai）"""
    now = datetime.now(LOCAL_TZ)
    return now.replace(tzinfo=None) if naive else now


def get_local_now_naive() -> datetime:
    """获取当前时间（Asia/Shanghai，去掉时区信息）"""
    return get_local_now(naive=True)


def get_beijing_now() -> datetime:
    """获取当前北京时间"""
    return get_local_now()


def to_local(dt: datetime, naive: bool = False) -> datetime:
    """将时间转换为 Asia/Shanghai 时区"""
    if dt.tzinfo is None:
        localized = dt.replace(tzinfo=LOCAL_TZ)
    else:
        localized = dt.astimezone(LOCAL_TZ)
    return localized.replace(tzinfo=None) if naive else localized


def to_local_naive(dt: datetime) -> datetime:
    """将时间转换为 Asia/Shanghai 时区并去掉时区信息"""
    return to_local(dt, naive=True)


def is_within_24h(dt: datetime) -> bool:
    """
    检查给定时间是否在过去24小时内

    Args:
        dt: 要检查的时间

    Returns:
        bool: 如果在24小时内返回True
    """
    now = get_beijing_now()
    # 确保 dt 有时区信息
    dt = to_local(dt)
    return now - dt <= timedelta(hours=24)


def is_in_time_window(start: str = "06:05", end: str = "06:20") -> bool:
    """
    检查当前时间是否在指定的时间窗口内

    Args:
        start: 开始时间，格式 HH:MM
        end: 结束时间，格式 HH:MM

    Returns:
        bool: 如果在窗口内返回True
    """
    now = get_beijing_now()
    current_time = now.time()

    start_time = time.fromisoformat(start + ":00")
    end_time = time.fromisoformat(end + ":00")

    return start_time <= current_time <= end_time


def format_beijing_time(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化北京时间

    Args:
        dt: datetime对象
        fmt: 格式字符串

    Returns:
        str: 格式化后的时间字符串
    """
    dt = to_local(dt)
    return dt.strftime(fmt)
