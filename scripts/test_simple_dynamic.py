"""
简单的Playwright功能测试
使用example.com作为测试目标
"""
import asyncio
from src.crawlers.browser_pool import BrowserPool
from src.crawlers.dynamic_crawler import DynamicCrawler


async def main():
    """测试基本功能"""
    print("=" * 60)
    print("Playwright 功能测试（使用 example.com）")
    print("=" * 60)

    # 初始化浏览器池
    print("\n[1/4] 初始化浏览器池...")
    pool = BrowserPool(max_contexts=2, headless=True)
    await pool.start()
    print("✓ 浏览器池启动成功")

    try:
        # 创建采集器
        print("\n[2/4] 创建动态采集器...")
        crawler = DynamicCrawler(
            source_id=999,
            source_name="Example Test",
            source_url="https://example.com",
            browser_pool=pool,
            parser_config={
                "need_scroll": False,
                "link_selectors": ["a[href]"],
                "max_links": 5,
            }
        )
        print("✓ 采集器创建成功")

        # 测试访问网页
        print("\n[3/4] 测试访问网页...")
        context = await pool.get_context()
        page = await context.new_page()

        await page.goto("https://example.com", timeout=30000)
        title = await page.title()
        print(f"✓ 成功访问页面: {title}")

        # 获取页面内容
        content = await page.content()
        print(f"✓ 页面内容长度: {len(content)} 字符")

        await page.close()
        await pool.close_context(context)

        # 测试采集流程
        print("\n[4/4] 测试完整采集流程...")
        items = await crawler._async_fetch(since=None)
        print(f"✓ 采集完成，获取 {len(items)} 个结果")

        if items:
            print("\n示例结果:")
            for i, item in enumerate(items[:2], 1):
                print(f"\n{i}. {item.get('title', 'N/A')[:50]}")
                print(f"   URL: {item.get('url', 'N/A')[:60]}")
                print(f"   内容长度: {len(item.get('content_text', ''))} 字符")

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        print("\n清理浏览器资源...")
        await pool.close()
        print("✓ 清理完成")


if __name__ == "__main__":
    asyncio.run(main())
