# -*- coding: utf-8 -*-
"""
基础采集框架
定义采集器的抽象基类和通用方法
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import random
import requests
from urllib.parse import urlparse, urlunparse
from loguru import logger
from src.config.settings import settings
from src.utils.retry import retry_on_network_error
from src.utils.time_utils import is_within_24h, to_local_naive


# 常用User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


class BaseCrawler(ABC):
    """采集器抽象基类"""

    def __init__(self, source_id: int, source_name: str, source_url: str, parser: Optional[str] = None):
        """
        初始化采集器

        Args:
            source_id: 信息源ID
            source_name: 信息源名称
            source_url: 信息源URL
        """
        self.source_id = source_id
        self.source_name = source_name
        self.source_url = source_url
        self.source_parser = parser or ""
        self.timeout = settings.CRAWL_TIMEOUT_SEC
        self.max_retries = settings.CRAWL_RETRY_TIMES

    @abstractmethod
    def fetch(self, since: Optional[datetime] = None) -> List[Dict]:
        """
        采集信息源

        Args:
            since: 起始时间，仅获取此时间之后的内容

        Returns:
            List[Dict]: 采集结果列表，每个元素包含:
                - title: 标题
                - url: 链接
                - published_at: 发布时间
                - content_text: 正文
                - source_name: 来源名称
        """
        pass

    def random_ua(self) -> str:
        """
        随机获取User-Agent

        Returns:
            str: User-Agent字符串
        """
        return random.choice(USER_AGENTS)

    def normalize_url(self, url: str) -> str:
        """
        URL标准化
        - 移除fragment (#后面的部分)
        - 统一协议为https
        - 移除尾部斜杠

        Args:
            url: 原始URL

        Returns:
            str: 标准化后的URL
        """
        try:
            parsed = urlparse(url)

            # 移除fragment
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/'),
                parsed.params,
                parsed.query,
                ''  # 移除fragment
            ))

            # 优先使用https
            if normalized.startswith('http://'):
                normalized = normalized.replace('http://', 'https://', 1)

            return normalized
        except Exception as e:
            logger.warning(f"URL标准化失败 {url}: {e}")
            return url

    def filter_by_time(self, items: List[Dict], since: Optional[datetime] = None) -> List[Dict]:
        """
        按时间过滤文章（保留24小时内的）

        Args:
            items: 文章列表
            since: 起始时间，如果为None则默认过去24小时

        Returns:
            List[Dict]: 过滤后的文章列表
        """
        normalized_items = []

        if not since:
            # 默认过滤24小时内的
            filtered = [
                item for item in items
                if item.get('published_at') and is_within_24h(item['published_at'])
            ]
        else:
            since_normalized = self._normalize_datetime(since)
            # 按指定时间过滤
            filtered = [
                item for item in items
                if item.get('published_at')
                and self._normalize_datetime(item['published_at']) >= since_normalized
            ]
            normalized_items = filtered

        # 将归一化后的时间写回，便于后续处理保持一致
        if normalized_items:
            for item in normalized_items:
                if item.get('published_at'):
                    item['published_at'] = self._normalize_datetime(item['published_at'])

        logger.info(f"时间过滤: {len(items)} -> {len(filtered)} 篇文章")
        return filtered

    @retry_on_network_error(max_attempts=3)
    def fetch_with_retry(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        带重试的HTTP请求

        Args:
            url: 请求URL
            method: 请求方法
            **kwargs: 其他requests参数

        Returns:
            requests.Response: 响应对象

        Raises:
            requests.RequestException: 请求失败
        """
        # 设置默认headers
        headers = kwargs.pop('headers', {})
        if 'User-Agent' not in headers:
            headers['User-Agent'] = self.random_ua()

        # 设置默认超时
        timeout = kwargs.pop('timeout', self.timeout)

        logger.debug(f"请求 {method} {url}")

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            timeout=timeout,
            **kwargs
        )
        response.raise_for_status()

        return response

    def clean_text(self, text: str) -> str:
        """
        清理文本
        - 移除多余空白
        - 统一换行符

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""

        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 移除多余空白
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]

        return '\n'.join(lines)

    def log_crawl_result(self, success_count: int, fail_count: int = 0):
        """
        记录采集结果

        Args:
            success_count: 成功数量
            fail_count: 失败数量
        """
        logger.info(
            f"[{self.source_name}] 采集完成: "
            f"成功 {success_count} 篇, 失败 {fail_count} 篇"
        )

    def _normalize_datetime(self, dt: datetime) -> datetime:
        """
        将 datetime 转换为 Asia/Shanghai 时区的无时区时间，便于比较
        """
        try:
            return to_local_naive(dt)
        except Exception:
            # 如果无法转换，尝试直接去掉 tzinfo
            return dt.replace(tzinfo=None)
