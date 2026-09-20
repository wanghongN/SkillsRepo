# 工具定义设计

工具定义（`tools` 字段）与系统提示词一起构成请求的静态前缀，其描述质量直接决定 Agent 用对工具的概率。把它当作给新员工的操作手册：好的描述能让从未用过该工具的人立即正确使用，并避开常见错误。

移除描述性文本、只保留函数签名与参数定义的对照实验中，工具调用错误率上升约 **45%**——频繁传无效参数值、误解参数含义。描述不是装饰。

## 四要素

| 要素 | 作用 | 写法示例 |
|------|------|---------|
| **使用边界** | 防止用错工具 | `NEVER invoke grep or rg as a Bash command; use the Grep tool instead.` |
| **具体示例值** | 消除格式歧义 | `timezone: 'America/New_York'`、`path: '/abs/path/file.ts'（必须绝对路径）` |
| **性能提示** | 引导高效调用 | `Batch your tool calls together when they are independent.` |
| **协作关系** | 表达调用顺序依赖 | `Use the Read tool at least once before editing a file.` |

## 参数描述清单

每个参数说明：类型与格式、是否必填、单位、枚举全集、默认值、非法值会发生什么。

反例：`limit: number — 数量限制`
正例：`limit: number — 返回条数上限，1-1000，默认 50；超过 1000 会被服务端截断为 1000`

## 描述模板

```
<一句话说明这个工具做什么>

WHEN TO USE:
- <场景 1>
- <场景 2>

WHEN NOT TO USE:
- <该走哪个工具>

HOW TO USE:
- <关键参数格式与约束>

LIMITATIONS / GOTCHAS:
- <常见错误与副作用>
```

## 渐进式披露（工具较多时）

2026 年起工具定义本身也走"按需加载"：静态前缀只保留工具名称与简述，模型搜索到之后才把完整 schema 追加到上下文末尾。

- OpenAI Responses API：`tool_search` 工具 + `defer_loading: true`，流程为 `tool_search_call → tool_search_output`。
- Anthropic：Tool Search（`tool_reference` blocks），Claude Code 对 MCP 工具默认延迟加载。
- Codex CLI：`tool_search`（BM25 检索）默认开启。

**为什么不破坏缓存**：因果注意力下每个 token 的 KV 只依赖它之前的 token，末尾追加不改变任何已缓存 token 的 K、V。新 schema 只在首次出现时计算一次，之后并入不断增长的前缀持续命中。

**容易误解的点**：追加只发生在工具被发现的那一轮，此后该 schema 固定在轨迹原位置，成为普通历史消息，不会每轮被搬到最新末尾（若每轮重新注入，就要每轮重新 prefill，缓存失去意义）。OpenAI 要求后续请求保持 `tool_search_output` 的原位置；Anthropic 在历史原位置内联展开 `tool_reference`。

**真正会导致重算的只有两种**：Prompt Cache TTL 过期；修改、移除或重排已加载的工具集（从变动点起失效）。

**前置条件**：模型必须在训练中见过"工具定义出现在对话中间"这种模式，因此该能力目前只有较新模型（GPT-5.4+、Claude 4.5+ 系列）支持，自托管开源模型需专门训练。

对提示词工程的含义：工具**名称与简述**要能被检索命中——名字里带上领域关键词，简述写清"什么场景用它"，否则模型搜不到就等于工具不存在。
