import time

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from streamlit_folium import folium_static
import numpy as np

from v2log.utils import (
    calculate_statistics,
    format_dataframe_for_display,
    get_map_markers,
    paginate_dataframe,
    prepare_timeline_data,
    prepare_donut_data,
)


class ProgressComponents:
    """进度显示组件类"""

    def __init__(self):
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.data_container = st.empty()

    def update(self, progress: float, status: str):
        """更新进度"""
        self.progress_bar.progress(progress)
        self.status_text.text(status)

    def clear(self):
        """清除所有组件"""
        self.progress_bar.empty()
        self.status_text.empty()
        self.data_container.empty()


class BatchUpdateHandler:
    """批量更新处理器类"""

    def __init__(self, container):
        self.container = container
        self.current_df = None

    def update(self, new_df: pd.DataFrame):
        """更新数据和显示"""
        if self.current_df is None:
            self.current_df = new_df
        else:
            self.current_df = pd.concat([self.current_df, new_df])

        with self.container.container():
            display_data_and_map(self.current_df)


def create_refresh_button() -> bool:
    """创建刷新按钮并返回是否需要刷新"""
    col_refresh, col_status = st.columns([1, 3])
    with col_refresh:
        clicked = st.button("🔄 重新分析日志")
        if clicked:
            st.session_state.last_refresh = time.strftime("%Y-%m-%d %H:%M:%S")
        return clicked

    with col_status:
        if "last_refresh" in st.session_state:
            st.info(f"上次更新时间: {st.session_state.last_refresh}")


def display_data_and_map(df: pd.DataFrame, search_mode: bool = False):
    """显示数据表格和对应的地图"""
    formatted_df = format_dataframe_for_display(df)
    total_rows = len(formatted_df)

    # 在搜索模式下显示时间轴和环形图
    if search_mode:
        display_timeline(df)
        display_donut_charts(df)

    # 确定要显示的数据
    if search_mode:
        display_df = formatted_df
        st.write(f"找到 {total_rows} 条记录")
    else:
        page_size = 100
        total_pages = (total_rows + page_size - 1) // page_size

        if total_pages > 1:
            # 使用组件位置和时间戳创建唯一key
            if "page_keys" not in st.session_state:
                st.session_state.page_keys = {}

            # 使用调用栈信息创建唯一标识
            import inspect

            caller_frame = inspect.currentframe().f_back
            component_id = (
                f"{caller_frame.f_code.co_filename}"
                f":{caller_frame.f_lineno}"
            )

            # 如果是新位置，创建新的key
            if component_id not in st.session_state.page_keys:
                st.session_state.page_keys[component_id] = str(time.time())

            key_prefix = "page_input"
            key_timestamp = st.session_state.page_keys[component_id]
            key = f"{key_prefix}_{component_id}_{key_timestamp}"

            col_page, col_info = st.columns([1, 3])
            with col_page:
                page = st.number_input(
                    "页码",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    key=key,
                )
            with col_info:
                st.write(f"总计 {total_rows} 条记录，共 {total_pages} 页")
        else:
            page = 1

        display_df = paginate_dataframe(formatted_df, page_size, page)

    # 创建两列布局显示表格和地图
    st.subheader("数据展示")
    col1, col2 = st.columns(2)

    with col1:
        st.write("访问列表")
        st.dataframe(display_df, height=400)

    with col2:
        st.write("访问地图")
        display_map(df[df.index.isin(display_df.index)])


def display_map(df: pd.DataFrame):
    """显示地图"""
    if df.empty:
        st.warning("没有可显示的地理位置数据")
        return

    # 获取地图标记数据
    markers_df = get_map_markers(df)
    if markers_df.empty:
        st.warning("没有有效的地理位置数据")
        return

    # 创建地图
    center_lat = markers_df["x"].mean()
    center_lon = markers_df["y"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4)

    # 添加标记
    for _, row in markers_df.iterrows():
        folium.CircleMarker(
            location=[row["x"], row["y"]],
            radius=np.log1p(row["count"]) * 3,  # 根据访问量调整大小
            popup=f"{row['city']}: {row['count']} 次访问",
            color="#3186cc",
            fill=True,
        ).add_to(m)

    # 显示地图
    folium_static(m)


def display_statistics(df: pd.DataFrame):
    """显示统计信息"""
    st.markdown("---")  # 添加分隔线
    st.subheader("统计信息")

    stats = calculate_statistics(df)

    # 使用三列布局显示基本统计
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总访问次数", stats["total_visits"])
    with col2:
        st.metric("独立IP数", stats["unique_ips"])
    with col3:
        st.metric("访问网站数", stats["unique_sites"])

    # 使用两列布局显示详细统计
    col1, col2 = st.columns(2)
    with col1:
        st.write("访问量最大的网站:")
        st.table(stats["top_sites"])
    with col2:
        st.write("访问量最大的城市:")
        st.table(stats["top_cities"])


