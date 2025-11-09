# -*- coding: utf-8 -*-
"""
正文抽取器
使用多种方法抽取网页正文内容
"""
from typing import Optional
import trafilatura
from readability import Document
from bs4 import BeautifulSoup
from loguru import logger


def extract_main_text(html: str, url: str) -> str:
    """
    从HTML中抽取正文
    优先级: trafilatura -> readability-lxml -> BeautifulSoup兜底

    Args:
        html: HTML内容
        url: 网页URL (用于日志)

    Returns:
        str: 抽取的正文
    """
    if not html:
        return ""

    # 方法1: 使用trafilatura (最准确)
    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        if text and len(text.strip()) > 100:
            logger.debug(f"[trafilatura] 成功抽取正文: {url}")
            return text.strip()
    except Exception as e:
        logger.warning(f"[trafilatura] 抽取失败 {url}: {e}")

    # 方法2: 使用readability-lxml
    try:
        doc = Document(html)
        text = doc.summary()
        soup = BeautifulSoup(text, 'lxml')
        text = soup.get_text(separator='\n', strip=True)
        if text and len(text.strip()) > 100:
            logger.debug(f"[readability] 成功抽取正文: {url}")
            return text.strip()
    except Exception as e:
        logger.warning(f"[readability] 抽取失败 {url}: {e}")

    # 方法3: BeautifulSoup兜底 (简单粗暴)
    try:
        soup = BeautifulSoup(html, 'lxml')

        # 移除script、style等标签
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()

        # 尝试找到主要内容区域
        main_content = None
        for selector in ['article', 'main', '[class*="content"]', '[class*="article"]']:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            # 如果找不到特定区域，使用整个body
            body = soup.find('body')
            text = body.get_text(separator='\n', strip=True) if body else ""

        if text and len(text.strip()) > 50:
            logger.debug(f"[BeautifulSoup] 成功抽取正文: {url}")
            return text.strip()
    except Exception as e:
        logger.warning(f"[BeautifulSoup] 抽取失败 {url}: {e}")

    logger.error(f"所有方法都失败，无法抽取正文: {url}")
    return ""


def clean_html_tags(text: str) -> str:
    """
    清除HTML标签，保留纯文本

    Args:
        text: 可能包含HTML标签的文本

    Returns:
        str: 纯文本
    """
    if not text:
        return ""

    try:
        soup = BeautifulSoup(text, 'lxml')
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        logger.warning(f"清除HTML标签失败: {e}")
        return text


def calculate_noise_ratio(text: str, html: str) -> float:
    """
    计算噪声比例
    噪声比 = (HTML长度 - 纯文本长度) / HTML长度

    Args:
        text: 纯文本
        html: HTML内容

    Returns:
        float: 噪声比例 (0-1)
    """
    if not html or not text:
        return 1.0

    text_len = len(text)
    html_len = len(html)

    if html_len == 0:
        return 1.0

    noise_ratio = (html_len - text_len) / html_len
    return max(0.0, min(1.0, noise_ratio))
