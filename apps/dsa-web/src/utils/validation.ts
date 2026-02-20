interface ValidationResult {
  valid: boolean;
  message?: string;
  normalized: string;
}

// 兼容 A/H/美股常见代码格式的基础校验
export const validateStockCode = (value: string): ValidationResult => {
  const normalized = value.trim().toUpperCase();

  if (!normalized) {
    return { valid: false, message: '请输入股票代码', normalized };
  }

  const patterns = [
    /^\d{6}$/, // A 股 6 位数字
    /^(SH|SZ)\d{6}$/, // A 股带交易所前缀
    /^\d{5}$/, // 港股 5 位数字
    /^HK\d{5}$/, // 港股带 HK 前缀
    /^[A-Z]{1,5}(\.[A-Z]{1,2})?$/, // 美股 Ticker (如 AAPL, BRK.B)
  ];

  const valid = patterns.some((regex) => regex.test(normalized));

  return {
    valid,
    message: valid ? undefined : '股票代码格式不正确',
    normalized,
  };
};
