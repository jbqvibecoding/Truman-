# PRD v2.0 — Truman 平台 (通用 Auto-Research × Persona Simulation)

> 版本 v2.0 (平台级) · 上一版 v1.0 见 `docs/PRD-ad-creative-vertical.md` (vertical 级, 保留作参考)
> 状态: 设计完成 · M0 (引擎 + 2 个 vertical) 已实现 · M1 起为后续开发

## 0. 本版相对 v1 的升级要点

v1 是把 AdCreative 当成"框架的第一个垂直"来写。v2 把视角拉高到产品 / 平台级:

- 把 **AdCreative** 重新定位为"平台所支持的多个垂直之一", 与软件工程 / 病毒传播 / 销售话术等并列
- 引入 **Eval Engine** (binary 黄金法则 + AI 推荐 + 模板库) 作为产品差异化核心
- 引入 **Persona Library + Cohort** 作为可复用资产, 模拟范围拓展到选举 / Reddit / 销售客户等
- 引入 **Evolution Changelog** 作为最终交付的一部分 (不只给"达标产物", 还给"为什么这样改有效"的可解释经验)
- 明确产品入口流: "AI 团队交付 / 用户上传" → "勾选 Auto Research" → "AI 推荐 + 用户编辑 Eval" → "自动迭代到达标"

## 1. 产品定位

### 1.1 一句话

**"任何 AI 交付物 → 套上量化目标 (binary Eval) + 真实世界 Persona 模拟 → 自动迭代直到达标"**

### 1.2 类比

- AutoResearch 给 ML 预训练套上 hill-climbing → 自动改 GPT
- Truman 给**任何 AI 交付物**套上 hill-climbing + Persona 模拟 → 自动改 task output

### 1.3 我们解决的核心问题

- AI multi-agent 团队能产出, 但**交付质量难量化、难复现、难持续改进**
- 缺三件事: 缺"好的定义" (Eval), 缺"真实反馈" (Persona Simulation), 缺"自动改进回路" (Auto-Research Loop)
- Truman = 这三件事的整合, 让 "AI 写完就完了" → "AI 写完 → 自动测试人群反应 → 自动改 → 达标"

### 1.4 五大差异化 (Moat)

1. **Persona-rich 真实世界模拟** — 投放 / 上线 / 发布前的"数字风洞", 可模拟从美国选民到 Web3 Degen 任意人群
2. **Binary Eval 黄金法则** — yes/no 评估稳定可靠, 拒绝量表叠加波动 (详 §4.2 与 `docs/eval-guide.md`)
3. **AI 推荐 + 用户可编辑 Eval** — 普通用户也能写出靠谱 Eval, 不需要"指标设计师"
4. **Evolution Changelog** — 改进史本身就是产物, 可解释 + 可审计 + 可作经验沉淀
5. **Vertical Registry** — 同一引擎一次开发跨场景复用, 加新场景 = 加新模块, 不动主循环

## 2. 用户与七大应用域

### 2.1 目标用户

增长 / 广告创意 / 内容运营 / 销售 / 产品 / 工程 / 客服 — 凡是用 AI 生产内容 / 代码 / 方案的角色。

### 2.2 七大应用域 (A–G)

