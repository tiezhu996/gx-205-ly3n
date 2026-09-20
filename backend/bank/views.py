from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from bank.paper_service import generate_paper, get_last_paper, grade_paper
from bank.questions import QUESTIONS_BY_ID, QUESTION_BANK
from bank.serializers import GeneratePaperSerializer, LatestPaperSerializer, SubmitExamSerializer

# 仪表盘沿用示例数据中的三道题，均来自真实题池，保证页面开箱即有内容。
DASHBOARD_SAMPLE_IDS = [101, 302, 203]


def build_dashboard() -> dict:
    return {
        "profile": {
            "nickname": "推理训练示例用户",
            "tier": "铂金",
            "totalAnswered": 1260,
            "correctRate": 86.5,
            "streakDays": 19,
            "practiceMinutes": 2480,
        },
        "categories": [
            {"id": 1, "name": "数字推理", "accuracy": 88, "total": 320},
            {"id": 2, "name": "图形推理", "accuracy": 76, "total": 240},
            {"id": 3, "name": "逻辑判断", "accuracy": 91, "total": 280},
            {"id": 4, "name": "类比推理", "accuracy": 84, "total": 210},
            {"id": 5, "name": "演绎推理", "accuracy": 80, "total": 210},
        ],
        "paper": [QUESTIONS_BY_ID[qid] for qid in DASHBOARD_SAMPLE_IDS],
        "wrongBook": [
            {"id": 1, "title": "集合包含关系反推", "type": "演绎推理", "mistakes": 5, "lastPracticed": "05-28"},
            {"id": 2, "title": "九宫格旋转规律", "type": "图形推理", "mistakes": 4, "lastPracticed": "05-27"},
            {"id": 3, "title": "多条件排序", "type": "逻辑判断", "mistakes": 3, "lastPracticed": "05-26"},
        ],
        "rankings": [
            {"rank": 1, "name": "ReasonMax", "tier": "王者", "score": 9820, "accuracy": 94.2},
            {"rank": 2, "name": "DeducePro", "tier": "钻石", "score": 8760, "accuracy": 91.7},
            {"rank": 3, "name": "推理训练示例用户", "tier": "铂金", "score": 7650, "accuracy": 86.5},
        ],
        "radar": [
            {"axis": "数字", "value": 88},
            {"axis": "图形", "value": 76},
            {"axis": "逻辑", "value": 91},
            {"axis": "类比", "value": 84},
            {"axis": "演绎", "value": 80},
        ],
        # 各难度可用题量，前端可据此提示题池规模。
        "poolAmounts": {difficulty: sum(1 for q in QUESTION_BANK if q["difficulty"] == difficulty)
                        for difficulty in ["入门", "初级", "中级", "高级", "专家"]},
    }


@api_view(["GET"])
def health(_request):
    return Response({"status": "ok", "service": "gxlogic-bank-backend"})


@api_view(["GET"])
def dashboard(_request):
    return Response(build_dashboard())


@api_view(["POST"])
def generate_paper_view(request):
    """智能组卷：同卷题目不重复，题池不足时返回实际题数和缺口原因。"""
    serializer = GeneratePaperSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    difficulty = serializer.validated_data["difficulty"]
    amount = int(serializer.validated_data["amount"])
    return Response(generate_paper(difficulty, amount))


@api_view(["GET"])
def latest_paper_view(request):
    """回读最近一次组卷结果，供页面刷新后恢复试卷、实际题数与缺口提示。"""
    serializer = LatestPaperSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    result = get_last_paper(serializer.validated_data.get("difficulty"))
    if result is None:
        return Response({"paper": [], "actual_amount": 0, "notice": "暂无最近一次组卷记录。", "has_gap": False})
    return Response(result)


@api_view(["POST"])
def submit_exam(request):
    """按最近一次实际生成的试卷判分，原有提交入口保持可用。"""
    serializer = SubmitExamSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    answers = serializer.validated_data.get("answers", {}) or {}
    latest = get_last_paper()
    question_ids = latest["question_ids"] if latest else []
    grade = grade_paper(question_ids, answers)
    return Response(
        {
            "score": grade["score"],
            "correct": grade["correct"],
            "total": grade["total"],
            "rank_hint": "本次表现接近黄金 I，继续强化图形推理可冲击铂金。",
            "analysis": ["数字推理稳定", "图形旋转规律仍需复盘", "演绎推理建议练习充分必要条件"],
        }
    )


@api_view(["POST"])
def demo_login(_request):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
    user.set_password("demo1234")
    user.save(update_fields=["password"])
    refresh = RefreshToken.for_user(user)
    return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
