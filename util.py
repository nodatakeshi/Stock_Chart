import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
from datetime import datetime


# ベンチマークへのリンク辞書
BENCHMARKS = {
    "S&P": "https://www.amova-am.com/api/fund-export?funds[]=645067",#インデックスファンドS&P500（アメリカ株式）
    "TOPIX": "https://www.amova-am.com/api/fund-export?funds[]=358290",#インデックスファンドＴＯＰＩＸ（日本株式）
    "Tracers50":"https://www.amova-am.com/api/fund-export?funds[]=945109",
    "ゴールドファンドH無":"https://www.amova-am.com/api/fund-export?funds[]=643718"
    }

# --- 全銘柄リストの取得 ---
#@st.cache_data
def get_all_jpx_stocks():
  csv_paths = ["/content/drive/MyDrive/Colab Notebooks/jpx_stocks.csv","./jpx_stocks.csv"]

  for path in csv_paths:
      try:
          df = pd.read_csv(path, encoding="shift_jis")
          # 表示用のラベル「8306 三菱UFJ銀行」を作成
          df["display_name"] = df["コード"].astype(str) + " " + df["銘柄名"]
          return df
      except:
          continue
  st.error(f"CSVファイルが見つかりませんでした.")
  return pd.DataFrame({"コード": [8306], "銘柄名": ["三菱UFJ"], "display_name": ["8306 三菱UFJ"]})


# --- サイドバー設定 ---
def side_bar_set():
  with st.sidebar:
      st.header("表示設定")

      # 全銘柄リスト取得
      df_master = get_all_jpx_stocks()

      # 4000銘柄から検索して選択
      default_codes = ["8306", "1802","2914","5334","8766","2802","8789"]
      selected_labels = st.multiselect(
          "銘柄を検索・選択",
          options = df_master["display_name"].tolist(),
          default = [l for l in df_master["display_name"] if any(code in l for code in default_codes)]
      )

      period_choice = st.radio("表示期間", ["5日", "1ヶ月", "6ヶ月", "1年", "3年", "5年","10年"], index=3)

      st.write("---")
      selected_benchmarks = [name for name, url in BENCHMARKS.items() if st.checkbox(name, value=(name=="S&P"))]
      normalize = st.checkbox("開始日を100%として規格化", True)

  date_offsets = {
      "5日": pd.DateOffset(days=5),
      "1ヶ月": pd.DateOffset(months=1),
      "6ヶ月": pd.DateOffset(months=6),
      "1年": pd.DateOffset(years=1),
      "3年": pd.DateOffset(years=3),
      "5年": pd.DateOffset(years=5)
  }

  start_date = datetime.now() - date_offsets.get(period_choice, pd.DateOffset(years=10))

  return selected_labels, selected_benchmarks, start_date, normalize


#yfinanceからデータを取得する
def get_yfinance_datas(names, start_date):
  df_stocks = pd.DataFrame()
  tickers = [label.split(maxsplit=1)[0] + ".T" for label in names]
  if names:
      try:
          tickers = [label.split(maxsplit=1)[0] + ".T" for label in names]
          df_stocks = yf.download(tickers, start=start_date)["Close"]
          df_stocks.columns = [label for label in names]
      except Exception as e:
          st.error(f"株価取得エラー: {e}")
  return df_stocks


#投信のサイトからcsvデータを取得する
#@st.cache_data
def get_csv_datas(names, start_date):
    try:
      df_list=[]
      df_mearge = pd.DataFrame()
      for name in names:
        url = BENCHMARKS[name]
        try:
            df = pd.read_csv(url, encoding="utf-8", header=1)
        except UnicodeDecodeError:
            df = pd.read_csv(url, encoding="shift-jis", header=1)
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
        df = df.set_index(df.columns[0]).sort_index()
        bench_series = df.iloc[:, 0]
        df_list.append(bench_series[start_date:])
      if df_list != []:
        df_mearge = pd.concat(df_list, axis=1)
        df_mearge.columns = names
      return df_mearge
    except Exception as e:
        st.error(f"CSV解析エラー: {e}")
        return pd.Series()