| 代号 | 域 | 典型目标 | 代表 Binary Eval (示例) | 典型玩法 |
| --- | --- | --- | --- | --- |
| **A 软件工程** | merge-ready code | 测试是否全绿? · 是否无 TODO? · 5 维加权 ≥ 9.0? (正确 35 / 测试 25 / 质量 20 / 安全 10 / 性能 10) | GitHub Issue → AI 实现 → 跑测试 + 多维评分 → 达标自动 PR + merge |
| **B 广告创意** | CTR / ROAS / 转化 | hook 是否在前 2 秒抛出? · CTA 是否唯一? · 标题是否含数字 / 卖点? · 预测 CTR ≥ 0.X? | 多版素材 × 5 分群模拟 → 留高分版本 |
| **C 病毒传播** | 转发 / 争议 / 二创 | 前 3 行是否抓人? · 争议性是否够? · 信息密度是否高? | 多版内容 × Reddit / Twitter / 小红书 / 黑粉 / KOL / 路人模拟 |
| **D 增长内容优化** | CTR / CVR / 留存 / SEO 排名 | 首屏价值传达? · CTA 清晰? · 标题具体? · 表单字段 ≤ 3? | 落地页 / 邮件 / SEO / 社媒同 B+C 模式, 域级模板复用 |
| **E 销售话术** | 约见 / 成交 / 续费 | 是否识别痛点? · CTA 是否明确? · 是否不过度推销? | 模拟潜客评分 → 优化 cold call / proposal / objection handling |
| **F 产品文档** | 可执行 / 减歧义 / 覆盖边界 | 目标是否清晰? · 用户故事是否完整? · 验收标准是否可测? | 模拟开发阅读 → 评分 → 改稿 |
| **G 运营流程** | 点击 / 加购 / 留存 | 商品页 / 活动页 / 推送的 yes/no 检查 | 模拟用户路径 → 找卡点 → 改 |

### 2.3 三个串联实例

- **新品广告上线 (B)**: 5 版创意 × 5 分群模拟 → 只投得分最高的 1–2 版
- **GitHub Issue 自动合并 (A)**: Issue → AI 写 PR → 跑测试 + 模拟代码评审 → 5 维 ≥ 9.0 → 自动 merge
- **选举核心主张测试 (跨域)**: 候选话术 N 版 × 美国 swing-state persona 群 → 找支持率最高的主张

## 3. 端到端用户流程

```
[Task 来源]                      [产品交互]                          [系统行为]
AI multi-agent 交付          ──┐
                               ├──> 勾选 Auto Research  ──>  AI 推荐 3-6 个 binary Eval
用户手动上传交付物           ──┘    设置 goal / 阈值 / 预算          用户增删 / 改文案 / 改阈值 / 改权重
                                                                ↓
                                                       选 Vertical + Cohort + Scene
                                                                ↓
                                  ┌──── Auto-Research Loop (复用 TrumanEngine) ──┐
                                  │ research → plan → create →                   │
                                  │ simulate (Persona World) →                   │
                                  │ run Evals (binary) → composite score →       │
                                  │ ledger → revise (灌入 feedback)              │
                                  │      ↑________________________↓             │
                                  └─ 达标 ∨ 预算耗尽 ∨ plateau ∨ max_iter 终止 ──┘
                                                                ↓
                                              达标产物 + Evolution Changelog
```

## 4. 核心功能模块

### 4.1 Task Intake (任务接入, 新)

- **来源 1**: AI multi-agent 团队 callback / webhook (我方主动接 或 团队主动 push)
- **来源 2**: 用户手动上传 (Markdown / 图片 / 视频 / 链接 / PDF / 代码 patch)
- **类目识别**: 自动推断 task 类目 → 推荐对应 Vertical + Eval 模板
- **数据结构**: `TaskIntake{source, category, payload, user_goal}`

### 4.2 Eval Engine ⭐ (差异化核心 1)

#### 4.2.1 黄金法则

- 每个 Eval **必须是 yes/no** (不是 1-7 量表, 不是"感觉判断")
- 推荐 **3-6 个 Eval** (超过 6 会被 Worker 钻空子; 少于 3 信号不足)
- Eval 必须**独立** (不能两个测同一维度, 否则重复计数)
- Eval 必须**可观测** (可被 LLM judge / regex / 长度 / 范围 / 代码运行稳定回答)
- **理由**: 量表会叠加波动, 4 个量表 Eval 的总分在不同运行间方差极大; 二元 Eval 才能给稳定信号

> 详细 Eval 设计指南见 `docs/eval-guide.md`

#### 4.2.2 校验类型 (`check_kind`)

