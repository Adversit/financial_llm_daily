# -*- coding: utf-8 -*-
"""
去重引擎
实现文章去重逻辑
"""
from typing import List, Dict, Optional
from simhash import Simhash
from loguru import logger


class Deduplicator:
    """文章去重器"""

    def __init__(self, hamming_threshold: int = 3):
        """
        初始化去重器

        Args:
            hamming_threshold: 汉明距离阈值，<=该值视为重复
        """
        self.hamming_threshold = hamming_threshold

    def compute_simhash(self, text: str) -> int:
        """
        计算文本的SimHash值

        Args:
            text: 文本内容

        Returns:
            int: SimHash值（有符号64位整数，适配PostgreSQL BIGINT）
        """
        if not text:
            return 0

        # 获取无符号64位SimHash值
        hash_value = Simhash(text).value

        # 转换为有符号64位整数（PostgreSQL BIGINT范围）
        # BIGINT范围: -2^63 到 2^63-1
        # 如果值 > 2^63-1，转换为负数表示
        MAX_BIGINT = 9223372036854775807  # 2^63 - 1
        if hash_value > MAX_BIGINT:
            hash_value = hash_value - 2**64

        return hash_value

    def is_duplicate(self, hash1: int, hash2: int) -> bool:
        """
        判断两个SimHash是否重复

        Args:
            hash1: 第一个SimHash
            hash2: 第二个SimHash

        Returns:
            bool: 是否重复
        """
        if hash1 == 0 or hash2 == 0:
            return False

        # 计算汉明距离
        hamming_distance = bin(hash1 ^ hash2).count('1')
        return hamming_distance <= self.hamming_threshold

    def deduplicate_by_url(self, items: List[Dict], existing_urls: set) -> List[Dict]:
        """
        基于URL去重（一级去重）

        Args:
            items: 文章列表
            existing_urls: 已存在的URL集合

        Returns:
            List[Dict]: 去重后的文章列表
        """
        unique_items = []
        seen_urls = set(existing_urls)

        for item in items:
            url = item.get('url', '')
            if url and url not in seen_urls:
                unique_items.append(item)
                seen_urls.add(url)
            else:
                logger.debug(f"URL重复，跳过: {url}")

        logger.info(f"URL去重: {len(items)} -> {len(unique_items)} 篇文章")
        return unique_items

    def deduplicate_by_simhash(
        self,
        items: List[Dict],
        existing_hashes: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        基于SimHash去重（二级去重）

        Args:
            items: 文章列表
            existing_hashes: 已存在的SimHash列表

        Returns:
            List[Dict]: 去重后的文章列表
        """
        if existing_hashes is None:
            existing_hashes = []

        unique_items = []
        seen_hashes = list(existing_hashes)

        for item in items:
            content = item.get('content_text', '')
            if not content:
                continue

            # 计算SimHash
            simhash_value = self.compute_simhash(content)
            item['simhash'] = simhash_value

            # 检查是否与已有的SimHash重复
            is_dup = False
            for existing_hash in seen_hashes:
                if self.is_duplicate(simhash_value, existing_hash):
                    is_dup = True
                    logger.debug(f"内容重复(SimHash)，跳过: {item.get('title', '')}")
                    break

            if not is_dup:
                unique_items.append(item)
                seen_hashes.append(simhash_value)

        logger.info(f"SimHash去重: {len(items)} -> {len(unique_items)} 篇文章")
        return unique_items

    def generate_dedup_key(self, item: Dict) -> str:
        """
        生成去重键
        基于: 标准化URL + 标题 + 发布时间

        Args:
            item: 文章信息

        Returns:
            str: 去重键
        """
        import hashlib

        url = item.get('canonical_url') or item.get('url', '')
        title = item.get('title', '')
        published_at = str(item.get('published_at', ''))

        key_str = f"{url}|{title}|{published_at}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def deduplicate(
        self,
        items: List[Dict],
        existing_urls: Optional[set] = None,
        existing_hashes: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        完整去重流程
        先URL去重，再SimHash去重

        Args:
            items: 文章列表
            existing_urls: 已存在的URL集合
            existing_hashes: 已存在的SimHash列表

        Returns:
            List[Dict]: 去重后的文章列表
        """
        if not items:
            return []

        logger.info(f"开始去重，原始数量: {len(items)}")

        # 一级去重: URL
        if existing_urls is None:
            existing_urls = set()
        items = self.deduplicate_by_url(items, existing_urls)

        # 二级去重: SimHash
        items = self.deduplicate_by_simhash(items, existing_hashes)

        # 生成去重键
        for item in items:
            item['dedup_key'] = self.generate_dedup_key(item)

        logger.info(f"去重完成，最终数量: {len(items)}")
        return items
