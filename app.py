import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from pathlib import Path

from config import WEIGHTS, UNITS
from needs_engine import (
    analyze, portfolio_score, profile_amounts, consultation_comment, underwriting_flags,
    apply_product_limits, calculate_bmi, infer_occupation_risk, build_current_coverage,
    income_loss_reserve_need
)
from statistical_risk import risk_summary

st.set_page_config(page_title="TOSS IA Portfolio Web v1.4.2", page_icon="🛡️", layout="wide")

# 토스 공식 브랜드 리소스 센터의 원본 미디어 이미지 URL. 이미지 자체는 변형하지 않음.

_money_component = components.declare_component(
    "krw_live_money_input",
    path=str(Path(__file__).parent / "money_component")
)

def money_input(label, value=0, min_value=0, max_value=10_000_000_000, step=1_000_000, key=None, help=None):
    """
    입력하는 순간 ₩ + 천 단위 쉼표 형식으로 표시되는 원화 전용 입력창.
    컴포넌트 내부에서 한글 금액도 실시간 표시한다.
    """
    result = _money_component(
        label=label,
        value=int(value),
        default_value=int(value),
        min_value=int(min_value),
        max_value=int(max_value),
        step=int(step),
        help=help or "",
        key=key or label,
        default=int(value),
    )
    try:
        return int(result)
    except (TypeError, ValueError):
        return int(value)

TOSS_LOGO_URL = "https://framerusercontent.com/images/t1w4UaHb50FmWPlwURqgvIXchYA.jpg?height=739&width=1080"

head1, head2 = st.columns([1, 5])
with head1:
    st.image(TOSS_LOGO_URL, width=180)
with head2:
    st.title("IA Portfolio Web v1.4.2")
    st.caption("비공식 보험 Needs 분석 웹도구 · 토스/토스인슈어런스의 공식 서비스가 아닙니다. 개발자 : IA-OWL")

st.warning(
    "웹 전용 익명 상담 모드입니다. 실명, 전화번호, 이메일, 주민등록번호, 주소, 회사명, 병원명, "
    "정확한 진단일·수술일 등 개인을 직접 식별할 수 있는 정보는 입력하지 마십시오."
)
with st.expander("🔒 개인정보·보안 및 모델 이용 안내", expanded=True):
    st.markdown(
        """
**개인정보 최소수집 원칙**
- 고객 실명 대신 임의의 상담번호/가명만 사용합니다.
- 생년월일·연락처·주소·회사명·병원명 입력란은 제공하지 않습니다.
- 직업은 자유서술이 아니라 넓은 직군으로만 선택합니다.
- 이 앱 코드에는 고객 입력값을 DB·CSV·로그 파일에 저장하는 기능이 없습니다.
- 브라우저를 닫거나 세션이 종료되면 앱 자체가 고객 분석값을 영구 보관하지 않도록 설계했습니다.

**중요한 웹 처리 특성**
- 웹앱이므로 입력값은 분석을 위해 Streamlit 서버로 전송되어 처리됩니다.
- 따라서 '사용자 PC 밖으로 정보가 전혀 나가지 않는다'는 로컬 앱과는 다릅니다.
- Streamlit 호스팅 인프라 자체의 운영 로그·보안 정책까지 이 앱 코드가 통제하는 것은 아닙니다.
- 실제 고객 상담에서는 반드시 가명·비식별화된 정보만 사용하십시오.

**분석모형 안내**
본 앱은 상품추천·인수승인 프로그램이 아닙니다. 권장금액과 가중치는 내부 Needs Analysis 정책모형이며,
상품별 약관·가입한도·직업급수·장해지급률·수술분류는 해당 보험사의 최신 기준을 별도로 확인해야 합니다.
"""
    )

tabs = st.tabs(["① 고객/재무", "② 건강/가족", "③ 현재 보장 상세", "④ 권장값 수정", "⑤ 상품한도(선택)", "⑥ 분석 결과"])
tab1, tab2, tab3, tab4, tab5, tab6 = tabs

