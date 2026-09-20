from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from bank.paper_service import paper_builder
from bank.question_bank import QUESTION_BANK
from bank.serializers import GeneratePaperSerializer, SubmitExamSerializer


QUESTIONS = QUESTION_BANK


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
        "paper": QUESTIONS[:3],
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
    }


@api_view(["GET"])
def health(_request):
    return Response({"status": "ok", "service": "gxlogic-bank-backend"})


@api_view(["GET"])
def dashboard(_request):
    return Response(build_dashboard())


@api_view(["POST"])
def generate_paper(request):
    serializer = GeneratePaperSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    difficulty = serializer.validated_data["difficulty"]
    amount = int(serializer.validated_data["amount"])
    return Response(paper_builder.generate(difficulty, amount))


@api_view(["GET"])
def latest_paper(_request):
    result = paper_builder.latest()
    if result is None:
        return Response({"paper": None})
    return Response(result)


@api_view(["POST"])
def submit_exam(request):
    serializer = SubmitExamSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    answers = serializer.validated_data.get("answers", {})
    correct = sum(1 for question in QUESTIONS if answers.get(str(question["id"])) == question["answer"])
    score = round(correct / len(QUESTIONS) * 100)
    return Response(
        {
            "score": score,
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
