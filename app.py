import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
from datetime import datetime

# --- 1. 全銘柄リストの取得 ---
@st.cache_data
def get_all_jpx_stocks():
  csv_paths = ["./jpx_stocks.csv","/content/drive/MyDrive/Colab Notebooks/jpx_stocks.csv"]

  for path in csv_paths:
      try:
          df = pd.read_csv(path, encoding="shift_jis")
          # 表示用のラベル「8306 三菱UFJ銀行」を作成
          df["display_name"] = df["コード"].astype(str) + " " + df["銘柄名"]
          return df
      except:
          continue
  st.error(f"CSVファイルが見つかりませんでした")
  return pd.DataFrame({"コード": [8306], "銘柄名": ["三菱UFJ"], "display_name": ["8306 三菱UFJ"]})

df_master = get_all_jpx_stocks()

# ベンチマークの設定
BENCHMARKS = {
    "S&P": "https://www.amova-am.com/products/etf/files/etf/dailydata/etf-funddata-615471.csv",
    "TOPIX": "https://www.amova-am.com/products/etf/files/etf/dailydata/etf-funddata-113085.csv",
    "GOLD":"https://www.amova-am.com/api/fund-export?funds[]=643718"
}

st.markdown("### 📈 株価チャート")

# --- 2. サイドバー設定 ---
with st.sidebar:
    st.header("表示設定")

    # 4000銘柄から検索して選択
    default_codes = ["8306", "1802","2914","5334"]
    selected_labels = st.multiselect(
        "銘柄を検索・選択",
        options=df_master["display_name"].tolist(),
        default=[l for l in df_master["display_name"] if any(code in l for code in default_codes)]
    )

    # 選択されたラベルから「名前」と「ティッカー」を動的に作成
    # selected_names: ["三菱UFJ銀行", ...]
    # current_stocks: {"三菱UFJ銀行": "8306.T", ...}
    selected_names = []
    current_stocks = {}
    for label in selected_labels:
        parts = label.split(maxsplit=1)
        code = parts[0]
        name = parts[1]
        selected_names.append(name)
        current_stocks[name] = f"{code}.T"

    period_choice = st.radio("表示期間", ["5日", "1ヶ月", "6ヶ月", "1年", "3年", "5年","10年"], index=3)

    st.write("---")
    selected_benchmarks = [name for name, url in BENCHMARKS.items() if st.checkbox(name, value=(name=="S&P"))]
    normalize = st.checkbox("開始日を100%として規格化", True)

# --- 3. 期間計算 ---
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

# --- 4. データ取得関数 ---
def get_csv_data(url, start):
    try:
        try:
            df = pd.read_csv(url, encoding="utf-8", header=1)
        except UnicodeDecodeError:
            df = pd.read_csv(url, encoding="shift-jis", header=1)

        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
        df = df.set_index(df.columns[0]).sort_index()
        bench_series = df.iloc[:, 0]
        return bench_series[start:]
    except Exception as e:
        st.error(f"CSV解析エラー: {e}")
        return pd.Series()

# --- 5. メイン表示 ---
if selected_names or selected_benchmarks:
    fig, ax = plt.subplots(figsize=(10, 6))

    # 1. 個別銘柄の描画
    if selected_names:
        tickers = [current_stocks[name] for name in selected_names]
        try:
            df_stocks = yf.download(tickers, start=start_date, end=end_date)["Close"]

            if isinstance(df_stocks, pd.Series):
                df_stocks = df_stocks.to_frame(name=selected_names[0])
            else:
                # ティッカーから名前に変換するための逆引き辞書
                ticker_to_name = {v: k for k, v in current_stocks.items()}
                df_stocks.columns = [ticker_to_name.get(col, col) for col in df_stocks.columns]

            for name in df_stocks.columns:
                series = df_stocks[name].dropna()
                if not series.empty:
                    val = (series / series.iloc[0] * 100) if normalize else series
                    ax.plot(val, label=name, lw=2)
        except Exception as e:
            st.error(f"株価取得エラー: {e}")

    # 2. ベンチマークの描画
    colors = ["#FFFFFF","#00FFFF","#FFD700"]
    for i, name in enumerate(selected_benchmarks):
        bench_series = get_csv_data(BENCHMARKS[name], start_date)
        if not bench_series.empty:
            val = (bench_series / bench_series.iloc[0] * 100) if normalize else bench_series
            ax.plot(val, label=name, color=colors[i % len(colors)], linestyle="--", alpha=0.7)

    # グラフ装飾
  # --- グラフ装飾（ダークモード設定） ---
    fig.patch.set_facecolor('#0E1117') # 外側の背景色
    ax.set_facecolor('#0E1117')        # 内側の背景色

    # 軸のラベルや目盛りの色を白にする
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_edgecolor('#444444') # 枠線の色

    ax.set_ylabel("値 (規格化)" if normalize else "価格")
    ax.grid(True, linestyle=':', alpha=0.3, color='gray') # グリッドを少し暗めに
    ax.tick_params(labelleft=True, labelright=True, left=True, right=True)

    # 凡例の文字色も白にする
    leg = ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=3, frameon=False)
    for text in leg.get_texts():
        text.set_color('white')

    plt.tight_layout()
    st.pyplot(fig)

# --- グラフの下に最新情報を表示 ---
st.write("---")
st.subheader("📌 最新の市場・銘柄情報")

# 1. 個別銘柄の表示
if selected_names and not df_stocks.empty:
    st.markdown("#### 【個別銘柄】")
    cols_s = st.columns(3) # 3列ずつ並べる
    for i, name in enumerate(selected_names):
        series = df_stocks[name].dropna()
        if len(series) >= 2:
            latest = series.iloc[-1]
            prev = series.iloc[-2]
            latest_date = series.index[-1].strftime('%m/%d')
            change = latest - prev
            pct = (change / prev) * 100
            with cols_s[i % 3]:
                st.metric(label=f"{name} ({latest_date})", value=f"{latest:,.1f}円", delta=f"{change:,.1f}円 ({pct:+.2f}%)")

# 2. ベンチマークの表示 (追加部分)
if selected_benchmarks:
    st.write("") # 少し隙間を空ける
    st.markdown("#### 【ベンチマーク】")
    cols_b = st.columns(3)
    for i, name in enumerate(selected_benchmarks):
        # 描画で使った get_csv_data を再利用
        bench_series = get_csv_data(BENCHMARKS[name], start_date)
        if len(bench_series) >= 2:
            latest = bench_series.iloc[-1]
            prev = bench_series.iloc[-2]
            latest_date = bench_series.index[-1].strftime('%m/%d')
            change = latest - prev
            pct = (change / prev) * 100
            with cols_b[i % 3]:
                # ベンチマークは円単位ではないものもあるので単位なしで表示
                st.metric(label=f"{name} ({latest_date})", value=f"{latest:,.1f}", delta=f"{change:,.1f} ({pct:+.2f}%)")