with tab1:
    c1,c2,c3 = st.columns(3)
    with c1:
        customer_name=st.text_input("상담번호/가명", "상담 A", help="실명·연락처 등 직접 식별정보를 입력하지 마세요.")
        age=st.number_input("만 나이",18,90,38, help="생년월일은 입력하지 않습니다.")
        sex=st.selectbox("성별",["여","남"])
        occupation=st.selectbox(
            "직업군",
            ["사무·금융·연구·개발", "영업·판매·서비스", "운전·배송·물류", "생산·공장·정비",
             "건설·건축·현장", "전기·용접·중장비·조선", "소방·구조·고공·광산·잠수", "기타"]
        )
        occupation_risk_map = {
            "사무·금융·연구·개발":1.0, "영업·판매·서비스":1.1, "운전·배송·물류":1.2,
            "생산·공장·정비":1.3, "건설·건축·현장":1.3, "전기·용접·중장비·조선":1.4,
            "소방·구조·고공·광산·잠수":1.5, "기타":1.1
        }
        occupation_risk=occupation_risk_map[occupation]
        st.metric("상담용 직업 위험지수",f"{occupation_risk:.1f}")
        st.caption("회사명·부서명 등은 입력하지 않습니다. 보험사의 공식 직업급수/상해급수와 동일하지 않습니다.")
    with c2:
        annual_income=money_input("본인 연소득(원)",60_000_000,0,2_000_000_000,1_000_000,key="annual_income")
        spouse_income=money_input("배우자 연소득(원)",0,0,2_000_000_000,1_000_000,key="spouse_income")
        monthly_expense=money_input("월 필수생활비(원)",3_000_000,0,50_000_000,100_000,key="monthly_expense")
        monthly_premium=money_input("현재 월 보험료(원)",300_000,0,10_000_000,10_000,key="monthly_premium")
    with c3:
        financial_assets=money_input("금융자산(원)",50_000_000,0,10_000_000_000,1_000_000,key="financial_assets")
        emergency_fund=money_input("비상자금(원)",15_000_000,0,5_000_000_000,1_000_000,key="emergency_fund")
        debt=money_input("부채(원)",150_000_000,0,10_000_000_000,1_000_000,key="debt")
        education_fund_needed=money_input("향후 자녀 교육자금 필요액(원)",0,0,5_000_000_000,5_000_000,key="education_fund_needed")

with tab2:
    st.info("병원명, 질병명 상세, 진단일·수술일, 의무기록 내용은 입력하지 않고 위험요인 존재 여부만 선택합니다.")
    a,b,d=st.columns(3)
    with a:
        married=st.checkbox("배우자 있음",True)
        nonworking_spouse=st.checkbox("배우자 비경제활동",False)
        dependents=st.number_input("부양가족 수",0,10,1)
        young_children=st.number_input("미성년/어린 자녀 수",0,10,1)
        parent_support=st.checkbox("부모 부양",False)
        primary_earner=st.checkbox("가구 주 소득원",True)
    with b:
        height_cm=st.number_input("키(cm)",120.0,220.0,165.0,0.5)
        weight_kg=st.number_input("몸무게(kg)",30.0,250.0,60.0,0.5)
        bmi=calculate_bmi(height_cm,weight_kg)
        st.metric("자동 계산 BMI",f"{bmi:.1f}")
        smoker=st.checkbox("현재 흡연")
        hypertension=st.checkbox("고혈압")
        diabetes=st.checkbox("당뇨")
        dyslipidemia=st.checkbox("이상지질혈증")
        medication=st.checkbox("현재 정기 투약")
    with d:
        cancer_history=st.checkbox("암 병력")
        cv_history=st.checkbox("심뇌혈관 병력")
        recent_hospitalization=st.checkbox("최근 입원 이력")
        recent_surgery=st.checkbox("최근 수술 이력")
        family_history_cancer=st.checkbox("암 가족력")
        family_history_brain=st.checkbox("뇌혈관 가족력")
        family_history_heart=st.checkbox("심장질환 가족력")
        family_history_dementia=st.checkbox("치매 가족력")

customer={
    "name":customer_name,"age":age,"sex":sex,"occupation":occupation,"occupation_risk":occupation_risk,
    "height_cm":height_cm,"weight_kg":weight_kg,"bmi":bmi,
    "annual_income":annual_income,"spouse_income":spouse_income,"monthly_essential_expense":monthly_expense,
    "financial_assets":financial_assets,"emergency_fund":emergency_fund,"debt":debt,
    "education_fund_needed":education_fund_needed,"married":married,"nonworking_spouse":nonworking_spouse,
    "dependents":dependents,"young_children":young_children,"parent_support":parent_support,"primary_earner":primary_earner,
    "smoker":smoker,"hypertension":hypertension,"diabetes":diabetes,"dyslipidemia":dyslipidemia,"medication":medication,
    "cancer_history":cancer_history,"cv_history":cv_history,"recent_hospitalization":recent_hospitalization,
    "recent_surgery":recent_surgery,"family_history_cancer":family_history_cancer,
    "family_history_brain":family_history_brain,"family_history_heart":family_history_heart,
    "family_history_dementia":family_history_dementia,
}

