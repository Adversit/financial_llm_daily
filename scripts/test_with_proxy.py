"""
使用代理测试Playwright采集

测试访问BBC News（通过代理）
"""
import asyncio
import os

# 设置代理环境变量
os.environ['PLAYWRIGHT_PROXY'] = 'http://127.0.0.1:7890'

from src.crawlers.browser_pool import BrowserPool


async def test_with_proxy():
    """使用代理测试"""
    print("=" * 60)
    print("Playwright 代理测试")
    print("=" * 60)

    proxy = "http://127.0.0.1:7890"
    print(f"\n使用代理: {proxy}")

    pool = BrowserPool(max_contexts=1, headless=True)
    await pool.start()

    try:
        # 获取带代理的上下文
        print("\n[1] 创建浏览器上下文（使用代理）...")
        context = await pool.get_context(proxy=proxy)
        page = await context.new_page()

        # 测试访问BBC
        print("\n[2] 访问 BBC News...")
        await page.goto("https://www.bbc.com/news", timeout=30000)

        title = await page.title()
        print(f"✓ 页面标题: {title}")

        # 提取一些链接
        print("\n[3] 提取文章链接...")
        links = await page.query_selector_all("a[href*='/news/articles/']")
        print(f"✓ 找到 {len(links)} 个文章链接")

        # 显示前5个链接
        for i, link in enumerate(links[:5], 1):
            href = await link.get_attribute('href')
            text = await link.text_content()
            if text:
                print(f"   {i}. {text[:60]}...")
                print(f"      {href}")

        # 获取页面内容
        html = await page.content()
        print(f"\n✓ 页面HTML长度: {len(html)} 字符")

        await page.close()
        await pool.close_context(context)

        print("\n" + "=" * 60)
        print("✓ 代理测试成功！")
        print("=" * 60)
        print("\n说明:")
        print("- 成功通过代理访问BBC News")
        print("- 成功提取页面内容")
        print("- Playwright代理功能正常")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(test_with_proxy())
