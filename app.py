import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# 页面配置
st.set_page_config(page_title="IDS提醒系统", layout="wide")

st.title("📋 IDS排查提醒系统")
st.markdown("---")

# 数据文件
DATA_FILE = "cases.csv"

# 初始化数据
def load_data():
    try:
        return pd.read_csv(DATA_FILE)
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
        return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 会话状态
if "df" not in st.session_state:
    st.session_state.df = load_data()
    # 转换日期格式
    for col in ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]:
        st.session_state.df[col] = pd.to_datetime(st.session_state.df[col], errors='coerce').dt.date

df = st.session_state.df
today = datetime.now().date()

# 侧边栏
st.sidebar.title("📁 功能")
page = st.sidebar.radio("选择", ["🏠 今日提醒", "📊 全部案件", "➕ 导入案件", "📦 已授权归档", "⚙️ 系统设置"])

# 奇偶判断
def get_parity(case_id):
    try:
        last = str(case_id)[-1]
        if last.isdigit():
            return "奇数" if int(last) % 2 == 1 else "偶数"
    except:
        pass
    return "未知"

# ==================== 页面1：今日提醒 ====================
if page == "🏠 今日提醒":
    st.header("📌 今日待排查案件")
    
    pending = df[(df["下次排查日"] <= today) & (df["最近排查日"].isna()) & (df["案件状态"] == "审查中")]
    
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
                st.write(row["下次排查日"].strftime("%Y-%m-%d"))
            with col3:
                st.write(row["首次IDS递交日"] if pd.notna(row["首次IDS递交日"]) else "-")
            with col4:
                st.write(row["递交日"].strftime("%Y-%m-%d"))
            with col5:
                if st.button("✅ 完成", key=f"done_{idx}"):
                    df.loc[df["卷号"] == row["卷号"], "最近排查日"] = today
                    df.loc[df["卷号"] == row["卷号"], "下次排查日"] = today + timedelta(days=75)
                    save_data(df)
                    st.rerun()
            st.markdown("---")

# ==================== 页面2：全部案件（带删除按钮） ====================
elif page == "📊 全部案件":
    st.header("📊 全部案件")
    
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
    
    # 显示带删除按钮的案件列表
    for idx, row in filtered.iterrows():
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.5, 1.2, 1.2, 1.2, 1.2, 1, 1, 0.8])
        
        with col1:
            st.write(row["卷号"])
        with col2:
            st.write(row["递交日"].strftime("%Y-%m-%d") if pd.notna(row["递交日"]) else "-")
        with col3:
            st.write(row["首次IDS递交日"].strftime("%Y-%m-%d") if pd.notna(row["首次IDS递交日"]) else "-")
        with col4:
            st.write(row["最近排查日"].strftime("%Y-%m-%d") if pd.notna(row["最近排查日"]) else "-")
        with col5:
            st.write(row["下次排查日"].strftime("%Y-%m-%d") if pd.notna(row["下次排查日"]) else "-")
        with col6:
            st.write(row["案件状态"])
        with col7:
            st.write(row["备注"] if pd.notna(row["备注"]) else "-")
        with col8:
            if st.button("🗑️", key=f"del_{idx}"):
                # 删除该行
                st.session_state.df = df[df["卷号"] != row["卷号"]]
                save_data(st.session_state.df)
                st.rerun()
        
        st.markdown("---")
    
    # 批量删除按钮
    st.markdown("---")
    st.subheader("⚡ 批量操作")
    
    col1, col2 = st.columns(2)
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

# ==================== 页面3：导入案件 ====================
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
                    new_df["递交日"] = pd.NA
                    new_df["最近排查日"] = pd.NA
                    new_df["备注"] = ""
                    new_df["案件状态"] = "审查中"
                    new_df["首次IDS递交日"] = pd.to_datetime(new_df["首次IDS递交日"]).dt.date
new_df["下次排查日"] = new_df["首次IDS递交日"] + timedelta(days=75)
                    
                    st.session_state.df = pd.concat([df, new_df[df.columns]], ignore_index=True)
                    save_data(st.session_state.df)
                    st.success(f"导入成功！共 {len(new_df)} 件")
                    st.rerun()
                else:
                    st.error("缺少必需列：卷号、首次IDS递交日")
        except Exception as e:
            st.error(f"读取失败：{e}")

# ==================== 页面4：已授权归档 ====================
elif page == "📦 已授权归档":
    st.header("📦 已授权案件")
    
    granted = df[df["案件状态"] == "已授权"]
    st.info(f"共 {len(granted)} 件")
    
    if len(granted) > 0:
        for idx, row in granted.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1.5, 1.5, 0.8])
            
            with col1:
                st.write(row["卷号"])
            with col2:
                st.write(row["递交日"].strftime("%Y-%m-%d") if pd.notna(row["递交日"]) else "-")
            with col3:
                st.write(row["首次IDS递交日"].strftime("%Y-%m-%d") if pd.notna(row["首次IDS递交日"]) else "-")
            with col4:
                st.write(row["下次排查日"].strftime("%Y-%m-%d") if pd.notna(row["下次排查日"]) else "-")
            with col5:
                st.write(row["备注"] if pd.notna(row["备注"]) else "-")
            with col6:
                if st.button("恢复", key=f"restore_{idx}"):
                    df.loc[df["卷号"] == row["卷号"], "案件状态"] = "审查中"
                    save_data(df)
                    st.rerun()
            st.markdown("---")
        
        # 批量删除已授权案件
        if st.button("🗑️ 永久删除所有已授权案件", type="primary"):
            st.session_state.df = df[df["案件状态"] != "已授权"]
            save_data(st.session_state.df)
            st.rerun()
    else:
        st.info("暂无已授权案件")

# ==================== 页面5：系统设置 ====================
elif page == "⚙️ 系统设置":
    st.header("⚙️ 系统设置")
    
    st.warning("⚠️ 危险操作区：以下操作将永久删除数据，无法恢复！")
    
    st.markdown("---")
    
    # 删除所有数据
    st.subheader("🗑️ 清空所有数据")
    st.write("此操作将删除全部案件记录，包括审查中和已授权的所有案件。")
    
    # 需要输入确认文字
    confirm = st.text_input("请输入「确认删除」以确认清空所有数据")
    
    if confirm == "确认删除":
        if st.button("⚠️ 永久删除全部数据", type="primary"):
            # 创建空DataFrame
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
        csv = df.to_csv(index=False)
        st.download_button(
            label="点击下载",
            data=csv,
            file_name=f"ids_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
