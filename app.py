import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
from datetime import datetime

st.set_page_config(page_title="株価チャート", layout="wide")

st.title("📈 株価チャート")

# 銘柄リスト
STOCKS = {
    "三菱UFJ銀行": "8306.T",
    "日本特殊陶業": "5334.T",
    "大林組": "1802.T",
    "アステラス製薬": "4503.T",
    "JT": "2914.T"
}

# ベンチマークの設定
BENCHMARKS = {
    "S&P": "https://www.amova-am.com/products/etf/files/etf/dailydata/etf-funddata-615471.csv",
    "TOPIX": "https://www.amova-am.com/products/etf/files/etf/dailydata/etf-funddata-113085.csv",
    "GOLD":"https://www.amova-am.com/api/fund-export?funds[]=643718"
}

with st.sidebar:
    st.header("表示設定")
    selected_names = st.multiselect("銘柄を選択", list(STOCKS.keys()), default=["三菱UFJ銀行"])

    period_choice = st.radio("表示期間", ["5日", "1ヶ月", "6ヶ月", "1年", "3年", "5年","10年"], index=3)

    st.write("---")
    # ベンチマーク選択
    selected_benchmarks = [name for name, url in BENCHMARKS.items() if st.checkbox(name, value=(name=="S&P"))]

    normalize = st.checkbox("開始日を100%として規格化", True)

# --- 期間計算 ---
end_date = datetime.now()
date_offsets = {
    "5日": pd.DateOffset(days=5),
    "1ヶ月": pd.DateOffset(months=1),
    "6ヶ月": pd.DateOffset(months=6),
    "1年": pd.DateOffset(years=1),
    "3年": pd.DateOffset(years=3),
    "5年": pd.DateOffset(years=5)
    }

start_date = end_date - date_offsets.get(period_choice, pd.DateOffset(years=10))

# --- データ取得・描画関数 ---
def get_csv_data(url, start):
    try:
        # エンコードを試行して読み込み
        try:
            df = pd.read_csv(url, encoding="utf-8", header=1)
        except UnicodeDecodeError:
            df = pd.read_csv(url, encoding="shift-jis", header=1)

        # 1. 「1列目」を日付として変換し、インデックスにする
        # iloc[:, 0] は全行の0番目の列を指します
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
        df = df.set_index(df.columns[0]).sort_index()

        # 2. 「2列目」を価格データとして抽出
        # インデックス化したので、元の2列目は現在の0番目の列になります
        bench_series = df.iloc[:, 0]

        # 3. 指定した開始日以降のデータを返す
        return bench_series[start:]

    except Exception as e:
        st.error(f"CSV解析エラー: {e}")
        return pd.Series()

# --- メイン表示 ---
if selected_names or selected_benchmarks:
    fig, ax = plt.subplots(figsize=(10, 6))

    # 1. 個別銘柄
    if selected_names:
        tickers = [STOCKS[name] for name in selected_names]
        try:
          # yfinanceを使用して指定期間の終値（Close）を一括ダウンロード
            df_stocks = yf.download(tickers, start=start_date, end=end_date)["Close"]

            # 【データ整形】1銘柄のみ選択した場合、戻り値がSeriesになるためDataFrameに変換
            if isinstance(df_stocks, pd.Series):
                df_stocks = df_stocks.to_frame(name=selected_names[0])
            else:
              # 複数銘柄の場合、カラム名をティッカーから銘柄名にする
                ticker_to_name = {v: k for k, v in STOCKS.items()}
                df_stocks.columns = [ticker_to_name[col] for col in df_stocks.columns]

            # 各銘柄のデータを1つずつループしてグラフにプロット
            for name in df_stocks.columns:
                series = df_stocks[name].dropna()
                #正規化処理
                if not series.empty:
                    val = (series / series.iloc[0] * 100) if normalize else series
                    ax.plot(val, label=name, lw=2)
        except:
            st.error("株価取得エラー")

    # 2. ベンチマーク (CSV)
    colors = ["black", "gray"] # ベンチマーク用の色
    for i, name in enumerate(selected_benchmarks):
        try:
            bench_series = get_csv_data(BENCHMARKS[name], start_date)
            if not bench_series.empty:
                val = (bench_series / bench_series.iloc[0] * 100) if normalize else bench_series
                ax.plot(val, label=name, color=colors[i % 2], linestyle="--", alpha=0.7)
        except:
            st.warning(f"{name} の読み込み失敗")

    #グラフ軸
    ax.set_ylabel("値 (規格化)" if normalize else "価格")
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.tick_params(labelleft=True, labelright=True, left=True, right=True)

    #凡例、レイアウト
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=3, frameon=False)
    plt.tight_layout()
    st.pyplot(fig)
