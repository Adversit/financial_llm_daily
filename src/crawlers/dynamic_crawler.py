"""
动态网页采集器（基于Playwright）
用于采集需要JavaScript渲染的动态网站
"""
import asyncio
import re
import time
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from loguru import logger

from .base import BaseCrawler
from .browser_pool import BrowserPool
from .text_extractor import extract_main_text
from .proxy_strategy import get_proxy_strategy
from src.utils.time_utils import to_local_naive
from src.config.settings import settings


class DynamicCrawler(BaseCrawler):
    """
    动态网页采集器

    特性：
    - 基于Playwright渲染JavaScript动态内容
    - 支持滚动加载
    - 灵活的选择器配置
    - 并发采集详情页
    - 自动提取标题、时间、正文
    """

    def __init__(
        self,
        source_id: int,
        source_name: str,
        source_url: str,
        browser_pool: BrowserPool,
        parser: Optional[str] = None,
        parser_config: Optional[dict] = None,
    ):
        """
        初始化动态采集器

        Args:
            source_id: 信息源ID
            source_name: 信息源名称
            source_url: 信息源URL
            browser_pool: 浏览器池实例
            parser: 解析器名称（保留兼容性）
            parser_config: 解析器配置字典
                {
                    "need_scroll": bool,  # 是否需要滚动加载
                    "link_selectors": List[str],  # 链接选择器
                    "wait_selector": str,  # 等待元素选择器
                    "allow_patterns": List[str],  # URL允许模式
                    "max_links": int,  # 最大链接数
                }
        """
        super().__init__(source_id, source_name, source_url, parser)
        self.browser_pool = browser_pool

        # 解析配置
        self.parser_config = parser_config or {}
        self.need_scroll = self.parser_config.get('need_scroll', False)
        self.link_selectors = self.parser_config.get('link_selectors', [
            'article a[href]',
            'a.title',
            'a[href*="/news/"]',
            'a[href*="/article/"]',
        ])
        self.wait_selector = self.parser_config.get('wait_selector')
        self.allow_patterns = self.parser_config.get('allow_patterns', [])
        self.max_links = self.parser_config.get('max_links', 20)
        self.scroll_times = self.parser_config.get('scroll_times', 3)

        # 初始化代理策略
        proxy_url = settings.PLAYWRIGHT_PROXY if settings.PLAYWRIGHT_PROXY else None
        self.proxy_strategy = get_proxy_strategy(proxy_url=proxy_url, max_failures=3)

    def fetch(self, since: Optional[datetime] = None) -> List[Dict]:
        """
        主采集入口（同步接口，内部调用异步方法）

        Args:
            since: 起始时间，仅获取此时间之后的内容

        Returns:
            List[Dict]: 采集结果列表
        """
        try:
            items = asyncio.run(self._async_fetch(since))
            return items
        except Exception as e:
            logger.error(f"[{self.source_name}] 采集失败: {e}")
            return []

    async def _async_fetch(self, since: Optional[datetime]) -> List[Dict]:
        """
        异步采集流程

        流程：
        1. 访问列表页
        2. 滚动加载（可选）
        3. 提取文章链接
        4. 并发采集详情页
        5. 时间过滤
        """
        context = None
        try:
            # 根据URL智能选择是否使用代理
            proxy = self.proxy_strategy.get_proxy_for_url(self.source_url)
            context = await self.browser_pool.get_context(proxy=proxy)
            page = await context.new_page()

            logger.info(f"[{self.source_name}] 开始访问列表页: {self.source_url}")

            # 1. 访问列表页
            try:
                await page.goto(
                    self.source_url,
                    wait_until='domcontentloaded',
                    timeout=30000
                )
                logger.debug(f"[{self.source_name}] 列表页加载完成")

                # 记录成功
                self.proxy_strategy.record_success(self.source_url)

            except Exception as e:
                logger.error(f"[{self.source_name}] 列表页访问失败: {e}")

                # 记录失败，检查是否需要切换策略
                should_switch = self.proxy_strategy.record_failure(self.source_url)

                if should_switch:
                    # 策略已切换，重试一次
                    logger.info(f"[{self.source_name}] 使用新策略重试...")
                    await page.close()
                    await self.browser_pool.close_context(context)

                    # 使用新策略重新获取代理
                    proxy = self.proxy_strategy.get_proxy_for_url(self.source_url)
                    context = await self.browser_pool.get_context(proxy=proxy)
                    page = await context.new_page()

                    await page.goto(
                        self.source_url,
                        wait_until='domcontentloaded',
                        timeout=30000
                    )
                    logger.info(f"[{self.source_name}] 新策略重试成功")
                    self.proxy_strategy.record_success(self.source_url)
                else:
                    # 不切换策略，直接抛出异常
                    raise

            # 2. 滚动加载（如果需要）
            if self.need_scroll:
                await self._scroll_to_load(page)

            # 3. 提取文章链接
            links = await self._extract_links(page)
            logger.info(f"[{self.source_name}] 提取到 {len(links)} 个链接")

            await page.close()

            if not links:
                logger.warning(f"[{self.source_name}] 未提取到任何链接")
                return []

            # 4. 并发采集详情页（限制并发数）
            items = []
            batch_size = 5  # 每批5个并发
            for i in range(0, len(links), batch_size):
                batch_links = links[i:i + batch_size]
                tasks = [self._fetch_article(context, url) for url in batch_links]
                batch_items = await asyncio.gather(*tasks, return_exceptions=True)

                # 过滤异常结果
                for item in batch_items:
                    if isinstance(item, dict):
                        items.append(item)
                    elif isinstance(item, Exception):
                        logger.debug(f"[{self.source_name}] 采集异常: {item}")

                # 批次间暂停
                await asyncio.sleep(0.5)

            logger.info(f"[{self.source_name}] 成功采集 {len(items)} 篇文章")

            # 5. 时间过滤
            items = self.filter_by_time(items, since)

            return items

        except Exception as e:
            logger.error(f"[{self.source_name}] 采集流程异常: {e}")
            return []

        finally:
            if context:
                await self.browser_pool.close_context(context)

    async def _scroll_to_load(self, page: Page):
        """
        滚动加载动态内容

        Args:
            page: Playwright页面对象
        """
        logger.debug(f"[{self.source_name}] 开始滚动加载...")

        for i in range(self.scroll_times):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            logger.debug(f"[{self.source_name}] 滚动 {i + 1}/{self.scroll_times}")

    async def _extract_links(self, page: Page) -> List[str]:
        """
        从列表页提取文章链接

        Args:
            page: Playwright页面对象

        Returns:
            List[str]: 文章链接列表
        """
        links = []

        for selector in self.link_selectors:
            try:
                elements = await page.query_selector_all(selector)
                logger.debug(f"[{self.source_name}] 选择器 '{selector}' 找到 {len(elements)} 个元素")

                for elem in elements:
                    href = await elem.get_attribute('href')
                    if href:
                        url = self._resolve_url(href)
                        if self._is_valid_article_url(url):
                            links.append(url)

            except Exception as e:
                logger.warning(f"[{self.source_name}] 选择器 '{selector}' 提取失败: {e}")

        # 去重并限制数量
        links = list(dict.fromkeys(links))[:self.max_links]
        return links

    async def _fetch_article(self, context, url: str) -> Optional[Dict]:
        """
        采集单篇文章详情

        Args:
            context: 浏览器上下文
            url: 文章URL

        Returns:
            Optional[Dict]: 文章数据，失败返回None
        """
        page = None
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries:
            try:
                start_time = time.time()
                page = await context.new_page()

                # 访问文章页
                try:
                    await page.goto(
                        url,
                        wait_until='domcontentloaded',
                        timeout=15000
                    )
                    # 记录成功
                    self.proxy_strategy.record_success(url)

                except Exception as goto_error:
                    # 记录失败
                    should_switch = self.proxy_strategy.record_failure(url)

                    if should_switch and retry_count == 0:
                        # 首次失败且需要切换策略，尝试用新策略
                        logger.info(f"[{self.source_name}] 文章页访问失败，切换代理策略重试: {url}")
                        await page.close()

                        # 创建新页面，context已经包含代理设置
                        # 注意：详情页通常与列表页在同一域名，所以会使用相同的策略
                        page = await context.new_page()
                        await page.goto(
                            url,
                            wait_until='domcontentloaded',
                            timeout=15000
                        )
                        self.proxy_strategy.record_success(url)
                    else:
                        raise goto_error

                # 等待关键元素（如果配置了）
                if self.wait_selector:
                    try:
                        await page.wait_for_selector(self.wait_selector, timeout=5000)
                    except PlaywrightTimeout:
                        logger.debug(f"[{self.source_name}] 等待选择器超时: {self.wait_selector}")

                # 获取完整HTML
                html = await page.content()

                # 提取正文
                content_text = extract_main_text(html, url)

                # 提取元数据
                title = await self._extract_title(page)
                if not title:
                    # 尝试从页面提取标题
                    try:
                        title = await page.title()
                    except:
                        title = ''

                published_at = await self._extract_date(page) or datetime.now()

                elapsed = time.time() - start_time
                logger.debug(f"[{self.source_name}] 采集 {url} 成功 ({elapsed:.2f}s)")

                return {
                    'source_id': self.source_id,
                    'source_name': self.source_name,
                    'title': title[:500] if title else '',
                    'url': url,
                    'content_text': content_text,
                    'published_at': published_at,
                    'section': '',
                }

            except PlaywrightTimeout:
                retry_count += 1
                if retry_count > max_retries:
                    logger.warning(f"[{self.source_name}] 超时重试达上限: {url}")
                    return None
                await asyncio.sleep(2 ** retry_count)  # 指数退避

            except Exception as e:
                logger.error(f"[{self.source_name}] 采集失败 {url}: {e}")
                return None

            finally:
                if page:
                    await page.close()

        return None

    async def _extract_title(self, page: Page) -> Optional[str]:
        """
        提取标题

        Args:
            page: Playwright页面对象

        Returns:
            Optional[str]: 标题文本
        """
        selectors = [
            'h1',
            'meta[property="og:title"]',
            'meta[name="twitter:title"]',
            'title',
        ]

        for selector in selectors:
            try:
                if selector.startswith('meta'):
                    elem = await page.query_selector(selector)
                    if elem:
                        content = await elem.get_attribute('content')
                        if content:
                            return content.strip()
                else:
                    text = await page.text_content(selector)
                    if text:
                        return text.strip()
            except:
                continue

        return None

    async def _extract_date(self, page: Page) -> Optional[datetime]:
        """
        提取发布时间

        Args:
            page: Playwright页面对象

        Returns:
            Optional[datetime]: 发布时间
        """
        selectors = [
            'meta[property="article:published_time"]',
            'meta[name="pubdate"]',
            'time[datetime]',
            'time[pubdate]',
        ]

        for selector in selectors:
            try:
                elem = await page.query_selector(selector)
                if not elem:
                    continue

                if selector.startswith('meta'):
                    date_str = await elem.get_attribute('content')
                elif 'time' in selector:
                    date_str = await elem.get_attribute('datetime')
                    if not date_str:
                        date_str = await page.text_content(selector)

                if date_str:
                    parsed_dt = self._parse_datetime(date_str)
                    if parsed_dt:
                        return to_local_naive(parsed_dt)

            except Exception as e:
                logger.debug(f"[{self.source_name}] 日期提取失败: {e}")
                continue

        return None

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        解析日期时间字符串

        Args:
            date_str: 日期字符串

        Returns:
            Optional[datetime]: 解析后的datetime对象
        """
        import dateparser

        try:
            # 使用dateparser解析各种格式
            dt = dateparser.parse(
                date_str,
                settings={
                    'TIMEZONE': 'Asia/Shanghai',
                    'RETURN_AS_TIMEZONE_AWARE': True
                }
            )
            return dt
        except Exception as e:
            logger.debug(f"日期解析失败 '{date_str}': {e}")
            return None

    def _resolve_url(self, url: str) -> str:
        """
        解析相对URL为绝对URL

        Args:
            url: 原始URL

        Returns:
            str: 绝对URL
        """
        if not url:
            return ""

        # 已经是绝对URL
        if url.startswith('http://') or url.startswith('https://'):
            return url

        # 相对URL，拼接base
        return urljoin(self.source_url, url)

    def _is_valid_article_url(self, url: str) -> bool:
        """
        验证URL是否为有效的文章链接

        Args:
            url: URL字符串

        Returns:
            bool: 是否有效
        """
        if not url or not url.startswith('http'):
            return False

        # 检查域名是否匹配
        source_domain = urlparse(self.source_url).netloc
        url_domain = urlparse(url).netloc
        if source_domain != url_domain:
            return False

        # 如果配置了允许模式，检查URL是否匹配
        if self.allow_patterns:
            return any(pattern in url for pattern in self.allow_patterns)

        # 排除常见的非文章链接
        exclude_patterns = [
            '/tag/', '/category/', '/author/',
            '/search', '/login', '/register',
            '.pdf', '.jpg', '.png', '.gif',
        ]
        return not any(pattern in url.lower() for pattern in exclude_patterns)
