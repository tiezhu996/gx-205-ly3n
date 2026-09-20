"""智能组卷服务：卷内去重、缺口说明、连续同难度组卷优先避开上一份。"""

import random
import threading

from bank.question_bank import QUESTION_BANK


class PaperBuilder:
    """按难度抽题组卷。

    保证：
    1. 同一份试卷内不出现重复题目（按题目 id 去重）；
    2. 请求题量超过可用题量时只返回实际题数，并给出缺口原因，不用重复题补齐；
    3. 连续按同一难度组卷时优先避开上一份已出现的题，题池不足才复用；
    4. 记录最近一次组卷结果，供页面刷新后回读。
    """

    def __init__(self, questions):
        self._questions = list(questions)
        self._lock = threading.Lock()
        self._last_ids = {}       # difficulty -> set[int]，该难度上一份试卷的题目 id
        self._latest_result = None  # 最近一次组卷结果（含试卷与元信息）

    def pool_for(self, difficulty):
        """返回指定难度的去重题池（按题目 id 去重，保持题库顺序）。"""
        seen, pool = set(), []
        for question in self._questions:
            if question["difficulty"] != difficulty or question["id"] in seen:
                continue
            seen.add(question["id"])
            pool.append(question)
        return pool

    def generate(self, difficulty, amount):
        pool = self.pool_for(difficulty)
        with self._lock:
            last_ids = self._last_ids.get(difficulty, set())
            # 优先使用上一份未出现过的题
            fresh = [q for q in pool if q["id"] not in last_ids]
            random.shuffle(fresh)
            picked = list(fresh[:amount])
            if len(picked) < amount:
                # 题池不足时才从上一份出现过的题里复用，仍保证卷内不重复
                chosen = {q["id"] for q in picked}
                rest = [q for q in pool if q["id"] not in chosen]
                random.shuffle(rest)
                picked.extend(rest[: amount - len(picked)])
            reused = sum(1 for q in picked if q["id"] in last_ids)
            self._last_ids[difficulty] = {q["id"] for q in picked}
            result = self._build_result(difficulty, amount, picked, reused, len(pool))
            self._latest_result = result
            return result

    @staticmethod
    def _build_result(difficulty, amount, picked, reused, pool_size):
        actual = len(picked)
        shortage = None
        if actual < amount:
            shortage = (
                f"「{difficulty}」难度题池仅有 {pool_size} 道不重复题目，"
                f"本次实际组卷 {actual} 题，缺口 {amount - actual} 题；"
                "不会用重复题目补齐，请降低题量或更换难度。"
            )
        return {
            "paper": picked,
            "difficulty": difficulty,
            "requested": amount,
            "actual": actual,
            "reused": reused,
            "shortage": shortage,
        }

    def latest(self):
        """返回最近一次组卷结果；尚未组卷时返回 None。"""
        with self._lock:
            return self._latest_result


paper_builder = PaperBuilder(QUESTION_BANK)
