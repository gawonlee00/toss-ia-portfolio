from __future__ import annotations
from typing import Dict, Any, List
from config import POLICY, WEIGHTS, UNITS, CORE_COVERAGES, MILLION, OCCUPATION_RULES
from statistical_risk import incidence_factor

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def round_money(x: float, step: int | None = None) -> int:
    if x <= 0: return 0
    step = step or POLICY["rounding"]
    return int(round(x / step) * step)

def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    if height_cm <= 0 or weight_kg <= 0:
        return 0.0
    return round(weight_kg / ((height_cm / 100.0) ** 2), 1)

def infer_occupation_risk(occupation: str) -> float:
    text = (occupation or "").strip().lower()
    for risk, keywords in OCCUPATION_RULES:
        if any(k.lower() in text for k in keywords):
            return risk
    return 1.1  # 미분류 직업은 중립에 가까운 내부 기본값

def age_factor(age: int) -> float:
    if age < 30: return 0.20
    if age < 40: return 0.35
    if age < 50: return 0.55
    if age < 60: return 0.75
    if age < 70: return 0.90
    return 1.00

def family_factor(c):
    raw = (
        0.15 * bool(c.get("married"))
        + 0.18 * bool(c.get("nonworking_spouse"))
        + 0.15 * min(int(c.get("dependents", 0)), 3) / 3
        + 0.22 * min(int(c.get("young_children", 0)), 2) / 2
        + 0.12 * bool(c.get("parent_support"))
        + 0.18 * bool(c.get("primary_earner"))
    )
    return clamp(raw)

def health_factor(c):
    risks = [
        bool(c.get("hypertension")), bool(c.get("diabetes")), bool(c.get("dyslipidemia")),
        bool(c.get("smoker")), float(c.get("bmi", 22)) >= 25,
        bool(c.get("recent_hospitalization")), bool(c.get("recent_surgery")), bool(c.get("medication")),
    ]
    return clamp(sum(risks) / 5)

def cv_health_factor(c):
    return clamp(
        0.22 * bool(c.get("hypertension"))
        + 0.22 * bool(c.get("diabetes"))
        + 0.18 * bool(c.get("dyslipidemia"))
        + 0.18 * bool(c.get("smoker"))
        + 0.12 * (float(c.get("bmi", 22)) >= 25)
        + 0.08 * bool(c.get("cv_history"))
    )

def cancer_health_factor(c):
    return clamp(
        0.30 * bool(c.get("smoker"))
        + 0.20 * (float(c.get("bmi", 22)) >= 25)
        + 0.25 * bool(c.get("cancer_history"))
        + 0.25 * bool(c.get("recent_hospitalization"))
    )

def occupation_factor(c):
    r = float(c.get("occupation_risk", 1.1))
    return clamp((r - 1.0) / 0.5)

def income_factor(c):
    annual = max(float(c.get("annual_income", 0)), 0)
    exp = max(float(c.get("monthly_essential_expense", 0)), 1)
    margin = max(annual/12 - exp, 0)
    return 1 - clamp(margin / max(exp * 2, 1))

def debt_factor(c):
    debt = max(float(c.get("debt", 0)), 0)
    liquid = max(float(c.get("financial_assets", 0)), 1)
    return clamp(debt / (debt + liquid))

def family_history_factor(c, kind):
    return 1.0 if bool(c.get(f"family_history_{kind}")) else 0.0

def critical_illness_target(c, kind):
    p = POLICY["critical_illness"][kind]
    monthly_income = max(float(c.get("annual_income", 0))/12, 0)
    essential = max(float(c.get("monthly_essential_expense", 0)), 0)
    base = max(monthly_income * p["income_replacement"], essential) * p["shock_months"]
    hf = cancer_health_factor(c) if kind == "cancer" else cv_health_factor(c)
    stat = incidence_factor(kind, int(c.get("age", 40)), c.get("sex", "여"))
    amount = base
    amount *= 1 + family_factor(c) * (p["family_mult_max"] - 1)
    amount *= 1 + hf * (p["health_mult_max"] - 1)
    amount *= 1 + stat * (p["stat_mult_max"] - 1)
    return round_money(amount)

def similar_cancer_target(c):
    p = POLICY["critical_illness"]["similar_cancer"]
    monthly_income = max(float(c.get("annual_income", 0))/12, 0)
    essential = max(float(c.get("monthly_essential_expense", 0)), 0)
    base = max(monthly_income * p["income_replacement"], essential * 0.50) * p["shock_months"]
    amount = base
    amount *= 1 + family_factor(c) * (p["family_mult_max"] - 1)
    amount *= 1 + cancer_health_factor(c) * (p["health_mult_max"] - 1)
    stat = incidence_factor("cancer", int(c.get("age", 40)), c.get("sex", "여"))
    amount *= 1 + stat * (p["stat_mult_max"] - 1)
    amount = min(max(amount, p["min_amount"]), p["max_amount"])
    return round_money(amount, MILLION)

