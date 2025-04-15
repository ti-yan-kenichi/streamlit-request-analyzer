import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager as fm
import os

# フォント設定（macOS ローカルのみ）
if os.path.exists("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"):
    font_path = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
    jp_font = fm.FontProperties(fname=font_path)
else:
    jp_font = None  # Cloudなどでは標準フォントを使う

st.title("リクエスト分析ツール")

# ファイルアップロード
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type="csv")

if uploaded_file:
    # データ読み込み
    df = pd.read_csv(uploaded_file, skiprows=3, encoding="shift_jis", encoding_errors="replace")
    df["リクエスト日時"] = pd.to_datetime(df["リクエスト日時"].str.strip("'"), errors="coerce")
    df = df.sort_values("リクエスト日時")

    # 1時間前までの件数を計算
    counts = []
    for time in df["リクエスト日時"]:
        count = df[
            (df["リクエスト日時"] < time) &
            (df["リクエスト日時"] >= time - pd.Timedelta(hours=1))
        ].shape[0]
        counts.append(count)
    df["1時間前までの件数"] = counts

    # 統計表示
    st.subheader("統計情報")
    st.metric("合計リクエスト数", len(df))
    st.metric("リクエスト数の平均", round(df["1時間前までの件数"].mean(), 2))
    st.metric("ピーク時リクエスト数", df["1時間前までの件数"].max())

    # グラフ表示
    st.subheader("リクエスト推移グラフ")
    fig, ax = plt.subplots(figsize=(18, 6))
    ax.plot(df["リクエスト日時"], df["1時間前までの件数"], marker='o')
    ax.set_title("1時間前までのリクエスト件数", fontproperties=jp_font)
    ax.set_xlabel("日時", fontproperties=jp_font)
    ax.set_ylabel("件数", fontproperties=jp_font)
    ax.grid(True)
    plt.xticks(rotation=45)

    # Y軸の最大値に応じて刻み幅を自動設定
    max_y = df["1時間前までの件数"].max()
    if max_y <= 500:
        y_tick_unit = 50
    elif max_y <= 1000:
        y_tick_unit = 100
    elif max_y <= 3000:
        y_tick_unit = 300
    else:
        y_tick_unit = 500
    plt.yticks(range(0, ((max_y // y_tick_unit) + 2) * y_tick_unit, y_tick_unit))

    # グラフ描画
    st.pyplot(fig)

    # CSV ダウンロード
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("分析結果をCSVでダウンロード", csv, "analysis_result.csv", "text/csv")