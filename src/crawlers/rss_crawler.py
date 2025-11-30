# -*- coding: utf-8 -*-
"""
RSS采集器
从RSS/Atom订阅源采集文章
"""
from typing import List, Dict, Optional
from datetime import datetime
import feedparser
from email.utils import parsedate_to_datetime
from loguru import logger
from .base import BaseCrawler
from .text_extractor import clean_html_tags
from src.utils.time_utils import get_local_now_naive


class RSSCrawler(BaseCrawler):
    """RSS采集器"""

    def fetch(self, since: Optional[datetime] = None) -> List[Dict]:
        """
        从RSS源采集文章

        Args:
            since: 起始时间

        Returns:
            List[Dict]: 文章列表
        """
        try:
            logger.info(f"开始采集RSS: {self.source_name} ({self.source_url})")

            # 获取RSS feed
            response = self.fetch_with_retry(self.source_url)
            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(f"RSS解析警告: {feed.bozo_exception}")

            # 解析条目
            items = []
            for entry in feed.entries:
                try:
                    item = self._parse_entry(entry)
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.error(f"解析RSS条目失败: {e}", exc_info=True)
                    continue

            logger.info(f"RSS采集完成: {self.source_name}, 获取 {len(items)} 篇文章")

            # 按时间过滤
            items = self.filter_by_time(items, since)

            self.log_crawl_result(len(items))
            return items

        except Exception as e:
            logger.error(f"RSS采集失败: {self.source_name} - {e}", exc_info=True)
            self.log_crawl_result(0, 1)
            return []

    def _parse_entry(self, entry) -> Optional[Dict]:
        """
        解析单个RSS条目

        Args:
            entry: feedparser的entry对象

        Returns:
            Optional[Dict]: 解析后的文章信息
        """
        # 提取标题
        title = entry.get('title', '').strip()
        if not title:
            logger.debug("跳过无标题条目")
            return None

        # 提取URL
        url = entry.get('link', '').strip()
        if not url:
            logger.debug(f"跳过无链接条目: {title}")
            return None

        url = self.normalize_url(url)

        # 提取发布时间
        published_at = self._parse_publish_time(entry)

        # 提取内容
        content_text = self._extract_content(entry)

        return {
            'source_id': self.source_id,
            'source_name': self.source_name,
            'title': title,
            'url': url,
            'published_at': published_at,
            'content_text': content_text,
        }

    def _parse_publish_time(self, entry) -> Optional[datetime]:
        """
        解析发布时间

        Args:
            entry: feedparser的entry对象

        Returns:
            Optional[datetime]: 发布时间
        """
        # 先尝试解析字符串字段（包含时区信息）
        for field in ["published", "updated", "created", "pubDate"]:
            value = entry.get(field)
            if value:
                try:
                    dt = parsedate_to_datetime(value)
                    return dt.replace(tzinfo=None)
                except Exception as e:
                    logger.debug(f"时间解析失败 {field}: {e}")
                    continue

        # 尝试多个时间字段
        for time_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
            time_tuple = entry.get(time_field)
            if time_tuple:
                try:
                    dt = datetime(*time_tuple[:6])
                    return dt
                except Exception as e:
                    logger.debug(f"时间解析失败 {time_field}: {e}")
                    continue

        # 如果都没有，返回当前时间
        logger.debug(f"未找到发布时间，使用当前时间: {entry.get('title', '')}")
        return get_local_now_naive()

    def _extract_content(self, entry) -> str:
        """
        提取文章内容

        Args:
            entry: feedparser的entry对象

        Returns:
            str: 文章内容
        """
        content = ""

        # 尝试从多个字段获取内容
        # 优先级: content -> summary -> description
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].get('value', '')
        elif hasattr(entry, 'summary') and entry.summary:
            content = entry.summary
        elif hasattr(entry, 'description') and entry.description:
            content = entry.description

        # 清除HTML标签
        if content:
            content = clean_html_tags(content)
            content = self.clean_text(content)

        return content
