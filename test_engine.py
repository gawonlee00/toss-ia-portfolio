import pytest
from config import WEIGHTS, CORE_COVERAGES
from needs_engine import (
    calculate_bmi, infer_occupation_risk, target_coverages, build_current_coverage,
    representative_surgery_amount, representative_disability_amount,
    care_cash_monthly_equivalent, income_loss_reserve_need, analyze, portfolio_score
)
from statistical_risk import risk_summary, incidence_factor, incidence_record

BASE={
    "age":40,"sex":"여","occupation_risk":1.0,"annual_income":60_000_000,
    "monthly_essential_expense":3_000_000,"financial_assets":50_000_000,
    "emergency_fund":15_000_000,"debt":100_000_000,"education_fund_needed":0,
    "married":False,"nonworking_spouse":False,"dependents":0,"young_children":0,
    "parent_support":False,"primary_earner":True,"bmi":22.0,"smoker":False,
    "hypertension":False,"diabetes":False,"dyslipidemia":False,"medication":False,
    "cancer_history":False,"cv_history":False,"recent_hospitalization":False,
    "recent_surgery":False,"family_history_cancer":False,"family_history_brain":False,
    "family_history_heart":False,"family_history_dementia":False
}

def test_bmi():
    assert calculate_bmi(170,65)==22.5

def test_occupation_office():
    assert infer_occupation_risk("사무직")==1.0

def test_occupation_construction():
    assert infer_occupation_risk("건설현장 근로자")>=1.3

def test_occupation_firefighter():
    assert infer_occupation_risk("소방관")==1.5

def test_no_income_protection_coverage():
    assert "소득보장" not in WEIGHTS
    assert "소득보장" not in target_coverages(BASE)

def test_14_analysis_buckets():
    assert len(target_coverages(BASE))==14

def test_surgery_rep_uses_flat_or_type3_not_sum():
    assert representative_surgery_amount(2_000_000,{1:1_000_000,2:2_000_000,3:5_000_000,4:8_000_000,5:10_000_000})==5_000_000
    assert representative_surgery_amount(7_000_000,{3:5_000_000})==7_000_000

def test_disability_split_rep():
    assert representative_disability_amount(100_000_000,20_000_000)==30_000_000
    assert representative_disability_amount(100_000_000,50_000_000)==50_000_000

def test_care_cash_equivalent():
    assert care_cash_monthly_equivalent(150_000)==4_500_000

def test_current_detail_conversion():
    d={"실손":True,"질병수술_정액":2_000_000,"질병종수술_3종":5_000_000,
       "상해수술_정액":3_000_000,"상해종수술_3종":1_000_000,
       "질병후유장해_80미만":100_000_000,"질병후유장해_80이상":10_000_000,
       "상해후유장해_80미만":50_000_000,"상해후유장해_80이상":30_000_000,
       "간병인사용일당":100_000}
    c=build_current_coverage(d)
    assert c["질병수술"]==5_000_000
    assert c["상해수술"]==3_000_000
    assert c["질병후유장해"]==30_000_000
    assert c["상해후유장해"]==30_000_000
    assert c["간병"]==3_000_000

def test_risk_summary_four_rows():
    assert len(risk_summary(45,"여"))==4

def test_targets_nonnegative():
    assert all(v>=0 for v in target_coverages(BASE).values())

def test_more_dependents_not_reduce_death():
    a=dict(BASE,dependents=0,young_children=0)
    b=dict(BASE,dependents=2,young_children=2)
    assert target_coverages(b)["사망"]>=target_coverages(a)["사망"]

def test_income_loss_internal_need_positive():
    assert income_loss_reserve_need(BASE)>0

def test_portfolio_score_range():
    rows=analyze(BASE,{})
    s=portfolio_score(rows,BASE,300_000)
    assert 0<=s["총점"]<=100

def test_core_has_no_income_protection():
    assert "소득보장" not in CORE_COVERAGES

def test_similar_cancer_independent():
    # 한 고객에서 우연히 일반암의 20%와 같은 값이 나올 수 있으므로
    # 구현 자체가 일반암×20% 연동식이 아닌지와 별도 상·하한을 갖는지를 검증한다.
    import inspect
    from needs_engine import similar_cancer_target
    src = inspect.getsource(similar_cancer_target)
    assert '0.20' not in src
    low = target_coverages(dict(BASE, annual_income=12_000_000, monthly_essential_expense=500_000))
    high = target_coverages(dict(BASE, annual_income=1_000_000_000, monthly_essential_expense=50_000_000))
    assert 3_000_000 <= low["유사암진단"] <= 20_000_000
    assert 3_000_000 <= high["유사암진단"] <= 20_000_000