def display_data_table(df: pd.DataFrame, search_mode: bool = False):
    """显示数据表格，支持分页和搜索模式"""
    st.subheader("访问列表")

    formatted_df = format_dataframe_for_display(df)
    total_rows = len(formatted_df)

    if search_mode:
        # 搜索模式显示所有结果
        st.write(f"找到 {total_rows} 条记录")
        st.dataframe(formatted_df)
    else:
        # 普通模式使用分页
        page_size = 100
        total_pages = (total_rows + page_size - 1) // page_size

        if total_pages > 1:
            page = st.number_input(
                "页码", min_value=1, max_value=total_pages, value=1
            )
            st.write(f"总计 {total_rows} 条记录，共 {total_pages} 页")
        else:
            page = 1

        st.dataframe(paginate_dataframe(formatted_df, page_size, page))


def display_timeline(df: pd.DataFrame):
    """显示访问量时间轴"""
    st.subheader("访问量时间趋势")

    # 准备数据
    timeline_data = prepare_timeline_data(df)

    # 创建图表
    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.7, 0.3],
        subplot_titles=("城市访问量分布", "总访问量趋势"),
        vertical_spacing=0.12,
    )

    # 添加城市访问量堆叠柱状图
    cities = [col for col in timeline_data.columns if col != "total"]
    for city in cities:
        fig.add_trace(
            go.Bar(
                x=timeline_data.index,
                y=timeline_data[city],
                name=city,
                text=timeline_data[city],  # 显示具体数值
                textposition="auto",  # 自动调整文本位置
            ),
            row=1,
            col=1,
        )

    # 更新堆叠模式
    fig.update_layout(barmode="stack")

    # 添加总访问量趋势线
    fig.add_trace(
        go.Scatter(
            x=timeline_data.index,
            y=timeline_data["total"],
            name="总访问量",
            line=dict(width=2),
        ),
        row=2,
        col=1,
    )

    # 更新布局
    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=-0.1,
            xanchor="left",
            x=0,
            orientation="h",
        ),
        hovermode="x unified",
    )

    # 更新Y轴标题
    fig.update_yaxes(title_text="访问量", row=1, col=1)
    fig.update_yaxes(title_text="总访问量", row=2, col=1)

    # 显示图表
    st.plotly_chart(fig, use_container_width=True)


def display_donut_charts(df: pd.DataFrame):
    """显示环形图"""
    period_data, ip_data, city_data = prepare_donut_data(df)

    # 创建三列布局
    col1, col2, col3 = st.columns(3)

    with col1:
        # 时间段分布图
        fig1 = go.Figure(
            data=[
                go.Pie(
                    labels=list(period_data.keys()),
                    values=list(period_data.values()),
                    hole=0.6,
                    textinfo="label+percent",
                    textposition="outside",
                )
            ]
        )
        fig1.update_layout(
            title="访问时间段分布",
            showlegend=False,
            height=400,
            annotations=[
                dict(
                    text=f"总访问量<br>{sum(period_data.values())}",
                    x=0.5,
                    y=0.5,
                    font_size=12,
                    showarrow=False,
                )
            ],
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # IP分布图
        fig2 = go.Figure(
            data=[
                go.Pie(
                    labels=[
                        f"{ip[:15]}..." if len(ip) > 15 else ip
                        for ip in ip_data.keys()
                    ],
                    values=list(ip_data.values()),
                    hole=0.6,
                    textinfo="label+percent",
                    textposition="outside",
                )
            ]
        )
        fig2.update_layout(
            title="Top 10 IP访问分布",
            showlegend=False,
            height=400,
            annotations=[
                dict(
                    text=f"IP数量<br>{len(ip_data)}",
                    x=0.5,
                    y=0.5,
                    font_size=12,
                    showarrow=False,
                )
            ],
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col3:
        # 地区分布图
        fig3 = go.Figure(
            data=[
                go.Pie(
                    labels=list(city_data.keys()),
                    values=list(city_data.values()),
                    hole=0.6,
                    textinfo="label+percent",
                    textposition="outside",
                )
            ]
        )
        fig3.update_layout(
            title="Top 10 地区访问分布",
            showlegend=False,
            height=400,
            annotations=[
                dict(
                    text=f"地区数量<br>{len(city_data)}",
                    x=0.5,
                    y=0.5,
                    font_size=12,
                    showarrow=False,
                )
            ],
        )
        st.plotly_chart(fig3, use_container_width=True)
