from rest_framework import serializers

DIFFICULTIES = ["入门", "初级", "中级", "高级", "专家"]
PAPER_AMOUNTS = [10, 20, 30, 50]


class GeneratePaperSerializer(serializers.Serializer):
    difficulty = serializers.ChoiceField(choices=DIFFICULTIES)
    amount = serializers.ChoiceField(choices=PAPER_AMOUNTS)


class LatestPaperSerializer(serializers.Serializer):
    # 刷新回读时可按难度取最近一份；不传则返回最新生成的试卷。
    difficulty = serializers.ChoiceField(choices=DIFFICULTIES, required=False)


class SubmitExamSerializer(serializers.Serializer):
    answers = serializers.DictField(child=serializers.CharField(), required=False)
