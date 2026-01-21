# 配置文件使用说明

## 📝 概述

为了方便管理自选股列表和邮件接收人，本项目支持使用配置文件的方式，无需频繁修改 GitHub Actions Secrets。

## 📁 配置文件

### 1. `stocks.txt` - 自选股列表

**文件位置**：项目根目录

**格式说明**：
- 每行一个股票代码
- 支持 A 股（6 位数字）和港股（5 位数字）
- 以 `#` 开头的行为注释
- 空行会被自动忽略

**示例**：
```txt
# A 股自选股
600519
000001
300750

# 港股（可选）
00700
09988
```

### 2. `email_receivers.txt` - 邮件接收人列表

**文件位置**：项目根目录

**格式说明**：
- 每行一个邮箱地址
- 以 `#` 开头的行为注释
- 空行会被自动忽略
- 如果文件为空或不存在，邮件将发送给发件人自己

**示例**：
```txt
# 邮件接收人列表
user1@example.com
user2@example.com
admin@company.com
```

## 🔄 配置优先级

系统会按以下优先级读取配置：

### 自选股列表 (STOCK_LIST)
1. **系统环境变量** `STOCK_LIST`（GitHub Actions Secrets/Variables）
2. **`.env` 文件** 中的 `STOCK_LIST`
3. **`stocks.txt` 配置文件** ⭐ 推荐
4. 默认值：`['600519', '000001', '300750']`

### 邮件接收人 (EMAIL_RECEIVERS)
1. **系统环境变量** `EMAIL_RECEIVERS`（GitHub Actions Secrets/Variables）
2. **`email_receivers.txt` 配置文件** ⭐ 推荐
3. 默认：发送给发件人自己

## 🚀 使用方式

### GitHub Actions 部署（推荐）

1. **编辑配置文件**
   ```bash
   # 编辑自选股列表
   vim stocks.txt
   
   # 编辑邮件接收人
   vim email_receivers.txt
   ```

2. **提交到仓库**
   ```bash
   git add stocks.txt email_receivers.txt
   git commit -m "更新自选股和邮件接收人配置"
   git push
   ```

3. **完成！**
   - 下次 GitHub Actions 运行时会自动使用新配置
   - 无需修改 Secrets，方便快捷

### 本地运行

1. **直接编辑配置文件**
   ```bash
   # 编辑自选股
   nano stocks.txt
   
   # 编辑邮件接收人
   nano email_receivers.txt
   ```

2. **运行程序**
   ```bash
   python main.py
   ```

### Docker 部署

1. **编辑配置文件**（同上）

2. **重启容器**
   ```bash
   docker-compose restart
   ```

## ⚙️ 兼容性说明

- ✅ **向后兼容**：如果你已经在 GitHub Secrets 中配置了 `STOCK_LIST` 和 `EMAIL_RECEIVERS`，它们仍然有效且优先级最高
- ✅ **灵活切换**：可以随时在环境变量和配置文件之间切换
- ✅ **混合使用**：可以用配置文件管理自选股，同时用环境变量管理邮件接收人（或反之）

## 💡 最佳实践

### GitHub Actions 用户
- ✅ **推荐**：使用 `stocks.txt` 和 `email_receivers.txt`
- ✅ **优点**：
  - 修改方便，直接提交代码即可
  - 支持注释，便于管理
  - 可以查看历史变更记录
  - 无需进入 Settings 修改 Secrets

### 本地/Docker 用户
- ✅ **推荐**：使用 `.env` 文件或配置文件
- ✅ **优点**：
  - 配置集中管理
  - 支持版本控制（注意不要提交敏感信息）

## 🔒 安全提示

- ⚠️ **不要在配置文件中存储敏感信息**（如 API Key、密码等）
- ✅ 敏感信息应继续使用 GitHub Secrets 或 `.env` 文件（不提交到仓库）
- ✅ 可以将 `email_receivers.txt` 添加到 `.gitignore`（如果包含私人邮箱）

## 📖 相关文档

- [完整配置指南](docs/full-guide.md)
- [README.md](README.md)

## ❓ 常见问题

**Q: 我已经在 Secrets 中配置了 STOCK_LIST，还需要创建 stocks.txt 吗？**

A: 不需要。系统会优先使用 Secrets 中的配置。只有当你想更方便地管理自选股时，才需要切换到配置文件方式。

**Q: 配置文件和环境变量可以同时使用吗？**

A: 可以。环境变量的优先级更高，如果设置了环境变量，配置文件会被忽略。

**Q: 修改配置文件后需要重启吗？**

A: 
- GitHub Actions：提交后下次运行自动生效
- 本地运行：重新执行 `python main.py` 即可
- Docker：需要重启容器 `docker-compose restart`

**Q: 配置文件支持中文注释吗？**

A: 支持！文件使用 UTF-8 编码，可以使用中文注释。
