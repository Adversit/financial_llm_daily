"""
代理策略管理器

根据域名和访问失败情况智能决定是否使用代理
"""
import re
from typing import Optional, Dict
from datetime import datetime, timedelta
from loguru import logger


class ProxyStrategy:
    """
    代理策略管理器

    功能：
    1. 根据域名判断是否需要代理（国内/国外）
    2. 跟踪访问失败记录
    3. 失败后自动切换代理策略
    4. 支持自定义域名规则
    """

    # 国内域名列表（不需要代理）
    DOMESTIC_DOMAINS = [
        # 财经网站
        'sina.com.cn',
        'eastmoney.com',
        'jrj.com.cn',
        'cls.cn',
        'caijing.com.cn',
        'finance.qq.com',
        '163.com',
        'sohu.com',
        'people.com.cn',
        'xinhuanet.com',
        'cnstock.com',
        'stcn.com',
        'yicai.com',
        'caixin.com',
        'wallstreetcn.com',
        'hexun.com',
        '10jqka.com.cn',

        # 科技网站
        'ithome.com',
        'cnbeta.com',
        'chinaz.com',
        '36kr.com',
        'pingwest.com',
        'tmtpost.com',

        # 其他常见国内域名
        'baidu.com',
        'taobao.com',
        'tmall.com',
        'jd.com',
        'zhihu.com',
        'douban.com',
        'weibo.com',
    ]

    # 国外域名列表（需要代理）
    FOREIGN_DOMAINS = [
        'bbc.com',
        'bbc.co.uk',
        'reuters.com',
        'bloomberg.com',
        'wsj.com',
        'ft.com',
        'nytimes.com',
        'economist.com',
        'cnbc.com',
        'forbes.com',
        'fortune.com',
        'marketwatch.com',
        'seeking alpha.com',
        'morningstar.com',

        # 科技网站
        'techcrunch.com',
        'theverge.com',
        'arstechnica.com',
        'wired.com',
        'engadget.com',

        # AI/科技公司
        'openai.com',
        'anthropic.com',
        'google.com',
        'microsoft.com',
        'apple.com',
        'nvidia.com',
    ]

    def __init__(self, proxy_url: Optional[str] = None, max_failures: int = 3):
        """
        初始化代理策略

        Args:
            proxy_url: 代理服务器地址
            max_failures: 最大失败次数，超过后切换策略
        """
        self.proxy_url = proxy_url
        self.max_failures = max_failures

        # 失败记录：{domain: {'count': int, 'last_fail': datetime, 'use_proxy': bool}}
        self.failure_records: Dict[str, Dict] = {}

        # 策略切换记录：{domain: {'switched': bool, 'switch_time': datetime}}
        self.strategy_switches: Dict[str, Dict] = {}

        logger.info(f"代理策略初始化: proxy={proxy_url}, max_failures={max_failures}")

    def get_proxy_for_url(self, url: str) -> Optional[str]:
        """
        根据URL决定是否使用代理

        Args:
            url: 目标URL

        Returns:
            Optional[str]: 代理地址，None表示不使用代理
        """
        domain = self._extract_domain(url)

        # 检查是否已切换策略
        if domain in self.strategy_switches:
            switch_info = self.strategy_switches[domain]
            # 如果切换时间在1小时内，使用切换后的策略
            if datetime.now() - switch_info['switch_time'] < timedelta(hours=1):
                use_proxy = switch_info['use_proxy']
                logger.info(f"[{domain}] 使用切换后的策略: use_proxy={use_proxy}")
                return self.proxy_url if use_proxy else None

        # 默认策略：根据域名判断
        if self._is_domestic_domain(domain):
            logger.debug(f"[{domain}] 国内域名，不使用代理")
            return None
        elif self._is_foreign_domain(domain):
            logger.debug(f"[{domain}] 国外域名，使用代理")
            return self.proxy_url
        else:
            # 未知域名，默认尝试不使用代理
            logger.debug(f"[{domain}] 未知域名，默认不使用代理")
            return None

    def record_failure(self, url: str) -> bool:
        """
        记录访问失败

        Args:
            url: 失败的URL

        Returns:
            bool: 是否需要切换策略
        """
        domain = self._extract_domain(url)
        current_proxy = self.get_proxy_for_url(url)
        use_proxy = current_proxy is not None

        # 初始化或更新失败记录
        if domain not in self.failure_records:
            self.failure_records[domain] = {
                'count': 1,
                'last_fail': datetime.now(),
                'use_proxy': use_proxy
            }
        else:
            record = self.failure_records[domain]
            # 如果策略相同，累加失败次数
            if record['use_proxy'] == use_proxy:
                record['count'] += 1
                record['last_fail'] = datetime.now()
            else:
                # 策略不同，重置计数
                record['count'] = 1
                record['last_fail'] = datetime.now()
                record['use_proxy'] = use_proxy

        failure_count = self.failure_records[domain]['count']
        logger.warning(
            f"[{domain}] 访问失败 ({failure_count}/{self.max_failures}), "
            f"当前策略: use_proxy={use_proxy}"
        )

        # 检查是否需要切换策略
        if failure_count >= self.max_failures:
            return self._switch_strategy(domain, use_proxy)

        return False

    def record_success(self, url: str):
        """
        记录访问成功，清除失败记录

        Args:
            url: 成功的URL
        """
        domain = self._extract_domain(url)

        # 清除失败记录
        if domain in self.failure_records:
            logger.info(f"[{domain}] 访问成功，清除失败记录")
            del self.failure_records[domain]

    def _switch_strategy(self, domain: str, current_use_proxy: bool) -> bool:
        """
        切换代理策略

        Args:
            domain: 域名
            current_use_proxy: 当前是否使用代理

        Returns:
            bool: 切换成功返回True
        """
        new_use_proxy = not current_use_proxy

        self.strategy_switches[domain] = {
            'use_proxy': new_use_proxy,
            'switch_time': datetime.now()
        }

        # 清除失败记录，从新策略重新开始
        if domain in self.failure_records:
            del self.failure_records[domain]

        logger.warning(
            f"[{domain}] 策略切换: {current_use_proxy} -> {new_use_proxy} "
            f"({'使用代理' if new_use_proxy else '不使用代理'})"
        )

        return True

    def _extract_domain(self, url: str) -> str:
        """
        从URL中提取域名

        Args:
            url: 完整URL

        Returns:
            str: 域名
        """
        # 提取域名部分
        match = re.search(r'https?://([^/]+)', url)
        if match:
            domain = match.group(1)
            # 移除端口号
            domain = domain.split(':')[0]
            # 移除www前缀
            domain = re.sub(r'^www\.', '', domain)
            return domain
        return url

    def _is_domestic_domain(self, domain: str) -> bool:
        """
        判断是否为国内域名

        Args:
            domain: 域名

        Returns:
            bool: 是否为国内域名
        """
        for domestic in self.DOMESTIC_DOMAINS:
            if domain.endswith(domestic):
                return True
        return False

    def _is_foreign_domain(self, domain: str) -> bool:
        """
        判断是否为国外域名

        Args:
            domain: 域名

        Returns:
            bool: 是否为国外域名
        """
        for foreign in self.FOREIGN_DOMAINS:
            if domain.endswith(foreign):
                return True
        return False

    def get_statistics(self) -> Dict:
        """
        获取策略统计信息

        Returns:
            Dict: 统计信息
        """
        return {
            'failure_records': len(self.failure_records),
            'strategy_switches': len(self.strategy_switches),
            'details': {
                'failures': self.failure_records,
                'switches': self.strategy_switches
            }
        }

    def reset(self):
        """重置所有记录"""
        self.failure_records.clear()
        self.strategy_switches.clear()
        logger.info("代理策略已重置")


# 全局单例
_global_strategy: Optional[ProxyStrategy] = None


def get_proxy_strategy(proxy_url: Optional[str] = None, max_failures: int = 3) -> ProxyStrategy:
    """
    获取全局代理策略单例

    Args:
        proxy_url: 代理服务器地址
        max_failures: 最大失败次数

    Returns:
        ProxyStrategy: 代理策略实例
    """
    global _global_strategy

    if _global_strategy is None:
        _global_strategy = ProxyStrategy(proxy_url, max_failures)

    return _global_strategy