def death_target(c):
    p = POLICY["death"]
    exp = max(float(c.get("monthly_essential_expense", 0)), 0)
    years = p["base_living_years"]
    years += p["young_child_extra_years"] * min(int(c.get("young_children", 0)), 2)
    years += p["nonworking_spouse_extra_years"] * int(bool(c.get("nonworking_spouse")))
    years += p["parent_support_extra_years"] * int(bool(c.get("parent_support")))
    years = min(years, p["max_living_years"])
    living = exp * 12 * years
    debt = max(float(c.get("debt", 0)), 0)
    edu = max(float(c.get("education_fund_needed", 0)), 0)
    liquid = max(float(c.get("financial_assets", 0)), 0) + max(float(c.get("emergency_fund", 0)), 0)
    return round_money(max(0, living + debt + edu - liquid * p["liquid_asset_offset_ratio"]))

def disability_target(c, kind):
    p = POLICY["disability"]
    months = p["disease_income_months"] if kind == "disease" else p["injury_income_months"]
    monthly_income = max(float(c.get("annual_income", 0))/12, 0)
    essential = max(float(c.get("monthly_essential_expense", 0)), 0)
    base = max(monthly_income*p["income_replacement"], essential) * months
    base *= 1 + (0.20*health_factor(c) if kind=="disease" else 0.35*occupation_factor(c))
    return round_money(base)

def income_loss_reserve_need(c):
    p = POLICY["income_loss_reserve"]
    monthly_income = max(float(c.get("annual_income", 0))/12, 0)
    essential = max(float(c.get("monthly_essential_expense", 0)), 0)
    return round_money(max(monthly_income*p["income_replacement"], essential) * p["months"])

def surgery_target(c, kind):
    p = POLICY["surgery"]
    exp = max(float(c.get("monthly_essential_expense", 0)), 0)
    months = p["disease_expense_months"] if kind=="disease" else p["injury_expense_months"]
    base = max(p["min_amount"], exp*months)
    base *= 1 + (0.20*health_factor(c) if kind=="disease" else 0.30*occupation_factor(c))
    return round_money(base, MILLION)

def monthly_care_target(c, kind):
    p = POLICY["long_term_care"] if kind=="care" else POLICY["dementia"]
    exp = max(float(c.get("monthly_essential_expense", 0)), 0)
    amt = exp*p["expense_ratio"]*(1 + 0.25*age_factor(int(c.get("age", 40))))
    return round_money(min(max(amt,p["min_monthly"]),p["max_monthly"]),100_000)

def hospital_daily_target(c):
    p=POLICY["hospital_daily"]
    exp=max(float(c.get("monthly_essential_expense",0)),0)
    amt=(exp/30)*p["expense_ratio"]
    return int(round(min(max(amt,p["min_daily"]),p["max_daily"])/10_000)*10_000)

def representative_surgery_amount(flat_amount, type_amounts):
    """정액 수술비와 1~5종 수술비를 단순합산하지 않고 3종을 중간 대표 시나리오로 비교한다."""
    rep_type = POLICY["surgery"]["representative_type"]
    type3 = float((type_amounts or {}).get(rep_type, 0) or 0)
    return int(max(float(flat_amount or 0), type3))

def representative_disability_amount(under80, over80):
    """80%미만은 30% 중등도 장해 시나리오로 환산. 실제 보험금 계산이 아님."""
    ref = POLICY["disability"]["under80_reference_ratio"]
    return int(max(float(over80 or 0), float(under80 or 0) * ref))

def care_cash_monthly_equivalent(daily_cash):
    return int(max(float(daily_cash or 0), 0) * 30)

def build_current_coverage(details):
    """세부 특약 입력을 Needs 엔진의 14개 분석 버킷으로 보수적으로 환산."""
    disease_types = {i: details.get(f"질병종수술_{i}종",0) for i in range(1,6)}
    injury_types = {i: details.get(f"상해종수술_{i}종",0) for i in range(1,6)}
    return {
        "실손": int(bool(details.get("실손"))),
        "일반암진단": details.get("일반암진단",0),
        "유사암진단": details.get("유사암진단",0),
        "뇌혈관진단": details.get("뇌혈관진단",0),
        "허혈성심장진단": details.get("허혈성심장진단",0),
        "질병수술": representative_surgery_amount(details.get("질병수술_정액",0), disease_types),
        "상해수술": representative_surgery_amount(details.get("상해수술_정액",0), injury_types),
        "질병후유장해": representative_disability_amount(details.get("질병후유장해_80미만",0), details.get("질병후유장해_80이상",0)),
        "상해후유장해": representative_disability_amount(details.get("상해후유장해_80미만",0), details.get("상해후유장해_80이상",0)),
        "사망": details.get("사망",0),
        "간병": care_cash_monthly_equivalent(details.get("간병인사용일당",0)),
        "치매": details.get("치매월생활자금",0),
        "입원일당": details.get("입원일당",0),
        "일상생활배상": details.get("일상생활배상",0),
    }

