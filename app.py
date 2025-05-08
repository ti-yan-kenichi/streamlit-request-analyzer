
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
st.title("📊 リクエスト分析ダッシュボード（CSV結合＋間の時間スキップ）")

# サイドバー設定
with st.sidebar:
    st.header("⚙️ 分析設定")
    threshold = st.number_input("制限値（この件数を超えると超過）", min_value=1, step=1, value=360)
    y_tick_label = st.selectbox("Y軸の目盛り間隔", [1000, 500, 300, 200, 100, 50], index=3)

uploaded_files = st.file_uploader("📁 CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    file_data = {}

    for file in uploaded_files:
        df = pd.read_csv(file, skiprows=3, encoding="shift_jis", encoding_errors="replace")
        df["リクエスト日時"] = pd.to_datetime(df["リクエスト日時"].str.strip("'"), errors="coerce")
        df = df.sort_values("リクエスト日時")
        file_data[file.name] = df

    if file_data:
        st.subheader("🔗 結合された全ファイルデータを分析")
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
                counts = []
                for time in df["リクエスト日時"]:
                    count = df[
                        (df["リクエスト日時"] < time) &
                        (df["リクエスト日時"] >= time - pd.Timedelta(hours=1))
                    ].shape[0]
                    counts.append(count)
                df["1時間前までの件数"] = counts

                with st.expander("📈 結合グラフ（空白なし）", expanded=True):
                    df["index"] = range(len(df))
                    fig, ax = plt.subplots(figsize=(20, 6), dpi=120)
                    ax.plot(df["index"], df["1時間前までの件数"], marker='o', linestyle='-', markersize=4, linewidth=1.5)
                    if jp_font:
                        ax.set_title("結合データのリクエスト件数", fontproperties=jp_font)
                        ax.set_xlabel("レコード順（時系列）", fontproperties=jp_font)
                        ax.set_ylabel("件数", fontproperties=jp_font)
                    ax.grid(True, linestyle='--', alpha=0.5)
                    ax.set_xticks([])  # ラベルを消すか最小限にする
                    ax.set_yticks(range(0, int(df["1時間前までの件数"].max()) + y_tick_label, y_tick_label))
                    st.pyplot(fig)
                    img_bytes = io.BytesIO()
                    fig.savefig(img_bytes, format="png", bbox_inches="tight")
                    st.download_button("📷 結合グラフをPNGでダウンロード", img_bytes.getvalue(), "combined_graph.png", "image/png")

                with st.expander("📊 統計情報（結合）", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("合計リクエスト数", len(df))
                    col2.metric("最大件数（1時間内）", df["1時間前までの件数"].max())
                    col3.metric("平均件数（1時間内）", round(df["1時間前までの件数"].mean(), 2))

                with st.expander("⚠️ 制限値超過（結合）", expanded=True):
                    exceeded = df[df["1時間前までの件数"] > threshold]
                    if not exceeded.empty:
                        st.dataframe(exceeded[["リクエスト日時", "1時間前までの件数"]])
                        csv_buffer = io.StringIO()
                        exceeded[["リクエスト日時", "1時間前までの件数"]].to_csv(csv_buffer, index=False)
                        st.download_button("📥 超過リストCSV（結合）", csv_buffer.getvalue(), "exceeded_combined.csv", "text/csv")
                    else:
                        st.success("制限値を超えたリクエストはありません。")
