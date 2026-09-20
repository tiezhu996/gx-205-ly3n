"""智能组卷领域服务。

核心规则：
1. 同一份试卷内题目绝不重复（先按 id 去重，再按题量截断，不用重复项凑数）；
2. 请求题量超过该难度可用题量时，返回实际题数与缺口原因；
3. 连续按同一难度组卷时，优先抽取上一份试卷未出现过的题，题池不足才复用；
4. 最近一次组卷结果在服务端保留一份，供刷新后回读。
"""

import copy
import random
import threading
from datetime import datetime
from typing import Dict, List, Optional

from bank.questions import QUESTIONS_BY_ID, questions_of_difficulty

_lock = threading.Lock()
# 进程内保存最近一次组卷（按难度区分），gunicorn 单 worker 下跨请求可回读。
_last_papers: Dict[str, dict] = {}
# 单调递增的组卷序号，避免同一秒内多份试卷无法判断谁是“最近一次”。
_generation_seq = 0


def _gap_reason(requested: int, available: int) -> str:
    return (
        f"该难度题库当前仅有 {available} 道可用题，实际生成 {available} 道，"
        f"距离请求的 {requested} 道还差 {requested - available} 道，已保留缺口、未补入重复题。"
    )


def generate_paper(difficulty: str, amount: int) -> dict:
    """按难度与题量生成一份不重复的试卷，并记录缺口与复用提示。"""
    pool = questions_of_difficulty(difficulty)
    total = len(pool)

    with _lock:
        previous = _last_papers.get(difficulty)
    previous_ids = set(previous["question_ids"]) if previous else set()

    # 先抽上一份试卷没出现过的“新题”，保证连续同难度组卷尽量不撞题。
    fresh = [q for q in pool if q["id"] not in previous_ids]
    reused = [q for q in pool if q["id"] in previous_ids]
    random.shuffle(fresh)
    random.shuffle(reused)

    picked: List[Dict] = fresh + reused
    # 再次按 id 去重，即便题池数据异常也不会让同一题在同一份卷中出现两次。
    unique: List[Dict] = []
    seen_ids = set()
    for question in picked:
        if question["id"] in seen_ids:
            continue
        seen_ids.add(question["id"])
        unique.append(question)

    actual = unique[:amount]
    actual_ids = [q["id"] for q in actual]
    actual_id_set = set(actual_ids)
    # 仅统计实际落入本份试卷的旧题：截断后未被选中的候选题不算复用。
    reused_in_paper = sorted(actual_id_set & previous_ids)
    fresh_in_paper = len(actual) - len(reused_in_paper)

    gap = amount - len(actual)
    notices: List[str] = []
    if gap > 0:
        notices.append(_gap_reason(amount, total))
    if reused_in_paper and previous:
        notices.append(
            f"未在上一份试卷中出现的该难度题目仅有 {len(fresh)} 道、本次命中 {fresh_in_paper} 道，"
            f"题池不足，已复用 {len(reused_in_paper)} 道旧题。"
        )
    elif previous and gap == 0:
        notices.append("已优先避开上一份试卷出现过的题目。")
    notice = "；".join(notices)

    result = {
        "difficulty": difficulty,
        "requested_amount": amount,
        "actual_amount": len(actual),
        "gap_amount": max(gap, 0),
        "pool_amount": total,
        "notice": notice,
        "has_gap": gap > 0,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "question_ids": actual_ids,
        "paper": actual,
    }

    with _lock:
        global _generation_seq
        _generation_seq += 1
        result["seq"] = _generation_seq
        _last_papers[difficulty] = result
    return result


def get_last_paper(difficulty: Optional[str] = None) -> Optional[dict]:
    """读取最近一次组卷结果：指定难度时取该难度，否则取生成序号最大的一份。

    返回深拷贝，调用方修改结果不会污染服务端保留的最近一次试卷。
    """
    with _lock:
        if difficulty is not None:
            snapshot = _last_papers.get(difficulty)
            return copy.deepcopy(snapshot) if snapshot else None
        if not _last_papers:
            return None
        latest = max(_last_papers.values(), key=lambda item: item["seq"])
        return copy.deepcopy(latest)


def grade_paper(question_ids: List[int], answers: Dict[str, str]) -> dict:
    """按试卷中实际包含的题目判分，缺题/缺答不影响其余题目的计算。"""
    resolved = [QUESTIONS_BY_ID[qid] for qid in question_ids if qid in QUESTIONS_BY_ID]
    answered = {str(qid): (answers.get(str(qid)) or answers.get(qid)) for qid in question_ids}
    correct = sum(
        1 for question in resolved if answered.get(str(question["id"])) == question["answer"]
    )
    denominator = len(resolved) or 1
    return {
        "correct": correct,
        "total": len(resolved),
        "score": round(correct / denominator * 100),
    }
