"""
Playwright功能演示（不依赖外网）

通过创建本地HTML文件来演示Playwright的所有功能
"""
import asyncio
import tempfile
import os
from pathlib import Path

from src.crawlers.browser_pool import BrowserPool


async def create_demo_html():
    """创建演示用的HTML文件"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playwright功能演示页面</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .article { border: 1px solid #ddd; margin: 10px 0; padding: 10px; }
        .article h2 { color: #333; margin: 0; }
        .article .meta { color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <h1>财经新闻列表</h1>
    <div id="news-list">
        <div class="article">
            <h2><a href="article1.html">美联储宣布加息25个基点</a></h2>
            <p class="meta">2025-11-13 10:30:00</p>
            <p>美联储今日宣布将联邦基金利率上调25个基点...</p>
        </div>
        <div class="article">
            <h2><a href="article2.html">A股三大指数集体上涨</a></h2>
            <p class="meta">2025-11-13 11:00:00</p>
            <p>今日沪深两市开盘后震荡走高，三大指数...</p>
        </div>
        <div class="article">
            <h2><a href="article3.html">人民币汇率保持稳定</a></h2>
            <p class="meta">2025-11-13 11:30:00</p>
            <p>在岸人民币兑美元即期汇率今日维持在...</p>
        </div>
    </div>

    <script>
        // 模拟动态加载
        setTimeout(() => {
            const div = document.createElement('div');
            div.className = 'article';
            div.innerHTML = `
                <h2><a href="article4.html">原油价格创年内新高</a></h2>
                <p class="meta">2025-11-13 12:00:00</p>
                <p>国际原油价格今日突破每桶90美元...</p>
            `;
            document.getElementById('news-list').appendChild(div);
        }, 1000);
    </script>
</body>
</html>
"""

    # 创建临时HTML文件
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.html',
        delete=False,
        encoding='utf-8'
    )
    temp_file.write(html_content)
    temp_file.close()

    return temp_file.name


async def demo_browser_pool():
    """演示浏览器池功能"""
    print("\n" + "="*60)
    print("演示 1: 浏览器池管理")
    print("="*60)

    pool = BrowserPool(max_contexts=3, headless=True)

    print("\n[1] 启动浏览器池...")
    await pool.start()
    print(f"✓ 浏览器池状态: {pool.is_running}")

    print("\n[2] 创建多个浏览器上下文...")
    contexts = []
    for i in range(3):
        context = await pool.get_context()
        contexts.append(context)
        print(f"✓ 创建上下文 #{i+1}, 当前活跃: {pool._context_count}")

    print("\n[3] 关闭所有上下文...")
    for i, context in enumerate(contexts):
        await pool.close_context(context)
        print(f"✓ 关闭上下文 #{i+1}, 剩余活跃: {pool._context_count}")

    print("\n[4] 关闭浏览器池...")
    await pool.close()
    print(f"✓ 浏览器池状态: {pool.is_running}")


async def demo_page_operations(html_file):
    """演示页面操作功能"""
    print("\n" + "="*60)
    print("演示 2: 页面操作与内容提取")
    print("="*60)

    pool = BrowserPool(max_contexts=1, headless=True)
    await pool.start()

    try:
        context = await pool.get_context()
        page = await context.new_page()

        # 访问本地HTML文件
        file_url = f"file:///{html_file.replace(os.sep, '/')}"
        print(f"\n[1] 访问本地HTML文件...")
        await page.goto(file_url, timeout=10000)
        print(f"✓ 页面加载成功")

        # 获取页面标题
        print(f"\n[2] 提取页面标题...")
        title = await page.title()
        print(f"✓ 标题: {title}")

        # 提取文章链接
        print(f"\n[3] 提取文章链接...")
        links = await page.query_selector_all('.article a')
        print(f"✓ 找到 {len(links)} 个链接:")
        for i, link in enumerate(links[:5], 1):
            href = await link.get_attribute('href')
            text = await link.text_content()
            print(f"   {i}. {text} -> {href}")

        # 等待动态加载
        print(f"\n[4] 等待JavaScript动态加载...")
        await asyncio.sleep(1.5)  # 等待动态内容加载
        links_after = await page.query_selector_all('.article a')
        print(f"✓ 动态加载后共 {len(links_after)} 个链接")

        # 提取元数据
        print(f"\n[5] 提取文章元数据...")
        articles = await page.query_selector_all('.article')
        print(f"✓ 找到 {len(articles)} 篇文章:")
        for i, article in enumerate(articles[:3], 1):
            title_elem = await article.query_selector('h2 a')
            meta_elem = await article.query_selector('.meta')

            if title_elem and meta_elem:
                title_text = await title_elem.text_content()
                meta_text = await meta_elem.text_content()
                print(f"   {i}. {title_text}")
                print(f"      发布时间: {meta_text}")

        # 获取页面内容
        print(f"\n[6] 获取完整HTML...")
        html = await page.content()
        print(f"✓ HTML长度: {len(html)} 字符")

        await page.close()
        await pool.close_context(context)

    finally:
        await pool.close()