| 类型 | 用途 | 例子 |
| --- | --- | --- |
| `llm_judge` | 主观但二元的判断 | "开头是否含具体时间 / 地点?" |
| `regex` | 禁用词 / 关键词 | "是否完全不含 [禁用词]?" |
| `length` | 字数 / 行数范围 | "正文是否在 150-400 字?" |
| `range` | 连续指标包装为二元 | "ctr 是否 ≥ 0.6?" (复用底层 metric) |
| `code` | 代码可运行 / 测试通过 | "pytest 是否全绿?" |
| `composed` | 多条件 AND / OR | "(含 CTA) ∧ (字数 ≤ 400)" |

#### 4.2.3 Eval 模板库 (按域预置, M2)

按 7 大域分类预置 30-60 个 binary Eval 模板, 用户一键引入再做个性化编辑。示例:

- **B 广告创意**: hook-in-2s / CTA-唯一 / 含数字或具体卖点 / 平台合规 / 预测 CTR ≥ 0.X
- **D 落地页**: 首屏价值传达 / CTA 清晰 / 无干扰元素 / 表单字段 ≤ 3
- **D 邮件**: 标题具体 / 个性化 / 明确下一步 / 不过度营销
- **A 软件工程**: 测试全绿 / 无 TODO / 函数命名描述性 / 无安全 lint warning / 性能 budget 内
- **C 病毒**: 前 3 行钩子 / 争议性 / 信息密度 / 平台适配
- **E 销售**: 痛点识别 / CTA 明确 / 无过度推销
- **F PRD**: 目标清晰 / 用户故事完整 / 验收标准可测

#### 4.2.4 AI 推荐 + 用户编辑流程

1. 用户描述 task 类目 + goal → LLM 推荐 3-6 个 binary Eval (检索模板 + 个性化生成)
2. 前端 UI 列出推荐 → 用户可: 增 / 删 / 改文案 / 改阈值 (range / length) / 改权重 / 切换 `check_kind`
3. 系统反模式提示: > 6 个 → 警告"会被钻空子"; 写成量表 → 强制改为二元

#### 4.2.5 评分聚合

- 每个 Eval 返回 `bool` (passed / failed)
- 加权: `score = Σ(weight_i × passed_i) / Σ(weight_i)`, 范围 0-1
- 与 `threshold` 比较 → deliver / revise

#### 4.2.6 与 v1 连续 metric 的兼容策略

- v1 的 `SuccessCriterion` (连续, 如 ctr / dwell / sentiment) **保留作为底层 soft 信号**
- 在 v2 的 `EvalQuestion(check_kind=range)` 里通过 "ctr ≥ X" 包装为二元
- `GoalConfig` 同时支持 `criteria` (旧) 与 `evals` (新), 二者可共存; 文档优先引导新写法

### 4.3 Persona Simulation ⭐⭐ (差异化核心 2)

#### 4.3.1 Persona Library (新, M3)

- **模板维度**: 平台 (TikTok / 小红书 / X / Reddit / B 站 / ...) × 国家 × 年龄 × 职业 × 价值观
- **派生**: 模板 → LLM 个性化 → Persona 实例 (复用 `build_personas` / `build_personas_llm`)
- **用户自定义**: CSV / JSON 上传或前端表单填写

#### 4.3.2 Cohort (人群组合)

- 每个 vertical 配套一个 Cohort 模板:
  - **B 广告**: `standard_5_segments` (小红书 / TikTok / 美国宝妈 / Web3 Degens / GenZ)
  - **C 病毒**: `social_6_segments` (Reddit / Twitter / 小红书女生 / Web3 KOL / 黑粉 / 路人)
  - **选举跨域**: `us_swing_states` (PA / MI / WI / GA / AZ swing voters)
- 用户可调整 Cohort 组成 / 人数权重 / 各 segment 持有比例

#### 4.3.3 Scene Builder

- 复用 WorldSeed `SceneConfig` (in-memory)
- 持有 artifact entity + 计数器 + 决策动作集
- 每垂直一个 scene 模板 (`build_*_scene`)

#### 4.3.4 双层 DM 架构

- **Persona Decider**: 角色扮演决策 (engage / skip / 哪种 action + 一句话 reaction)
- **Evaluator DM**: 预测量化反馈 (CTR / dwell / 转发 / 评分), 累加到 artifact 计数器

