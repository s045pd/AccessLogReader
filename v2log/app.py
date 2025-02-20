import os
from pathlib import Path

import streamlit as st

from v2log.analyzer import IPAnalyzer
from v2log.components import (
    BatchUpdateHandler,
    ProgressComponents,
    create_refresh_button,
    display_data_and_map,
    display_statistics,
)
from v2log.utils import filter_dataframe

st.set_page_config(page_title="访问日志分析器", layout="wide")

# 从环境变量获取配置
LOG_FILE = Path(os.environ["READER_LOG_FILE"])
DB_PATH = Path(os.environ["READER_DB_PATH"])
FILTER = os.environ.get("READER_FILTER", "")


@st.cache_resource
def get_analyzer():
    return IPAnalyzer(db_path=DB_PATH, batch_size=10000 * 10 * 4)


def load_data(log_file, use_cache=True):
    """加载数据"""
    analyzer = get_analyzer()
    return analyzer.process_log_file(log_file, use_cache=use_cache)


def main():
    """主程序入口"""
    # 处理刷新逻辑
    should_refresh = create_refresh_button()
    if should_refresh:
        st.session_state.refresh_data = True

    # 加载数据
    try:
        use_cache = not st.session_state.get("refresh_data", False)
        with st.spinner("正在加载数据..."):
            df = load_data(LOG_FILE, use_cache=use_cache)
        if "refresh_data" in st.session_state:
            del st.session_state.refresh_data
    except Exception as e:
        st.error(f"加载数据时出错: {str(e)}")
        return

    # 搜索框
    search_term = st.text_input("搜索网站:", "")
    if search_term:
        filtered_df = filter_dataframe(df, search_term)
        display_data_and_map(filtered_df, search_mode=True)
    else:
        filtered_df = df
        display_data_and_map(filtered_df, search_mode=False)

    # 显示统计信息
    display_statistics(filtered_df)


if __name__ == "__main__":
    main()
