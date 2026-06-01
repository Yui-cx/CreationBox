# CreationBox 开发与迭代记录

本文档用于持续记录 CreationBox 后续开发、架构调整、功能迭代、缺陷修复和发布验证情况。每次较完整的改动建议新增一条记录，避免需求、实现和验证过程散落在聊天或临时代码中。

## 记录规范

- 每次迭代按时间倒序追加到“迭代记录”。
- 每条记录必须写清：目标、变更范围、影响面、验证结果、遗留问题。
- 涉及数据库、接口、配置、部署方式的变更，必须补充“架构/工程备注”。
- 涉及用户可见体验的变更，必须补充“产品/交互备注”。
- 未验证或验证失败的内容不得写成已完成。

## 当前基线

| 项目 | 内容 |
| --- | --- |
| 当前阶段 | MVP 初版 |
| 前端技术栈 | React + TypeScript + Vite + TanStack Query + Zustand |
| 后端技术栈 | FastAPI + SQLAlchemy |
| 数据存储 | PostgreSQL，开发/测试可使用 SQLite |
| 缓存/限流 | Redis |
| 部署方式 | Docker Compose + Nginx |
| AI 接入 | OpenAI-compatible Provider 抽象，默认 DeepSeek，支持 OpenRouter 切换，未配置密钥时 fallback mock |
| 认证方式 | 账号密码注册/登录，JWT access token + refresh token |
| 核心功能 | 三工具生成、SSE 流式输出、每日额度、历史记录、复制、Markdown 导出 |

## 迭代记录

### 2026-05-28 / 图片水印去除一阶段 OpenCV 效果增强

**目标**

在不引入 LaMa 等重型模型的前提下，提升现有 OpenCV 极速修复模式对水印边缘残留的处理效果。

**主要变更**

- 后端新增 mask 预处理流程：二值化、闭运算、膨胀、轻微模糊后重新二值化。
- 后端默认修复半径从 `3` 调整为 `5`。
- 前端图片水印去除页默认半径同步为 `5`。
- 前端补充极速修复说明，提示当前模式适合小水印、角落 Logo 和简单背景。
- 新增后端测试，验证 mask 预处理会扩大标记区域，降低边缘残留概率。

**架构/工程备注**

- 本次仍使用 `cv2.inpaint`，未引入 LaMa 或异步任务。
- API 形态不变，仍为 `POST /api/images/inpaint`。
- 增强策略会让实际修复区域略大于用户标记区域，这是为减少残影做的有意取舍。

**产品/交互备注**

- 用户仍使用原有画笔/矩形标记，不增加新操作成本。
- 页面文案明确默认半径 5 会扩大修复覆盖范围以减少边缘残留。

**验证结果**

- 后端测试：`pytest -q backend/tests/test_api.py` 通过，13 个测试通过。
- 前端构建：`npm run build` 通过。
- 浏览器检查：图片水印去除页显示默认半径 5、OpenCV 边缘清理说明，并且当前视口无横向溢出。

**风险与回滚**

- 风险：标记区域扩大可能会影响水印周边的细节纹理。
- 回滚：移除 `_prepare_inpaint_mask`，恢复直接使用原始二值 mask，并将默认半径改回 `3`。

**遗留问题**

- 复杂背景、大面积半透明水印仍建议后续接入 LaMa 高清修复模式。

### 2026-05-28 / 默认管理员账号与无限额度

**目标**

将登录模块调整为默认管理员账号模式，不再开放用户注册，并让默认管理员不限次数使用生成能力。

**主要变更**

- 后端启动时自动创建或修正默认管理员账号：`admin/admin`。
- 禁用 `POST /api/auth/register`，返回 `REGISTRATION_DISABLED`。
- 登录接口仅允许默认管理员用户名登录，旧的普通用户账号不再可登录。
- 默认管理员的额度返回无限标记，生成前不扣减每日额度。
- 前端登录页移除注册切换，默认填入 `admin/admin`。
- 前端侧边栏额度展示改为“使用次数：无限”。

**架构/工程备注**

