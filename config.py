# TOSS IA Portfolio v1.3.0
# 모든 금액 단위: 원
MILLION = 1_000_000

POLICY = {
    "rounding": 5 * MILLION,
    "critical_illness": {
        "cancer": {
            "shock_months": 8, "income_replacement": 0.60,
            "family_mult_max": 1.20, "health_mult_max": 1.20, "stat_mult_max": 1.15,
        },
        "similar_cancer": {
            "shock_months": 2, "income_replacement": 0.50,
            "family_mult_max": 1.10, "health_mult_max": 1.10,
            # 유사암은 표준화된 국가 단일 집계가 없어 공식 통계 보정 미적용
            "stat_mult_max": 1.08,
            "min_amount": 3 * MILLION, "max_amount": 20 * MILLION,
        },
        "brain": {
            "shock_months": 12, "income_replacement": 0.60,
            "family_mult_max": 1.25, "health_mult_max": 1.25, "stat_mult_max": 1.15,
        },
        "heart": {
            "shock_months": 8, "income_replacement": 0.60,
            "family_mult_max": 1.20, "health_mult_max": 1.25, "stat_mult_max": 1.15,
        },
    },
    "death": {
        "base_living_years": 3, "max_living_years": 10,
        "young_child_extra_years": 2, "nonworking_spouse_extra_years": 2,
        "parent_support_extra_years": 1, "liquid_asset_offset_ratio": 0.70,
    },
    "disability": {
        "disease_income_months": 18, "injury_income_months": 12,
        "income_replacement": 0.60,
        # 80%미만 담보를 분석용 대표 금액으로 환산할 때 사용하는 중등도 장해 시나리오
        # 실제 보험금 산식이 아님.
        "under80_reference_ratio": 0.30,
    },
    # '소득보장 특약'으로 판매되는 보편적 독립 담보가 있다는 가정은 제거.
    # 아래 값은 보험계약 입력이 아니라 내부 소득상실 Needs 참고치에만 사용.
    "income_loss_reserve": {"months": 12, "income_replacement": 0.60},
    "surgery": {
        "disease_expense_months": 1.5, "injury_expense_months": 1.0,
        "min_amount": 3 * MILLION,
        # 1~5종 종수술비는 상품마다 금액표가 다르므로 3종을 상담용 중간 대표치로 사용.
        "representative_type": 3,
    },
    "long_term_care": {
        "expense_ratio": 0.30, "min_monthly": 500_000, "max_monthly": 2_000_000,
    },
    "dementia": {
        "expense_ratio": 0.25, "min_monthly": 500_000, "max_monthly": 2_000_000,
    },
    "hospital_daily": {"expense_ratio": 0.20, "min_daily": 20_000, "max_daily": 100_000},
    "liability": {"target": 100 * MILLION},
}

# NeedScore 가중치. 공식 계리위험률이 아니라 상담 우선순위를 위한 내부 정책모형.
WEIGHTS = {
    "실손":             {"age": 4, "health": 12, "occupation": 4, "family": 3, "income": 5, "gap": 25, "impact": 22},
    "일반암진단":       {"stat_risk": 10, "health": 10, "family_history": 8, "family": 4, "income": 8, "gap": 25, "impact": 35},
    # 유사암에는 공식 '유사암 전체' 통계지수를 사용하지 않는다.
    "유사암진단":       {"stat_risk": 6, "health": 6, "family_history": 4, "family": 4, "income": 5, "gap": 25, "impact": 24},
    "뇌혈관진단":       {"stat_risk": 13, "health": 12, "family_history": 6, "family": 4, "income": 5, "gap": 25, "impact": 35},
    "허혈성심장진단":   {"stat_risk": 13, "health": 12, "family_history": 6, "family": 4, "income": 5, "gap": 25, "impact": 35},
    "질병수술":         {"age": 8, "health": 10, "family": 4, "income": 5, "gap": 25, "impact": 25},
    "상해수술":         {"age": 4, "occupation": 16, "family": 4, "income": 4, "gap": 25, "impact": 22},
    "질병후유장해":     {"age": 7, "health": 10, "family": 8, "income": 10, "gap": 25, "impact": 35},
    "상해후유장해":     {"age": 4, "occupation": 14, "family": 8, "income": 9, "gap": 25, "impact": 35},
    "사망":             {"age": 3, "family": 20, "debt": 10, "income": 7, "gap": 25, "impact": 35},
    "간병":             {"age": 16, "health": 10, "family": 5, "income": 4, "gap": 25, "impact": 30},
    "치매":             {"age": 18, "health": 6, "family_history": 5, "family": 4, "income": 2, "gap": 25, "impact": 30},
    "입원일당":         {"age": 5, "health": 8, "occupation": 4, "income": 3, "gap": 20, "impact": 15},
    "일상생활배상":     {"family": 8, "gap": 25, "impact": 18},
}

UNITS = {
    "실손": "가입여부",
    "일반암진단": "일시금",
    "유사암진단": "일시금",
    "뇌혈관진단": "일시금",
    "허혈성심장진단": "일시금",
    "질병수술": "분석용 대표 1회 금액",
    "상해수술": "분석용 대표 1회 금액",
    "질병후유장해": "분석용 대표 일시금",
    "상해후유장해": "분석용 대표 일시금",
    "사망": "일시금",
    "간병": "현금 일당 월환산",
    "치매": "월 생활자금",
    "입원일당": "1일 보장액",
    "일상생활배상": "보상한도",
}

CORE_COVERAGES = [
    "실손", "일반암진단", "뇌혈관진단", "허혈성심장진단",
    "질병후유장해", "상해후유장해", "사망"
]

# 보험사 공식 직업급수가 아니라 상담용 내부 위험지수.
OCCUPATION_RULES = [
    (1.5, ["소방", "구조대", "광부", "광산", "잠수", "다이버", "지붕", "고공", "폭발물"]),
    (1.4, ["용접", "중장비", "전기공", "선박", "조선", "크레인", "철골", "굴착", "배관공"]),
    (1.3, ["건설", "건축", "현장", "정비", "공장", "생산직", "목수", "미장", "택배상하차"]),
    (1.2, ["운전", "기사", "배송", "물류", "창고", "기계", "기술직", "조리", "요리사"]),
    (1.1, ["영업", "판매", "서비스", "매장", "미용", "간호", "간호사", "요양보호", "자영업"]),
    (1.0, ["사무", "회사원", "공무원", "교사", "교수", "연구", "개발자", "프로그래머", "회계", "세무", "은행", "금융", "디자이너"]),
]