def test_cancer_risk_sex_age_table_still_works():
    rows=risk_summary(45,"여")
    c=next(x for x in rows if x["key"]=="cancer")
    assert "명/10만명" in c["공식통계"]

def test_official_cancer_rate_restored():
    assert incidence_record("cancer",45,"여")["rate_per_100k"] == 590.0

def test_official_brain_stroke_rate_restored():
    assert incidence_record("brain",45,"남")["rate_per_100k"] == 95.9

def test_official_heart_mi_rate_restored():
    assert incidence_record("heart",45,"남")["rate_per_100k"] == 58.6

def test_similar_cancer_uses_cancer_stat_reference():
    assert incidence_factor("cancer",45,"여") > 0
    rows=risk_summary(45,"여")
    s=next(x for x in rows if x["질환"].startswith("유사암"))
    assert "전체 암 통계 참고" in s["질환"]
    assert "직접 통계 아님" in s["출처"]


def test_custom_target_overrides_auto_target():
    current={}
    auto=target_coverages(BASE)["일반암진단"]
    custom=auto+10_000_000
    rows=analyze(BASE,current,{"일반암진단":custom})
    r=next(x for x in rows if x["보장"]=="일반암진단")
    assert r["자동권장"]==auto
    assert r["권장"]==custom
    assert r["권장값출처"]=="사용자 수정"

def test_gap_recalculates_from_custom_target():
    rows=analyze(BASE,{"일반암진단":20_000_000},{"일반암진단":50_000_000})
    r=next(x for x in rows if x["보장"]=="일반암진단")
    assert r["GAP"]==30_000_000
    assert r["충족률"]==40.0

def test_no_custom_target_uses_auto_target():
    rows=analyze(BASE,{})
    r=next(x for x in rows if x["보장"]=="일반암진단")
    assert r["권장"]==r["자동권장"]
    assert r["권장값출처"]=="자동"

def test_zero_custom_target_allowed():
    rows=analyze(BASE,{"일반암진단":10_000_000},{"일반암진단":0})
    r=next(x for x in rows if x["보장"]=="일반암진단")
    assert r["권장"]==0
    assert r["GAP"]==0


def test_money_format_examples():
    assert f"{50_000_000:,}" == "50,000,000"
    assert int("50,000,000".replace(",","")) == 50_000_000


def test_korean_won_reader():
    from money_utils import number_to_korean_won
    assert number_to_korean_won(59_000_000) == "오천구백만 원"
    assert number_to_korean_won(100_000_000) == "일억 원"
    assert number_to_korean_won(12_345_000) == "천이백삼십사만오천 원"
    assert number_to_korean_won(0) == "영 원"

def test_live_money_component_exists():
    from pathlib import Path
    p = Path(__file__).with_name("money_component") / "index.html"
    assert p.exists()
    html = p.read_text(encoding="utf-8")
    assert "streamlit:setComponentValue" in html
    assert "오천구백만" not in html  # generic algorithm, not hard-coded example
    assert "₩" in html


def test_web_privacy_files_exist():
    from pathlib import Path
    root=Path(__file__).parent
    assert (root/"WEB_PRIVACY_NOTICE.md").exists()
    assert (root/".streamlit"/"config.toml").exists()

def test_local_launchers_exist_for_v142():
    from pathlib import Path
    root=Path(__file__).parent
    launch=(root/"실행.cmd")
    diag=(root/"run.cmd")
    assert launch.exists()
    assert diag.exists()
    assert (root/"run_core.cmd").exists()
    launch_text=launch.read_text(encoding="utf-8-sig")
    diag_text=diag.read_text(encoding="ascii")
    core_text=(root/"run_core.cmd").read_text(encoding="ascii")
    assert "run_core.cmd" in launch_text
    assert "run_core.cmd" in diag_text
    assert "127.0.0.1" in core_text
    assert "python --version" in core_text
    assert "py -3 --version" in core_text
    assert ".venv" in core_text
    assert "run_log.txt" in core_text
