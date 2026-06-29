"""분석가/검증자 서브에이전트의 구조화 출력 스키마.

client.messages.parse() 가 이 Pydantic 모델로 응답을 강제·검증한다.
(min/max 등 미지원 제약은 SDK가 자동으로 제거하므로 단순 타입만 사용)
"""
from typing import List

from pydantic import BaseModel


class MeasurementItem(BaseModel):
    항목: str
    측정값: str  # "확인 필요"가 들어갈 수 있어 문자열
    단위: str
    기준: str
    판정: str  # 합격 / 불합격 / 확인 필요
    비고: str


class AnalysisResult(BaseModel):
    """분석가 산출물."""

    items: List[MeasurementItem]
    특이사항: List[str]
    후속조치: List[str]


class Finding(BaseModel):
    항목: str
    문제: str
    심각도: str  # 높음 / 중간 / 낮음


class VerdictResult(BaseModel):
    """검증자 산출물 — 직접 수정하지 않고 PASS/FAIL과 사유만 보고."""

    passed: bool
    findings: List[Finding]
    summary: str
