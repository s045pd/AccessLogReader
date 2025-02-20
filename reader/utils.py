from typing import Any, Dict, Tuple

import numpy as np
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
        "top_sites": df.groupby("dst")["count"]
        .sum()
        .sort_values(ascending=False)
        .head(),
        "top_cities": df.groupby("city")["count"]
        .sum()
        .sort_values(ascending=False)
        .head(),
    }


def get_valid_coordinates(
    df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    """获取有效的坐标点数据"""
    mask = (df["x"] != 0) & (df["y"] != 0)
    valid_df = df[mask]

    return (
        valid_df["x"].values,
        valid_df["y"].values,
        valid_df["count"].values,
        [
            f"IP: {row['src']}<br>"
            f"目标: {row['dst']}<br>"
            f"城市: {row['city']}<br>"
            f"访问次数: {row['count']}"
            for _, row in valid_df.iterrows()
        ],
    )


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


def prepare_timeline_data(df: pd.DataFrame) -> pd.DataFrame:
    """准备时间轴数据，按城市分组统计"""
    # 按时间和城市分组计算访问量
    timeline_data = (
        df.groupby(["min", "city"])["count"]
        .sum()
        .reset_index()
        .sort_values("min")
    )

    # 数据透视表，每个城市一列
    pivot_data = timeline_data.pivot(
        index="min", columns="city", values="count"
    ).fillna(0)

    # 添加总量列
    pivot_data["total"] = pivot_data.sum(axis=1)

    return pivot_data


def prepare_map_data(df: pd.DataFrame) -> pd.DataFrame:
    """准备地图数据，按城市聚合"""
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


def get_map_markers(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, list]:
    """获取地图标记数据"""
    map_data = prepare_map_data(df)

    return (
        map_data["x"].values,
        map_data["y"].values,
        [
            f"城市: {row['city']}<br>" f"访问次数: {int(row['count'])}"
            for _, row in map_data.iterrows()
        ],
    )