# ---チャート描画 ---
def draw_chart(ax, df_drows, normalize, colors=[None],linestyle=None):
  for i, name in enumerate(df_drows.columns):
    series = df_drows[name].dropna()
    if not series.empty:
      val = (series / series.iloc[0] * 100) if normalize else series
      ax.plot(val, label=name, color=colors[i % len(colors)], linestyle = linestyle)

# ---チャート描画全体 ---
def chart_display(df_stocks, df_benchies, normalize):
    fig, ax = plt.subplots(figsize=(10, 6))

    # 個別株の描画
    draw_chart(ax,df_stocks,normalize)
    # ベンチマークの描画
    colors = ["#FFFFFF","#00FFFF","#FFD700"]
    draw_chart(ax,df_benchies,normalize,colors,"--")

    # グラフ装飾---ダークモード---
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

    return df_stocks, df_benchies


# 本日の価格の表示
def price_display(df_display):
  if not df_display.empty:
      cols_s = st.columns(3) # 3列ずつ並べる
      for i, name in enumerate(df_display.columns):
          series = df_display[name].dropna()
          if len(series) >= 2:
              latest = series.iloc[-1]
              prev = series.iloc[-2]
              latest_date = series.index[-1].strftime('%m/%d')
              change = latest - prev
              pct = (change / prev) * 100
              with cols_s[i % 3]:
                  st.metric(label=f"{name} ({latest_date})", value=f"{latest:,.0f}円", delta=f"{change:,.0f}円 ({pct:+.2f}%)"
                  ,delta_color="inverse" )

def drop_display(df_stocks):
  if not df_stocks.empty:
      cols_buy = st.columns(3)
      for i, name in enumerate(df_stocks.columns):
          # 直近1ヶ月（約20営業日）のデータを抽出
          recent_data = df_stocks[name].dropna().tail(20)

          if not recent_data.empty:
              current_price = recent_data.iloc[-1]
              max_price = recent_data.max()
              # 高値からの下落率（ドローダウン）
              drop_rate = ((current_price - max_price) / max_price) * 100

              with cols_buy[i % 3]:
                  # 下落率が-5%を超えたら「買い検討？」と強調する
                label = "安値圏" if drop_rate < -5 else "安定"
                label_color = "#ff6b6b" if label == "安値圏" else "#5be386"
                bg_color = "#3d2227" if label == "安値圏" else "#173828"

                st.markdown(f"""
                    <div style="font-size:14px; color:#cccccc;">{name}</div>
                    <div style="font-size:28px; font-weight:bold; color:#ffffff">{drop_rate:.1f}%</div>
                    <div style="
                      display:inline-block;
                      padding:6px 6px;
                      border-radius:12px;
                      background-color:{bg_color};
                      margin-bottom:20px;
                      color:{label_color};
                      font-size:12px;
                    ">{label}</div>


                """, unsafe_allow_html=True)

st.set_page_config(layout="wide")
selected_labels, selected_benchmarks, start_date, normalize = side_bar_set()
st.error(f"株価取得エラー: {start_date}")

df_stocks = get_yfinance_datas(selected_labels, start_date)
df_benchies = get_csv_datas(selected_benchmarks, start_date)

st.markdown("### 📈 株価チャート")
chart_display(df_stocks, df_benchies, normalize)
st.write("---")

st.subheader("📌 最新の市場・銘柄情報")
st.markdown("#### 【個別銘柄】")
price_display(df_stocks)
st.write("") # 少し隙間を空ける
st.markdown("#### 【ベンチマーク】")
price_display(df_benchies)
st.write("---")

st.subheader("🛒 お買い得（急落）チェック")
st.caption("直近1ヶ月の高値から現在何％値下がりしているか")
util.drop_display(df_stocks)