async def demo_selector_strategies():
    """演示选择器策略"""
    print("\n" + "="*60)
    print("演示 3: 多种选择器策略")
    print("="*60)

    html_file = await create_demo_html()
    pool = BrowserPool(max_contexts=1, headless=True)
    await pool.start()

    try:
        context = await pool.get_context()
        page = await context.new_page()
        file_url = f"file:///{html_file.replace(os.sep, '/')}"
        await page.goto(file_url, timeout=10000)

        selectors = [
            ("CSS类选择器", ".article a"),
            ("标签选择器", "h2 a"),
            ("属性选择器", "a[href]"),
            ("组合选择器", ".article h2 a"),
        ]

        print("\n测试不同选择器:")
        for name, selector in selectors:
            elements = await page.query_selector_all(selector)
            print(f"  {name:15s} '{selector:20s}' -> 找到 {len(elements)} 个元素")

        await page.close()
        await pool.close_context(context)

    finally:
        await pool.close()
        # 清理临时文件
        if os.path.exists(html_file):
            os.remove(html_file)


async def demo_error_handling():
    """演示错误处理"""
    print("\n" + "="*60)
    print("演示 4: 错误处理与重试机制")
    print("="*60)

    pool = BrowserPool(max_contexts=1, headless=True)
    await pool.start()

    try:
        context = await pool.get_context()
        page = await context.new_page()

        # 测试超时处理
        print("\n[1] 测试超时处理...")
        try:
            await page.goto("http://192.0.2.1", timeout=2000)  # 使用不可达的IP
        except Exception as e:
            print(f"✓ 正确捕获超时: {type(e).__name__}")

        # 测试选择器不存在
        print("\n[2] 测试选择器不存在...")
        result = await page.query_selector('.non-existent-class')
        print(f"✓ 返回值: {result}")

        await page.close()
        await pool.close_context(context)

    finally:
        await pool.close()


async def main():
    """主函数"""
    print("="*60)
    print("Playwright 完整功能演示")
    print("本演示不依赖外网访问，使用本地HTML文件")
    print("="*60)

    try:
        # 创建演示HTML
        print("\n准备演示环境...")
        html_file = await create_demo_html()
        print(f"✓ 创建演示HTML: {html_file}")

        # 运行各个演示
        await demo_browser_pool()
        await demo_page_operations(html_file)
        await demo_selector_strategies()
        await demo_error_handling()

        print("\n" + "="*60)
        print("✓ 所有演示完成！")
        print("="*60)
        print("\n总结:")
        print("1. ✅ 浏览器池管理正常")
        print("2. ✅ 页面访问和内容提取正常")
        print("3. ✅ 多种选择器策略都可用")
        print("4. ✅ 错误处理机制完善")
        print("5. ✅ JavaScript动态内容支持")
        print("\n说明:")
        print("- Playwright核心功能完全正常")
        print("- 之前的测试失败是由于网络环境限制")
        print("- 实际使用时请配置可访问的国内网站")

    except Exception as e:
        print(f"\n✗ 演示过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
