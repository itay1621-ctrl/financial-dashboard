import streamlit as st
import json
import os
import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf

# ==========================================
# 1. CONFIGURATION & RTL STYLING
# ==========================================
st.set_page_config(page_title="הדרך שלנו לדירה", page_icon="🏡", layout="wide")

st.markdown("""
    <style>
        .stApp { direction: rtl; text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        
        div[data-testid="metric-container"] {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.04);
            text-align: center;
        }
        
        .fund-card {
            background: linear-gradient(145deg, #ffffff, #f0f2f6);
            padding: 25px 20px;
            border-radius: 15px;
            border: 1px solid #e6e6e6;
            margin-bottom: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            transition: transform 0.2s ease;
            position: relative;
            color: #2c3e50;
        }
        .fund-card:hover { transform: translateY(-3px); }
        .fund-title { color: #2c3e50; font-size: 1.1rem; font-weight: bold; margin-bottom: 10px; text-align: center;}
        .fund-amount { color: #2e86de; font-size: 2rem; font-weight: 800; margin: 0; text-align: center;}
        .fund-sub { color: #7f8c8d; font-size: 0.9rem; text-align: center; margin-top: 5px;}
        
        .timer-badge {
            background-color: #e8f4fd;
            color: #0984e3;
            border-radius: 20px;
            padding: 4px 10px;
            font-size: 0.8rem;
            font-weight: bold;
            display: inline-block;
            margin-top: 10px;
        }
        
        div[data-baseweb="input"] { direction: rtl; }
        .stButton > button { 
            width: 100%; border-radius: 8px; font-weight: bold;
            background-color: #2e86de; color: white; border: none; padding: 10px;
        }
        .stButton > button:hover { background-color: #1a73e8; }
        
        .stTabs [data-baseweb="tab-list"] { justify-content: center; margin-bottom: 20px; }
        .stTabs [data-baseweb="tab"] { font-size: 1.2rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. DATA MANAGEMENT
# ==========================================
DATA_FILE = "data.json"

DEFAULT_DATA = {
    "last_updated_month": datetime.datetime.now().strftime("%Y-%m"),
    "funds": {
        "migdal": {"name": "מגדל - קופת גמל", "balance": 99046.0, "monthly": 2000.0, "yield_applies": True},
        "clal": {"name": "כלל - קופת גמל", "balance": 72805.0, "monthly": 2000.0, "yield_applies": True},
        "hishtalmut": {"name": "קרן השתלמות", "balance": 57507.0, "monthly": 1500.0, "yield_applies": True},
        "kupa_ktana": {"name": "קופה קטנה", "balance": 3000.0, "monthly": 300.0, "yield_applies": False}
    },
    "real_estate": {
        "base_price": 1500000.0,
        "extra_expenses": 30000.0,
        "target_equity_pct": 25
    },
    "allocation": {
        "sp500_pct": 30
    },
    "settings": {
        "hishtalmut_start_date": "2024-02-01"
    }
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "settings" not in data:
                data["settings"] = DEFAULT_DATA["settings"]
            return data
    return DEFAULT_DATA.copy()

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@st.cache_data(ttl=86400)
def fetch_market_returns():
    try:
        tickers = yf.Tickers("^GSPC TA125.TA")
        hist = tickers.history(period="1y")
        sp500_data = hist['Close']['^GSPC'].dropna()
        ta125_data = hist['Close']['TA125.TA'].dropna()
        
        sp500_return = (sp500_data.iloc[-1] / sp500_data.iloc[0]) - 1 if not sp500_data.empty else 0.10
        ta125_return = (ta125_data.iloc[-1] / ta125_data.iloc[0]) - 1 if not ta125_data.empty else 0.05
        return float(sp500_return), float(ta125_return)
    except:
        return 0.10, 0.05

sp500_ret, ta125_ret = fetch_market_returns()

def apply_auto_deposits(data):
    current_month_str = datetime.datetime.now().strftime("%Y-%m")
    last_month_str = data.get("last_updated_month", current_month_str)
    
    curr_dt = datetime.datetime.strptime(current_month_str, "%Y-%m")
    last_dt = datetime.datetime.strptime(last_month_str, "%Y-%m")
    months_passed = (curr_dt.year - last_dt.year) * 12 + (curr_dt.month - last_dt.month)
    
    if months_passed > 0:
        sp_weight = data["allocation"]["sp500_pct"] / 100.0
        blended_annual_yield = (sp500_ret * sp_weight) + (ta125_ret * (1 - sp_weight))
        monthly_yield = blended_annual_yield / 12
        
        for key, fund in data["funds"].items():
            for _ in range(months_passed):
                fund["balance"] += fund["monthly"]
                if fund["yield_applies"]:
                    fund["balance"] *= (1 + monthly_yield)
                    
        data["last_updated_month"] = current_month_str
        save_data(data)
        st.toast(f"עודכנו הפקדות ותשואות אוטומטיות עבור {months_passed} חודשים!", icon="📈")
        
    return data

if 'data' not in st.session_state:
    st.session_state.data = apply_auto_deposits(load_data())


# ==========================================
# 3. CALCULATIONS
# ==========================================
target_amount = (st.session_state.data["real_estate"]["base_price"] * (st.session_state.data["real_estate"]["target_equity_pct"] / 100)) + st.session_state.data["real_estate"]["extra_expenses"]

total_saved = sum(fund["balance"] for fund in st.session_state.data["funds"].values())
current_equity_pct = (total_saved / target_amount) * st.session_state.data["real_estate"]["target_equity_pct"] if target_amount > 0 else 0
gap = target_amount - total_saved
progress_value = max(0.0, min(total_saved / target_amount if target_amount > 0 else 1.0, 1.0))

# Hishtalmut Timer Calculation
start_date_str = st.session_state.data["settings"].get("hishtalmut_start_date", "2024-02-01")
start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
opening_date = start_date + relativedelta(years=6)
today = datetime.date.today()

time_left = relativedelta(opening_date, today)
total_months_duration = 72 # 6 years
months_passed_total = (today.year - start_date.year) * 12 + (today.month - start_date.month)
hishtalmut_progress = max(0.0, min(months_passed_total / total_months_duration, 1.0))

if time_left.years > 0 or time_left.months > 0 or time_left.days > 0:
    time_left_str = f"נזיל בעוד {time_left.years} שנים ו-{time_left.months} חודשים"
else:
    time_left_str = "הקרן נזילה! 🔓"


# ==========================================
# 4. MAIN UI (TABS)
# ==========================================
st.title("🎯 המעקב שלנו לדירה")
tab_main, tab_mortgage, tab_settings = st.tabs(["📊 תמונת מצב קופות", "🏦 סימולטור משכנתא", "⚙️ הגדרות"])

# ----------------- TAB 1: MAIN SNAPSHOT -----------------
with tab_main:
    st.markdown("### התקדמות לקראת היעד")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("אחוז הון קיים (מתוך הדירה)", f"{current_equity_pct:.2f}%")
    kpi2.metric("סה״כ הון שנצבר", f"₪ {total_saved:,.0f}")
    kpi3.metric("פער שקלי להון העצמי הנדרש", f"₪ {gap:,.0f}" if gap > 0 else "הגעתם ליעד! 🎉")
    
    st.progress(float(progress_value))
    st.caption(f"היעד: ₪ {target_amount:,.0f} (כולל הוצאות נלוות). הפקדה חודשית כוללת: ₪ {sum(f['monthly'] for f in st.session_state.data['funds'].values()):,.0f}")
    
    st.divider()
    
    cols = st.columns(4)
    fund_keys = list(st.session_state.data["funds"].keys())
    
    def handle_transaction(fund_key, amount, action_type):
        if action_type == "הפקדה":
            st.session_state.data["funds"][fund_key]["balance"] += amount
        elif action_type == "משיכה":
            st.session_state.data["funds"][fund_key]["balance"] -= amount
        elif action_type == "עדכון יתרה מדויקת":
            st.session_state.data["funds"][fund_key]["balance"] = amount
        save_data(st.session_state.data)
        st.rerun()

    for i, col in enumerate(cols):
        fund_key = fund_keys[i]
        fund = st.session_state.data["funds"][fund_key]
        
        with col:
            timer_html = ""
            if fund_key == "hishtalmut":
                timer_html = f'<div style="text-align: center;"><span class="timer-badge">⏳ {time_left_str}</span><div style="margin-top: 5px; padding: 0 10px;"><progress value="{hishtalmut_progress}" max="1" style="width: 100%; height: 5px; accent-color: #0984e3;"></progress></div></div>'

            st.markdown(f"""
<div class="fund-card">
<div class="fund-title">{fund["name"]}</div>
<div class="fund-amount">₪ {fund["balance"]:,.0f}</div>
<div class="fund-sub">הפקדה חודשית: ₪ {fund["monthly"]:,.0f}</div>
{timer_html}
</div>
""", unsafe_allow_html=True)
            
            with st.expander("עדכון / פעולה", expanded=False):
                action = st.radio("פעולה:", ["עדכון יתרה מדויקת", "הפקדה", "משיכה"], key=f"radio_{fund_key}", horizontal=False)
                amount = st.number_input("סכום (₪):", min_value=0.0, step=1000.0, key=f"amt_{fund_key}")
                if st.button("אישור עדכון", key=f"btn_{fund_key}"):
                    if amount >= 0:
                        handle_transaction(fund_key, amount, action)


# ----------------- TAB 2: MORTGAGE SIMULATOR -----------------
with tab_mortgage:
    st.markdown("### הערכת משכנתא צפויה")
    st.write("חישוב זה מציג את המשכנתא שתצטרכו לקחת **אילו הייתם קונים את הדירה היום**, בהתבסס על ההון העצמי הקיים שלכם ומחיר הדירה (כולל הוצאות).")
    
    mortgage_needed = max(0, (st.session_state.data["real_estate"]["base_price"] + st.session_state.data["real_estate"]["extra_expenses"]) - total_saved)
    
    mort_col1, mort_col2 = st.columns([1, 2])
    
    with mort_col2:
        interest_rate = st.slider("ריבית שנתית ממוצעת משוערת (%)", min_value=2.0, max_value=8.0, value=4.8, step=0.1)
        years = st.slider("תקופת המשכנתא (בשנים)", min_value=10, max_value=30, value=30, step=1)
    
    with mort_col1:
        if mortgage_needed > 0:
            monthly_rate = (interest_rate / 100) / 12
            months = years * 12
            monthly_payment = mortgage_needed * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
        else:
            monthly_payment = 0
            
        st.markdown(f'''
            <div class="fund-card" style="border-left: 5px solid #e1b12c;">
                <div class="fund-title">סכום המשכנתא הנדרש</div>
                <div class="fund-amount" style="color: #e1b12c;">₪ {mortgage_needed:,.0f}</div>
            </div>
            <div class="fund-card" style="border-left: 5px solid #e84118;">
                <div class="fund-title">החזר חודשי משוער</div>
                <div class="fund-amount" style="color: #e84118;">₪ {monthly_payment:,.0f}</div>
                <div class="fund-sub">{years} שנים לפי {interest_rate}% ריבית</div>
            </div>
        ''', unsafe_allow_html=True)


# ----------------- TAB 3: SETTINGS -----------------
with tab_settings:
    st.markdown("### הגדרות ונתוני בסיס")
    
    set_col1, set_col2 = st.columns(2)
    with set_col1:
        new_base_price = st.number_input("מחיר דירה בסיסי (₪)", value=float(st.session_state.data["real_estate"]["base_price"]), step=50000.0)
        new_extra = st.number_input("הוצאות נלוות / מדד תשומות (₪)", value=float(st.session_state.data["real_estate"]["extra_expenses"]), step=5000.0)
        new_start_date = st.date_input("תאריך תחילת עבודה (לחישוב קרן השתלמות)", value=start_date)
    with set_col2:
        new_target_pct = st.slider("יעד הון עצמי רשמי (%)", min_value=10, max_value=40, value=int(st.session_state.data["real_estate"]["target_equity_pct"]), step=1)
        new_sp500_pct = st.slider("חשיפה למדד S&P 500 לעומת ת״א 125 (%)", min_value=0, max_value=100, value=int(st.session_state.data["allocation"]["sp500_pct"]), step=5)
    
    if st.button("שמור שינויים"):
        st.session_state.data["real_estate"]["base_price"] = new_base_price
        st.session_state.data["real_estate"]["extra_expenses"] = new_extra
        st.session_state.data["real_estate"]["target_equity_pct"] = new_target_pct
        st.session_state.data["allocation"]["sp500_pct"] = new_sp500_pct
        st.session_state.data["settings"]["hishtalmut_start_date"] = new_start_date.strftime("%Y-%m-%d")
        save_data(st.session_state.data)
        st.success("ההגדרות נשמרו בהצלחה!")
        st.rerun()
