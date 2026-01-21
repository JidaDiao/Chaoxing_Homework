# Research: Playwright 架构升级

## Decision 1: 浏览器自动化框架
- **Decision**: 使用 Playwright 异步 API 作为唯一浏览器自动化方案
- **Rationale**: 与迁移目标一致，支持异步并发与上下文复用，降低同步/异步混用风险
- **Alternatives considered**: Selenium 同步模式、Selenium + 线程池

## Decision 2: 并发控制策略
- **Decision**: 使用 asyncio 并发 + `Semaphore` 限流，默认并发 > 8
- **Rationale**: 高并发满足批量作业处理效率要求，同时避免无限并发导致资源耗尽
- **Alternatives considered**: ThreadPoolExecutor、多进程、无上限并发

## Decision 3: 浏览器生命周期管理
- **Decision**: 通过 `BrowserManager` 统一管理浏览器、上下文与共享 cookies
- **Rationale**: 复用上下文减少启动开销，集中管理避免资源泄露
- **Alternatives considered**: 每次任务独立创建浏览器实例

## Decision 4: 输出结果处理策略
- **Decision**: 输出路径存在时覆盖同名结果
- **Rationale**: 保持当前用户习惯与批改模块兼容，避免旧数据残留
- **Alternatives considered**: 版本化输出、存在则跳过

## Decision 5: 日志与隐私
- **Decision**: 日志脱敏，不记录学生姓名与作答内容
- **Rationale**: 降低敏感信息暴露风险，同时保留必要的错误与流程信息
- **Alternatives considered**: 记录姓名、不脱敏完整日志

## Decision 6: 迁移期间旧文件处理
- **Decision**: 迁移过程中立即删除旧 Selenium 文件
- **Rationale**: 避免双实现并存导致维护混乱与误用
- **Alternatives considered**: 迁移验证后删除、长期保留

## Decision 7: 失败处理策略
- **Decision**: 登录失败立即退出；单个作业失败不影响其他任务
- **Rationale**: 登录失败后继续爬取无意义；任务级隔离保证整体吞吐
- **Alternatives considered**: 登录重试、失败后降级仅导出列表

## Decision 8: 测试方式
- **Decision**: 采用现有手工脚本进行回归验证
- **Rationale**: 当前工程缺少统一测试框架，已有脚本可作为最小可行验证
- **Alternatives considered**: 追加 pytest 测试套件
