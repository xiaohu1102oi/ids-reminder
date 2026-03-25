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
        df = pd.read_csv(DATA_FILE)
        # 转换日期列
        for col in ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
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
        for col in ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        return df

def save_data(df):
    # 保存前将日期转为字符串，避免保存时带时间
    df_to_save = df.copy()
    for col in ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]:
        if col in df_to_save.columns:
            df_to_save[col] = df_to_save[col].astype(str).replace("NaT", "")
    df_to_save.to_csv(DATA_FILE, index=False)

# 会话状态
if "df" not in st.session_state:
    st.session_state.df = load_data()

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

# 格式化日期显示
def format_date(date_val):
    if pd.isna(date_val) or date_val == "":
        return "-"
    try:
        return date_val.strftime("%Y-%m-%d")
    except:
        return "-"

# 强制清洗日期函数（去掉时间部分）
def clean_date(date_val):
    """强制将各种日期格式转为纯日期，去掉时间部分"""
    if pd.isna(date_val) or date_val == "" or date_val == "NaT":
        return pd.NA
    try:
        # 先转成datetime，再转成字符串取前10位，再转回date
        date_str = str(pd.to_datetime(date_val))[:10]
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return pd.NA

# ==================== 页面1：今日提醒 ====================
if page == "🏠 今日提醒":
    st.header("📌 今日待排查案件")
    
    # 确保日期类型正确
    df["下次排查日"] = pd.to_datetime(df["下次排查日"], errors='coerce').dt.date
    df["最近排查日"] = pd.to_datetime(df["最近排查日"], errors='coerce').dt.date
    
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

# ==================== 页面2：全部案件（带删除按钮） ====================
elif page == "📊 全部案件":
    st.header("📊 全部案件")
    
    # 确保日期类型正确
    for col in ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    
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
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.5, 1.2, 1.2, 1.2, 1.2, 1, 1, 0.8])
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
        st.markdown("**操作**")
    st.markdown("---")
    
    # 显示带删除按钮的案件列表
    for idx, row in filtered.iterrows():
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.5, 1.2, 1.2, 1.2, 1.2, 1, 1, 0.8])
        
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
            st.write(row["案件状态"])
        with col7:
            st.write(row["备注"] if pd.notna(row["备注"]) else "-")
        with col8:
            if st.button("🗑️", key=f"del_{idx}"):
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

# ==================== 页面3：导入案件（强制去时间） ====================
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
            # 读取文件
            if uploaded.name.endswith(".xlsx"):
                new_df = pd.read_excel(uploaded)
            else:
                new_df = pd.read_csv(uploaded)
            
            st.success(f"读取 {len(new_df)} 条记录")
            
            # 显示原始数据预览
            st.write("原始数据预览：")
            st.dataframe(new_df.head())
            
            if st.button("确认导入"):
                if "卷号" in new_df.columns and "首次IDS递交日" in new_df.columns:
                    # 添加默认列
                    new_df["递交日"] = pd.NA
                    new_df["最近排查日"] = pd.NA
                    new_df["备注"] = ""
                    new_df["案件状态"] = "审查中"
                    
                    # ========== 强制清洗日期，去掉时间部分 ==========
                    # 清洗首次IDS递交日
                    new_df["首次IDS递交日"] = new_df["首次IDS递交日"].apply(clean_date)
                    
                    # 如果有递交日列，也清洗
                    if "递交日" in new_df.columns:
                        new_df["递交日"] = new_df["递交日"].apply(clean_date)
                    
                    # 计算下次排查日（75天后）
                    new_df["下次排查日"] = new_df["首次IDS递交日"] + timedelta(days=75)
                    
                    # 再次确保是 date 类型
                    new_df["下次排查日"] = new_df["下次排查日"].apply(lambda x: x if pd.notna(x) else pd.NA)
                    
                    # 确保列顺序一致
                    for col in df.columns:
                        if col not in new_df.columns:
                            new_df[col] = pd.NA
                    
                    # 显示清洗后的数据预览
                    st.write("清洗后数据预览：")
                    preview_df = new_df[df.columns].head()
                    for col in ["递交日", "首次IDS递交日", "最近排查日", "下次排查日"]:
                        if col in preview_df.columns:
                            preview_df[col] = preview_df[col].astype(str).replace("NaT", "")
                    st.dataframe(preview_df)
                    
                    # 合并数据
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
    
    # 确保日期类型正确
    for col in ["递交日", "首次IDS递交日", "下次排查日"]:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    
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
