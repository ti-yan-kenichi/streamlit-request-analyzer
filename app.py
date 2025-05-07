
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
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

st.title("リクエスト分析ツール（拡張版）")

# アップロード（複数対応）
uploaded_files = st.file_uploader("CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

# 粒度選択
freq_label_map = {
    "1時間": "1H",
    "30分": "30T",
    "15分": "15T",
    "5分": "5T"
}
selected_freq_label = st.selectbox("X軸の粒度を選択", list(freq_label_map.keys()))
selected_freq = freq_label_map[selected_freq_label]

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

    # 粒度でリサンプリングして件数を集計
    df_all.set_index("リクエスト日時", inplace=True)
    grouped = df_all.resample(selected_freq).size().rename("件数")
    grouped = grouped.reset_index()

    # グラフ表示
    st.subheader(f"リクエスト件数（{selected_freq_label}単位）")
    fig, ax = plt.subplots(figsize=(18, 6))
    ax.plot(grouped["リクエスト日時"], grouped["件数"], marker='o')

    if jp_font:
        ax.set_title("時間帯ごとのリクエスト件数", fontproperties=jp_font)
        ax.set_xlabel("時間", fontproperties=jp_font)
        ax.set_ylabel("件数", fontproperties=jp_font)
    else:
        ax.set_title("Request Count by Time")
        ax.set_xlabel("Time")
        ax.set_ylabel("Count")

    ax.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # 統計情報
    st.subheader("統計情報")
    st.metric("合計リクエスト数", len(df_all))
    st.metric(f"{selected_freq_label}単位の最大件数", grouped["件数"].max())
    st.metric("平均件数", round(grouped["件数"].mean(), 2))

    # 閾値超過の時間を抽出
    exceeded = grouped[grouped["件数"] > threshold]

    st.subheader(f"制限値（{threshold}件）を超えた時間帯")
    if not exceeded.empty:
        st.dataframe(exceeded)

        # CSVダウンロード用
        csv_buffer = io.StringIO()
        exceeded.to_csv(csv_buffer, index=False)
        st.download_button("超過時間リストをCSVでダウンロード", csv_buffer.getvalue(), "exceeded_times.csv", "text/csv")
    else:
        st.info("制限値を超えた時間帯はありません。")