details={}
with tab3:
    st.subheader("현재 보장 상세 입력")
    st.caption("‘소득보장 특약’ 입력란은 제거했습니다. 소득상실 대비는 진단비·후유장해 보장의 충족도로 별도 분석합니다.")
    basic1,basic2,basic3=st.columns(3)
    with basic1:
        details["실손"]=st.checkbox("실손 가입",True)
        details["일반암진단"]=money_input("일반암 진단비",0,0,5_000_000_000,1_000_000,key="cur_cancer")
        details["유사암진단"]=money_input("유사암 진단비",0,0,1_000_000_000,1_000_000,key="cur_similar_cancer")
    with basic2:
        details["뇌혈관진단"]=money_input("뇌혈관질환 진단비",0,0,5_000_000_000,1_000_000,key="cur_brain")
        details["허혈성심장진단"]=money_input("허혈성심장질환 진단비",0,0,5_000_000_000,1_000_000,key="cur_heart")
        details["사망"]=money_input("사망 보장액",0,0,10_000_000_000,1_000_000,key="cur_death")
    with basic3:
        details["입원일당"]=money_input("일반 입원일당(1일)",0,0,1_000_000,10_000,key="cur_hospital")
        details["일상생활배상"]=money_input("일상생활배상 보상한도",0,0,2_000_000_000,1_000_000,key="cur_liability")

    st.markdown("#### 수술비 상세")
    s1,s2=st.columns(2)
    with s1:
        details["질병수술_정액"]=money_input("질병수술비(정액)",0,0,1_000_000_000,100_000,key="d_surg_flat")
        for i in range(1,6):
            details[f"질병종수술_{i}종"]=money_input(f"질병 종수술 {i}종",0,0,1_000_000_000,100_000,key=f"d_surg_{i}")
    with s2:
        details["상해수술_정액"]=money_input("상해수술비(정액)",0,0,1_000_000_000,100_000,key="i_surg_flat")
        for i in range(1,6):
            details[f"상해종수술_{i}종"]=money_input(f"상해 종수술 {i}종",0,0,1_000_000_000,100_000,key=f"i_surg_{i}")
    st.caption("종수술은 1~5종 금액을 각각 보존합니다. GAP 엔진에는 정액수술비와 3종 금액 중 큰 값을 ‘대표 1회 금액’으로 사용하며 실제 지급보험금을 의미하지 않습니다.")

    st.markdown("#### 후유장해 상세")
    h1,h2=st.columns(2)
    with h1:
        details["질병후유장해_80미만"]=money_input("질병후유장해 80% 미만 가입금액",0,0,5_000_000_000,1_000_000,key="d_dis_under80")
        details["질병후유장해_80이상"]=money_input("질병후유장해 80% 이상 가입금액",0,0,5_000_000_000,1_000_000,key="d_dis_over80")
    with h2:
        details["상해후유장해_80미만"]=money_input("상해후유장해 80% 미만 가입금액",0,0,5_000_000_000,1_000_000,key="i_dis_under80")
        details["상해후유장해_80이상"]=money_input("상해후유장해 80% 이상 가입금액",0,0,5_000_000_000,1_000_000,key="i_dis_over80")
    st.caption("80%미만 담보는 실제 지급률이 장해율에 따라 달라질 수 있어 단순 합산하지 않습니다. 분석에서는 30% 중등도 장해 시나리오와 80%이상 가입금액 중 큰 값을 대표치로 사용합니다.")

    st.markdown("#### 간병·치매 상세")
    g1,g2=st.columns(2)
    with g1:
        details["간병인지원_사람"]=st.checkbox("간병인지원 특약(보험사가 간병인 지원) 보유")
        details["간병인사용일당"]=money_input("간병인사용일당/현금수당(1일)",0,0,1_000_000,10_000,key="care_daily")
    with g2:
        details["치매월생활자금"]=money_input("치매/장기요양 월 생활자금",0,0,20_000_000,100_000,key="dementia_monthly")
    st.caption("직접 간병인지원과 간병인사용일당(현금)은 별도 구조로 기록합니다. 사람 지원은 임의의 금액으로 환산하지 않습니다.")

current=build_current_coverage(details)
coverage_names=list(WEIGHTS.keys())

# 자동 권장값을 먼저 계산한 뒤, 상담자가 직접 수정할 수 있도록 기본값으로 제공
from needs_engine import target_coverages
auto_targets = target_coverages(customer)
custom_targets = {}

