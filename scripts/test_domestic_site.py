"""
测试采集国内财经网站
使用新浪财经作为测试目标
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from src.db.session import get_db
from src.models.source import Source, SourceType, RegionHint
from src.tasks.crawl_tasks import crawl_dynamic_task
from src.models.article import Article
import json


def add_sina_finance_source(db: Session):
    """添加新浪财经测试源"""

    # 检查是否已存在
    existing = db.query(Source).filter(Source.name == "新浪财经测试").first()
    if existing:
        print(f"✓ 测试源已存在: ID={existing.id}")
        return existing

    # 创建新的测试源
    test_source = Source(
        name="新浪财经测试",
        type=SourceType.DYNAMIC,
        url="https://finance.sina.com.cn/",
        enabled=True,
        parser_config={
            "need_scroll": False,
            "link_selectors": [
                "a[href*='finance.sina.com.cn']",
                ".news-item a",
                "h3 a",
                "h2 a"
            ],
            "wait_selector": None,
            "allow_patterns": ["/stock/", "/money/", "/china/", "/roll/"],
            "max_links": 10,  # 限制为10个用于测试
            "scroll_times": 2
        },
        region_hint=RegionHint.DOMESTIC,
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
        print(f"  信息源类型: {result.get('source_type')}")
        print(f"  原始获取: {result.get('fetched', 0)} 篇")
        print(f"  去重后: {result.get('after_dedup', 0)} 篇")
        print(f"  新增保存: {result.get('saved', 0)} 篇")
        print(f"  加入队列: {result.get('queued', 0)} 篇")

        if result.get('status') == 'error':
            print(f"  错误信息: {result.get('error', 'Unknown error')}")
            return None

        return result

    except Exception as e:
        print(f"✗ 采集失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_articles(db: Session, source_id: int):
    """检查采集到的文章"""
    articles = db.query(Article).filter(
        Article.source_id == source_id
    ).order_by(Article.fetched_at.desc()).limit(10).all()

    print(f"\n数据库中的文章（最近 {len(articles)} 篇）:")
    print("=" * 60)

    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article.title[:80]}...")
        print(f"   URL: {article.url[:80]}...")
        print(f"   发布时间: {article.published_at}")
        print(f"   内容长度: {article.content_len} 字符")
        print(f"   处理状态: {article.processing_status}")


def main():
    """主函数"""
    print("=" * 60)
    print("国内财经网站动态采集测试 - 新浪财经")
    print("=" * 60)

    db = next(get_db())

    try:
        # 1. 添加测试源
        print("\n步骤 1: 添加新浪财经测试源")
        print("-" * 60)
        source = add_sina_finance_source(db)

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
        print("1. 文章已保存到数据库")
        print("2. Web界面查看: http://localhost:5000/admin/sources")
        print("3. 查看报告: http://localhost:5000/reports")
        print(f"4. 删除测试源: DELETE FROM sources WHERE id={source.id};")

    except KeyboardInterrupt:
        print("\n\n用户中断测试")
    except Exception as e:
        print(f"\n✗ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
