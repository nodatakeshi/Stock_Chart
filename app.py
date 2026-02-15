import util
import streamlit as st


st.set_page_config(layout="wide")
selected_labels, selected_benchmarks, start_date, normalize = util.side_bar_set()

df_stocks = util.get_yfinance_datas(selected_labels, start_date)
df_benchies = util.get_csv_datas(selected_benchmarks, start_date)

st.markdown("### 📈 株価チャート")
util.chart_display(df_stocks, df_benchies, normalize)
st.write("---")

st.subheader("📌 最新の市場・銘柄情報")
st.markdown("#### 【個別銘柄】")
util.price_display(df_stocks)
st.write("") # 少し隙間を空ける
st.markdown("#### 【ベンチマーク】")
util.price_display(df_benchies)
st.write("---")

st.subheader("🛒 お買い得（急落）チェック")
st.caption("直近1ヶ月の高値から現在何％値下がりしているか")
util.drop_display(df_stocks)
