"""
测试动态信息源采集

这个脚本会：
1. 添加一个测试用的动态信息源
2. 触发采集任务
3. 查看采集结果
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from src.db.session import get_db
from src.models.source import Source, SourceType, RegionHint
from src.tasks.crawl_tasks import crawl_dynamic_task
from src.models.article import Article
import json


def add_test_source(db: Session):
    """添加测试用的动态信息源"""

    # 检查是否已存在
    existing = db.query(Source).filter(Source.name == "BBC News 测试").first()
    if existing:
        print(f"✓ 测试源已存在: ID={existing.id}")
        return existing

    # 创建新的测试源
    test_source = Source(
        name="BBC News 测试",
        type=SourceType.DYNAMIC,
        url="https://www.bbc.com/news",
        enabled=True,
        parser_config={
            "need_scroll": False,
            "link_selectors": [
                "a[data-testid*='internal-link']",
                "article a[href]",
                "a[href*='/news/articles/']"
            ],
            "wait_selector": None,
            "allow_patterns": ["/news/articles/", "/news/world-"],
            "max_links": 5,  # 限制为5个链接用于测试
            "scroll_times": 2
        },
        region_hint=RegionHint.FOREIGN,
        concurrency=1,
        timeout_sec=30
    )

    db.add(test_source)
    db.commit()
    db.refresh(test_source)

    print(f"✓ 成功添加测试源: ID={test_source.id}")
    print(f"  名称: {test_source.name}")
    print(f"  URL: {test_source.url}")
    print(f"  配置: {json.dumps(test_source.parser_config, indent=2, ensure_ascii=False)}")

    return test_source


def test_crawl(source_id: int):
    """测试采集"""
    print(f"\n开始测试采集 source_id={source_id}...")
    print("=" * 60)

    try:
        # 执行采集任务
        result = crawl_dynamic_task(source_id)

        print(f"\n采集结果:")
        print(f"  状态: {result.get('status')}")
        print(f"  原始获取: {result.get('fetched', 0)} 篇")
        print(f"  去重后: {result.get('after_dedup', 0)} 篇")
        print(f"  新增保存: {result.get('saved', 0)} 篇")
        print(f"  加入队列: {result.get('queued', 0)} 篇")

        if result.get('status') == 'error':
            print(f"  错误: {result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        print(f"✗ 采集失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_articles(db: Session, source_id: int):
    """检查采集到的文章"""
    articles = db.query(Article).filter(Article.source_id == source_id).all()

    print(f"\n数据库中的文章（共 {len(articles)} 篇）:")
    print("=" * 60)

    for i, article in enumerate(articles[:5], 1):  # 只显示前5篇
        print(f"\n{i}. {article.title[:60]}...")
        print(f"   URL: {article.url}")
        print(f"   发布时间: {article.published_at}")
        print(f"   内容长度: {article.content_len} 字符")
        print(f"   处理状态: {article.processing_status}")

    if len(articles) > 5:
        print(f"\n... 还有 {len(articles) - 5} 篇文章")


def main():
    """主函数"""
    print("=" * 60)
    print("Playwright 动态采集测试")
    print("=" * 60)

    # 获取数据库会话
    db = next(get_db())

    try:
        # 1. 添加测试源
        print("\n步骤 1: 添加测试信息源")
        print("-" * 60)
        source = add_test_source(db)

        # 2. 执行采集
        print("\n步骤 2: 执行动态采集")
        print("-" * 60)
        result = test_crawl(source.id)

        if not result or result.get('status') != 'success':
            print("\n⚠️ 采集未成功，请查看上面的错误信息")
            return

        # 3. 查看结果
        print("\n步骤 3: 查看采集结果")
        print("-" * 60)
        check_articles(db, source.id)

        print("\n" + "=" * 60)
        print("✓ 测试完成！")
        print("=" * 60)
        print("\n提示:")
        print("1. 如果采集成功，文章已保存到数据库")
        print("2. 可以在Web界面查看: http://localhost:5000/admin/sources")
        print("3. 查看采集的文章: http://localhost:5000/reports")
        print(f"4. 如需删除测试源，运行: DELETE FROM sources WHERE id={source.id};")

    finally:
        db.close()


if __name__ == "__main__":
    main()
