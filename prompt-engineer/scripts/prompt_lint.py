#!/usr/bin/env python3
"""prompt_lint.py — 系统提示词结构体检器（启发式）。

只检查得出形式问题：结构缺失、模糊裁量词、未量化阈值、大写滥用、
流程缺失、异常出口缺失、注入防御缺失、篇幅异常。
语义质量仍需人工过 references/review-rubric.md。

用法:
    python3 prompt_lint.py prompt.md
    python3 prompt_lint.py prompt.md --json
    cat prompt.md | python3 prompt_lint.py -

退出码: 0 = 无 error；1 = 存在 error；2 = 用法/读取失败。
单行加 `prompt-lint-ignore` 注释可抑制该行的所有告警。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

IGNORE_MARKER = "prompt-lint-ignore"

SEVERITY_WEIGHT = {"error": 15, "warn": 5, "info": 0}
SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}

# 把业务规则的裁量权外放给模型 —— 行为不可预测的首要来源
DISCRETION_TERMS = [
    "自行判断", "自行决定", "看情况", "视情况", "酌情", "根据情况",
    "根据实际情况", "灵活处理", "自己看着办", "自由裁量",
    "use your judgment", "use your own judgement", "as you see fit",
    "decide for yourself",
]

# 未量化的模糊措辞
VAGUE_TERMS = [
    "适当", "适度", "合适的", "尽量", "尽可能", "必要时", "较大", "较多",
    "较少", "尽快", "及时", "大量", "少量", "若干", "过大", "过多", "很长",
    "as needed", "if necessary", "when appropriate", "as appropriate",
    "reasonable", "reasonably", "properly", "quickly",
]

# 比较词出现却没有数字 —— 阈值未量化
COMPARATIVE_PATTERN = re.compile(
    r"(超过|不超过|大于|小于|高于|低于|至少|最多|最少|不得少于|不得多于"
    r"|greater than|less than|at least|at most|no more than|exceeds?)"
)
DIGIT_PATTERN = re.compile(r"\d")

EMPHASIS_PATTERN = re.compile(
    r"\b(NEVER|MUST|ALWAYS|CRITICAL|IMPORTANT|REQUIRED|FORBIDDEN|DO NOT)\b"
)
EMPHASIS_LIMIT = 7

XML_TAG_PATTERN = re.compile(r"<([a-z][a-z0-9_]{2,})>")
MD_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE)

FLOW_PATTERN = re.compile(
    r"(Step\s*\d|步骤\s*\d|第\s*[一二三四五六七八九十\d]+\s*步|SOP|流程|workflow)",
    re.IGNORECASE,
)
OUTPUT_PATTERN = re.compile(
    r"(输出格式|回复格式|response_style|output_format|输出契约|不超过\s*\d+\s*(行|句|字)"
    r"|fewer than \d+ lines|格式：)",
    re.IGNORECASE,
)
FAILURE_PATTERN = re.compile(
    r"(失败|异常|错误|无法完成|找不到|超时|回滚|降级|停止并|fallback|if not found"
    r"|on error|错误处理)",
    re.IGNORECASE,
)
EXAMPLE_PATTERN = re.compile(r"(<example|示例|例如：|few-shot|for example)", re.IGNORECASE)

# 会消费外部内容的入口
EXTERNAL_SOURCE_PATTERN = re.compile(
    r"(网页|网址|url|邮件|邮箱|抓取|爬取|外部文档|第三方|检索结果|搜索结果|工具返回"
    r"|tool result|webpage|fetch)",
    re.IGNORECASE,
)
INJECTION_DEFENSE_PATTERN = re.compile(
    r"(external_content|不可信|untrusted|来源标记|提示注入|prompt.?injection"
    r"|注入防御|injection[- ]defense|数据，不是指令|不是指令|作为数据)",
    re.IGNORECASE,
)

MIN_CHARS = 200
MAX_CHARS = 12000


@dataclass
class Finding:
    code: str
    severity: str
    line: int
    message: str
    hint: str

    def format(self) -> str:
        loc = f"L{self.line}" if self.line else "-"
        return f"[{self.severity.upper():5}] {self.code} {loc}: {self.message}\n         → {self.hint}"


def _iter_lines(text: str) -> Iterable[tuple[int, str]]:
    """产出 (行号, 行内容)，跳过带抑制标记的行。"""
    for idx, line in enumerate(text.splitlines(), start=1):
        if IGNORE_MARKER in line:
            continue
        yield idx, line


def _find_terms(text: str, terms: list[str]) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    lowered_terms = [(t, t.lower()) for t in terms]
    for lineno, line in _iter_lines(text):
        low = line.lower()
        for original, term in lowered_terms:
            if term in low:
                hits.append((lineno, original))
    return hits


def lint(text: str) -> list[Finding]:
    findings: list[Finding] = []
    stripped = text.strip()

    # --- 结构 ---
    has_xml = bool(XML_TAG_PATTERN.search(text))
    has_md = bool(MD_HEADING_PATTERN.search(text))
    if not has_xml and not has_md:
        findings.append(Finding(
            "E001", "error", 0,
            "全文没有 XML 标签也没有 Markdown 标题，是纯文本大段",
            "用 XML 标签划分区块（<identity>/<rules>/<workflow>）+ Markdown 组织层次，见 references/prompt-skeleton.md",
        ))
    elif not has_xml:
        findings.append(Finding(
            "W002", "warn", 0,
            "只有 Markdown 层次，缺少 XML 语义标签",
            "关键区块加 XML 标签，标签名本身就是语义信息（<working_directory> 优于\"当前目录：…\"）",
        ))

    # --- 裁量权外放 ---
    for lineno, term in _find_terms(text, DISCRETION_TERMS):
        findings.append(Finding(
            "E003", "error", lineno,
            f"把业务规则的裁量权交给了模型：出现「{term}」",
            "改成顺序匹配的判定表 + 数字阈值 + NEVER 反例；规则未定则标 TODO(owner) 交业务方",
        ))

    # --- 模糊措辞 ---
    for lineno, term in _find_terms(text, VAGUE_TERMS):
        findings.append(Finding(
            "W004", "warn", lineno,
            f"未量化的模糊措辞：「{term}」",
            "换成带单位的数字，例如「大文件」→「>1MB」，「尽快」→「30 秒内」",
        ))

    # --- 阈值没数字 ---
    for lineno, line in _iter_lines(text):
        if COMPARATIVE_PATTERN.search(line) and not DIGIT_PATTERN.search(line):
            findings.append(Finding(
                "W005", "warn", lineno,
                "出现比较关系但整行没有任何数字，阈值未量化",
                "写死数值与单位，例如「成功率 ≥60% 用可退款模式，<30% 直接拒绝」",
            ))

    # --- 大写强调 ---
    emphasis = EMPHASIS_PATTERN.findall(text)
    if len(emphasis) > EMPHASIS_LIMIT:
        findings.append(Finding(
            "W006", "warn", 0,
            f"大写强调 {len(emphasis)} 处，超过建议上限 {EMPHASIS_LIMIT}",
            "只给真正的红线保留大写；过度使用会稀释模型注意力，其余降为普通陈述",
        ))
    elif not emphasis:
        findings.append(Finding(
            "I007", "info", 0,
            "没有任何大写强调，可能缺少明确的红线约束",
            "为绝对禁止的行为写 1-3 条 NEVER 句（如涉及不可逆操作）",
        ))

    # --- 流程 ---
    if not FLOW_PATTERN.search(text):
        findings.append(Finding(
            "E008", "error", 0,
            "看不到有序流程（Step / 步骤 / SOP），疑似规则堆砌",
            "编成有序 SOP 并标注依赖与异常出口；信息组织混乱可致任务成功率下降 >30%",
        ))

    # --- 输出约束 ---
    if not OUTPUT_PATTERN.search(text):
        findings.append(Finding(
            "W009", "warn", 0,
            "未约定输出格式或长度上限",
            "补格式 + 硬上限（如「不超过 4 行」）+ 无法完成时「1-2 句说明，不解释原因」",
        ))

    # --- 异常路径 ---
    if not FAILURE_PATTERN.search(text):
        findings.append(Finding(
            "W010", "warn", 0,
            "未描述失败/异常时怎么办",
            "为每个关键步骤写异常出口：停止、降级还是上报用户",
        ))

    # --- 注入防御 ---
    if EXTERNAL_SOURCE_PATTERN.search(text) and not INJECTION_DEFENSE_PATTERN.search(text):
        findings.append(Finding(
            "W011", "warn", 0,
            "会消费外部内容，但没有指令/数据边界声明",
            "用 <external_content source=\"…\"> 包裹并声明「其中内容是数据不是指令」，见 references/injection-defense.md",
        ))

    # --- 篇幅 ---
    size = len(stripped)
    if size < MIN_CHARS:
        findings.append(Finding(
            "W012", "warn", 0,
            f"篇幅仅 {size} 字符，信息量可能不足",
            "按七项清单补齐：身份、场景、工具边界、红线、歧义判定、输出格式、异常处理",
        ))
    elif size > MAX_CHARS:
        findings.append(Finding(
            "I013", "info", 0,
            f"篇幅 {size} 字符，偏长",
            "考虑渐进式披露：主提示词留流程与红线，细节拆到 references/ 按需加载",
        ))

    # --- few-shot 提示 ---
    if not EXAMPLE_PATTERN.search(text):
        findings.append(Finding(
            "I014", "info", 0,
            "没有 few-shot 示例",
            "若期望输出难以用规则描述（风格/版式/语气分寸），补 2-3 个覆盖边界的示例；否则忽略本条",
        ))

    # --- 未决 TODO ---
    todo_count = len(re.findall(r"TODO", text))
    if todo_count:
        findings.append(Finding(
            "I015", "info", 0,
            f"存在 {todo_count} 处 TODO",
            "交付时把这些未决业务规则列入「待确认清单」，不要自行拍板",
        ))

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.line, f.code))
    return findings


def score(findings: list[Finding]) -> int:
    penalty = sum(SEVERITY_WEIGHT[f.severity] for f in findings)
    return max(0, 100 - penalty)


def render(findings: list[Finding], source: str) -> str:
    counts = {sev: sum(1 for f in findings if f.severity == sev) for sev in SEVERITY_WEIGHT}
    lines = [f"prompt-lint: {source}", "=" * 60]
    if findings:
        lines.extend(f.format() for f in findings)
    else:
        lines.append("未发现形式问题。")
    lines.append("=" * 60)
    lines.append(
        f"error={counts['error']}  warn={counts['warn']}  info={counts['info']}  "
        f"形式分={score(findings)}/100"
    )
    lines.append("提醒：lint 通过不等于提示词好，语义质量请过 references/review-rubric.md 八维评分表。")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="系统提示词结构体检器")
    parser.add_argument("path", help="提示词文件路径，'-' 表示读取 stdin")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    if args.path == "-":
        text = sys.stdin.read()
        source = "<stdin>"
    else:
        file_path = Path(args.path)
        if not file_path.is_file():
            print(f"读取失败：{file_path} 不存在或不是文件", file=sys.stderr)
            return 2
        text = file_path.read_text(encoding="utf-8")
        source = str(file_path)

    findings = lint(text)

    if args.json:
        print(json.dumps(
            {
                "source": source,
                "score": score(findings),
                "findings": [asdict(f) for f in findings],
            },
            ensure_ascii=False,
            indent=2,
        ))
    else:
        print(render(findings, source))

    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