with tab4:
    st.subheader("보장 GAP 권장값 직접 수정")
    st.caption(
        "자동 계산된 Needs 권장값이 기본값으로 입력되어 있습니다. "
        "상담 판단이나 고객 상황에 따라 직접 수정하면 이후 GAP·충족률·우선순위·Portfolio Score가 수정값 기준으로 다시 계산됩니다."
    )
    st.info("권장값을 원래 자동값으로 되돌리려면 해당 입력값을 자동권장값과 동일하게 입력하면 됩니다.")

    cols = st.columns(3)
    for i, cov in enumerate(coverage_names):
        auto = int(auto_targets.get(cov, 0))
        with cols[i % 3]:
            if cov == "실손":
                custom_targets[cov] = st.selectbox(
                    "실손 권장상태",
                    options=[1, 0],
                    index=0 if auto >= 1 else 1,
                    format_func=lambda x: "가입 권장" if x == 1 else "미가입",
                    key="custom_target_실손"
                )
                st.caption(f"자동 권장: {'가입' if auto >= 1 else '미가입'}")
            elif cov in ("간병","치매"):
                custom_targets[cov] = money_input(
                    f"{cov} 권장 월금액(원)", auto, 0, 20_000_000, 100_000,
                    key=f"custom_target_{cov}"
                )
                st.caption(f"자동 권장: {auto:,}원/월")
            elif cov == "입원일당":
                custom_targets[cov] = money_input(
                    f"{cov} 권장 1일금액(원)", auto, 0, 1_000_000, 10_000,
                    key=f"custom_target_{cov}"
                )
                st.caption(f"자동 권장: {auto:,}원/일")
            else:
                custom_targets[cov] = money_input(
                    f"{cov} 권장금액(원)", auto, 0, 10_000_000_000, 1_000_000,
                    key=f"custom_target_{cov}"
                )
                st.caption(f"자동 권장: {auto:,}원")

product_limits={}
with tab5:
    st.subheader("Needs 버킷별 상품 가입한도 · 선택")
    st.caption("상품의 실제 세부 특약 한도는 회사 시스템/약관 확인 후 입력하세요. 0원은 미확인입니다.")
    cols=st.columns(3)
    for i,cov in enumerate(coverage_names):
        with cols[i%3]:
            if cov=="실손":
                product_limits[cov]=0;st.caption("실손: 가입여부")
            elif cov in ("간병","치매"):
                product_limits[cov]=money_input(f"{cov} 월환산/월 한도",0,0,20_000_000,100_000,key=f"lim_{cov}")
            elif cov=="입원일당":
                product_limits[cov]=money_input(f"{cov} 1일 한도",0,0,1_000_000,10_000,key=f"lim_{cov}")
            else:
                product_limits[cov]=money_input(f"{cov} 가입한도",0,0,5_000_000_000,1_000_000,key=f"lim_{cov}")

rows=analyze(customer,current,custom_targets)
limited_rows=apply_product_limits(rows,product_limits)
df=pd.DataFrame(rows)
score=portfolio_score(rows,customer,monthly_premium)
profiles=pd.DataFrame(profile_amounts(rows))