### 4.4 Auto-Research Loop (复用 + 升级停止条件)

- **完全复用** `TrumanEngine.run()`
- **autoresearch 纪律**: keep-only-improvement (上轮分数更高才保留, 否则只记 reject)
- **反馈驱动迭代**: 上轮 judge feedback + weaknesses 直接灌入下轮 worker prompt (替代盲循环)
- **停止条件** (升级): `composite ≥ threshold` ∨ `iter ≥ max_iterations` ∨ `plateau (连续 K 轮无改进)` ∨ `budget_tokens 耗尽`

### 4.5 Vertical Registry (复用)

- **已实现** (M0): `HeadlineVertical`, `AdCreativeVertical`
- **每垂直 = 七件套**: Research + Creative + Persona/Cohort + Decider + Evaluator + Scene + Metrics
- **加新垂直**: 一个 `src/truman/verticals/<name>.py` + 一个 `register()` 调用, 主循环零改动

### 4.6 Evolution Changelog ⭐ (差异化核心 3, 新, M4)

#### 4.6.1 数据结构

完整进化树, 每个 candidate 记录:

- `iteration / parent_iteration` — 进化链
- `diff` — vs 上轮 artifact 字段级 diff
- `score / per_eval` — 总分 + 每个 binary Eval pass / fail
- `feedback` — judge 给出的修改建议
- `rationale` — worker 说明"本轮为什么这样改"
- `status` — kept / rejected / delivered
- `cost` — tokens / wall-time

#### 4.6.2 用户价值

- 一份 changelog 一目了然: "改了什么 / 为什么改 / 效果如何 / 哪些尝试没用"
- 可解释 + 可审计 + 可学习
- 用户能从 changelog 总结出"什么风格的 hook 对哪类人群有效", 形成可复用经验, 喂回下次任务的 worker prompt

#### 4.6.3 呈现 / 导出

- 前端: timeline + diff view (每轮折叠展开)
- 导出: Markdown / JSON / Slack 摘要

## 5. 数据契约

### 5.1 TaskIntake (新)

```python
@dataclass
class TaskIntake:
    source: Literal["ai_team", "user_upload"]
    category: str          # 自动识别 / 用户选
    payload: dict          # 原始交付物 (text / files / code patch / ...)
    user_goal: str         # 用户自由文本描述
```

### 5.2 EvalQuestion (新, 与旧 `SuccessCriterion` 共存)

```python
@dataclass
class EvalQuestion:
    id: str
    prompt: str                                                       # "标题是否含数字或具体卖点?"
    check_kind: Literal["llm_judge","regex","length","range","code","composed"]
    config: dict                                                      # check_kind 对应参数 (regex pattern / min-max / metric+op+value / ...)
    weight: float                                                     # 0-1
    category: str = "default"
```

### 5.3 GoalConfig 升级

```yaml
vertical: ad_creative
goal: "..."
threshold: 0.75
max_iterations: 6
budget_tokens: 200_000     # 新: 预算上限
plateau_window: 2          # 新: 连续 K 轮无改进则停
criteria: [...]            # 旧 (连续 metric, 保留)
evals:                     # 新 (binary)
  - {id: e1, prompt: "标题是否含数字或具体卖点?", check_kind: llm_judge, weight: 0.3}
  - {id: e2, prompt: "脚本是否在 60 字以内?", check_kind: length, config: {max: 60}, weight: 0.2}
  - {id: e3, prompt: "ctr 是否 ≥ 0.6 ?", check_kind: range, config: {metric: ctr, op: ">=", value: 0.6}, weight: 0.3}
  - {id: e4, prompt: "是否完全不含 [game-changer, here's the kicker]?", check_kind: regex, config: {forbid: [...]}, weight: 0.2}
scene:
  product: "..."
  cohort: standard_5_segments
```

### 5.4 ChangelogEntry (新, 升级 `IterationRecord`)

