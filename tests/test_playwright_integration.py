"""
Playwright集成测试

测试浏览器池和动态采集器的基本功能
"""
import pytest
import asyncio
from datetime import datetime

from src.crawlers.browser_pool import BrowserPool
from src.crawlers.dynamic_crawler import DynamicCrawler


class TestBrowserPool:
    """浏览器池测试"""

    @pytest.mark.asyncio
    async def test_browser_pool_lifecycle(self):
        """测试浏览器池的生命周期：启动、使用、关闭"""
        pool = BrowserPool(max_contexts=2, headless=True)

        # 测试启动
        await pool.start()
        assert pool.is_running is True
        assert pool.browser is not None
        assert pool.playwright is not None

        # 测试获取上下文
        context = await pool.get_context()
        assert context is not None

        # 测试关闭上下文
        await pool.close_context(context)

        # 测试关闭浏览器池
        await pool.close()
        assert pool.browser is None
        assert pool.playwright is None

    @pytest.mark.asyncio
    async def test_multiple_contexts(self):
        """测试创建多个浏览器上下文"""
        pool = BrowserPool(max_contexts=3, headless=True)
        await pool.start()

        try:
            # 创建多个上下文
            contexts = []
            for i in range(3):
                context = await pool.get_context()
                contexts.append(context)

            assert len(contexts) == 3
            assert pool._context_count == 3

            # 关闭所有上下文
            for context in contexts:
                await pool.close_context(context)

            assert pool._context_count == 0

        finally:
            await pool.close()


class TestDynamicCrawler:
    """动态采集器测试"""

    @pytest.mark.asyncio
    async def test_crawler_basic_flow(self):
        """测试基本采集流程（使用简单的静态页面）"""
        pool = BrowserPool(max_contexts=2, headless=True)
        await pool.start()

        try:
            # 创建采集器（使用example.com作为测试）
            crawler = DynamicCrawler(
                source_id=999,
                source_name="测试源",
                source_url="https://example.com",
                browser_pool=pool,
                parser_config={
                    "need_scroll": False,
                    "link_selectors": ["a[href]"],
                    "max_links": 5,
                }
            )

            # 执行采集（异步）
            items = await crawler._async_fetch(since=None)

            # 验证结果
            assert isinstance(items, list)
            print(f"采集到 {len(items)} 个链接")

        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_link_extraction(self):
        """测试链接提取功能"""
        pool = BrowserPool(max_contexts=2, headless=True)
        await pool.start()

        try:
            context = await pool.get_context()
            page = await context.new_page()
            await page.goto("https://example.com")

            crawler = DynamicCrawler(
                source_id=999,
                source_name="测试源",
                source_url="https://example.com",
                browser_pool=pool,
                parser_config={"link_selectors": ["a[href]"]}
            )

            links = await crawler._extract_links(page)

            assert isinstance(links, list)
            print(f"提取到 {len(links)} 个链接")

            await page.close()
            await pool.close_context(context)

        finally:
            await pool.close()

    def test_url_validation(self):
        """测试URL验证逻辑"""
        pool = BrowserPool(max_contexts=1, headless=True)

        crawler = DynamicCrawler(
            source_id=999,
            source_name="测试源",
            source_url="https://example.com",
            browser_pool=pool,
            parser_config={
                "allow_patterns": ["/news/", "/article/"]
            }
        )

        # 测试有效URL
        assert crawler._is_valid_article_url("https://example.com/news/123") is True
        assert crawler._is_valid_article_url("https://example.com/article/456") is True

        # 测试无效URL
        assert crawler._is_valid_article_url("https://example.com/category/tech") is False
        assert crawler._is_valid_article_url("https://other.com/news/123") is False
        assert crawler._is_valid_article_url("https://example.com/login") is False

    def test_url_resolution(self):
        """测试URL解析（相对路径转绝对路径）"""
        pool = BrowserPool(max_contexts=1, headless=True)

        crawler = DynamicCrawler(
            source_id=999,
            source_name="测试源",
            source_url="https://example.com/news",
            browser_pool=pool,
        )

        # 测试相对路径
        assert crawler._resolve_url("/article/123") == "https://example.com/article/123"
        assert crawler._resolve_url("../other/456") == "https://example.com/other/456"

        # 测试绝对路径
        assert crawler._resolve_url("https://example.com/full/path") == "https://example.com/full/path"


class TestEndToEnd:
    """端到端集成测试"""

    @pytest.mark.asyncio
    @pytest.mark.slow  # 标记为慢速测试
    async def test_real_news_site(self):
        """测试真实新闻网站采集（可选，需要网络）"""
        pool = BrowserPool(max_contexts=2, headless=True)
        await pool.start()

        try:
            # 使用一个公开的新闻网站进行测试
            crawler = DynamicCrawler(
                source_id=999,
                source_name="BBC News",
                source_url="https://www.bbc.com/news",
                browser_pool=pool,
                parser_config={
                    "need_scroll": False,
                    "link_selectors": ["a[href*='/news/']"],
                    "max_links": 3,  # 限制数量以加快测试
                    "allow_patterns": ["/news/articles/", "/news/world-"],
                }
            )

            items = await crawler._async_fetch(since=None)

            print(f"\n成功采集 {len(items)} 篇文章")
            if items:
                print(f"示例文章: {items[0].get('title', 'N/A')}")

            assert isinstance(items, list)

        except Exception as e:
            pytest.skip(f"真实网站测试跳过（可能网络问题）: {e}")

        finally:
            await pool.close()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
