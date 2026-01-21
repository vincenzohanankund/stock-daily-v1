# 🚀 配置文件快速开始

## 1️⃣ 编辑自选股列表

编辑 `stocks.txt` 文件：

```bash
# 自选股列表配置文件
# 每行一个股票代码，支持 A 股和港股
# 以 # 开头的行为注释，空行会被忽略

# 我的自选股
600519    # 贵州茅台
000001    # 平安银行
300750    # 宁德时代
002594    # 比亚迪

# 港股（可选）
00700     # 腾讯控股
09988     # 阿里巴巴
```

## 2️⃣ 编辑邮件接收人（可选）

编辑 `email_receivers.txt` 文件：

```bash
# 邮件接收人列表配置文件
# 每行一个邮箱地址
# 以 # 开头的行为注释，空行会被忽略
# 如果文件为空或不存在，则发送给发件人自己

# 接收人列表
user1@example.com
user2@example.com
admin@company.com
```

> 💡 提示：如果不配置此文件，邮件将发送给发件人自己

## 3️⃣ 提交到仓库（GitHub Actions 用户）

```bash
git add stocks.txt email_receivers.txt
git commit -m "更新自选股和邮件接收人配置"
git push
```

## 4️⃣ 完成！

- **GitHub Actions**: 下次运行时自动使用新配置
- **本地运行**: 直接运行 `python main.py` 即可
- **Docker**: 重启容器 `docker-compose restart`

## 📖 更多信息

- [配置文件详细说明](CONFIG_FILES.md)
- [项目 README](README.md)
- [完整配置指南](docs/full-guide.md)

## ❓ 常见问题

**Q: 我已经在 Secrets 中配置了 STOCK_LIST，还需要创建 stocks.txt 吗？**

A: 不需要。Secrets 优先级更高，如果已配置则会优先使用。只有当你想更方便地管理时，才需要切换到配置文件方式。

**Q: 可以同时使用配置文件和 Secrets 吗？**

A: 可以。系统会按优先级使用：Secrets > .env > 配置文件 > 默认值

**Q: 配置文件支持中文注释吗？**

A: 支持！文件使用 UTF-8 编码。

## 🎯 示例

### 示例 1：只关注几只核心股票

`stocks.txt`:
```
600519
000858
300750
```

### 示例 2：分类管理自选股

`stocks.txt`:
```
# 白酒板块
600519    # 贵州茅台
000858    # 五粮液

# 新能源板块
300750    # 宁德时代
002594    # 比亚迪

# 科技板块
000063    # 中兴通讯
002415    #海康威视
```

### 示例 3：多人接收邮件

`email_receivers.txt`:
```
# 团队成员
team-leader@company.com
analyst1@company.com
analyst2@company.com

# 抄送
manager@company.com
```

## ✅ 验证配置

运行测试脚本验证配置是否正确：

```bash
python test_config_files.py
```

预期输出：
```
==================================================
配置文件功能测试
==================================================

1. 检查配置文件
   stocks.txt: ✅ 存在
   email_receivers.txt: ✅ 存在

2. stocks.txt 内容:
   - 600519
   - 000001
   - 300750

✅ 测试完成！
==================================================
```