def target_coverages(c):
    return {
        "실손":1,
        "일반암진단":critical_illness_target(c,"cancer"),
        "유사암진단":similar_cancer_target(c),
        "뇌혈관진단":critical_illness_target(c,"brain"),
        "허혈성심장진단":critical_illness_target(c,"heart"),
        "질병수술":surgery_target(c,"disease"),
        "상해수술":surgery_target(c,"injury"),
        "질병후유장해":disability_target(c,"disease"),
        "상해후유장해":disability_target(c,"injury"),
        "사망":death_target(c),
        "간병":monthly_care_target(c,"care"),
        "치매":monthly_care_target(c,"dementia"),
        "입원일당":hospital_daily_target(c),
        "일상생활배상":POLICY["liability"]["target"],
    }

def gap_ratio(target,current):
    if target<=0:return 0
    return clamp((target-current)/target)

def need_score(c,coverage,target,current):
    w=WEIGHTS[coverage]
    f={"age":age_factor(int(c.get("age",40))),"health":health_factor(c),"occupation":occupation_factor(c),
       "family":family_factor(c),"income":income_factor(c),"debt":debt_factor(c),
       "gap":gap_ratio(target,current),"impact":1.0,"stat_risk":0.0,"family_history":0.0}
    if coverage=="일반암진단":
        f["health"]=cancer_health_factor(c);f["stat_risk"]=incidence_factor("cancer",int(c.get("age",40)),c.get("sex","여"));f["family_history"]=family_history_factor(c,"cancer")
    elif coverage=="유사암진단":
        f["health"]=cancer_health_factor(c);f["stat_risk"]=incidence_factor("cancer",int(c.get("age",40)),c.get("sex","여"));f["family_history"]=family_history_factor(c,"cancer")
    elif coverage=="뇌혈관진단":
        f["health"]=cv_health_factor(c);f["stat_risk"]=incidence_factor("brain",int(c.get("age",40)),c.get("sex","여"));f["family_history"]=family_history_factor(c,"brain")
    elif coverage=="허혈성심장진단":
        f["health"]=cv_health_factor(c);f["stat_risk"]=incidence_factor("heart",int(c.get("age",40)),c.get("sex","여"));f["family_history"]=family_history_factor(c,"heart")
    elif coverage=="치매":
        f["family_history"]=family_history_factor(c,"dementia")
    raw=sum(float(v)*f.get(k,0) for k,v in w.items())
    return int(round(clamp(raw/max(sum(w.values()),1))*100))

def status_from_ratio(r):
    if r<0.5:return "매우 부족"
    if r<0.8:return "부족"
    if r<1.2:return "적정"
    if r<1.5:return "충분"
    return "과다 가능성 검토"

def analyze(c,current,custom_targets=None):
    """
    자동 Needs 권장값을 기본으로 사용하되,
    custom_targets에 값이 있으면 해당 보장의 권장값을 사용자 수정값으로 대체한다.
    모든 GAP/충족률/NeedScore/우선순위 계산은 최종 적용 권장값 기준으로 재계산된다.
    """
    auto_targets = target_coverages(c)
    custom_targets = custom_targets or {}
    rows=[]
    for cov,auto_target in auto_targets.items():
        custom_value = custom_targets.get(cov, None)
        if custom_value is None:
            target = auto_target
            target_source = "자동"
        else:
            target = max(float(custom_value), 0)
            target_source = "사용자 수정"
        cur=float(current.get(cov,0) or 0)
        ratio=cur/target if target>0 else 1
        gap=max(target-cur,0)
        ns=need_score(c,cov,target,cur)
        rows.append({
            "보장":cov,
            "단위":UNITS[cov],
            "현재":int(cur),
            "자동권장":int(auto_target),
            "권장":int(target),
            "권장값출처":target_source,
            "GAP":int(gap),
            "충족률":round(ratio*100,1),
            "판정":status_from_ratio(ratio),
            "NeedScore":ns,
            "우선순위점수":int(round(ns*gap_ratio(target,cur)))
        })
    return rows

