# PRD — AI 广告创意进化系统 (AdCreativeVertical)

> 文档版本 v1.0 · 状态: 已实现 · 模块路径 `src/truman/verticals/ad_creative.py` ·
> 上游框架 Truman Goal-Driven Recursive AI System

## 1. 背景 (Why)

短视频广告 (TikTok / Meta / 小红书) 的创意试错成本极高: 一个 hook / 角度错了,
真金白银的投流预算就烧没了, 而真实 CTR / 停留 / 评论情绪要等到投出去才能拿到。
传统 A/B 测试既慢又贵。

Truman 主框架已经把 "目标驱动 + 真实世界反应模拟 + 递归自优化" 抽象成通用引擎,
现在需要落到第一个**真实有商业价值的垂直**——广告创意进化。
同时,这个垂直也充当了框架**可插拔性的验证靶子**: 加新垂直不应该改主循环。

## 2. 目标 / 非目标

**目标 (In-Scope)**

- 输入广告投放目标 (产品 / 平台 / 目标人群) → 自动产出综合得分高于阈值的视频创意结构 (title / hook / script / storyboard)
- 综合得分由四个模拟指标加权: **CTR**, **dwell (停留)**, **sentiment (评论情绪)**, **ROAS proxy (转化代理分)**
- 验证 vertical 注册表机制: 不改 `orchestrator/loop.py` 就能加新垂直
- 把 Research / Creative 做成 **可插拔 Protocol**, 给未来的外部多智能体团队留接口
- 离线 `mock` 模式可复现 / 零网络 / 严格单调改进 / 在 `max_iterations` 内 deliver
- 真实 `--llm` 模式接 Anthropic Claude, 走通完整推理链路

**非目标 (Out-of-Scope, v1)**

- 不接广告平台 API / 不做真实投放
- 不实现外部多智能体创意团队 (只预留 Protocol 接口)
- 不做视频画面生成 / 视觉合成 (只产出脚本 + 分镜文本)
- 不做归因 / 转化追踪 (ROAS 仅作合成代理分)
- 不做多 tick / 推荐扩散 / 评论级联 (单 tick 模拟)

## 3. 用户与典型场景

- **主要用户**: 增长团队 / 广告创意负责人 / 独立投手 / DTC 品牌的 marketing ops
- **场景 1 (新品上线)**: 模拟器先跑 5–10 版创意, 把预算只投给得分高的 1–2 版
- **场景 2 (人群拓展)**: 同一产品针对小红书 / TikTok / 美国宝妈 / Web3 Degens / GenZ 五个分群分别生成最佳创意
- **场景 3 (迭代调优)**: 产品升级后快速重生成创意变体, 不再依赖人工灵感

## 4. 核心功能模块

### 4.1 Research Agents (调研层, 可插拔)

- **接口**: `truman.research.base.ResearchProvider.research(goal) -> ResearchBrief`
- **输入**: `GoalConfig` (含 `scene.product`, `scene.platform`, `scene.audience_segments`)
- **输出**: `ResearchBrief{summary, audience_insights[], competitor_examples[], recommended_angles[]}`
- **本垂直实现**:
  - `MockAdResearcher` — 从 `topic_pool(product)` 派生 6 个候选角度 (offline 确定性)
  - `LLMAdResearcher` — Claude system prompt "performance-ads strategist", 分析 TikTok/Meta 爆款规律产出 angles
- **预留**: 后续可替换为外部多智能体调研团队 (Crawler + VisionAnalyst + TrendDetector)

### 4.2 Creative Agents (创意生成层, 可插拔)

- **接口**: `truman.agents.base.WorkerProvider.create(...)/.revise(...) -> CandidateArtifact`
- **结构化输出**: `CandidateArtifact.fields = {title, hook, script, storyboard[]}`
  - `title` — 标题
  - `hook` — 前 2 秒钩子
  - `script` — ≤60 字口播 / 脚本
  - `storyboard` — 3–5 条短镜头描述
- **本垂直实现**:
  - `MockAdCreativeWorker` — 渐进添加 angles (第 k 轮用前 k+1 个), 保证单调改进
  - `LLMAdCreativeWorker` — Claude system "viral short-form ad creative director", 输出严格 JSON
- **revise 路径**: 接收 `JudgeVerdict.feedback` + `weaknesses[]`, 生成针对性新版本
- **预留**: 后续可替换为外部 Copywriter + Director + Storyboarder 多智能体团队

### 4.3 Persona Generation (受众生成, 复用通用模块)

- **5 个目标分群**: 小红书用户 / TikTok 用户 / 美国宝妈 / Web3 Degens / GenZ
- **复用** 现有 `build_personas` / `build_personas_llm` (零新代码)
- **传入方式**: `goal.scene.audience_segments`
  - mock 模式: 基于 `topic_pool(product)` 确定性生成 N 个角色 (segments 不显式注入, 与决策"复用通用 persona"一致)
  - llm 模式: scene 整体 JSON 进 prompt, Claude 按分群上下文生成多样化人设

