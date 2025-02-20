from typing import Any, Dict

import pandas as pd


def filter_dataframe(
    df: pd.DataFrame, search_term: str, column: str = "dst"
) -> pd.DataFrame:
    """根据搜索词过滤DataFrame"""
    if not search_term:
        return df
    return df[df[column].str.contains(search_term, case=False)]


def calculate_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """计算数据统计信息"""
    return {
        "total_visits": df["count"].sum(),
        "unique_ips": df["src"].nunique(),
        "unique_sites": df["dst"].nunique(),
        "top_sites": (
            df.groupby("dst")["count"]
            .sum()
            .sort_values(ascending=False)
            .head()
        ),
        "top_cities": (
            df.groupby("city")["count"]
            .sum()
            .sort_values(ascending=False)
            .head()
        ),
    }


def format_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """格式化用于显示的DataFrame"""
    return df[["min", "src", "dst", "city", "count"]].sort_values(
        "min", ascending=False
    )


def paginate_dataframe(
    df: pd.DataFrame, page_size: int = 100, page: int = 1
) -> pd.DataFrame:
    """对DataFrame进行分页"""
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return df.iloc[start_idx:end_idx]


def get_map_markers(df: pd.DataFrame) -> pd.DataFrame:
    """获取地图标记数据"""
    # 按城市分组计算总访问量
    map_data = (
        df.groupby("city")
        .agg(
            {
                "count": "sum",
                "x": "first",  # 使用第一个坐标
                "y": "first",
            }
        )
        .reset_index()
    )

    # 过滤掉无效坐标
    return map_data[(map_data["x"] != 0) & (map_data["y"] != 0)]


def prepare_timeline_data(df: pd.DataFrame) -> pd.DataFrame:
    """准备时间轴数据"""
    # 按时间和城市分组
    timeline = df.groupby(["min", "city"])["count"].sum().unstack(fill_value=0)

    # 添加总访问量列
    timeline["total"] = timeline.sum(axis=1)

    return timeline


def prepare_donut_data(df: pd.DataFrame) -> tuple[dict, dict, dict]:
    """准备环形图数据"""
    # 时间段分布
    df["hour"] = df["min"].dt.hour
    time_periods = {
        "凌晨 (0-6)": (0, 6),
        "上午 (6-12)": (6, 12),
        "下午 (12-18)": (12, 18),
        "晚上 (18-24)": (18, 24),
    }

    period_data = {}
    for period, (start, end) in time_periods.items():
        mask = (df["hour"] >= start) & (df["hour"] < end)
        period_data[period] = df[mask]["count"].sum()

    # IP分布（取前10个IP）
    ip_data = (
        df.groupby("src")["count"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .to_dict()
    )

    # 地区分布（取前10个地区）
    city_data = (
        df.groupby("city")["count"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .to_dict()
    )

    return period_data, ip_data, city_data
