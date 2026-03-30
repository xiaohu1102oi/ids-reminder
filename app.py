import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# ========== 页面配置 ==========
st.set_page_config(page_title="IDS提醒系统", layout="wide")

# ========== 密码验证 ==========
def check_password():
    """密码验证"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 身份验证")
        password = st.text_input("请输入访问密码", type="password")
        
        # 请修改下面的密码为您自己的密码
        CORRECT_PASSWORD = "P0ssword"  # ← 改成您的密码
        
        if password == CORRECT_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        elif password:
            st.error("密码错误，无法访问")
        return False
    return True

# 验证密码，不通过则停止
if not check_password():
    st.stop()

st.title("📋 IDS排查提醒系统")
st.markdown("---")

# ========== 数据文件配置 ==========
DATA_FILE = "cases.csv"

# ========== 辅助函数 ==========
def ensure_date_columns(df):
    """确保所有日期列都是正确的 date 类型"""
    date_cols = ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    return df

def load_data():
    """加载数据"""
    try:
        df = pd.read_csv(DATA_FILE)
        df = ensure_date_columns(df)
        return df
    except:
        # 创建示例数据
        df = pd.DataFrame({
            "卷号": ["US-10001", "US-10002", "US-10003"],
            "递交日": ["2026-01-01", "2026-01-15", "2026-02-01"],
            "首次IDS递交日": ["2026-01-15", "2026-01-30", ""],
            "最近排查日": ["", "", ""],
            "下次排查日": ["2026-04-15", "2026-04-30", "2026-05-01"],
            "案件状态": ["审查中", "审查中", "审查中"],
            "备注": ["", "", ""]
        })
        df = ensure_date_columns(df)
        return df

def save_data(df):
    """保存数据"""
    df_to_save = df.copy()
    for col in ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]:
        if col in df_to_save.columns:
            df_to_save[col] = df_to_save[col].astype(str).replace("NaT", "")
    df_to_save.to_csv(DATA_FILE, index=False)

# ========== 会话状态初始化 ==========
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df
today = datetime.now().date()

# ========== 侧边栏导航 ==========
st.sidebar.title("📁 功能")
page = st.sidebar.radio("选择", ["🏠 今日提醒", "📊 全部案件", "➕ 导入案件", "📦 已授权归档", "⚙️ 系统设置"])

# ========== 通用函数 ==========
def get_parity(case_id):
    """判断卷号末尾数字奇偶性"""
    try:
        last = str(case_id)[-1]
        if last.isdigit():
            return "奇数" if int(last) % 2 == 1 else "偶数"
    except:
        pass
    return "未知"

def format_date(date_val):
    """格式化日期显示"""
    if pd.isna(date_val) or date_val == "":
        return "-"
    try:
        return date_val.strftime("%Y-%m-%d")
    except:
        return "-"

def clean_date(date_val):
    """强制清洗日期，去掉时间部分"""
    if pd.isna(date_val) or date_val == "" or date_val == "NaT":
        return pd.NA
    try:
        date_str = str(pd.to_datetime(date_val))[:10]
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return pd.NA

# ========== 页面1：今日提醒 ==========
if page == "🏠 今日提醒":
    st.header("📌 今日待排查案件")
    
    # 确保数据类型正确
    df = ensure_date_columns(df)
    today = datetime.now().date()
    
    # 筛选待办案件
    condition1 = df["下次排查日"].notna()
    condition2 = df["下次排查日"] <= today
    condition3 = df["最近排查日"].isna()
    condition4 = df["案件状态"] == "审查中"
    
    pending = df[condition1 & condition2 & condition3 & condition4]
    
    if len(pending) == 0:
        st.success("🎉 今日无待办案件！")
    else:
        st.info(f"共 {len(pending)} 件需要排查")
        
        for idx, row in pending.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            
            parity = get_parity(row["卷号"])
            if parity == "奇数":
                bg = "#e6f3ff"
            elif parity == "偶数":
                bg = "#e6ffe6"
            else:
                bg = "#f0f0f0"
            
            with col1:
                st.markdown(f"<div style='background:{bg}; padding:6px; border-radius:5px;'><strong>{row['卷号']}</strong></div>", unsafe_allow_html=True)
            with col2:
                st.write(format_date(row["下次排查日"]))
            with col3:
                st.write(format_date(row["首次IDS递交日"]))
            with col4:
                st.write(format_date(row["递交日"]))
            with col5:
                if st.button("✅ 完成", key=f"done_{idx}"):
                    df.loc[df["卷号"] == row["卷号"], "最近排查日"] = today
                    df.loc[df["卷号"] == row["卷号"], "下次排查日"] = today + timedelta(days=75)
                    save_data(df)
                    st.rerun()
            st.markdown("---")

# ========== 页面2：全部案件 ==========
elif page == "📊 全部案件":
    st.header("📊 全部案件")
    
    # 确保数据类型正确
    df = ensure_date_columns(df)
    
    # 筛选器
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect("筛选状态", ["审查中", "已授权"], default=["审查中", "已授权"])
    with col2:
        search = st.text_input("搜索卷号", "")
    
    # 应用筛选
    filtered = df[df["案件状态"].isin(status_filter)]
    if search:
        filtered = filtered[filtered["卷号"].str.contains(search, case=False)]
    
    st.info(f"共 {len(filtered)} 件案件")
    
    # 表头
    col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([1.5, 1.2, 1.2, 1.2, 1.2, 1, 1, 1, 0.8])
    with col1:
        st.markdown("**卷号**")
    with col2:
        st.markdown("**递交日**")
    with col3:
        st.markdown("**首次IDS日**")
    with col4:
        st.markdown("**最近排查日**")
    with col5:
        st.markdown("**下次排查日**")
    with col6:
        st.markdown("**状态**")
    with col7:
        st.markdown("**备注**")
    with col8:
        st.markdown("**修改状态**")
    with col9:
        st.markdown("**操作**")
    st.markdown("---")
    
    # 显示案件列表
    for idx, row in filtered.iterrows():
        col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([1.5, 1.2, 1.2, 1.2, 1.2, 1, 1, 1, 0.8])
        
        with col1:
            st.write(row["卷号"])
        with col2:
            st.write(format_date(row["递交日"]))
        with col3:
            st.write(format_date(row["首次IDS递交日"]))
        with col4:
            st.write(format_date(row["最近排查日"]))
        with col5:
            st.write(format_date(row["下次排查日"]))
        with col6:
            if row["案件状态"] == "审查中":
                st.markdown("🟢 审查中")
            else:
                st.markdown("🔵 已授权")
        with col7:
            st.write(row["备注"] if pd.notna(row["备注"]) else "-")
        with col8:
            new_status = st.selectbox(
                "修改状态",
                options=["审查中", "已授权"],
                index=0 if row["案件状态"] == "审查中" else 1,
                key=f"status_{idx}",
                label_visibility="collapsed"
            )
            if new_status != row["案件状态"]:
                df.loc[df["卷号"] == row["卷号"], "案件状态"] = new_status
                save_data(df)
                st.rerun()
        with col9:
            if st.button("🗑️", key=f"del_{idx}"):
                st.session_state.df = df[df["卷号"] != row["卷号"]]
                save_data(st.session_state.df)
                st.rerun()
        
        st.markdown("---")
    
    # 批量操作
    st.markdown("---")
    st.subheader("⚡ 批量操作")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🗑️ 删除所有【审查中】案件", type="secondary"):
            st.session_state.df = df[df["案件状态"] != "审查中"]
            save_data(st.session_state.df)
            st.rerun()
    
    with col2:
        if st.button("🗑️ 删除所有【已授权】案件", type="secondary"):
            st.session_state.df = df[df["案件状态"] != "已授权"]
            save_data(st.session_state.df)
            st.rerun()
    
    with col3:
        if st.button("📋 批量设为【已授权】", type="primary"):
            cases_to_auth = st.multiselect("选择要改为已授权的案件", df[df["案件状态"] == "审查中"]["卷号"].tolist(), key="batch_auth")
            if cases_to_auth and st.button("确认批量授权", key="confirm_batch"):
                for case in cases_to_auth:
                    df.loc[df["卷号"] == case, "案件状态"] = "已授权"
                save_data(df)
                st.success(f"已将 {len(cases_to_auth)} 件案件设为已授权")
                st.rerun()

# ========== 页面3：导入案件 ==========
elif page == "➕ 导入案件":
    st.header("➕ 批量导入")
    
    st.markdown("""
    **文件要求**：
    - 必须包含：卷号、首次IDS递交日
    - 可选：递交日、备注
    - 支持 Excel (.xlsx) 或 CSV
    """)
    
    uploaded = st.file_uploader("选择文件", type=["xlsx", "csv"])
    
    if uploaded:
        try:
            if uploaded.name.endswith(".xlsx"):
                new_df = pd.read_excel(uploaded)
            else:
                new_df = pd.read_csv(uploaded)
            
            st.success(f"读取 {len(new_df)} 条记录")
            st.dataframe(new_df.head())
            
            if st.button("确认导入"):
                if "卷号" in new_df.columns and "首次IDS递交日" in new_df.columns:
                    # 添加默认列
                    new_df["递交日"] = pd.NA
                    new_df["最近排查日"] = pd.NA
                    new_df["备注"] = ""
                    new_df["案件状态"] = "审查中"
                    
                    # 清洗日期
                    new_df["首次IDS递交日"] = new_df["首次IDS递交日"].apply(clean_date)
                    
                    if "递交日" in new_df.columns:
                        new_df["递交日"] = new_df["递交日"].apply(clean_date)
                    
                    # 计算下次排查日
                    new_df["下次排查日"] = new_df["首次IDS递交日"] + timedelta(days=75)
                    
                    # 确保列顺序一致
                    for col in df.columns:
                        if col not in new_df.columns:
                            new_df[col] = pd.NA
                    
                    # 合并数据
                    st.session_state.df = pd.concat([df, new_df[df.columns]], ignore_index=True)
                    save_data(st.session_state.df)
                    st.success(f"导入成功！共 {len(new_df)} 件")
                    st.rerun()
                else:
                    st.error("缺少必需列：卷号、首次IDS递交日")
        except Exception as e:
            st.error(f"读取失败：{e}")

# ========== 页面4：已授权归档 ==========
elif page == "📦 已授权归档":
    st.header("📦 已授权案件")
    
    # 确保数据类型正确
    df = ensure_date_columns(df)
    
    granted = df[df["案件状态"] == "已授权"]
    st.info(f"共 {len(granted)} 件")
    
    if len(granted) > 0:
        # 表头
        col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1.5, 1.5, 0.8])
        with col1:
            st.markdown("**卷号**")
        with col2:
            st.markdown("**递交日**")
        with col3:
            st.markdown("**首次IDS日**")
        with col4:
            st.markdown("**下次排查日**")
        with col5:
            st.markdown("**备注**")
        with col6:
            st.markdown("**操作**")
        st.markdown("---")
        
        for idx, row in granted.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1.5, 1.5, 0.8])
            
            with col1:
                st.write(row["卷号"])
            with col2:
                st.write(format_date(row["递交日"]))
            with col3:
                st.write(format_date(row["首次IDS递交日"]))
            with col4:
                st.write(format_date(row["下次排查日"]))
            with col5:
                st.write(row["备注"] if pd.notna(row["备注"]) else "-")
            with col6:
                if st.button("恢复", key=f"restore_{idx}"):
                    df.loc[df["卷号"] == row["卷号"], "案件状态"] = "审查中"
                    save_data(df)
                    st.rerun()
            st.markdown("---")
        
        if st.button("🗑️ 永久删除所有已授权案件", type="primary"):
            st.session_state.df = df[df["案件状态"] != "已授权"]
            save_data(st.session_state.df)
            st.rerun()
    else:
        st.info("暂无已授权案件")

# ========== 页面5：系统设置 ==========
elif page == "⚙️ 系统设置":
    st.header("⚙️ 系统设置")
    
    # 确保数据类型正确
    df = ensure_date_columns(df)
    
    st.warning("⚠️ 危险操作区：以下操作将永久删除数据，无法恢复！")
    
    st.markdown("---")
    
    # 删除所有数据
    st.subheader("🗑️ 清空所有数据")
    st.write("此操作将删除全部案件记录，包括审查中和已授权的所有案件。")
    
    confirm = st.text_input("请输入「确认删除」以确认清空所有数据")
    
    if confirm == "确认删除":
        if st.button("⚠️ 永久删除全部数据", type="primary"):
            empty_df = pd.DataFrame(columns=df.columns)
            st.session_state.df = empty_df
            save_data(st.session_state.df)
            st.success("所有数据已清空")
            st.rerun()
    else:
        st.info("请输入「确认删除」以启用删除按钮")
    
    st.markdown("---")
    
    # 数据统计
    st.subheader("📊 数据统计")
    st.write(f"- 总案件数：{len(df)}")
    st.write(f"- 审查中：{len(df[df['案件状态'] == '审查中'])}")
    st.write(f"- 已授权：{len(df[df['案件状态'] == '已授权'])}")
    
    # 导出数据
    st.markdown("---")
    st.subheader("📥 导出数据")
    
    if st.button("导出全部数据为CSV"):
        df_export = df.copy()
        for col in ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]:
            if col in df_export.columns:
                df_export[col] = df_export[col].astype(str).replace("NaT", "")
        csv = df_export.to_csv(index=False)
        st.download_button(
            label="点击下载",
            data=csv,
            file_name=f"ids_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