- 无限额度使用 `quota_total=-1`、`quota_remaining=-1` 作为后端到前端的哨兵值。
- 启动时会更新默认管理员密码哈希，确保本地数据库中已有 admin 时也能使用新默认密码。
- 测试环境强制 `AI_PROVIDER=mock`，避免自动测试调用真实模型。

**产品/交互备注**

- 登录页文案改为默认管理员账号，不再展示注册入口。
- 默认账号适合 MVP 演示和内部使用，生产环境应改强密码或恢复正式账号体系。

**验证结果**

- 后端测试：`pytest -q backend/tests/test_api.py` 通过，7 个测试通过。
- 前端构建：`npm run build` 通过。
- 接口验证：`admin/admin` 登录成功，`/api/me` 返回 `quota_total=-1`、`quota_remaining=-1`。
- 浏览器检查：登录页默认填入 `admin/admin`，无注册入口。

**风险与回滚**

- 风险：默认弱密码不适合公网环境。
- 回滚：恢复注册接口和普通额度扣减逻辑，删除启动时默认管理员初始化。

**遗留问题**

- 后续上线前建议把默认密码改为环境变量强密码，或接入正式管理员账号管理。

### 2026-05-28 / 登录 token 失效处理优化

**目标**

修复切换 `.env` 中 `JWT_SECRET` 后，浏览器旧登录态继续请求导致“INVALID_TOKEN”的体验问题。

**主要变更**

- 前端普通 API 请求遇到 401 或 `INVALID_TOKEN` 时自动清空本地登录态。
- 前端 SSE 生成请求遇到 401 或 `INVALID_TOKEN` 时自动清空本地登录态。

**架构/工程备注**

- 错误来源为 JWT 签名密钥变化后的旧 token 失效，不是 DeepSeek Provider 错误。
- 本次未修改后端鉴权逻辑，只优化前端失效态恢复。

**产品/交互备注**

- 用户刷新页面后会回到登录页，重新登录即可继续生成。

**验证结果**

- 前端构建：`npm run build` 通过。
- 后端测试：`pytest -q backend/tests/test_api.py` 通过，6 个测试通过。
- 浏览器检查：刷新后旧登录态被清理，页面回到登录入口。

**风险与回滚**

- 风险：401 会统一触发登出，后续如果有非鉴权型 401 需细分。
- 回滚：移除 `clearAuthOnUnauthorized` 调用。

**遗留问题**

- 后续可增加 refresh token 自动续期，减少 access token 过期带来的重新登录。

### 2026-05-28 / 真实大模型接入与 Provider 切换

**目标**

将 AI 生成从默认 mock 升级为默认对接 DeepSeek，并支持通过环境变量切换到 OpenRouter。

**主要变更**

- 后端配置默认 `AI_PROVIDER=deepseek`。
- 新增 DeepSeek 专用配置：`DEEPSEEK_BASE_URL`、`DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL_TEXT`、`DEEPSEEK_THINKING_ENABLED`、`DEEPSEEK_REASONING_EFFORT`。
- 新增 OpenRouter 专用配置：`OPENROUTER_BASE_URL`、`OPENROUTER_API_KEY`、`OPENROUTER_MODEL_TEXT`、`OPENROUTER_HTTP_REFERER`、`OPENROUTER_APP_TITLE`、`OPENROUTER_REASONING_ENABLED`。
- 保留通用 `openai-compatible` Provider，便于后续接入其他兼容 Chat Completions 的模型服务。
- SSE 解析兼容 usage-only chunk，避免 OpenRouter/兼容服务返回空 `choices` 时中断。
- `.env.example`、`.env`、`README.md` 更新为 DeepSeek 默认配置。

**架构/工程备注**

- 业务层仍只依赖 `AIProvider` 抽象，不直接感知 DeepSeek/OpenRouter。
- Provider 切换通过服务端环境变量完成，避免把模型密钥或任意 Provider 选择暴露给前端。
- 未配置所选 Provider 密钥时仍 fallback 到 mock provider，方便本地无密钥启动。
- OpenRouter 可选 `HTTP-Referer` 和 `X-Title` 请求头只在配置后发送。
- 本地开发时后端从 `backend` 目录启动，配置读取已兼容项目根目录 `.env` 和 `backend/.env`。

**产品/交互备注**

