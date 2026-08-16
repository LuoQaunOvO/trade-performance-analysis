# -*- coding: utf-8 -*-
"""
黑色系商品研究: 螺纹钢基差 + 库存 + 产业链分析
数据源: akshare(免费)
"""
import akshare as ak
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False
import os
import datetime

OUT = r"C:\Users\LuoOVO\Documents\Default Project\trade_project\black_series"
os.makedirs(OUT, exist_ok=True)

# ============ 1. 数据获取 ============
print("=== 1. 获取数据 ===")

# 1.1 螺纹钢期货主力连续(新浪)
print("拉取螺纹钢期货主力连续(2025-01 ~ 至今)...")
fut = ak.futures_main_sina(symbol="RB0", start_date="20250101",
                           end_date=datetime.date.today().strftime("%Y%m%d"))
fut["日期"] = pd.to_datetime(fut["日期"])
fut = fut.sort_values("日期").reset_index(drop=True)
print(f"  期货数据: {len(fut)} 条, 最新收盘 {fut['收盘价'].iloc[-1]}")

# 1.2 螺纹钢现货价格+基差(逐个交易日查询, 取最近120个交易日)
print("拉取螺纹钢现货价与基差(近120个交易日)...")
trade_days = [d for d in pd.date_range(fut["日期"].iloc[-120], fut["日期"].iloc[-1], freq="D")]
basis_rows = []
for d in trade_days:
    ds = d.strftime("%Y%m%d")
    try:
        df = ak.futures_spot_price(date=ds, vars_list=["RB"])
        if len(df):
            basis_rows.append(df.iloc[0])
    except Exception:
        pass
basis = pd.DataFrame(basis_rows)
basis["date"] = pd.to_datetime(basis["date"], format="%Y%m%d")
print(f"  基差数据: {len(basis)} 条")

# 1.3 螺纹钢库存(交易所/社库)
print("拉取螺纹钢库存...")
try:
    inv = ak.futures_inventory_em(symbol="螺纹钢")
    inv["日期"] = pd.to_datetime(inv["日期"])
    inv = inv.sort_values("日期").reset_index(drop=True)
    print(f"  库存数据: {len(inv)} 条")
except Exception as e:
    inv = None
    print(f"  库存失败: {e}")

# ============ 2. 分析计算 ============
print("\n=== 2. 分析 ===")

# 2.1 基差统计
b = basis.copy()
b["near_basis_rate"] = pd.to_numeric(b["near_basis_rate"], errors="coerce")
b["dom_basis_rate"] = pd.to_numeric(b["dom_basis_rate"], errors="coerce")
b["dom_basis"] = pd.to_numeric(b["dom_basis"], errors="coerce")
b["near_basis"] = pd.to_numeric(b["near_basis"], errors="coerce")
b["spot_price"] = pd.to_numeric(b["spot_price"], errors="coerce")

print("基差(期货升贴水)近", len(b), "个交易日统计:")
print(f"  最新基差(主力): {b['dom_basis'].iloc[-1]:+.0f} 元/吨 (现货-期货)")
print(f"  基差均值: {b['dom_basis'].mean():+.0f} | 最大升水: {b['dom_basis'].max():+.0f} | 最大贴水: {b['dom_basis'].min():+.0f}")
print(f"  升水天数占比: {(b['dom_basis']>0).mean()*100:.0f}% | 贴水天数占比: {(b['dom_basis']<0).mean()*100:.0f}%")

# 2.2 库存趋势
if inv is not None:
    inv["库存"] = pd.to_numeric(inv["库存"], errors="coerce")
    inv_30d_ago = inv[inv["日期"] >= inv["日期"].max() - pd.Timedelta(days=30)]
    print(f"\n库存(近30日): {len(inv_30d_ago)} 条")
    if len(inv_30d_ago) >= 2:
        d_inv = inv_30d_ago["库存"].iloc[-1] - inv_30d_ago["库存"].iloc[0]
        print(f"  近30日变化: {d_inv:+.0f} (去库{'<' if d_inv<0 else '>'}0)")
        print(f"  最新库存: {inv_30d_ago['库存'].iloc[-1]:.0f}")

# 2.3 价格与库存联动
print("\n=== 3. 生成图表 ===")

# 图1: 期货价格 + 基差(双轴)
fig, ax1 = plt.subplots(figsize=(12, 5))
ax1.plot(fut["日期"], fut["收盘价"], color="#1f77b4", linewidth=1.2, label="螺纹钢期货主力收盘价")
ax1.set_ylabel("价格 (元/吨)", color="#1f77b4")
ax2 = ax1.twinx()
ax2.bar(b["date"], b["dom_basis"], color=["#2ca02c" if v > 0 else "#d62728" for v in b["dom_basis"]], alpha=0.6, width=1.5, label="基差(现货-期货)")
ax2.axhline(0, color="gray", linewidth=0.8)
ax2.set_ylabel("基差 (元/吨)", color="#555")
ax1.set_title("螺纹钢: 期货价格与基差走势(2025-2026)")
fig.autofmt_xdate()
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "rb_price_basis.png"), dpi=150)
print("图1: rb_price_basis.png")

# 图2: 基差率分布
fig, ax = plt.subplots(figsize=(12, 4.5))
ax.plot(b["date"], b["dom_basis_rate"] * 100, color="#9467bd", marker="o", markersize=3, linewidth=1)
ax.axhline(0, color="gray", linewidth=0.8)
ax.set_ylabel("基差率 (%)")
ax.set_title("螺纹钢基差率走势(现货-期货)/期货")
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(os.path.join(OUT, "rb_basis_rate.png"), dpi=150)
print("图2: rb_basis_rate.png")

# 图3: 库存走势
if inv is not None:
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(inv["日期"], inv["库存"], color="#d62728", linewidth=1.2)
    ax.set_ylabel("库存")
    ax.set_title("螺纹钢库存走势")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "rb_inventory.png"), dpi=150)
    print("图3: rb_inventory.png")

# 图4: 价格-库存散点(相关性)
if inv is not None:
    merged = pd.merge(fut[["日期", "收盘价"]], inv[["日期", "库存"]], on="日期", how="inner")
    if len(merged) > 10:
        corr = merged["收盘价"].corr(merged["库存"])
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(merged["库存"], merged["收盘价"], alpha=0.5, s=15)
        ax.set_xlabel("库存")
        ax.set_ylabel("期货收盘价 (元/吨)")
        ax.set_title(f"价格与库存相关性 r={corr:.2f}")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "rb_price_inv_corr.png"), dpi=150)
        print(f"图4: rb_price_inv_corr.png (r={corr:.2f})")

# ============ 4. 输出汇总 ============
print("\n=== 4. 汇总 ===")
print(f"螺纹钢期货最新价: {fut['收盘价'].iloc[-1]} 元/吨 ({fut['日期'].iloc[-1].date()})")
print(f"最新基差(主力): {b['dom_basis'].iloc[-1]:+.0f} 元/吨, 基差率 {b['dom_basis_rate'].iloc[-1]*100:+.2f}%")
if inv is not None:
    print(f"最新库存: {inv['库存'].iloc[-1]:.0f}")
    if len(inv_30d_ago) >= 2:
        print(f"近30日库存变化: {d_inv:+.0f}")
print(f"输出目录: {OUT}")
