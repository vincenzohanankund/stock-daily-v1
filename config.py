# -*- coding: utf-8 -*-
"""
===================================
A股自選股智能分析系統 - 配置管理模塊
===================================

職責：
1. 使用單例模式管理全局配置
2. 從 .env 文件加載敏感配置
3. 提供類型安全的配置訪問接口
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv, dotenv_values
from dataclasses import dataclass, field


@dataclass
class Config:
    """
    系統配置類 - 單例模式
    
    設計說明：
    - 使用 dataclass 簡化配置屬性定義
    - 所有配置項從環境變量讀取，支持默認值
    - 類方法 get_instance() 實現單例訪問
    """
    
    # === 自選股配置 ===
    stock_list: List[str] = field(default_factory=list)

    # === 飛書雲文檔配置 ===
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    feishu_folder_token: Optional[str] = None  # 目標文件夾 Token

    # === 數據源 API Token ===
    finmind_token: Optional[str] = None  # FinMind API Token（台股專用，https://finmindtrade.com/）
    tushare_token: Optional[str] = None
    
    # === AI 分析配置 ===
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3-flash-preview"  # 主模型
    gemini_model_fallback: str = "gemini-2.5-flash"  # 備選模型
    
    # Gemini API 請求配置（防止 429 限流）
    gemini_request_delay: float = 2.0  # 請求間隔（秒）
    gemini_max_retries: int = 5  # 最大重試次數
    gemini_retry_delay: float = 5.0  # 重試基礎延時（秒）
    
    # OpenAI 兼容 API（備選，當 Gemini 不可用時使用）
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None  # 如: https://api.openai.com/v1
    openai_model: str = "gpt-4o-mini"  # OpenAI 兼容模型名稱
    
    # === 搜索引擎配置（支持多 Key 負載均衡）===
    bocha_api_keys: List[str] = field(default_factory=list)  # Bocha API Keys
    tavily_api_keys: List[str] = field(default_factory=list)  # Tavily API Keys
    serpapi_keys: List[str] = field(default_factory=list)  # SerpAPI Keys
    
    # === 通知配置（可同時配置多個，全部推送）===
    
    # 企業微信 Webhook
    wechat_webhook_url: Optional[str] = None
    
    # 飛書 Webhook
    feishu_webhook_url: Optional[str] = None
    
    # Telegram 配置（需要同時配置 Bot Token 和 Chat ID）
    telegram_bot_token: Optional[str] = None  # Bot Token（@BotFather 獲取）
    telegram_chat_id: Optional[str] = None  # Chat ID
    
    # 郵件配置（只需郵箱和授權碼，SMTP 自動識別）
    email_sender: Optional[str] = None  # 發件人郵箱
    email_password: Optional[str] = None  # 郵箱密碼/授權碼
    email_receivers: List[str] = field(default_factory=list)  # 收件人列表（留空則發給自己）
    
    # Pushover 配置（手機/桌面推送通知）
    pushover_user_key: Optional[str] = None  # 用戶 Key（https://pushover.net 獲取）
    pushover_api_token: Optional[str] = None  # 應用 API Token
    
    # 自定義 Webhook（支持多個，逗號分隔）
    # 適用於：釘釘、Discord、Slack、自建服務等任意支持 POST JSON 的 Webhook
    custom_webhook_urls: List[str] = field(default_factory=list)
    custom_webhook_bearer_token: Optional[str] = None  # Bearer Token（用於需要認證的 Webhook）
    
    # Discord 通知配置
    discord_bot_token: Optional[str] = None  # Discord Bot Token
    discord_main_channel_id: Optional[str] = None  # Discord 主頻道 ID
    discord_webhook_url: Optional[str] = None  # Discord Webhook URL
    
    # 單股推送模式：每分析完一隻股票立即推送，而不是彙總後推送
    single_stock_notify: bool = False
    
    # 消息長度限制（字節）- 超長自動分批發送
    feishu_max_bytes: int = 20000  # 飛書限制約 20KB，默認 20000 字節
    wechat_max_bytes: int = 4000   # 企業微信限制 4096 字節，默認 4000 字節
    
    # === 數據庫配置 ===
    database_path: str = "./data/stock_analysis.db"
    
    # === 日誌配置 ===
    log_dir: str = "./logs"  # 日誌文件目錄
    log_level: str = "INFO"  # 日誌級別
    
    # === 系統配置 ===
    max_workers: int = 3  # 低併發防封禁
    debug: bool = False
    
    # === 定時任務配置 ===
    schedule_enabled: bool = False            # 是否啟用定時任務
    schedule_time: str = "18:00"              # 每日推送時間（HH:MM 格式）
    market_review_enabled: bool = True        # 是否啟用大盤覆盤
    
    # === 流控配置（防封禁關鍵參數）===
    # Akshare 請求間隔範圍（秒）
    akshare_sleep_min: float = 2.0
    akshare_sleep_max: float = 5.0
    
    # Tushare 每分鐘最大請求數（免費配額）
    tushare_rate_limit_per_minute: int = 80
    
    # 重試配置
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    
    # === WebUI 配置 ===
    webui_enabled: bool = False
    webui_host: str = "127.0.0.1"
    webui_port: int = 8000
    
    # === 機器人配置 ===
    bot_enabled: bool = True              # 是否啟用機器人功能
    bot_command_prefix: str = "/"         # 命令前綴
    bot_rate_limit_requests: int = 10     # 頻率限制：窗口內最大請求數
    bot_rate_limit_window: int = 60       # 頻率限制：窗口時間（秒）
    bot_admin_users: List[str] = field(default_factory=list)  # 管理員用戶 ID 列表
    
    # 飛書機器人（事件訂閱）- 已有 feishu_app_id, feishu_app_secret
    feishu_verification_token: Optional[str] = None  # 事件訂閱驗證 Token
    feishu_encrypt_key: Optional[str] = None         # 消息加密密鑰（可選）
    feishu_stream_enabled: bool = False              # 是否啟用 Stream 長連接模式（無需公網IP）
    
    # 釘釘機器人
    dingtalk_app_key: Optional[str] = None      # 應用 AppKey
    dingtalk_app_secret: Optional[str] = None   # 應用 AppSecret
    dingtalk_stream_enabled: bool = False       # 是否啟用 Stream 模式（無需公網IP）
    
    # 企業微信機器人（回調模式）
    wecom_corpid: Optional[str] = None              # 企業 ID
    wecom_token: Optional[str] = None               # 回調 Token
    wecom_encoding_aes_key: Optional[str] = None    # 消息加解密密鑰
    wecom_agent_id: Optional[str] = None            # 應用 AgentId
    
    # Telegram 機器人 - 已有 telegram_bot_token, telegram_chat_id
    telegram_webhook_secret: Optional[str] = None   # Webhook 密鑰
    
    # 單例實例存儲
    _instance: Optional['Config'] = None
    
    @classmethod
    def get_instance(cls) -> 'Config':
        """
        獲取配置單例實例
        
        單例模式確保：
        1. 全局只有一個配置實例
        2. 配置只從環境變量加載一次
        3. 所有模塊共享相同配置
        """
        if cls._instance is None:
            cls._instance = cls._load_from_env()
        return cls._instance
    
    @classmethod
    def _load_from_env(cls) -> 'Config':
        """
        從 .env 文件加載配置
        
        加載優先級：
        1. 系統環境變量
        2. .env 文件
        3. 代碼中的默認值
        """
        # 加載項目根目錄下的 .env 文件
        env_path = Path(__file__).parent / '.env'
        load_dotenv(dotenv_path=env_path)
        
        # 解析自選股列表（逗號分隔）
        stock_list_str = os.getenv('STOCK_LIST', '')
        stock_list = [
            code.strip() 
            for code in stock_list_str.split(',') 
            if code.strip()
        ]
        
        # 如果沒有配置，使用默認的示例股票（台股）
        if not stock_list:
            stock_list = ['2330.TW', '2317.TW', '2454.TW']  # 台積電、鴻海、聯發科
        
        # 解析搜索引擎 API Keys（支持多個 key，逗號分隔）
        bocha_keys_str = os.getenv('BOCHA_API_KEYS', '')
        bocha_api_keys = [k.strip() for k in bocha_keys_str.split(',') if k.strip()]
        
        tavily_keys_str = os.getenv('TAVILY_API_KEYS', '')
        tavily_api_keys = [k.strip() for k in tavily_keys_str.split(',') if k.strip()]
        
        serpapi_keys_str = os.getenv('SERPAPI_API_KEYS', '')
        serpapi_keys = [k.strip() for k in serpapi_keys_str.split(',') if k.strip()]
        
        return cls(
            stock_list=stock_list,
            feishu_app_id=os.getenv('FEISHU_APP_ID'),
            feishu_app_secret=os.getenv('FEISHU_APP_SECRET'),
            feishu_folder_token=os.getenv('FEISHU_FOLDER_TOKEN'),
            finmind_token=os.getenv('FINMIND_TOKEN'),
            tushare_token=os.getenv('TUSHARE_TOKEN'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            gemini_model=os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview'),
            gemini_model_fallback=os.getenv('GEMINI_MODEL_FALLBACK', 'gemini-2.5-flash'),
            gemini_request_delay=float(os.getenv('GEMINI_REQUEST_DELAY', '2.0')),
            gemini_max_retries=int(os.getenv('GEMINI_MAX_RETRIES', '5')),
            gemini_retry_delay=float(os.getenv('GEMINI_RETRY_DELAY', '5.0')),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_base_url=os.getenv('OPENAI_BASE_URL'),
            openai_model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            bocha_api_keys=bocha_api_keys,
            tavily_api_keys=tavily_api_keys,
            serpapi_keys=serpapi_keys,
            wechat_webhook_url=os.getenv('WECHAT_WEBHOOK_URL'),
            feishu_webhook_url=os.getenv('FEISHU_WEBHOOK_URL'),
            telegram_bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            email_sender=os.getenv('EMAIL_SENDER'),
            email_password=os.getenv('EMAIL_PASSWORD'),
            email_receivers=[r.strip() for r in os.getenv('EMAIL_RECEIVERS', '').split(',') if r.strip()],
            pushover_user_key=os.getenv('PUSHOVER_USER_KEY'),
            pushover_api_token=os.getenv('PUSHOVER_API_TOKEN'),
            custom_webhook_urls=[u.strip() for u in os.getenv('CUSTOM_WEBHOOK_URLS', '').split(',') if u.strip()],
            custom_webhook_bearer_token=os.getenv('CUSTOM_WEBHOOK_BEARER_TOKEN'),
            discord_bot_token=os.getenv('DISCORD_BOT_TOKEN'),
            discord_main_channel_id=os.getenv('DISCORD_MAIN_CHANNEL_ID'),
            discord_webhook_url=os.getenv('DISCORD_WEBHOOK_URL'),
            single_stock_notify=os.getenv('SINGLE_STOCK_NOTIFY', 'false').lower() == 'true',
            feishu_max_bytes=int(os.getenv('FEISHU_MAX_BYTES', '20000')),
            wechat_max_bytes=int(os.getenv('WECHAT_MAX_BYTES', '4000')),
            database_path=os.getenv('DATABASE_PATH', './data/stock_analysis.db'),
            log_dir=os.getenv('LOG_DIR', './logs'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            max_workers=int(os.getenv('MAX_WORKERS', '3')),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            schedule_enabled=os.getenv('SCHEDULE_ENABLED', 'false').lower() == 'true',
            schedule_time=os.getenv('SCHEDULE_TIME', '18:00'),
            market_review_enabled=os.getenv('MARKET_REVIEW_ENABLED', 'true').lower() == 'true',
            webui_enabled=os.getenv('WEBUI_ENABLED', 'false').lower() == 'true',
            webui_host=os.getenv('WEBUI_HOST', '127.0.0.1'),
            webui_port=int(os.getenv('WEBUI_PORT', '8000')),
            # 機器人配置
            bot_enabled=os.getenv('BOT_ENABLED', 'true').lower() == 'true',
            bot_command_prefix=os.getenv('BOT_COMMAND_PREFIX', '/'),
            bot_rate_limit_requests=int(os.getenv('BOT_RATE_LIMIT_REQUESTS', '10')),
            bot_rate_limit_window=int(os.getenv('BOT_RATE_LIMIT_WINDOW', '60')),
            bot_admin_users=[u.strip() for u in os.getenv('BOT_ADMIN_USERS', '').split(',') if u.strip()],
            # 飛書機器人
            feishu_verification_token=os.getenv('FEISHU_VERIFICATION_TOKEN'),
            feishu_encrypt_key=os.getenv('FEISHU_ENCRYPT_KEY'),
            feishu_stream_enabled=os.getenv('FEISHU_STREAM_ENABLED', 'false').lower() == 'true',
            # 釘釘機器人
            dingtalk_app_key=os.getenv('DINGTALK_APP_KEY'),
            dingtalk_app_secret=os.getenv('DINGTALK_APP_SECRET'),
            dingtalk_stream_enabled=os.getenv('DINGTALK_STREAM_ENABLED', 'false').lower() == 'true',
            # 企業微信機器人
            wecom_corpid=os.getenv('WECOM_CORPID'),
            wecom_token=os.getenv('WECOM_TOKEN'),
            wecom_encoding_aes_key=os.getenv('WECOM_ENCODING_AES_KEY'),
            wecom_agent_id=os.getenv('WECOM_AGENT_ID'),
            # Telegram
            telegram_webhook_secret=os.getenv('TELEGRAM_WEBHOOK_SECRET'),
        )
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置單例（主要用於測試）"""
        cls._instance = None

    def refresh_stock_list(self) -> None:
        """
        熱讀取 STOCK_LIST 環境變量並更新配置中的自選股列表
        
        支持兩種配置方式：
        1. .env 文件（本地開發、定時任務模式） - 修改後下次執行自動生效
        2. 系統環境變量（GitHub Actions、Docker） - 啟動時固定，運行中不變
        """
        # 若 .env 中配置了 STOCK_LIST，則以 .env 為準；否則回退到系統環境變量
        env_path = Path(__file__).parent / '.env'
        stock_list_str = ''
        if env_path.exists():
            env_values = dotenv_values(env_path)
            stock_list_str = (env_values.get('STOCK_LIST') or '').strip()

        if not stock_list_str:
            stock_list_str = os.getenv('STOCK_LIST', '')

        stock_list = [
            code.strip()
            for code in stock_list_str.split(',')
            if code.strip()
        ]

        if not stock_list:        
            stock_list = ['000001']

        self.stock_list = stock_list
    
    def validate(self) -> List[str]:
        """
        驗證配置完整性
        
        Returns:
            缺失或無效配置項的警告列表
        """
        warnings = []
        
        if not self.stock_list:
            warnings.append("警告：未配置自選股列表 (STOCK_LIST)")
        
        if not self.tushare_token:
            warnings.append("提示：未配置 Tushare Token，將使用其他數據源")
        
        if not self.gemini_api_key and not self.openai_api_key:
            warnings.append("警告：未配置 Gemini 或 OpenAI API Key，AI 分析功能將不可用")
        elif not self.gemini_api_key:
            warnings.append("提示：未配置 Gemini API Key，將使用 OpenAI 兼容 API")
        
        if not self.bocha_api_keys and not self.tavily_api_keys and not self.serpapi_keys:
            warnings.append("提示：未配置搜索引擎 API Key (Bocha/Tavily/SerpAPI)，新聞搜索功能將不可用")
        
        # 檢查通知配置
        has_notification = (
            self.wechat_webhook_url or 
            self.feishu_webhook_url or
            (self.telegram_bot_token and self.telegram_chat_id) or
            (self.email_sender and self.email_password) or
            (self.pushover_user_key and self.pushover_api_token) or
            (self.custom_webhook_urls and self.custom_webhook_bearer_token) or
            (self.discord_bot_token and self.discord_main_channel_id) or
            self.discord_webhook_url
        )
        if not has_notification:
            warnings.append("提示：未配置通知渠道，將不發送推送通知")
        
        return warnings
    
    def get_db_url(self) -> str:
        """
        獲取 SQLAlchemy 數據庫連接 URL
        
        自動創建數據庫目錄（如果不存在）
        """
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path.absolute()}"


# === 便捷的配置訪問函數 ===
def get_config() -> Config:
    """獲取全局配置實例的快捷方式"""
    return Config.get_instance()


if __name__ == "__main__":
    # 測試配置加載
    config = get_config()
    print("=== 配置加載測試 ===")
    print(f"自選股列表: {config.stock_list}")
    print(f"數據庫路徑: {config.database_path}")
    print(f"最大併發數: {config.max_workers}")
    print(f"調試模式: {config.debug}")
    
    # 驗證配置
    warnings = config.validate()
    if warnings:
        print("\n配置驗證結果:")
        for w in warnings:
            print(f"  - {w}")
