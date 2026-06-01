# CreationBox MVP 系统架构方案

## Summary

基于现有静态原型，将 CreationBox 升级为可上线 MVP：React + FastAPI + PostgreSQL + Redis + Docker Compose。首版聚焦三类文本生成工具、账号密码登录、每日额度、SSE 流式生成、默认保存历史记录；链接抓取、文件解析、支付会员、批量处理和在线编辑器进入后续版本。

核心原则：先做低成本闭环，避免一开始上 K8s、消息队列和复杂多模型路由；但在后端保留 AI Provider 抽象，方便后续切换模型或扩展多模型。

## Key Changes

- 前端：使用 React + TypeScript + Vite，保留当前原型的信息架构和三工具工作台布局。
- 状态管理：服务端数据用 TanStack Query，本地 UI 状态用轻量 Zustand 或 React Context。
- 后端：FastAPI 提供认证、用户额度、生成任务、历史记录和 SSE 流式输出。
- 数据库：PostgreSQL 存用户、额度、生成记录、模型调用日志；Redis 做登录限流、额度短缓存、SSE 生成锁。
- AI 接入：实现统一 AIProvider 接口，首版通过环境变量配置 AI_BASE_URL / AI_API_KEY / AI_MODEL_TEXT，默认按 OpenAI-compatible Chat Completions 协议适配。
- 部署：Docker Compose 编排 frontend / api / postgres / redis / nginx，后续可平滑迁移到 K8s。

## Public APIs

- POST /api/auth/register：账号密码注册。

- POST /api/auth/login：登录并返回 access token / refresh token。

- POST /api/auth/refresh：刷新 token。

- GET /api/me：获取用户信息、今日剩余额度。

- POST /api/generations/stream

  ：SSE 流式生成。

  - 入参：tool_type 为 humanize | imitate | generate，mode 为对应工具模式，input_text/input_url/topic/materials/config 按工具传入。
  - 返回事件：metadata、delta、usage、done、error。

- GET /api/generations：分页查询历史记录。

- GET /api/generations/{id}：查看单条生成记录。

- DELETE /api/generations/{id}：用户删除自己的历史记录。

- POST /api/generations/{id}/export-markdown：返回 Markdown 文本或下载响应。

## Data Model

- users：账号、密码哈希、状态、创建时间、最后登录时间。
- daily_quotas：用户 ID、日期、总额度、已用额度，唯一键 (user_id, date)。
- generations：用户 ID、工具类型、模式、输入快照、配置快照、输出内容、状态、token 用量、耗时、错误信息。
- model_call_logs：generation ID、provider、model、prompt token、completion token、成本估算、请求状态。
- 索引：
  - users.username/email 唯一索引。
  - daily_quotas(user_id, date) 唯一索引。
  - generations(user_id, created_at desc) 支撑历史分页。
  - model_call_logs(generation_id) 支撑问题追踪。

## Implementation Details

- 认证：账号密码登录，密码使用 argon2 或 bcrypt 哈希；JWT access token 短有效期，refresh token 服务端可撤销。
- 额度：生成前在数据库事务内校验并扣减额度；失败时按错误类型回滚或补偿，避免并发多扣。
- SSE：后端边接收模型流边写入客户端；同时聚合完整输出，结束后落库。
- 异常处理：统一错误码，例如 QUOTA_EXCEEDED、VALIDATION_ERROR、AI_PROVIDER_TIMEOUT、AI_PROVIDER_RATE_LIMIT。
- 安全：所有历史记录按 user_id 隔离查询；输入输出落库前做长度限制；管理密钥只放服务端环境变量。
- 成本控制：首版不引入消息队列；Redis 仅做限流和短缓存；长文本限制沿用 PRD：极速 600 字、长文本 2500 字。
- 前端体验：保持当前空态、加载态、成功态、错误态；生成时使用 SSE 增量渲染，完成后启用复制、导出、重新生成。
- 合规文案：继续避免“保证绕过检测”“规避检测”等承诺性表达。

## Test Plan

- API 单测：注册、登录、token 刷新、鉴权失败、越权访问历史记录。
- 额度测试：正常扣减、额度不足、并发双击生成只扣一次或按真实成功次数扣减。
- SSE 测试：正常流式输出、模型超时、客户端断开、provider 报错。
- 数据库测试：历史分页按时间倒序、用户数据隔离、删除后不可见。
- 前端测试：三工具各模式表单显隐、字数/必填校验、SSE 增量渲染、复制和 Markdown 导出。
- E2E 场景：注册登录 -> 生成文章 -> 查看历史 -> 导出 Markdown -> 删除历史。
- 移动端验收：390px 宽度无横向滚动，工具切换、输入、生成、结果操作可用。

## Assumptions

- 首版不做真实链接抓取和 PDF 正文解析；相关入口可以保留，但提示“即将支持”或仅做文本类能力。
- 首版不做支付和会员套餐，只做每日免费额度。
- AI Provider 使用 OpenAI-compatible 协议封装，具体模型通过环境变量配置。
- 部署优先单机 Docker Compose；高可用方案等用户增长后再升级。