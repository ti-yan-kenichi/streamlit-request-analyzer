
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

st.title("リクエスト分析ツール（日時フィルター対応）")

uploaded_files = st.file_uploader("CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    all_data = []

    for file in uploaded_files:
        df = pd.read_csv(file, skiprows=3, encoding="shift_jis", encoding_errors="replace")
        df["リクエスト日時"] = pd.to_datetime(df["リクエスト日時"].str.strip("'"), errors="coerce")
        df = df.sort_values("リクエスト日時")
        all_data.append(df)

    df_all = pd.concat(all_data).reset_index(drop=True)

    # 日時フィルター
    min_dt = df_all["リクエスト日時"].min()
    max_dt = df_all["リクエスト日時"].max()

    st.subheader("表示する日時範囲を選択")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日", value=min_dt.date(), min_value=min_dt.date(), max_value=max_dt.date())
        start_time = st.time_input("開始時刻", value=min_dt.time())
    with col2:
        end_date = st.date_input("終了日", value=max_dt.date(), min_value=min_dt.date(), max_value=max_dt.date())
        end_time = st.time_input("終了時刻", value=max_dt.time())

    start_dt = pd.to_datetime(f"{start_date} {start_time}")
    end_dt = pd.to_datetime(f"{end_date} {end_time}")

    if start_dt >= end_dt:
        st.error("終了日時は開始日時より後にしてください。")
        st.stop()

    df_all = df_all[(df_all["リクエスト日時"] >= start_dt) & (df_all["リクエスト日時"] <= end_dt)]

    # 1時間前までの件数を計算
    counts = []
    for time in df_all["リクエスト日時"]:
        count = df_all[
            (df_all["リクエスト日時"] < time) &
            (df_all["リクエスト日時"] >= time - pd.Timedelta(hours=1))
        ].shape[0]
        counts.append(count)
    df_all["1時間前までの件数"] = counts

    # X軸目盛り選択（デフォルト: 1時間）
    x_tick_options = {
        "1時間": mdates.HourLocator(interval=1),
        "30分": mdates.MinuteLocator(interval=30),
        "15分": mdates.MinuteLocator(interval=15),
        "5分": mdates.MinuteLocator(interval=5)
    }
    x_tick_label = st.selectbox("X軸の目盛り間隔", list(x_tick_options.keys()), index=0)
    x_tick_locator = x_tick_options[x_tick_label]

    # Y軸目盛り（デフォルト: 200）
    y_tick_label = st.selectbox("Y軸の目盛り間隔", [1000, 500, 300, 200, 100, 50], index=3)

    # 閾値（デフォルト: 360）
    threshold = st.number_input("制限値（この件数を超えた時間を抽出）", min_value=1, step=1, value=360)

    # グラフ描画（改善）
    st.subheader(f"リクエスト時系列グラフ（X軸: {x_tick_label}, Y軸: {y_tick_label}間隔）")
    fig, ax = plt.subplots(figsize=(20, 6), dpi=120)
    ax.plot(df_all["リクエスト日時"], df_all["1時間前までの件数"], marker='o', linestyle='-', markersize=4, linewidth=1.5)

    if jp_font:
        ax.set_title("リクエスト件数（1時間前までの件数）", fontproperties=jp_font, fontsize=14)
        ax.set_xlabel("時刻", fontproperties=jp_font, fontsize=12)
        ax.set_ylabel("件数", fontproperties=jp_font, fontsize=12)
    else:
        ax.set_title("Requests in Past Hour")
        ax.set_xlabel("Time")
        ax.set_ylabel("Count")

    ax.grid(True, linestyle='--', alpha=0.5)
    ax.xaxis.set_major_locator(x_tick_locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    ax.set_yticks(range(0, int(df_all["1時間前までの件数"].max()) + y_tick_label, y_tick_label))
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # 統計情報
    st.subheader("統計情報")
    st.metric("合計リクエスト数", len(df_all))
    st.metric("最大件数（1時間内）", df_all["1時間前までの件数"].max())
    st.metric("平均件数（1時間内）", round(df_all["1時間前までの件数"].mean(), 2))

    # 閾値超過リスト
    exceeded = df_all[df_all["1時間前までの件数"] > threshold]
    st.subheader(f"制限値（{threshold}件）を超えたリクエスト")
    if not exceeded.empty:
        st.dataframe(exceeded[["リクエスト日時", "1時間前までの件数"]])
        csv_buffer = io.StringIO()
        exceeded[["リクエスト日時", "1時間前までの件数"]].to_csv(csv_buffer, index=False)
        st.download_button("超過リストをCSVでダウンロード", csv_buffer.getvalue(), "exceeded_requests.csv", "text/csv")
    else:
        st.info("制限値を超えたリクエストはありません。")