### 4.4 Simulation Agents (反应模拟)

- 每个 persona 通过 `AdDecider.decide(persona, artifact)` 决定 `watch` 还是 `skip`
- **mock**: `appeal = 0.3·情绪偏好 + 0.7·兴趣匹配度`, ≥ 0.25 则 watch
- **llm**: Claude 角色扮演产出 `{watch:bool, reaction:str}`
- watch 动作携带参数: `click_prob`, `dwell_seconds`, `sentiment`, `reaction`
  (mock 携带数值; llm 只携带 reaction 文本, 由 Evaluator DM 预测数值)

### 4.5 Evaluator (评估 DM, WorldSeed DMProvider)

- **mock `MockAdEvaluatorDM`** (继承 `MockDMProvider`): 记录 decider 携带的数值, 输出 increment effects
- **llm `LLMAdEvaluatorDM`**: 异步 Anthropic 调用, 输入 `world_state + reaction`, 预测
  `{click_prob ∈ [0,1], dwell_seconds ∈ [0,30], sentiment ∈ [-1,1]}`
- 每次 watch 产生 4 个 effects: `clicks += click_prob`, `dwell_total += dwell`,
  `sentiment_total += max(0, sentiment)`, emit `reaction` 事件

### 4.6 Metrics & Scoring

单次模拟产出四个核心指标:

| 指标 | 计算 | 范围 | 含义 |
|---|---|---|---|
| `ctr` | `clicks / N` | 0–1 | 点击率代理 |
| `avg_dwell` | `dwell_total / (N · 30s)` | 0–1 | 标准化平均停留 |
| `sentiment_ratio` | `sentiment_total / N` | 0–1 | 正向情绪占比 |
| `roas_proxy` | `ctr · sentiment_ratio · avg_dwell` | 0–1 | 三者乘积, 拉大头部尾部差距 |

- **复用** 通用 `EngagementScorer` 按 criteria 权重加权 → `composite ∈ [0,1]`
- `composite ≥ threshold` ⇒ deliver; 否则 feedback 灌给 Creative Agents 走 `revise`

### 4.7 Recursive Optimization Loop (复用 orchestrator)

- **完全复用** `TrumanEngine.run()`, 本垂直零新增循环代码
- 每轮: `research → plan → create/revise → simulate → score → ledger → 判停`
- ledger 状态: `kept` (改进了) / `rejected` / `delivered`

## 5. 技术架构

```
GoalConfig{vertical:"ad_creative", scene:{product,platform,segments}, criteria, threshold}
     │
     ▼
get_vertical("ad_creative") → AdCreativeVertical
     │
     ├─ make_research(mode,model)   → MockAdResearcher | LLMAdResearcher
     ├─ make_creative(mode,model)   → MockAdCreativeWorker | LLMAdCreativeWorker
     ├─ make_personas(goal,mode,..) → 复用 build_personas[_llm]
     ├─ make_decider(mode,model)    → MockAdDecider | LLMAdDecider
     ├─ make_dm(mode,model)         → MockAdEvaluatorDM | LLMAdEvaluatorDM
     ├─ build_scene(goal,artifact)  → WorldSeed SceneConfig (artifact entity + watch/skip actions)
     └─ compute_metrics(...)        → {ctr, avg_dwell, sentiment_ratio, roas_proxy}
              │
              ▼
   通用 TrumanEngine 递归循环 (与 headline vertical 共用同一份代码)
```

## 6. 数据契约

### 6.1 输入 (`examples/ad_creative_ctr.yaml`)

```yaml
goal: "Maximize CTR / ROAS / conversion for our new budget travel app's short-form video ad."
vertical: ad_creative
artifact_kind: ad_creative
threshold: 0.55
max_iterations: 6
persona_count: 6
seed: 42
criteria:
  - {name: ctr,       metric: ctr,             weight: 0.4}
  - {name: dwell,     metric: avg_dwell,       weight: 0.2}
  - {name: sentiment, metric: sentiment_ratio, weight: 0.2}
  - {name: roas,      metric: roas_proxy,      weight: 0.2}
scene:
  product: "budget travel"
  platform: "tiktok"
  audience_segments: [小红书用户, TikTok用户, 美国宝妈, Web3 Degens, GenZ]
```

### 6.2 输出 (`RunResult`)

- `final_artifact.fields = {title, hook, script, storyboard[]}` — 交付的结构化创意
- `final_artifact.content` — 渲染好的纯文本摘要 (供 ledger / 打印)
- `final_verdict = {score, threshold, threshold_met, per_criterion, feedback, weaknesses}`
- `ledger.records[]` — 完整迭代历史 (每轮 score / status / feedback / 产物)

### 6.3 WorldSeed Scene 结构 (`build_ad_scene`)