```python
@dataclass
class ChangelogEntry:
    iteration: int
    parent: int | None
    diff: dict                  # field-level diff vs parent
    score: float
    per_eval: dict[str, bool]   # binary Eval 结果
    feedback: str
    rationale: str              # worker 说明本轮为什么这样改
    status: Literal["kept","rejected","delivered"]
    cost: dict                  # {tokens_in, tokens_out, wall_seconds}
```

## 6. 技术架构 (复用 + 新增)

```
┌──────────────────────────────────────────────────────────┐
│ Intake → CategoryDetector → EvalRecommender (LLM+模板库) │  ← 新增
└──────────────────┬───────────────────────────────────────┘
                   ↓ GoalConfig (含 evals + cohort)
┌──────────────────────────────────────────────────────────┐
│ TrumanEngine (复用)                                      │
│   + Vertical Registry (复用)                             │
│   + EvalRunner (新: 跑 6 种 check_kind)                  │
│   + WorldSeed Simulation (复用)                          │
│   + ChangelogRenderer (新: timeline + diff + 导出)       │
└──────────────────┬───────────────────────────────────────┘
                   ↓
        达标产物 + Evolution Changelog (Markdown / JSON)
```

### 6.1 复用 (零改动)

- `src/truman/orchestrator/loop.py` (TrumanEngine 主循环)
- `src/truman/verticals/` (注册表 + 已有垂直)
- `src/truman/sim/` (WorldSeed 驱动)

### 6.2 轻量升级

- `src/truman/goal/schema.py` — 加 `evals: list[EvalQuestion]`, `budget_tokens`, `plateau_window`
- `src/truman/judge/scorer.py` — 加 binary Eval 适配器 (兼容 `criteria` + `evals` 双路)
- `src/truman/orchestrator/loop.py` — 停止条件加 budget / plateau / 多种停止原因

### 6.3 新增模块

- `src/truman/intake/` — TaskIntake + CategoryDetector
- `src/truman/eval/` — EvalQuestion schema + 6 种 EvalChecker + EvalRecommender + 模板库 loader
- `src/truman/personas/library/` — Persona / Cohort 模板库 + 用户自定义 loader
- `src/truman/changelog/` — Renderer + Exporter (markdown / json / slack)

## 7. 路线图

| 里程碑 | 内容 | 验收 |
| --- | --- | --- |
| **M0** ✅ | 通用引擎 + Headline + AdCreative + 连续 metric 评分 | 已交付, 10/10 test 通过 |
| **M1** | Eval Engine: binary schema + EvalRunner 6 种 check + scorer 兼容层 | 任一 vertical 可换成 binary Evals, demo 跑通 |
| **M2** | Eval Recommender + 模板库 v1 (B + D 两域 30+ 模板) | AI 推荐 3-6 个 Eval, 用户 UI 可编辑 |
| **M3** | Persona Library + Cohort 模板 + 用户自定义 persona 上传 | 5+ Cohort 模板, CSV / JSON 上传通路 |
| **M4** | Changelog v1 (timeline + diff + 导出) | 用户可查看完整进化史, Markdown 导出 |
| **M5** | 域扩展 1: SoftwareEng (A) + ViralContent (C) + 落地页 / 邮件 / SEO (D) | 新增 5+ vertical |
| **M6** | 域扩展 2: Sales (E) + Product (F) + Operations (G) | 新增 6+ vertical |
| **M7** | 真实数据回流: 投放 / 上线 KPI 反喂 Simulator 校准 | Simulator ↔ 真实 KPI 相关度 r ≥ 0.6 |
| **M8** | 投放 / 上线集成: 一键导出到 Meta Ads / GitHub PR / Notion | 端到端从想法到投放 |

## 8. KPI / 北极星

| 指标 | 定义 | 目标 |
| --- | --- | --- |
| **达标率** | 启动 Auto-Research 的 task 中, 预算内达 threshold 的比例 | ≥ 70% |
| **加速比** | vs 人工 A/B 的平均迭代加速倍数 | ≥ 5× |
| **Eval 接受率** | AI 推荐 Eval 直接采纳比例 | ≥ 60% |
| **Changelog 回看率** | 达标后用户查看 changelog 比例 | ≥ 50% |
| **Vertical 覆盖度** | 累积支持 vertical 数 / 月活 vertical 数 | 每季度 +3 |
| **Simulator 校准度** | 模拟分数 ↔ 真实 KPI 的相关系数 r | 长期 ≥ 0.6 |