with tab6:
    st.subheader(f"{customer_name} 포트폴리오 분석")
    st.caption("이 결과는 현재 브라우저 세션에서 계산되며, 앱 코드에는 고객별 분석결과를 서버 파일/DB에 저장하는 기능이 없습니다.")
    m1,m2,m3,m4,m5=st.columns(5)
    m1.metric("Portfolio Score",f"{score['총점']} / 100")
    m2.metric("등급",score["등급"])
    m3.metric("보험료 부담률",f"{score['보험료부담률']}%")
    m4.metric("부족 보장 수",int((df["GAP"]>0).sum()))
    m5.metric("12개월 소득상실 Needs",f"{income_loss_reserve_need(customer)/10_000:.0f}만원")
    st.caption("12개월 소득상실 Needs는 보험특약 가입액이 아니라 진단비·후유장해 등으로 얼마나 대비할지 보는 내부 참고금액입니다.")
    st.info(consultation_comment(rows,score,customer))

    st.markdown("#### 성·연령별 공식 발생통계 기반 위험 참고")
    risk=pd.DataFrame(risk_summary(age,sex))
    risk["모델위험지수(0~100)"]=(risk["모델위험지수"]*100).round(1)
    st.dataframe(
        risk[["질환","연령구간","성별","공식통계","50대 대비 발생률비","모델위험지수(0~100)","통계연도","출처"]],
        use_container_width=True,hide_index=True
    )
    st.caption(
        "전체 암·뇌졸중·심근경색은 2023 공식 성·연령별 발생률을 사용합니다. "
        "유사암은 별도 국가 표준 통계가 없어 전체 암 발생률을 제한적 참고치로 재사용하며, "
        "유사암 자체 발생률로 해석해서는 안 됩니다."
    )

    flags=underwriting_flags(customer)
    if flags:st.warning("인수심사 확인 필요: "+", ".join(flags)+" · 실제 가입 가능 여부는 보험사별 기준 확인 필요")

    st.markdown("#### 세부 특약 입력 원본")
    detail_rows=[]
    for k,v in details.items():
        if isinstance(v,bool):
            disp="가입" if v else "미가입"
        else:
            disp=f"{int(v):,}"
        detail_rows.append({"세부특약":k,"입력값":disp})
    st.dataframe(pd.DataFrame(detail_rows),use_container_width=True,hide_index=True)

    st.markdown("#### 분석용 환산값")
    conv=pd.DataFrame([{"분석버킷":k,"환산 현재보장":f"{int(v):,}"} for k,v in current.items()])
    st.dataframe(conv,use_container_width=True,hide_index=True)
    if details.get("간병인지원_사람"):
        st.success("간병인지원(사람) 특약 보유: 현금가치로 임의 환산하지 않고 별도 구조 보장으로 표시합니다.")

    st.markdown("#### 영역별 점수")
    score_df=pd.DataFrame({"영역":["핵심보장","소득상실","가족책임","보험료","보장구조","지속가능성"],
        "점수":[score["핵심보장"],score["소득상실"],score["가족책임"],score["보험료"],score["보장구조"],score["지속가능성"]],
        "만점":[40,15,15,15,10,5]})
    st.dataframe(score_df,use_container_width=True,hide_index=True)

    st.markdown("#### 보장 GAP")
    show=df.copy()
    for col in ["현재","자동권장","권장","GAP"]:
        show[col]=show[col].map(lambda x:f"{int(x):,}")
    st.dataframe(
        show[["보장","단위","현재","자동권장","권장","권장값출처","GAP","충족률","판정","NeedScore","우선순위점수"]],
        use_container_width=True,hide_index=True
    )
    edited = int((df["권장"] != df["자동권장"]).sum())
    if edited:
        st.success(f"현재 {edited}개 보장의 권장값이 자동 계산값에서 수정되어 있으며, 모든 분석은 수정값 기준입니다.")

    st.markdown("#### Needs와 상품 가입한도")
    ldf=pd.DataFrame(limited_rows)
    lshow=ldf[["보장","자동권장","권장","권장값출처","현재","GAP","상품가입한도","실제제안가능추가액","한도판정"]].copy()
    for col in ["자동권장","권장","현재","GAP","상품가입한도","실제제안가능추가액"]:
        lshow[col]=lshow[col].map(lambda x:f"{int(x):,}")
    st.dataframe(lshow,use_container_width=True,hide_index=True)

    chart=df[df["보장"].isin(["일반암진단","유사암진단","뇌혈관진단","허혈성심장진단","질병후유장해","상해후유장해","사망"])].copy()
    chart["충족률_캡"]=chart["충족률"].clip(upper=150)
    fig=px.bar(chart,x="보장",y="충족률_캡",text="충족률",title="핵심 보장 충족률(150% cap)")
    fig.add_hline(y=80,line_dash="dash",annotation_text="적정 하한 80%")
    st.plotly_chart(fig,use_container_width=True)

    st.markdown("#### 보완 우선순위")
    priority=df[df["GAP"]>0].sort_values(["우선순위점수","NeedScore"],ascending=False)
    st.dataframe(priority[["보장","NeedScore","우선순위점수","GAP","판정"]].head(8),use_container_width=True,hide_index=True)

    st.markdown("#### 3가지 상담 시나리오")
    pshow=profiles.copy()
    for col in ["현재","최소형","균형형","강화형"]:pshow[col]=pshow[col].map(lambda x:f"{int(x):,}")
    st.dataframe(pshow,use_container_width=True,hide_index=True)

    with st.expander("계산 근거/가중치"):
        st.dataframe(pd.DataFrame(WEIGHTS).fillna(0).T,use_container_width=True)
        st.write("수술 종수술비와 후유장해 세부담보는 실제 지급보험금을 합산하지 않고 상담용 대표 시나리오로 환산합니다. 유사암은 별도 공식 통계가 없어 전체 암 통계를 제한적 보정치로 사용합니다.")

    csv=pd.DataFrame(limited_rows).to_csv(index=False).encode("utf-8-sig")
    st.download_button("보장분석 CSV 다운로드",csv,file_name=f"{customer_name}_portfolio_v1.3.csv",mime="text/csv")

st.divider()
st.caption("TOSS IA Portfolio v1.4.2 WEB · 비공식 내부 프로토타입 · 토스/토스인슈어런스 공식 서비스가 아닙니다.")