- entity `feed` (type: space)
- entity `artifact` (type: ad_creative)
  - 平铺属性: `title`, `hook`, `script` (供 LLM Evaluator 读 world_state)
  - 计数器属性: `clicks`, `dwell_total`, `sentiment_total` (constraints: min=0)
- action `watch` (params: `click_prob` / `dwell_seconds` / `sentiment` (number, optional) + `reaction` (free_text, optional); DM allowed_ops: increment / emit_event)
- action `skip` (mechanical, 无 params)

## 7. 关键指标 (KPI) / 验收标准

### 7.1 自动化测试 (`tests/test_verticals.py`)

- `test_registry_exposes_both_verticals` — registry 暴露 `headline` + `ad_creative`
- `test_ad_creative_loop_improves_and_delivers`:
  - 离线 mock 模式分数**严格单调递增**
  - `final_verdict.threshold_met == True`
  - 最后 ledger.status == `"delivered"`
  - `per_criterion` 包含 `{ctr, dwell, sentiment, roas}`
  - `final_artifact.fields` 包含 `{title, hook, script, storyboard}` 且非空
- `test_ad_creative_is_deterministic` — 同 seed 两次运行 final_artifact + scores 完全一致
- **回归**: 不破坏既有 7 个 headline / scene / scorer 测试 (目标 10/10 通过)

### 7.2 已观测的离线收敛

- 6 轮迭代分数: `0.0590 → 0.2229 → 0.2893 → 0.4644 → 0.5374 → 0.7613 (delivered)`
- 命令: `python -m truman run examples/ad_creative_ctr.yaml`, exit 0

### 7.3 LLM 模式 (需要凭证)

- 命令: `python -m truman run examples/ad_creative_ctr.yaml --llm --model claude-haiku-4-5-20251001 --persona-count 5`
- 依赖: `ANTHROPIC_OAUTH_TOKEN` 或 `ANTHROPIC_API_KEY` 环境变量
- 链路: 已确认走通到凭证检查 (无凭证时正确抛 `RuntimeError`)

## 8. 使用方式

**CLI**:

```bash
python -m truman run examples/ad_creative_ctr.yaml              # 离线 mock
python -m truman run examples/ad_creative_ctr.yaml --llm        # 真实 LLM
```

**程序化**:

```python
from truman.goal.loader import load_goal
from truman.orchestrator.loop import TrumanEngine

goal = load_goal("examples/ad_creative_ctr.yaml")
result = await TrumanEngine(goal, mode="mock").run()
print(result.final_artifact.fields)   # {"title":..., "hook":..., "script":..., "storyboard":[...]}
print(result.final_verdict.score, result.final_verdict.per_criterion)
```

## 9. 风险 / 依赖

- **凭证依赖**: `--llm` 模式要求 Anthropic 凭证, 容器/CI 缺凭证时需提前注入
- **mock 偏差**: 决策器用 keyword-match, 与真实分布存在偏差, **不应作业务依据**, 仅作排序/迭代信号
- **ROAS proxy 非真实业务 ROAS**: 是 `ctr·sentiment·dwell` 的合成代理分, 只在同一目标内做相对比较
- **WorldSeed DSL 严格白名单** (`extra="forbid"`): scene/effect/param 字段必须严格合规 (已对齐)
- **persona segments 在 mock 模式不显式**: 与决策 "复用现有通用 persona" 一致, llm 模式通过 scene 上下文体现
- **单 tick 模拟**: 不建模冷启动 → 推荐扩散 → 评论级联, 后续可扩展

## 10. 路线图 (后续可选增量)

- **v1.1** 外部多智能体调研团队接入 (Crawler + VisionAnalyst + TrendDetector), 保持 `ResearchProvider` Protocol 不变
- **v1.2** 外部创意团队接入 (Copywriter + Director + Storyboarder), 保持 `WorkerProvider` Protocol 不变
- **v1.3** 创意维度扩展: 视频时长 / 口播节奏 / 字幕密度 / BGM 风格
- **v1.4** 多 tick 模拟: 冷启动 → 推荐扩散 → 评论级联 → 二次创作 (UGC)
- **v1.5** Cohort-level 输出: 每个 segment 单独给 CTR / dwell / sentiment, 支持人群差异化创意

## 11. 关键文件清单

- 实现: `src/truman/verticals/ad_creative.py`
- 接口: `src/truman/verticals/base.py`, `src/truman/verticals/registry.py`
- 默认垂直 (作回归基线): `src/truman/verticals/headline.py`
- 通用层重构: `src/truman/sim/driver.py`, `src/truman/sim/result.py`, `src/truman/agents/base.py`, `src/truman/goal/schema.py`, `src/truman/judge/scorer.py`
- 复用受众: `src/truman/sim/personas.py` (未改动)
- 复用主循环: `src/truman/orchestrator/loop.py`
- 配置样例: `examples/ad_creative_ctr.yaml`
- 测试: `tests/test_verticals.py`