## 9. 风险与对策

| 风险 | 描述 | 对策 |
| --- | --- | --- |
| Simulator 真实性 | 模拟分数与真实 KPI 相关度未知 | M7 真实数据回流校准 + 文档明确"模拟仅作相对排序" |
| Eval 钻空子 | Worker 过拟合 Eval 形式而非真实质量 | hold-out persona / adversarial probe / 限 Eval ≤ 6 / 定期人工抽检 |
| 量表回潮 | 用户 / 产品贪图灵活, 写成 1-10 量表 | UI 校验拦截 + 文档黄金法则 + AI 推荐只出二元 |
| 成本失控 | LLM 模式持续烧 token | `budget_tokens` 硬上限 + 成本可视化 + 缓存命中 |
| 用户预期 | "AI 帮我赚钱"过高预期 | 定位"加速迭代工具, 非真实预测" + 案例佐证而非夸大 |
| 法律合规 | 政治 / 医疗 / 金融场景敏感 | 域级 disclaimer + 敏感词过滤 + 禁用域名单 |
| Persona 偏见 | LLM 训练数据偏见传导 | 定期 audit + 用户可调权重 + 允许覆盖模板 |
| 兼容期管理 | v1 连续 metric vs v2 binary Eval 共存 | 文档优先引导 v2 + 旧 yaml 自动迁移工具 |

## 10. 已实现案例: AdCreativeVertical (M0)

> 详见 `docs/PRD-ad-creative-vertical.md` (vertical 级 PRD, 保留)

**当前状态**:

- 结构化创意: `{title, hook, script, storyboard}`
- 5 分群 Cohort: 小红书 / TikTok / 美国宝妈 / Web3 Degens / GenZ
- 4 维**连续** metric: `ctr / avg_dwell / sentiment_ratio / roas_proxy`
- mock 模式 6 轮收敛: `0.059 → 0.761`, delivered

**v2 升级方向** (M1 后):

- 把 4 维连续 metric 用 `check_kind=range` 包装成 binary Eval (例 `ctr ≥ 0.6 ?`)
- 加 5-6 个**内容层** binary Eval (例 `hook 是否在前 2 秒抛出?` / `CTA 是否唯一?` / `禁用词列表是否完全不出现?`)
- 接入 Eval Recommender 自动出推荐, 用户编辑

## 11. 关键文件清单

**已有 (复用)**:

- `src/truman/orchestrator/loop.py`
- `src/truman/verticals/{base,registry,headline,ad_creative}.py`
- `src/truman/sim/{driver,result,scene_builder,personas}.py`
- `src/truman/judge/{scorer,verdict,reaction_dm}.py`
- `src/truman/agents/{base,planner,worker,mock_worker}.py`
- `src/truman/research/{base,mock_researcher,llm_researcher}.py`

**新增 (M1–M4)**:

- `src/truman/intake/` — TaskIntake + CategoryDetector
- `src/truman/eval/` — EvalQuestion + 6 种 EvalChecker + EvalRecommender + 模板库
- `src/truman/personas/library/` — Cohort + Persona 模板
- `src/truman/changelog/` — Renderer + Exporter

**轻量升级**:

- `src/truman/goal/schema.py` — `evals`, `budget_tokens`, `plateau_window`
- `src/truman/judge/scorer.py` — binary Eval 适配器
- `src/truman/orchestrator/loop.py` — 停止条件升级

**文档**:

- `docs/PRD.md` — 本 PRD v2.0 (平台级)
- `docs/PRD-ad-creative-vertical.md` — v1, vertical 级参考
- `docs/eval-guide.md` — Eval 设计指南 (黄金法则 + 好坏对照 + 模板)
