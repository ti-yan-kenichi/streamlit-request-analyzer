
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import os
import io

# 日本語フォント設定（ローカル or Cloud）
if os.path.exists("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"):
    font_path = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
elif os.path.exists("fonts/NotoSansJP-Regular.ttf"):
    font_path = "fonts/NotoSansJP-Regular.ttf"
else:
    font_path = None

jp_font = fm.FontProperties(fname=font_path) if font_path else None

st.set_page_config(page_title="リクエスト分析ダッシュボード", layout="wide")
st.title("📊 リクエスト分析ダッシュボード（超過点赤色表示対応）")

# サイドバー設定
with st.sidebar:
    st.header("⚙️ 分析設定")
    threshold = st.number_input("制限値（この件数を超えると超過）", min_value=1, step=1, value=360)
    y_tick_label = st.selectbox("Y軸の目盛り間隔", [1000, 500, 300, 200, 100, 50], index=3)
    x_tick_label = st.selectbox("X軸の目盛り間隔", ["1日", "12時間", "6時間", "1時間", "30分", "15分", "5分"], index=3)
    xaxis_type = st.radio("結合グラフのX軸表示方法", ["📅 時系列（空白あり）", "➡️ 詰めた表示（インデックス）"], horizontal=True)

uploaded_files = st.file_uploader("📁 CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    file_data = {}
    for file in uploaded_files:
        df = pd.read_csv(file, skiprows=3, encoding="shift_jis", encoding_errors="replace")
        df["リクエスト日時"] = pd.to_datetime(df["リクエスト日時"].str.strip("'"), errors="coerce")
        df = df.sort_values("リクエスト日時")
        file_data[file.name] = df

    tab_names = list(file_data.keys()) + ["🔗 結合分析"]
    tabs = st.tabs(tab_names)

    def plot_graph(df, x_col, title):
        fig, ax = plt.subplots(figsize=(20, 6), dpi=120)
        below = df[df["1時間前までの件数"] <= threshold]
        above = df[df["1時間前までの件数"] > threshold]
        ax.plot(below[x_col], below["1時間前までの件数"], marker='o', linestyle='-', markersize=4, label="正常")
        ax.plot(above[x_col], above["1時間前までの件数"], marker='o', linestyle='None', color='red', markersize=6, label="超過")
        ax.set_title(title, fontproperties=jp_font)
        ax.set_ylabel("件数", fontproperties=jp_font)
        ax.set_xlabel("時刻" if x_col == "リクエスト日時" else "順序", fontproperties=jp_font)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_yticks(range(0, int(df["1時間前までの件数"].max()) + y_tick_label, y_tick_label))
        ax.legend()
        return fig

    # 各CSVファイル個別分析
    for i, (filename, df_all) in enumerate(file_data.items()):
        with tabs[i]:
            st.subheader(f"📁 ファイル名: {filename}")
            min_dt, max_dt = df_all["リクエスト日時"].min(), df_all["リクエスト日時"].max()
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(f"[{filename}] 開始日", value=min_dt.date(), min_value=min_dt.date(), max_value=max_dt.date(), key=f"start_{filename}")
                start_time = st.time_input(f"[{filename}] 開始時刻", value=min_dt.time(), key=f"stime_{filename}")
            with col2:
                end_date = st.date_input(f"[{filename}] 終了日", value=max_dt.date(), min_value=min_dt.date(), max_value=max_dt.date(), key=f"end_{filename}")
                end_time = st.time_input(f"[{filename}] 終了時刻", value=max_dt.time(), key=f"etime_{filename}")

            start_dt = pd.to_datetime(f"{start_date} {start_time}")
            end_dt = pd.to_datetime(f"{end_date} {end_time}")

            if start_dt >= end_dt:
                st.error("終了日時は開始日時より後にしてください。")
                continue

            if st.button(f"✅ {filename} を分析", key=f"run_{filename}"):
                df_filtered = df_all[(df_all["リクエスト日時"] >= start_dt) & (df_all["リクエスト日時"] <= end_dt)].copy()
                df_filtered["1時間前までの件数"] = df_filtered["リクエスト日時"].apply(
                    lambda t: df_filtered[
                        (df_filtered["リクエスト日時"] < t) &
                        (df_filtered["リクエスト日時"] >= t - pd.Timedelta(hours=1))
                    ].shape[0]
                )
                x_tick_options = {
                    "1日": mdates.DayLocator(interval=1),
                    "12時間": mdates.HourLocator(interval=12),
                    "6時間": mdates.HourLocator(interval=6),
                    "1時間": mdates.HourLocator(interval=1),
                    "30分": mdates.MinuteLocator(interval=30),
                    "15分": mdates.MinuteLocator(interval=15),
                    "5分": mdates.MinuteLocator(interval=5)
                }
                fig = plot_graph(df_filtered, "リクエスト日時", "リクエスト件数")
                ax = fig.axes[0]
                ax.xaxis.set_major_locator(x_tick_options[x_tick_label])
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
                st.pyplot(fig)

                with st.expander("📊 統計情報", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("合計リクエスト数", len(df_filtered))
                    col2.metric("最大件数（1時間内）", df_filtered["1時間前までの件数"].max())
                    col3.metric("平均件数（1時間内）", round(df_filtered["1時間前までの件数"].mean(), 2))

                with st.expander("⚠️ 超過リスト", expanded=False):
                    exceeded = df_filtered[df_filtered["1時間前までの件数"] > threshold]
                    if not exceeded.empty:
                        st.dataframe(exceeded[["リクエスト日時", "1時間前までの件数"]])
                        csv_buf = io.StringIO()
                        exceeded[["リクエスト日時", "1時間前までの件数"]].to_csv(csv_buf, index=False)
                        st.download_button("📥 超過CSV", csv_buf.getvalue(), f"exceeded_{filename}.csv", "text/csv")
                    else:
                        st.success("制限値を超えたリクエストはありません。")

    # 結合分析
    with tabs[-1]:
        st.subheader("🔗 結合分析")
        combined_df = pd.concat(file_data.values()).sort_values("リクエスト日時").reset_index(drop=True)
        min_dt, max_dt = combined_df["リクエスト日時"].min(), combined_df["リクエスト日時"].max()
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("開始日（結合）", value=min_dt.date(), min_value=min_dt.date(), max_value=max_dt.date())
            start_time = st.time_input("開始時刻（結合）", value=min_dt.time())
        with col2:
            end_date = st.date_input("終了日（結合）", value=max_dt.date(), min_value=min_dt.date(), max_value=max_dt.date())
            end_time = st.time_input("終了時刻（結合）", value=max_dt.time())

        start_dt = pd.to_datetime(f"{start_date} {start_time}")
        end_dt = pd.to_datetime(f"{end_date} {end_time}")

        if start_dt >= end_dt:
            st.error("終了日時は開始日時より後にしてください。")
        else:
            if st.button("✅ 結合データを分析"):
                df = combined_df[(combined_df["リクエスト日時"] >= start_dt) & (combined_df["リクエスト日時"] <= end_dt)].copy()
                df["1時間前までの件数"] = df["リクエスト日時"].apply(
                    lambda t: df[
                        (df["リクエスト日時"] < t) &
                        (df["リクエスト日時"] >= t - pd.Timedelta(hours=1))
                    ].shape[0]
                )
                if xaxis_type == "➡️ 詰めた表示（インデックス）":
                    df["index"] = range(len(df))
                    fig = plot_graph(df, "index", "結合リクエスト件数（詰めた表示）")
                else:
                    fig = plot_graph(df, "リクエスト日時", "結合リクエスト件数")
                    locator = {
                        "1日": mdates.DayLocator(interval=1),
                        "12時間": mdates.HourLocator(interval=12),
                        "6時間": mdates.HourLocator(interval=6),
                        "1時間": mdates.HourLocator(interval=1),
                        "30分": mdates.MinuteLocator(interval=30),
                        "15分": mdates.MinuteLocator(interval=15),
                        "5分": mdates.MinuteLocator(interval=5)
                    }[x_tick_label]
                    ax = fig.axes[0]
                    ax.xaxis.set_major_locator(locator)
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
                    plt.xticks(rotation=45)
                st.pyplot(fig)

                with st.expander("📊 統計情報（結合）", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("合計リクエスト数", len(df))
                    col2.metric("最大件数（1時間内）", df["1時間前までの件数"].max())
                    col3.metric("平均件数（1時間内）", round(df["1時間前までの件数"].mean(), 2))

                with st.expander("⚠️ 超過リスト（結合）", expanded=False):
                    exceeded = df[df["1時間前までの件数"] > threshold]
                    if not exceeded.empty:
                        st.dataframe(exceeded[["リクエスト日時", "1時間前までの件数"]])
                        csv_buf = io.StringIO()
                        exceeded[["リクエスト日時", "1時間前までの件数"]].to_csv(csv_buf, index=False)
                        st.download_button("📥 超過CSV（結合）", csv_buf.getvalue(), "exceeded_combined.csv", "text/csv")
                    else:
                        st.success("制限値を超えたリクエストはありません。")
