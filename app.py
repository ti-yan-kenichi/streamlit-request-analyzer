
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

st.title("リクエスト分析ツール（X軸粒度はグラフ表記のみ）")

# アップロード（複数対応）
uploaded_files = st.file_uploader("CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

# X軸ラベル間隔設定
x_tick_options = {
    "1時間": mdates.HourLocator(interval=1),
    "30分": mdates.MinuteLocator(interval=30),
    "15分": mdates.MinuteLocator(interval=15),
    "5分": mdates.MinuteLocator(interval=5)
}
x_tick_label = st.selectbox("X軸の目盛り間隔を選択", list(x_tick_options.keys()))
x_tick_locator = x_tick_options[x_tick_label]

# 閾値入力
threshold = st.number_input("制限値（この件数を超えた時間を抽出）", min_value=1, step=1)

if uploaded_files:
    all_data = []

    for file in uploaded_files:
        df = pd.read_csv(file, skiprows=3, encoding="shift_jis", encoding_errors="replace")
        df["リクエスト日時"] = pd.to_datetime(df["リクエスト日時"].str.strip("'"), errors="coerce")
        df = df.sort_values("リクエスト日時")
        all_data.append(df)

    df_all = pd.concat(all_data).reset_index(drop=True)

    # 1時間前までの件数を計算
    counts = []
    for time in df_all["リクエスト日時"]:
        count = df_all[
            (df_all["リクエスト日時"] < time) &
            (df_all["リクエスト日時"] >= time - pd.Timedelta(hours=1))
        ].shape[0]
        counts.append(count)
    df_all["1時間前までの件数"] = counts

    # グラフ表示（X軸目盛りのみ制御）
    st.subheader(f"リクエスト時系列グラフ（X軸間隔：{x_tick_label}）")
    fig, ax = plt.subplots(figsize=(18, 6))
    ax.plot(df_all["リクエスト日時"], df_all["1時間前までの件数"], marker='o', linestyle='-')

    if jp_font:
        ax.set_title("リクエスト件数（1時間前までの件数）", fontproperties=jp_font)
        ax.set_xlabel("時刻", fontproperties=jp_font)
        ax.set_ylabel("件数", fontproperties=jp_font)
    else:
        ax.set_title("Requests in Past Hour")
        ax.set_xlabel("Time")
        ax.set_ylabel("Count")

    ax.grid(True)
    ax.xaxis.set_major_locator(x_tick_locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # 統計表示
    st.subheader("統計情報")
    st.metric("合計リクエスト数", len(df_all))
    st.metric("最大件数（1時間内）", df_all["1時間前までの件数"].max())
    st.metric("平均件数（1時間内）", round(df_all["1時間前までの件数"].mean(), 2))

    # 閾値超過の時間を抽出
    exceeded = df_all[df_all["1時間前までの件数"] > threshold]
    st.subheader(f"制限値（{threshold}件）を超えたリクエスト")
    if not exceeded.empty:
        st.dataframe(exceeded[["リクエスト日時", "1時間前までの件数"]])

        # CSVダウンロード
        csv_buffer = io.StringIO()
        exceeded[["リクエスト日時", "1時間前までの件数"]].to_csv(csv_buffer, index=False)
        st.download_button("超過リストをCSVでダウンロード", csv_buffer.getvalue(), "exceeded_requests.csv", "text/csv")
    else:
        st.info("制限値を超えたリクエストはありません。")
