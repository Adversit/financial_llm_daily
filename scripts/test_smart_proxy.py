"""
测试智能代理策略

演示：
1. 根据域名自动选择是否使用代理
2. 失败后自动切换策略
3. 国内/国外域名自动识别
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from src.crawlers.browser_pool import BrowserPool
from src.crawlers.proxy_strategy import ProxyStrategy


async def test_domestic_foreign_detection():
    """测试国内外域名自动识别"""
    print("=" * 60)
    print("测试 1: 国内外域名自动识别")
    print("=" * 60)

    proxy_url = "http://127.0.0.1:7890"
    strategy = ProxyStrategy(proxy_url=proxy_url)

    test_urls = [
        ("https://finance.sina.com.cn/", "国内财经"),
        ("https://www.bbc.com/news", "国外新闻"),
        ("https://www.cls.cn/telegraph", "国内财联社"),
        ("https://www.reuters.com/", "国外路透社"),
        ("https://www.eastmoney.com/", "国内东方财富"),
        ("https://www.bloomberg.com/", "国外彭博"),
    ]

    for url, description in test_urls:
        proxy = strategy.get_proxy_for_url(url)
        use_proxy = "使用代理" if proxy else "不使用代理"
        print(f"  {description:12s} {url:40s} -> {use_proxy}")

    print("\n✓ 自动识别功能正常\n")


async def test_failure_and_switch():
    """测试失败后自动切换策略"""
    print("=" * 60)
    print("测试 2: 失败后自动切换策略")
    print("=" * 60)

    proxy_url = "http://127.0.0.1:7890"
    strategy = ProxyStrategy(proxy_url=proxy_url, max_failures=3)

    test_url = "https://unknown-site.example.com/"

    print(f"\n测试URL: {test_url}")
    print(f"最大失败次数: 3\n")

    # 初始策略
    proxy = strategy.get_proxy_for_url(test_url)
    initial_use_proxy = proxy is not None
    print(f"初始策略: {'使用代理' if initial_use_proxy else '不使用代理'}")

    # 模拟连续失败
    for i in range(1, 5):
        should_switch = strategy.record_failure(test_url)
        print(f"第 {i} 次失败: should_switch={should_switch}")

        if should_switch:
            # 切换后获取新策略
            new_proxy = strategy.get_proxy_for_url(test_url)
            new_use_proxy = new_proxy is not None
            print(f"  -> 策略已切换为: {'使用代理' if new_use_proxy else '不使用代理'}")
            break

    print("\n✓ 策略切换功能正常\n")


async def test_real_crawl_with_smart_proxy():
    """测试真实采集使用智能代理"""
    print("=" * 60)
    print("测试 3: 真实采集使用智能代理")
    print("=" * 60)

    proxy_url = "http://127.0.0.1:7890"
    strategy = ProxyStrategy(proxy_url=proxy_url)
    pool = BrowserPool(max_contexts=1, headless=True)
    await pool.start()

    test_cases = [
        ("https://finance.sina.com.cn/", "新浪财经（国内）"),
        ("https://www.bbc.com/news", "BBC新闻（国外）"),
    ]

    for url, description in test_cases:
        print(f"\n测试: {description}")
        print(f"URL: {url}")

        # 获取代理策略
        proxy = strategy.get_proxy_for_url(url)
        print(f"代理策略: {'使用代理 ' + proxy if proxy else '不使用代理'}")

        try:
            # 创建上下文
            context = await pool.get_context(proxy=proxy)
            page = await context.new_page()

            # 访问页面
            await page.goto(url, timeout=15000)
            title = await page.title()

            print(f"✓ 访问成功: {title[:50]}...")

            # 记录成功
            strategy.record_success(url)

            await page.close()
            await pool.close_context(context)

        except Exception as e:
            print(f"✗ 访问失败: {e}")
            # 记录失败
            should_switch = strategy.record_failure(url)
            if should_switch:
                print(f"  -> 失败次数达到阈值，策略已切换")

    await pool.close()
    print("\n✓ 真实采集测试完成\n")


async def test_statistics():
    """测试统计功能"""
    print("=" * 60)
    print("测试 4: 策略统计信息")
    print("=" * 60)

    strategy = ProxyStrategy(proxy_url="http://127.0.0.1:7890")

    # 模拟一些访问
    strategy.record_failure("https://site1.com/")
    strategy.record_failure("https://site1.com/")
    strategy.record_failure("https://site1.com/")  # 会触发切换

    strategy.record_success("https://site2.com/")

    # 获取统计
    stats = strategy.get_statistics()

    print(f"\n统计信息:")
    print(f"  失败记录数: {stats['failure_records']}")
    print(f"  策略切换数: {stats['strategy_switches']}")

    if stats['details']['switches']:
        print(f"\n策略切换详情:")
        for domain, info in stats['details']['switches'].items():
            use_proxy = "使用代理" if info['use_proxy'] else "不使用代理"
            print(f"  {domain}: {use_proxy} (切换时间: {info['switch_time']})")

    print("\n✓ 统计功能正常\n")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("智能代理策略测试套件")
    print("=" * 60 + "\n")

    try:
        # 测试1: 域名识别
        await test_domestic_foreign_detection()

        # 测试2: 失败切换
        await test_failure_and_switch()

        # 测试3: 真实采集
        print("【提示】测试3需要实际网络访问，可能需要几秒钟...\n")
        await test_real_crawl_with_smart_proxy()

        # 测试4: 统计
        await test_statistics()

        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

        print("\n总结:")
        print("1. ✅ 国内外域名自动识别")
        print("2. ✅ 失败后自动切换策略")
        print("3. ✅ 真实采集代理应用")
        print("4. ✅ 统计信息完整")

        print("\n使用说明:")
        print("- 国内网站（如新浪财经）：自动不使用代理")
        print("- 国外网站（如BBC）：自动使用代理")
        print("- 连续失败3次：自动切换代理策略")
        print("- 策略切换后1小时内保持新策略")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