- 前端交互不变，用户仍从三类智能创作工具发起生成。
- 当前版本不提供页面内切换模型；切换 Provider 需要调整 `.env` 并重启后端。

**验证结果**

- 后端测试：`pytest -q` 通过，6 个测试通过。
- 前端构建：`npm run build` 通过。
- 服务重启后健康检查：`GET /health` 返回 `{"status":"ok"}`。
- 当前 `.env` 已选择 `deepseek`；因未配置 `DEEPSEEK_API_KEY`，运行时按设计 fallback 到 mock provider。
- 已配置本地 DeepSeek Key 后复验：运行时 Provider 为 `deepseek`，模型为 `deepseek-v4-flash`。

**风险与回滚**

- 风险：真实 Provider 的模型名、余额、区域网络或限流会影响生成稳定性。
- 回滚：将 `.env` 中 `AI_PROVIDER` 改为 `mock`，重启后端即可恢复本地 mock。

**遗留问题**

- 后续可增加后台配置页，支持管理员在页面内切换 Provider 和模型。
- 后续可把真实 token usage 写入 `model_call_logs`，替换当前按文本长度估算的用量。

### 2026-05-27 / AI痕迹去除结果与 Markdown 富文本展示调整

**目标**

精简 AI痕迹去除生成结果，只展示优化后正文，并让输入和结果支持 Markdown 富文本显示。

**主要变更**

- AI痕迹去除后端 prompt 调整为只输出优化后正文。
- AI痕迹去除 mock provider 调整为基于输入做轻量优化，并尽量保留原始 Markdown 结构。
- 移除 AI痕迹去除结果中的编辑建议、处理前/处理后、编辑洞察。
- 前端新增轻量 Markdown 渲染组件，支持标题、列表、引用、行内代码、粗体、斜体、代码块等常用 Markdown。
- AI痕迹去除输入区新增 Markdown 富文本预览。
- AI痕迹去除生成结果改为富文本渲染，不再以纯 `pre` 文本块展示。

**架构/工程备注**

- 本次未新增第三方 Markdown 依赖，使用 React 节点渲染，避免直接注入 HTML。
- 后端 API 结构不变，仍通过 SSE 返回文本流。
- 历史记录仍保存 Markdown 原文，展示时可继续复用现有字段。

**产品/交互备注**

- 用户输入普通文本或 Markdown 均可预览排版。
- 生成结果只保留正文，降低结果区噪音。
- 文案继续避免“检测规避”承诺。

**验证结果**

- 前端构建：`npm run build` 通过。
- 后端测试：`pytest -q` 通过。
- 浏览器检查：Markdown 输入预览可显示标题和列表；生成结果富文本显示；结果中不再出现编辑建议、处理前/处理后、编辑洞察。

**风险与回滚**

- 风险：当前 Markdown 渲染器覆盖常用语法，不是完整 CommonMark 实现。
- 回滚：恢复纯文本 `pre` 输出，并将 humanize prompt 改回结构化多块结果。

**遗留问题**

- 后续如需完整 Markdown 能力，可引入成熟渲染库并增加 XSS 安全策略。

### 2026-05-26 / 左侧导航与历史记录页面调整

**目标**

将智能创作功能整理为左侧一级模块下的二级目录，并把历史记录从功能工作区移到独立页面。

**主要变更**

- 左侧菜单新增一级入口“历史记录”。
- 左侧菜单新增一级模块“智能创作”，将“AI痕迹去除”“公众号文章仿写”“生成文章”作为二级功能放入该模块。
- 移除创作工作区右侧的内嵌历史记录栏，工作区仅保留输入面板和结果面板。
- 新增独立历史记录页面，并按三个智能创作功能分类展示历史记录。
- 历史记录页面支持载入历史结果、导出 Markdown、删除记录。

**架构/工程备注**

- 本次为前端结构调整，未修改后端 API 和数据库结构。
- 使用 `activeView` 区分“智能创作”和“历史记录”页面，历史记录仍复用现有 `/api/generations`、删除和导出接口。

**产品/交互备注**

- 历史记录不再占用功能操作区域，降低创作页面的信息密度。
- 移动端保留横向导航，增加“历史记录”入口。

**验证结果**

