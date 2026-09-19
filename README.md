# SEVENTEEN × 泡泡玛特 发售信息监控

自动监控泡泡玛特官网及 Weverse 公告页，检测到 SEVENTEEN / MINITEEN 相关发售信息后，通过微信第一时间推送通知。

## 工作原理

```
每 15 分钟自动运行 → 抓取监控页面 → 搜索关键词 → 命中则微信推送
```

- **常规模式**：每 15 分钟检查一次
- **预热模式**：检测到关键词命中后，自动加密到每 5 分钟检查一轮
- **去重机制**：同一内容不重复推送，只有内容变化才通知

## 快速开始

### 第一步：wxpusher 配置（拿密钥）

1. 打开 [wxpusher 管理后台](https://wxpusher.zjiecode.com/admin/)，微信扫码登录
2. 点击「创建应用」，填写应用名称（比如"SVT泡泡玛特监控"）
3. 创建后复制 **`appToken`**（应用密钥）
4. 点击应用的「二维码」，用微信扫码关注
5. 进入「用户管理」→「用户列表」，复制你的 **`UID`**

### 第二步：创建 GitHub 仓库

1. 打开 [github.com/new](https://github.com/new)
2. 仓库名填 `svt-popmart-monitor`（或你喜欢的名字）
3. 选择 **Public**（公开仓库 Actions 完全免费）
4. 勾选「Add a README file」
5. 点击 **Create repository**

### 第三步：上传代码文件

把以下 3 个文件上传到仓库根目录：

```
svt-popmart-monitor/
├── monitor.py          # 主监控脚本
├── config.json         # 配置文件（监控源+关键词）
└── .github/
    └── workflows/
        └── monitor.yml  # GitHub Actions 定时任务
```

> 上传方式：仓库页面点「Add file」→「Upload files」，把文件拖进去即可。
> 注意 `.github` 文件夹要保持这个目录结构。

### 第四步：配置 Secrets（密钥）

1. 进入仓库 → **Settings** → 左侧 **Secrets and variables** → **Actions**
2. 点击 **New repository secret**，添加以下两个：

   | Name | Value |
   |------|-------|
   | `WXPUSHER_APP_TOKEN` | 第一步拿到的 appToken |
   | `WXPUSHER_UID` | 第一步拿到的 UID |

3. 同一页面往下滚动，找到 **Workflow permissions**：
   - 选择 **Read and write permissions**
   - 点击 **Save**

### 第五步：手动触发测试

1. 进入仓库 → **Actions** 标签页
2. 左侧选择 **SVT Popmart Monitor**
3. 右上角点击 **Run workflow** → **Run workflow**
4. 等待运行完成（约 30 秒）
5. 如果看到绿色勾号 ✅，说明配置成功！

> 首次运行不会触发推送（因为还没建立对比基准）。
> 从第二次开始，如果检测到新内容就会推送。

## 文件说明

### `config.json` — 配置文件

| 字段 | 说明 |
|------|------|
| `keywords` | 触发推送的关键词列表，可自行增删 |
| `sources` | 监控的页面列表，每个包含 `name` 和 `url` |

**想加监控源？** 直接在 `sources` 数组里加一行就行，比如：

```json
{
  "name": "新的监控源",
  "url": "https://example.com"
}
```

**想加关键词？** 在 `keywords` 数组里加就行。

### `state.json` — 运行状态（自动生成）

记录上次检测的结果和当前模式（normal/preheat），**不需要手动修改**。
这个文件会被脚本自动更新并提交回仓库，保证状态不丢失。

## 注意事项

1. **GitHub Actions 定时任务可能有几分钟延迟**，不是精确到秒级的，正常现象
2. **免费额度**：公开仓库 Actions 无限运行，完全够用
3. **推送频率**：同一内容不会重复推送，只有内容发生变化才会通知
4. **预热模式**：一旦检测到关键词命中，会自动加密检查频率，持续到下次运行
5. 如果想**重置状态**（重新开始监控），删掉仓库里的 `state.json` 即可

## 常见问题

**Q: 没收到推送？**
- 检查 Secrets 里的 appToken 和 UID 是否正确
- 确认微信已经关注了 wxpusher 应用
- 去 Actions 页面看运行日志，有没有报错

**Q: 想改监控频率？**
- 编辑 `.github/workflows/monitor.yml` 里的 `cron` 行
- 比如改成 `*/30 * * * *` 就是每 30 分钟一次

**Q: 想加新的监控网站？**
- 编辑 `config.json`，在 `sources` 里加一条
