# prompt-engineer

> 把系统提示词当作 Agent 的「员工手册」来写。

一个面向 Agent 的**系统提示词工程技能**：起草、重写、诊断 System Prompt 与工具描述，并自带一个可执行的结构体检器 `prompt_lint.py`。

| 项 | 说明 |
| --- | --- |
| 技能名 | `prompt-engineer` |
| 版本 | 1.0.0（见 `SKILL.md` frontmatter） |
| 依赖 | Python 3（`prompt_lint.py` 仅用标准库）；运行单元测试需要 pytest |
| 方法论来源 | 《AI Agents in Depth》中译本 2.4「提示工程」、2.5「动态提示词与 Agent Skills」及实验 2-4 / 2-5 |

---

## 功能概览

### 黄金检验标准

**大语言模型是一位聪明的新员工——能力出众，但对你们的工作流程和内部约定一无所知。如果一个聪明的新员工读完这份提示词还不知道该怎么做，Agent 也一样不知道。**

每次交付前都用这一句话复核。

### 四条工作路径

| 路径 | 何时走 | 做什么 |
| --- | --- | --- |
| **Path A：起草** | 从零写一个新提示词 / 新 Agent | 七项需求采集 → 选骨架 → 编成有序 SOP → 去模糊化 → few-shot 决策 → 注入防御 → 自检 → 交付 |
| **Path B：重写** | 已有提示词，要更好 / 更精简 | 先盘点「保留清单」，按八维评分表只重构低分维度，输出变更表（改了什么｜为什么｜风险） |
| **Path C：消融诊断** | Agent 表现不佳、行为不稳定、偶发违规 | 先用「症状 → 病灶 → 处方」表定位，再单变量改动 + 同批 case 回归；**优先级高于 Path B**，禁止一上来全面重写 |
| **Path D：工具定义** | 只是 `tools` 字段 / 工具描述有问题 | 按四要素补齐：使用边界 + 具体示例值 + 性能提示 + 与其他工具的协作关系 |

路径判断不了就问，最多一轮。

### 内置的硬性规约

- **不替业务方拍板**：业务规则由业务方定义，未知项写成 `TODO(owner)` 并列入待确认清单。
- **禁止把裁量权交给模型**：不写「根据情况选择合适的类型」，改写顺序匹配的判定表 + NEVER 反例。
- **阈值必须是数字**：不是「成功率高就接」，而是「≥60% 用可退款模式，<30% 直接拒绝」。
- **大写强调 ≤7 条**：`NEVER` / `MUST` / `ALWAYS` 只留给真正的红线，其余降为普通陈述。
- **双层结构**：XML 标签承载机器可解析的语义，Markdown 承载人机共读的层次。
- **流程优先于规则**：让模型任何时刻都知道「我在第几步、本步目标、下一步去哪、异常从哪出」。
- **few-shot 少而准**：2-3 个覆盖边界的示例，一旦确定就字节级冻结（保护 KV Cache 前缀稳定性）。
- **改动单变量、可回滚**：交付必须附「怎么验证」。

### 交付契约

每次交付固定三段，不夹带旁白：

1. 提示词全文（一个代码块，可直接复制粘贴）
2. 设计说明表（`段落 | 解决什么问题 | 依据的原则`；重写场景为 `改了什么 | 为什么 | 风险`）
3. 待确认 TODO + 验证建议

### 自检工具 prompt_lint.py

启发式结构体检，共 15 项检查：

| 代码 | 检查项 |
| --- | --- |
| `E001` / `W002` | 结构：纯文本大段无层次 / 只有 Markdown 缺 XML 语义标签 |
| `E003` | 把业务裁量权外放给模型（「根据情况」「自行判断」…） |
| `W004` / `W005` | 未量化的模糊措辞 / 出现比较关系但整行没有任何数字 |
| `W006` / `I007` | 大写强调超过 7 条 / 完全没有红线强调 |
| `E008` | 看不到有序流程（Step / 步骤 / SOP），疑似规则堆砌 |
| `W009` / `W010` | 未约定输出格式与长度上限 / 未描述失败与异常出口 |
| `W011` | 会消费外部内容，却缺少指令与数据的边界声明 |
| `W012` / `I013` | 篇幅过短（<200 字符）/ 偏长（>12000 字符） |
| `I014` / `I015` | 没有 few-shot 示例 / 存在未决 TODO |

输出附带**形式分（0-100）**：error 扣 15、warn 扣 5、info 不扣分。

---

## 适用场景

- 从零起草一份新的 System Prompt，或新 Agent 的人设与规则
- 重写、精简一份已有的提示词，或按评分表做评审
- Agent 行为不稳定：跳过前置步骤、偶发违规、同类请求分类不一致
- 输出冗长、反复解释「为什么做不到」
- 工具参数传错、误解参数含义，需要修 `tools` 字段描述
- 写完 / 改了 `SKILL.md` 的指令正文，想知道形式是否过关
- 提示词会读取网页、邮件、文档、检索结果，担心被内容里的伪指令带跑

## 边界（不负责）

- 模型选型
- RAG 检索调优
- 模型微调

---

## 安装

本技能是纯目录形态（`SKILL.md` + `references/` + `scripts/` + `tests/`），没有第三方运行时依赖，也不需要 npm / pip 安装技能本身。安装 = **把整个目录放进你的 Agent 技能目录**。

技能自身的 `SKILL.md` 声明了 `metadata.requires.bins: ["python3"]`，即需要 Python 3 可执行文件。

