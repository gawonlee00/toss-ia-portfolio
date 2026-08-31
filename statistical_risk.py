from __future__ import annotations
from pathlib import Path
import math
import pandas as pd

_DATA = pd.read_csv(Path(__file__).with_name("epidemiology_2023.csv"))

def age_band(age: int) -> str:
    if age < 30: return "20-29"
    if age < 40: return "30-39"
    if age < 50: return "40-49"
    if age < 60: return "50-59"
    if age < 70: return "60-69"
    if age < 80: return "70-79"
    return "80+"

def incidence_record(disease: str, age: int, sex: str) -> dict:
    band = age_band(age)
    row = _DATA[
        (_DATA["disease"] == disease) &
        (_DATA["sex"] == sex) &
        (_DATA["age_band"] == band)
    ]
    if row.empty:
        raise ValueError(f"통계 데이터 없음: {disease}/{sex}/{band}")
    r = row.iloc[0]

    ref = _DATA[
        (_DATA["disease"] == disease) &
        (_DATA["sex"] == sex) &
        (_DATA["age_band"] == "50-59")
    ].iloc[0]["rate_per_100k"]

    max_rate = _DATA[_DATA["disease"] == disease]["rate_per_100k"].max()
    rate = float(r["rate_per_100k"])

    rate_ratio_to_50s = rate / float(ref) if ref else 0.0
    normalized_factor = math.sqrt(max(rate, 0.0) / float(max_rate)) if max_rate else 0.0

    return {
        "disease": disease,
        "age_band": band,
        "sex": sex,
        "rate_per_100k": rate,
        "rate_ratio_to_50s": rate_ratio_to_50s,
        "normalized_factor": min(max(normalized_factor, 0.0), 1.0),
        "source_year": str(r["source_year"]),
        "source": str(r["source"]),
        "unit": str(r["unit"]),
        "age_proxy_used": age < 20,
    }

def incidence_factor(disease: str, age: int, sex: str) -> float:
    return incidence_record(disease, age, sex)["normalized_factor"]

def risk_summary(age: int, sex: str):
    labels = {
        "cancer": "전체 암",
        "brain": "뇌졸중",
        "heart": "심근경색증",
    }
    rows = []
    for d in ("cancer", "brain", "heart"):
        x = incidence_record(d, age, sex)
        rows.append({
            "key": d,
            "질환": labels[d],
            "연령구간": x["age_band"],
            "성별": x["sex"],
            "공식통계": f'{x["rate_per_100k"]:,.1f} {x["unit"]}',
            "50대 대비 발생률비": round(x["rate_ratio_to_50s"], 2),
            "모델위험지수": x["normalized_factor"],
            "출처": x["source"],
            "통계연도": x["source_year"],
        })

    # 유사암은 별도 국가 표준통계가 없으므로 v1.2.2 방식대로
    # 전체 암 발생률을 제한적 상담 보정치로 재사용하되 명시적으로 표시.
    c = incidence_record("cancer", age, sex)
    rows.insert(1, {
        "key": "similar_cancer",
        "질환": "유사암(전체 암 통계 참고)",
        "연령구간": c["age_band"],
        "성별": c["sex"],
        "공식통계": f'{c["rate_per_100k"]:,.1f} {c["unit"]}',
        "50대 대비 발생률비": round(c["rate_ratio_to_50s"], 2),
        "모델위험지수": c["normalized_factor"],
        "출처": c["source"] + " (유사암 직접 통계 아님)",
        "통계연도": c["source_year"],
    })
    return rows