- 前端构建：`npm run build` 通过。
- 浏览器检查：桌面左侧出现“历史记录”和“智能创作”，功能区不再显示历史列表。
- 历史记录页面检查：按 AI痕迹去除、公众号文章仿写、生成文章分类展示。

**风险与回滚**

- 风险：移动端横向导航入口增多，窄屏需要横向滑动。
- 回滚：恢复 `HistoryPanel` 内嵌工作区，并移除 `activeView` 页面切换。

**遗留问题**

- 历史记录筛选、搜索和分页仍待后续完善。

### 2026-05-26 / MVP 初版落地

**目标**

将静态原型升级为可运行的全栈 MVP，形成前端、后端、数据库、缓存和容器部署闭环。

**主要变更**

- 新增 `backend` FastAPI 服务。
- 新增 `frontend` React 工作台。
- 新增 Docker Compose 编排：`postgres`、`redis`、`api`、`frontend`、`nginx`。
- 新增账号密码注册/登录、JWT 鉴权、每日免费额度。
- 新增 `POST /api/generations/stream` SSE 流式生成接口。
- 新增生成历史查询、详情、删除和 Markdown 导出接口。
- 新增 AI Provider 抽象，支持 mock provider 和 OpenAI-compatible provider。
- 新增 README、环境变量示例和基础测试。

**架构/工程备注**

- 首版暂不引入消息队列，生成请求由 API 进程直接流式处理。
- Redis 用于登录限流和用户生成锁，避免同一用户重复并发生成。
- 数据库表在 FastAPI lifespan 中自动创建，适合 MVP；生产化前建议引入 Alembic 迁移。
- bcrypt 直接使用官方 `bcrypt` 包，避免 `passlib` 与新版 bcrypt 的兼容问题。
- `.env` 未配置 `AI_API_KEY` 时自动使用 mock provider，便于本地演示和验收。

**产品/交互备注**

- 保留原型工作台结构：左侧工具导航、顶部状态栏、输入面板、结果面板、历史记录。
- 继续避免“保证通过检测”“规避检测”等承诺性文案。
- 移动端使用横向工具切换，无横向页面溢出。

**验证结果**

- 后端测试：`pytest -q` 通过，覆盖注册/登录、`/api/me`、SSE 生成、历史隔离。
- 前端构建：`npm run build` 通过。
- 浏览器冒烟：注册、进入工作台、SSE 生成、额度扣减、历史记录写入通过。
- 移动端 390px：无横向溢出。

**遗留问题**

- 未接入真实链接抓取。
- 未接入 PDF/txt/markdown 文件解析。
- 未实现支付、会员套餐、运营后台。
- 未引入 Alembic 数据库迁移。
- 未实现 refresh token 自动续期拦截器。
- 前端暂无系统化组件测试和 E2E 自动化测试。

## 后续待办池

| 优先级 | 类型 | 事项 | 备注 |
| --- | --- | --- | --- |
| P0 | 工程 | 引入 Alembic 迁移 | 替代启动时自动建表 |
| P0 | 安全 | 增加 refresh token 自动续期和退出登录撤销 | 完善账号闭环 |
| P0 | AI | 记录真实 provider token usage 和成本 | 需解析各 Provider usage chunk |
| P1 | 产品 | 历史记录详情页/侧栏展开 | 支持复用历史输入 |
| P1 | 工程 | 增加前端组件测试和 Playwright E2E | 覆盖注册到生成闭环 |
| P1 | 数据 | 增加模型调用成本统计 | 支撑后续会员定价 |
| P1 | 能力 | 链接正文抓取与清洗 | 新闻、博客、公众号分阶段支持 |
| P1 | 能力 | txt/markdown/pdf 文件解析 | 先支持 txt/md，再支持 PDF |
| P2 | 产品 | 模板库与常用风格 | 登录后保存用户偏好 |
| P2 | 商业化 | 套餐、支付、消耗流水 | MVP 数据验证后再做 |

## 新迭代记录模板

### YYYY-MM-DD / 迭代标题

**目标**

- 

**主要变更**

- 

**架构/工程备注**

- 

**产品/交互备注**

- 

**验证结果**

- 

**风险与回滚**

- 

**遗留问题**

- 