def apply_product_limits(rows, product_limits=None):
    product_limits=product_limits or {}
    out=[]
    for r in rows:
        x=dict(r);limit=float(product_limits.get(r["보장"],0) or 0)
        if limit>0:
            cap=max(limit-float(r["현재"]),0)
            x.update({"상품가입한도":int(limit),"실제제안가능추가액":int(min(r["GAP"],cap)),"한도판정":"한도 적용"})
        else:
            x.update({"상품가입한도":0,"실제제안가능추가액":int(r["GAP"]),"한도판정":"미확인"})
        out.append(x)
    return out

def portfolio_score(rows,c,monthly_premium):
    core=[r for r in rows if r["보장"] in CORE_COVERAGES]
    fulfillment=sum(min(r["충족률"],100) for r in core)/max(len(core),1)/100
    coverage_pts=40*fulfillment

    # 별도 '소득보장 특약'을 가정하지 않고 진단비+후유장해의 충족도로 소득상실 대비를 평가.
    income_names={"일반암진단","뇌혈관진단","허혈성심장진단","질병후유장해","상해후유장해"}
    inc=[r for r in rows if r["보장"] in income_names]
    income_pts=15*(sum(min(r["충족률"],100) for r in inc)/max(len(inc),1)/100)

    death=next(r for r in rows if r["보장"]=="사망")
    ff=family_factor(c);family_base=min(death["충족률"],100)/100
    family_pts=15*(family_base*max(ff,0.35)+(1-ff)*0.65)

    monthly_income=max(float(c.get("annual_income",0))/12,1)
    pr=monthly_premium/monthly_income
    premium_factor=1 if pr<=.05 else .9 if pr<=.08 else .75 if pr<=.12 else .5 if pr<=.18 else .25
    premium_pts=15*premium_factor

    severe=sum(r["판정"]=="매우 부족" for r in core)
    structure_pts=10*max(0,1-severe/max(len(core),1))
    emergency=max(float(c.get("emergency_fund",0)),0)
    sustain=clamp(emergency/max(monthly_premium*12,1))
    sustainability_pts=5*sustain

    total=round(coverage_pts+income_pts+family_pts+premium_pts+structure_pts+sustainability_pts,1)
    if total>=90:grade,comment="A+","보장 구조와 지속가능성이 매우 양호합니다."
    elif total>=80:grade,comment="A","전반적으로 양호하며 일부 보장만 점검하면 됩니다."
    elif total>=70:grade,comment="B","기본 구조는 갖추었으나 핵심 보장 일부의 보완 검토가 필요합니다."
    elif total>=60:grade,comment="C","여러 핵심 영역에서 보장 공백이 확인됩니다."
    elif total>=50:grade,comment="D","보장 공백과 보험료 구조를 함께 재점검할 필요가 있습니다."
    else:grade,comment="E","핵심 위험 대비가 전반적으로 부족하여 우선순위 중심 재설계 검토가 필요합니다."
    return {"총점":total,"등급":grade,"코멘트":comment,"핵심보장":round(coverage_pts,1),
            "소득상실":round(income_pts,1),"가족책임":round(family_pts,1),"보험료":round(premium_pts,1),
            "보장구조":round(structure_pts,1),"지속가능성":round(sustainability_pts,1),
            "보험료부담률":round(pr*100,1)}

def profile_amounts(rows):
    ms={"최소형":.70,"균형형":1.0,"강화형":1.25};out=[]
    for r in rows:
        row={"보장":r["보장"],"현재":r["현재"]}
        for name,m in ms.items():
            if r["보장"]=="실손": row[name]=1
            else:
                step=100_000 if r["보장"] in ("간병","치매") else 10_000 if r["보장"]=="입원일당" else MILLION
                row[name]=round_money(r["권장"]*m,step)
        out.append(row)
    return out

def underwriting_flags(c):
    labels=[("cancer_history","암 병력"),("cv_history","심뇌혈관 병력"),("recent_hospitalization","최근 입원"),
            ("recent_surgery","최근 수술"),("medication","현재 투약"),("hypertension","고혈압"),("diabetes","당뇨")]
    return [label for key,label in labels if c.get(key)]

def consultation_comment(rows,score,c):
    top=[r["보장"] for r in sorted(rows,key=lambda x:x["우선순위점수"],reverse=True) if r["GAP"]>0][:3]
    s=[f"전체 포트폴리오는 {score['등급']}등급({score['총점']}점)입니다.",score["코멘트"]]
    if top:s.append("현재 분석상 우선 검토 영역은 "+", ".join(top)+"입니다.")
    s.append(f"월 보험료 부담률은 월소득 대비 {score['보험료부담률']}%입니다.")
    flags=underwriting_flags(c)
    if flags:s.append("인수심사 확인 필요: "+", ".join(flags)+". 실제 가입 가능 여부는 보험사별 기준 확인이 필요합니다.")
    return " ".join(s)
