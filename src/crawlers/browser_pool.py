"""
浏览器池管理器
用于管理Playwright浏览器实例，支持浏览器复用和上下文隔离
"""
import logging
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright

logger = logging.getLogger(__name__)


# 用户代理池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


class BrowserPool:
    """
    浏览器实例池，用于管理Playwright浏览器

    特性：
    - 浏览器实例复用，避免重复启动开销
    - 每个任务使用独立的BrowserContext保证隔离
    - 随机UA池，降低被检测风险
    - 反自动化检测措施
    """

    def __init__(self, max_contexts: int = 5, headless: bool = True):
        """
        初始化浏览器池

        Args:
            max_contexts: 最大并发上下文数（建议≤10）
            headless: 是否无头模式
        """
        self.max_contexts = max_contexts
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self._context_count = 0

        logger.info(f"浏览器池初始化: max_contexts={max_contexts}, headless={headless}")

    async def start(self):
        """启动Playwright和浏览器"""
        if self.playwright is not None:
            logger.warning("浏览器池已经启动，跳过重复启动")
            return

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            logger.info("浏览器启动成功")
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            raise

    async def get_context(self, proxy: Optional[str] = None) -> BrowserContext:
        """
        获取一个新的浏览器上下文

        Args:
            proxy: 代理服务器地址，格式如 "http://127.0.0.1:7890"

        Returns:
            BrowserContext: 独立的浏览器会话
        """
        if self.browser is None:
            raise RuntimeError("浏览器池未启动，请先调用 start()")

        try:
            # 准备上下文配置
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': self._get_random_ua(),
                'locale': 'zh-CN',
                'timezone_id': 'Asia/Shanghai',
                'extra_http_headers': {
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                },
                'ignore_https_errors': True,
            }

            # 如果提供了代理，添加到配置中
            if proxy:
                context_options['proxy'] = {'server': proxy}
                logger.info(f"使用代理: {proxy}")

            context = await self.browser.new_context(**context_options)

            # 注入反检测脚本
            await context.add_init_script("""
                // 隐藏webdriver属性
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // 模拟Chrome对象
                window.chrome = {
                    runtime: {}
                };

                // 覆盖permissions查询
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
            """)

            self._context_count += 1
            logger.debug(f"创建浏览器上下文成功 (当前活跃: {self._context_count})")

            return context

        except Exception as e:
            logger.error(f"创建浏览器上下文失败: {e}")
            raise

    async def close_context(self, context: BrowserContext):
        """关闭浏览器上下文"""
        try:
            await context.close()
            self._context_count = max(0, self._context_count - 1)
            logger.debug(f"关闭浏览器上下文 (剩余活跃: {self._context_count})")
        except Exception as e:
            logger.error(f"关闭浏览器上下文失败: {e}")

    async def close(self):
        """关闭所有资源"""
        try:
            if self.browser:
                await self.browser.close()
                logger.info("浏览器已关闭")
            if self.playwright:
                await self.playwright.stop()
                logger.info("Playwright已停止")
        except Exception as e:
            logger.error(f"关闭浏览器池失败: {e}")
        finally:
            self.browser = None
            self.playwright = None
            self._context_count = 0

    def _get_random_ua(self) -> str:
        """随机选择一个用户代理"""
        return random.choice(USER_AGENTS)

    @property
    def is_running(self) -> bool:
        """浏览器池是否正在运行"""
        return self.browser is not None and self.playwright is not None
