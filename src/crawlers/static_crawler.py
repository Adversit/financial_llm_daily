# -*- coding: utf-8 -*-
"""
静态网站采集器
使用 requests 采集静态 HTML 页面，并支持站点定制化解析
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseCrawler
from .rss_crawler import RSSCrawler
from .text_extractor import extract_main_text


@dataclass
class SiteRule:
    """站点定制配置"""

    landing_url: Optional[str] = None
    list_selectors: List[str] = field(default_factory=list)
    allow_patterns: Optional[List[str]] = None
    deny_patterns: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    max_links: int = 50
    mode: str = "html"  # 支持 html / rss
    rss_url: Optional[str] = None
    date_selectors: List[tuple[str, Optional[str]]] = field(default_factory=list)
    title_selectors: List[tuple[str, Optional[str]]] = field(default_factory=list)


DEFAULT_LINK_SELECTORS = [
    "article a[href]",
    ".post a[href]",
    ".entry a[href]",
    "[class*='article'] a[href]",
    "[class*='post'] a[href]",
    "h2 a[href]",
    "h3 a[href]",
]

DEFAULT_ALLOW_PATTERNS = [
    "/news",
    "/blog",
    "/press",
    "/story",
    "/article",
]

SITE_RULES: Dict[str, SiteRule] = {
    "openai.com": SiteRule(
        list_selectors=[
            "article a[href]",
            "a[href^='/news/']",
            "a[href^='/blog/']",
            "[data-component='Card'] a[href]",
        ],
        allow_patterns=["/news/", "/blog/"],
        allowed_domains=["openai.com", "www.openai.com"],
        date_selectors=[
            ("meta[property='article:published_time']", "content"),
            ("meta[name='date']", "content"),
            ("time[datetime]", "datetime"),
        ],
    ),
    "blog.google": SiteRule(
        list_selectors=[
            "a[href^='/blog/']",
            "a[href^='/updates/']",
            "article a[href]",
        ],
        allow_patterns=["/blog/", "/updates/", "/articles/"],
        allowed_domains=["blog.google"],
        date_selectors=[
            ("meta[itemprop='datePublished']", "content"),
            ("time[datetime]", "datetime"),
        ],
    ),
    "anthropic.com": SiteRule(
        list_selectors=[
            "a[href^='/news/']",
            "article a[href]",
            "[class*='ArticleCard'] a[href]",
        ],
        allow_patterns=["/news/", "/blog/", "/updates/"],
        allowed_domains=["anthropic.com", "www.anthropic.com"],
        date_selectors=[
            ("meta[property='article:published_time']", "content"),
            ("time[datetime]", "datetime"),
        ],
    ),
    "x.ai": SiteRule(
        list_selectors=[
            "a[href^='/news/']",
            "article a[href]",
            "[class*='news-card'] a[href]",
        ],
        allow_patterns=["/news/", "/blog/"],
        allowed_domains=["x.ai", "www.x.ai"],
        date_selectors=[
            ("meta[property='article:published_time']", "content"),
            ("time[datetime]", "datetime"),
        ],
    ),
    "nvidia.com": SiteRule(
        landing_url="https://nvidianews.nvidia.com/news",
        list_selectors=[
            "a[href*='/news/']",
            ".news-listing__item a[href]",
            ".c-news-list__item a[href]",
        ],
        allow_patterns=["/news/"],
        allowed_domains=["nvidianews.nvidia.com", "www.nvidia.com", "nvidia.com"],
        date_selectors=[
            ("meta[property='article:published_time']", "content"),
            ("meta[name='pubdate']", "content"),
            ("time[datetime]", "datetime"),
        ],
    ),
    "microsoft.com": SiteRule(
        landing_url="https://blogs.microsoft.com/ai/",
        list_selectors=[
            "article a[href]",
            "a[href*='/ai/']",
            ".c-post-list a[href]",
        ],
        allow_patterns=["/ai/", "/ai-blog/"],
        allowed_domains=["blogs.microsoft.com", "www.microsoft.com", "microsoft.com"],
        date_selectors=[
            ("meta[property='article:published_time']", "content"),
            ("meta[name='publish-date']", "content"),
            ("time[datetime]", "datetime"),
        ],
    ),
    "finextra.com": SiteRule(
        list_selectors=[
            ".news-listing a[href]",
            "a[href*='/newsarticle/']",
            "article a[href]",
        ],
        allow_patterns=["/newsarticle/", "/pressarticle/"],
        allowed_domains=["finextra.com", "www.finextra.com"],
        date_selectors=[
            ("meta[property='article:published_time']", "content"),
            ("meta[name='date']", "content"),
            ("time[datetime]", "datetime"),
        ],
    ),
    "savanta.com": SiteRule(
        list_selectors=[
            "a[href*='/industries/financial-services/']",
            ".cards-grid a[href]",
            "article a[href]",
        ],
        allow_patterns=["/industries/financial-services", "/insights/", "/news/"],
        allowed_domains=["savanta.com", "www.savanta.com"],
        date_selectors=[
            ("meta[property='article:published_time']", "content"),
            ("meta[name='date']", "content"),
            ("time[datetime]", "datetime"),
        ],
    ),
    "idc.com": SiteRule(
        mode="rss",
        rss_url="https://www.idc.com/rss/idcpressreleases.xml",
    ),
}


class StaticCrawler(BaseCrawler):
    """静态网站采集器"""

    def __init__(self, source_id: int, source_name: str, source_url: str, parser: Optional[str] = None):
        super().__init__(source_id, source_name, source_url, parser)
        parsed = urlparse(self.source_url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        config_key = (self.source_parser or "").lower() or domain
        template_rule = SITE_RULES.get(config_key) or SITE_RULES.get(domain)
        if template_rule:
            self.site_rule = SiteRule(**asdict(template_rule))
        else:
            self.site_rule = SiteRule()

        # 允许域名缺省时默认当前域名
        if not self.site_rule.allowed_domains:
            base_domain = domain
            self.site_rule.allowed_domains = [base_domain, f"www.{base_domain}"]

        self.request_url = self.site_rule.landing_url or self.source_url
        self._base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else self.source_url

    def fetch(self, since: Optional[datetime] = None) -> List[Dict]:
        """
        从静态网站采集文章

        Args:
            since: 起始时间

        Returns:
            List[Dict]: 文章列表
        """
        try:
            logger.info(f"开始采集静态网站: {self.source_name} ({self.request_url})")

            if self.site_rule.mode == "rss" or self.request_url.lower().endswith((".xml", "/rss")):
                return self._fetch_via_rss(since)

            # 获取列表页
            response = self.fetch_with_retry(self.request_url)
            html = response.text

            # 解析文章链接
            article_urls = self._extract_article_links(html)
            max_links = self.site_rule.max_links or 50
            if len(article_urls) > max_links:
                article_urls = article_urls[:max_links]
            logger.info(f"发现 {len(article_urls)} 个文章链接")

            # 采集每篇文章
            items = []
            for url in article_urls:
                try:
                    item = self._fetch_article(url)
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.error(f"采集文章失败 {url}: {e}", exc_info=True)
                    continue

            logger.info(f"静态网站采集完成: {self.source_name}, 获取 {len(items)} 篇文章")

            # 按时间过滤
            items = self.filter_by_time(items, since)

            self.log_crawl_result(len(items))
            return items

        except Exception as e:
            logger.error(f"静态网站采集失败: {self.source_name} - {e}", exc_info=True)
            self.log_crawl_result(0, 1)
            return []

    def _fetch_via_rss(self, since: Optional[datetime]) -> List[Dict]:
        """部分站点提供 RSS，直接复用 RSSCrawler"""
        rss_url = self.site_rule.rss_url or self.source_url
        logger.info(f"站点配置为 RSS 模式，使用 RSSCrawler: {rss_url}")
        rss_crawler = RSSCrawler(self.source_id, self.source_name, rss_url, self.source_parser)
        return rss_crawler.fetch(since=since)

    def _extract_article_links(self, html: str) -> List[str]:
        """
        从列表页提取文章链接

        Args:
            html: HTML内容

        Returns:
            List[str]: 文章链接列表
        """
        soup = BeautifulSoup(html, "lxml")
        links: List[str] = []

        selectors = list(dict.fromkeys(self.site_rule.list_selectors + DEFAULT_LINK_SELECTORS))

        for selector in selectors:
            elements = soup.select(selector)
            if not elements:
                continue

            for elem in elements:
                href = (elem.get("href") or "").strip()
                url = self._resolve_url(href)
                if not url:
                    continue
                if not self._is_valid_article_url(url):
                    continue
                if url not in links:
                    links.append(url)

            # 如果站点配置了明确的选择器，首个命中即可，不强制继续遍历
            if links and self.site_rule.list_selectors:
                break

        return links

    def _is_valid_article_url(self, url: str) -> bool:
        """
        判断是否为有效的文章URL

        Args:
            url: URL

        Returns:
            bool: 是否有效
        """
        if not url:
            return False

        exclude_patterns = [
            "#",
            "javascript:",
            "mailto:",
            ".jpg",
            ".png",
            ".gif",
            ".pdf",
            ".xml",
            "/tag/",
            "/category/",
            "/author/",
            "/page/",
            "/search",
            "/feed",
        ]

        url_lower = url.lower()
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # 允许的路径关键词
        allow_patterns = self.site_rule.allow_patterns
        if allow_patterns is None:
            allow_patterns = DEFAULT_ALLOW_PATTERNS
        if allow_patterns and not any(pattern in url_lower for pattern in allow_patterns):
            return False

        if self.site_rule.deny_patterns and any(pattern in url_lower for pattern in self.site_rule.deny_patterns):
            return False

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False

        if parsed.netloc and self.site_rule.allowed_domains:
            if not any(parsed.netloc.endswith(domain) for domain in self.site_rule.allowed_domains):
                return False

        return True

    def _resolve_url(self, href: str) -> Optional[str]:
        """标准化文章链接"""
        if not href:
            return None

        href = href.strip()
        if href.startswith("//"):
            href = f"{urlparse(self.request_url).scheme}:{href}"

        if href.startswith("http"):
            normalized = self.normalize_url(href)
        else:
            normalized = self.normalize_url(urljoin(self.request_url, href))

        return normalized

    def _fetch_article(self, url: str) -> Optional[Dict]:
        """
        采集单篇文章

        Args:
            url: 文章URL

        Returns:
            Optional[Dict]: 文章信息
        """
        response = self.fetch_with_retry(url)
        html = response.text

        soup = BeautifulSoup(html, "lxml")

        # 提取标题
        title = self._extract_title(soup)
        if not title:
            logger.debug(f"未找到标题，跳过: {url}")
            return None

        # 提取发布时间
        published_at = self._extract_publish_time(soup)
        if published_at:
            published_at = self._normalize_datetime(published_at)

        # 提取正文
        content_text = extract_main_text(html, url)
        if not content_text or len(content_text.strip()) < 100:
            logger.debug(f"正文过短，跳过: {url}")
            return None

        canonical = soup.find("link", rel="canonical")
        canonical_url = self.normalize_url(canonical["href"]) if canonical and canonical.get("href") else url

        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "title": title,
            "url": url,
            "canonical_url": canonical_url,
            "published_at": published_at,
            "content_text": content_text,
        }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取文章标题"""
        title_selectors = self.site_rule.title_selectors or []

        for selector, attr in title_selectors:
            tag = soup.select_one(selector)
            if tag:
                if attr:
                    value = tag.get(attr, "").strip()
                else:
                    value = tag.get_text(strip=True)
                if value:
                    return value

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            for separator in [" | ", " - ", " – "]:
                if separator in title:
                    title = title.split(separator)[0]
            return title

        return ""

    def _extract_publish_time(self, soup: BeautifulSoup) -> Optional[datetime]:
        """提取发布时间"""
        selectors = self.site_rule.date_selectors + [
            ("meta[property='article:published_time']", "content"),
            ("meta[name='pubdate']", "content"),
            ("meta[name='date']", "content"),
            ("time[datetime]", "datetime"),
        ]

        seen_values: set[str] = set()
        for selector, attr in selectors:
            tag = soup.select_one(selector)
            if not tag:
                continue

            value = tag.get(attr) if attr else tag.get_text(strip=True)
            if not value:
                continue

            value = value.strip()
            if value in seen_values:
                continue
            seen_values.add(value)

            dt = self._parse_datetime(value)
            if dt:
                return dt

        json_ld_dt = self._extract_datetime_from_jsonld(soup)
        if json_ld_dt:
            return json_ld_dt

        return None

    def _parse_datetime(self, value: str) -> Optional[datetime]:
        """解析日期时间字符串"""
        try:
            from dateutil import parser as date_parser

            return date_parser.parse(value)
        except Exception:
            return None

    def _extract_datetime_from_jsonld(self, soup: BeautifulSoup) -> Optional[datetime]:
        """尝试从 JSON-LD 中提取发布时间"""
        scripts = soup.find_all("script", type=re.compile("ld\\+json", re.IGNORECASE))
        for script in scripts:
            try:
                data = json.loads(script.string or "{}")
            except Exception:
                continue

            for value in self._iter_jsonld_dates(data):
                dt = self._parse_datetime(value)
                if dt:
                    return dt
        return None

    def _iter_jsonld_dates(self, data: object) -> Iterable[str]:
        """遍历 JSON-LD 结构中的日期字段"""
        date_keys = {"datePublished", "dateCreated", "dateModified", "uploadDate"}

        if isinstance(data, dict):
            for key, value in data.items():
                if key in date_keys and isinstance(value, str):
                    yield value
                else:
                    yield from self._iter_jsonld_dates(value)
        elif isinstance(data, list):
            for item in data:
                yield from self._iter_jsonld_dates(item)