| Agent | 技能目录（常见约定，以各自文档为准） |
| --- | --- |
| Codex | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| 其他支持 `SKILL.md` 的 Agent | 见其文档 |

```bash
# 拷贝目录（示例：Codex）
cp -R prompt-engineer ~/.agents/skills/prompt-engineer
```

安装后的目录应为：

```text
<skills-dir>/prompt-engineer/
├── SKILL.md
├── references/
├── scripts/
└── tests/
```

### 验证安装

```bash
cd <skills-dir>/prompt-engineer
python3 scripts/prompt_lint.py --help      # 应打印用法说明
```

> Windows 上没有 `python3` 命令时，把示例里的 `python3` 换成 `python`。

---

## 使用

### 1. 交给 Agent 使用

技能靠 `SKILL.md` 的 `description` 自动匹配触发；也可以显式点名：

```text
用 prompt-engineer 帮我把这段客服 Agent 的 system prompt 重写一遍，
重点修「跳过身份验证」和「退款计费分类不一致」两个问题。
```

```text
用 prompt-engineer 从零起草一个网页摘要 Agent 的 system prompt，
它会读取外部网页，需要注入防御。
```

技能会根据意图选择路径：起草走 Path A，重写走 Path B；说「效果不好」会先走 Path C 做诊断，只改工具描述走 Path D。

### 2. 直接使用 prompt_lint.py

```bash
python3 scripts/prompt_lint.py prompt.md          # 人读报告
python3 scripts/prompt_lint.py prompt.md --json   # 机器可解析
cat prompt.md | python3 scripts/prompt_lint.py -  # 读 stdin
```

报告示例：

```text
prompt-lint: prompt.md
============================================================
[ERROR] E008 -: 看不到有序流程（Step / 步骤 / SOP），疑似规则堆砌
         → 编成有序 SOP 并标注依赖与异常出口；信息组织混乱可致任务成功率下降 >30%
[WARN ] W009 -: 未约定输出格式或长度上限
         → 补格式 + 硬上限（如「不超过 4 行」）+ 无法完成时「1-2 句说明，不解释原因」
[WARN ] W010 -: 未描述失败/异常时怎么办
         → 为每个关键步骤写异常出口：停止、降级还是上报用户
[INFO ] I014 -: 没有 few-shot 示例
         → 若期望输出难以用规则描述（风格/版式/语气分寸），补 2-3 个覆盖边界的示例；否则忽略本条
============================================================
error=1  warn=2  info=2  形式分=75/100
提醒：lint 通过不等于提示词好，语义质量请过 references/review-rubric.md 八维评分表。
```

退出码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 无 error；warn / info 逐条处理，或在回复中说明为何不改 |
| `1` | 存在 **error**，必须修掉再交付（可用于 CI 卡点） |
| `2` | 用法错误 / 文件不存在或不是文件 |

`--json` 输出结构：`source`、`score`、`findings[]`，每项含 `code`、`severity`、`line`、`message`、`hint`。

某行属于误报时，在该行加抑制标记，并在交付说明里给出理由：

```markdown
- 不要出现「根据情况」这类表述 <!-- prompt-lint-ignore -->
```

### 3. 运行单元测试

```bash
pip install pytest
python3 -m pytest tests/ -q
```

---

## 目录结构

```text
prompt-engineer/
├── SKILL.md                     # 技能入口：路由、四条路径 SOP、硬性规约、输出契约
├── references/                  # 按需加载的细则（渐进式披露，不要一次性全读）
│   ├── prompt-skeleton.md       # 最小骨架、XML 标签词汇表、填好的范例
│   ├── review-rubric.md         # 八维评分表、反模式对照表、交付前 checklist
│   ├── tool-definition.md       # 工具描述四要素、参数描述清单、渐进式披露
│   ├── injection-defense.md     # 提示注入防御三道防线
│   └── ablation-protocol.md     # 消融实验协议、指标记录表、常见误判
├── scripts/
│   └── prompt_lint.py           # 结构体检器（CLI / --json / stdin）
└── tests/
    └── test_prompt_lint.py      # prompt_lint.py 的单元测试
```

## 参考文件

| 文件 | 何时读 |
| --- | --- |
| `references/prompt-skeleton.md` | Path A 选骨架；需要 XML 标签词汇表和填好的范例 |
| `references/review-rubric.md` | 自检、Path B 打分；需要反模式对照表 |
| `references/tool-definition.md` | Path D，或提示词涉及工具调用 |
| `references/injection-defense.md` | 提示词会消费外部内容（网页 / 邮件 / 文档 / 第三方 Skill / 状态栏） |
| `references/ablation-protocol.md` | Path C 诊断；需要设计消融实验或做改动前后对比 |

## 常见问题

**Windows 上提示 `python3: command not found`**
改用 `python scripts/prompt_lint.py ...`，或安装 Python 3 后把 `python3` 加进 PATH。

**lint 通过了，但提示词效果还是不好**
lint 只查得出形式问题（结构、措辞、阈值、篇幅），语义质量仍需人工过 `references/review-rubric.md` 的八维评分表；若是「Agent 表现不佳」，按 Path C 先做消融诊断再改。

**想新增一条检查规则**
在 `scripts/prompt_lint.py` 的 `lint()` 里追加 `Finding`，并在 `tests/test_prompt_lint.py` 补一条用例，保持退出码语义不变。

**正文里确实需要保留「根据情况」这类字样**
在该行加 `<!-- prompt-lint-ignore -->` 抑制，不要为了过 lint 牺牲正文表达。