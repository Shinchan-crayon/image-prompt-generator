# 图片生成渠道

## 何时读取

仅在用户选择、配置、检查或调用图片生成渠道时读取。本文件只管理 Prompt 审核后的执行
阶段，不改变封面模式与正文配图模式，也不参与文章理解和视觉判断。

## 用户菜单

必须按以下顺序向用户展示，不增加普通用户需要理解的 URL 或模型 ID：

1. ThinkAI
2. 火山引擎 Seedream
3. OpenAI GPT Image
4. Google Nano Banana
5. 其他

未指定渠道时使用 ThinkAI。配置任何其他渠道都不得自动改变默认渠道。

## 配置体验

正式渠道只让用户选择渠道并安全输入 API Key：

```bash
python3 scripts/configure_provider.py <provider>
```

其中 `<provider>` 为 `thinkai`、`volcengine`、`openai` 或 `google`。脚本从
`data/image_providers.json` 读取固定 API 地址、推荐模型、默认尺寸和适配器，不要求普通
用户手工填写 URL 或模型 ID。API Key 使用隐藏输入；自动化环境只能通过标准输入传入。

配置后运行：

```bash
python3 scripts/provider_preflight.py --provider <provider>
```

预检只验证本地配置和请求结构，不联网、不生成图片、不产生费用。`verified-local` 只代表
本地契约通过，不能写成服务端认证成功。

## 正式渠道契约

| ID | 用户名称 | Prompt 语言 | 默认行为 |
|---|---|---|---|
| `thinkai` | ThinkAI | 中文或中英混合 | 默认渠道，保留旧平铺配置与旧审核哈希 |
| `volcengine` | 火山引擎 Seedream | 中文或中英混合 | 使用注册表推荐 Seedream 模型 |
| `openai` | OpenAI GPT Image | 中文或中英混合 | 使用 OpenAI Image API |
| `google` | Google Nano Banana | 中文或中英混合 | 使用 Google 图片生成接口 |

正式渠道的地址、模型别名和默认尺寸集中维护在 `data/image_providers.json`。不要把 API Key
写入注册表，也不要允许配置文件覆盖正式渠道地址。模型发生变化时更新注册表和适配器，
普通用户仍只选择渠道并输入 Key。

## 其他渠道

“其他”不是任意 HTTP 客户端。Agent 必须先读取用户指定服务的官方图片生成文档，确认它是
同步 JSON 图片接口，并能映射到以下协议之一：

- `openai-image-compatible`
- `generic-sync-json-image`

确认后由 Agent 决定 Endpoint、模型、鉴权类型、图片字段路径与返回类型，再调用：

```bash
python3 scripts/configure_provider.py custom \
  --custom-id custom-<name> \
  --name '<显示名称>' \
  --profile '<受支持协议>' \
  --endpoint '<公网 HTTPS Endpoint>' \
  --model '<图片模型 ID>' \
  --auth-type '<bearer 或 api-key-header>' \
  --response-path '<受限点路径>' \
  --response-type '<url 或 base64>'
```

命令启动后由用户在隐藏输入中填写 API Key。不得要求用户把 Key 发到对话里。

以下情况必须停止，不能为了“兼容”动态执行代码：

- 只有异步任务轮询、WebSocket、浏览器登录或签名算法，当前适配器无法表达。
- 需要上传输入图片、编辑图片、批量生成或视频生成。
- Endpoint 不是公网 HTTPS，或包含 URL 凭据、localhost、私网地址。
- 需要白名单之外的自定义 Header。
- 响应无法通过受限点路径提取一个 URL 或 Base64 图片。

Seedance 是视频生成模型，不属于本 Skill 的图片生成渠道。

## 审核绑定

ThinkAI 为兼容旧流程，审核哈希只绑定精确 Prompt。其他渠道的审核哈希绑定：

- 精确 Prompt
- 渠道 ID
- 实际模型
- 规范化尺寸
- 质量参数

Prompt 或任一执行条件变化后必须重新展示并重新获得批准。

## 共同安全边界

- 所有凭据只写入本 Skill 的 `config.json`，权限为 `0600`。
- API Key 不得进入对话、命令参数、日志、快照、案例或注册表。
- 付费生成 POST 只发送一次，不自动重试。
- 超时、断线或结果不明确时，先让用户检查所选渠道后台。
- 响应快照必须移除 Base64 大字段和签名 URL 查询参数。
- URL 下载失败或不完整时才使用系统 `curl` 兜底；完整 URL 必须作为一个参数传递。
