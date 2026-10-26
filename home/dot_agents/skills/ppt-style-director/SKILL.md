---
name: ppt-style-director
description: Use when making or improving PPT, PowerPoint, slide deck, or presentation visual style, especially when the deck 风格不好看, AI 味, 模板味, 卡片堆叠, or needs product keynote plus technical architecture polish.
---

# PPT Style Director

## 角色

这是一个 PPT 的上层风格导演 skill。它不替代内置的 `Presentations`
skill，而是在 `Presentations` 之前和之后介入：先把审美方向、视觉禁区、
页面节奏和 proof object 说清楚，再对生成后的预览做风格 QA。

默认审美：**产品发布感 + 技术架构清爽感**。

## 何时使用

当用户提出这些需求时使用：

- 制作 PPT、PowerPoint、slide deck、presentation，且视觉质量很重要；
- 优化已有 deck 的风格、节奏、版式、质感；
- 避免“AI 味”“模板味”“泛 SaaS 紫色卡片味”“咨询套模板感”；
- 做产品、平台、AI、工程、基础设施、技术战略、技术解释类幻灯片。

如果任务需要产出最终 `.pptx`，同时使用 `Presentations`。本 skill 是它外层的
style brief、art direction 和 QA 层。

## 默认风格

默认走 **B+D**：

- **B: Keynote 产品发布感**：一个强观点，一个 hero object，舞台感清楚，
  文案克制，高对比，有自信的章节转换。
- **D: 技术架构清爽感**：标签准确，系统图干净，数据流或工作流逻辑可见，
  不用装饰性复杂度假装高级。

最终效果应该像一份认真打磨过的产品/工程 keynote，而不是 dashboard 模板、
营销落地页，也不是密密麻麻的内部 memo。

## 必须流程

1. **确定风格模式**
   - 除非用户另选方向，否则默认 B+D。
   - 如果用户提供公司模板，保留模板的品牌语法；B+D 只用于改善构图和节奏，
     不能破坏模板约束。
   - 如果 deck 以中文为主，加载 `references/chinese-slide-design.md`，把中文
     标题、正文密度、中英混排和中文空泛词作为额外 QA 门槛。

2. **在生成幻灯片前写 style brief**
   包含：
   - 一句话说明 deck 的气质；
   - deck-level palette：全 deck 的背景、正文、主强调色、辅助强调色、
     语义色用途；
   - 单页配色规则：每页如何从同一 palette 取色，哪些颜色不能同时出现；
   - 字体层级；
   - 信息层级：标题、主视觉、证据、注释、脚注的优先级；
   - 页面节奏计划；
   - 必须出现的 proof objects：产品截图、架构图、工作流、指标、引用、表格、
     决策对象等；
   - 克制原则：哪些元素必须删掉，哪些元素必须放大；
   - 明确要避开的 anti-patterns。

3. **规划页面 archetypes**
   用多样的页面类型，不要反复使用卡片网格：
   - 一个 thesis 开场页；
   - hero capability 页；
   - architecture map；
   - workflow sequence；
   - metric / evidence 页；
   - comparison / tradeoff 页；
   - section transition；
   - closing decision / next-action 页。

4. **用 style brief 约束 `Presentations`**
   创建或编辑 deck 时，把 style brief 当作阻塞性设计约束。不要为了省事滑回
   泛用模板。

5. **渲染后做风格 QA**
   用 `references/review-rubric.md` 检查 contact sheet 或预览图。如果 deck
   显得泛、重复、过度装饰，或技术解释不够清楚，先迭代最弱的页面，再导出最终
   PPTX。

6. **从参考素材沉淀规则**
   当用户提供优秀或糟糕的 PPT、截图、网页、keynote、模板或 deck 参考时，按
   `references/reference-intake.md` 拆解。输出可迁移规则，并明确写入
   `style-directions.md`、`anti-patterns.md` 或 `review-rubric.md`。

## 核心规则

- 每页标题都要有观点。不要用 “Architecture Overview” 这种描述性标签；
  能写成 “三段式 policy loop 让系统可解释” 就不要写空标题。
- 每个重要页面都要有一个 proof object：图、指标、截图、工作流、表格或具体
  artifact。不要用图标填空间。
- 优先一个 hero object，而不是四个平权卡片。
- 层级顺序默认是：观点标题 > 主视觉/proof object > 关键证据 > 注释 > 脚注。
  如果一页里有两个元素都在争第一视觉焦点，必须降级或删除一个。
- 必须先定义全 deck 统一 palette。暗色页、浅色页可以交替，但它们必须来自同一
  色彩系统；除非是明确的章节转场，不要一页一个新配色。
- 单页配色要和谐：通常使用一个底色、一个主强调色、一个辅助强调色和中性色。
  红、橙、蓝、绿等语义色不能随意混用，除非它们代表明确状态。
- 卡片不能成为默认版式。可以用少量圆角卡片做分组或承载局部信息，但不要把所有
  页面都做成平权卡片网格；完全直角、过分规整的页面也要用轻微圆角、留白或视觉
  层级软化。
- 留白是结构，不是装饰。
- 克制是默认门槛：删掉不承载观点、不承载证据、不改善导航的图形、图标、glow、
  边框、装饰线和重复文案。
- 技术图必须先语义准确，再追求好看。标签可以短，但不能把真实机制简化没了。
- 中文 deck 对标题纪律要求更高：少抽象名词，少口号，多具体判断。
- 中文 PPT 不能直接套英文 deck 的版式习惯。中文更容易变成灰墙，标题、正文、
  中英混排和数字层级必须单独检查。

## 参考文件

按需加载：

- `references/style-directions.md`：B+D 视觉语言、页面 archetypes、构图规则。
- `references/anti-patterns.md`：禁止的难看味道，以及替代方案。
- `references/review-rubric.md`：contact sheet 和单页审美评分表。
- `references/reference-intake.md`：拆解参考 PPT/截图，并转成可迁移 skill 规则。
- `references/chinese-slide-design.md`：中文 PPT 的标题、正文、中英混排和空泛词规则。

当用户明确讨厌某种新视觉模式时，后续把它沉淀到
`references/anti-patterns.md`。
