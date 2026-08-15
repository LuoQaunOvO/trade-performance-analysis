# -*- coding: utf-8 -*-
"""生成交互式HTML绩效报告(pyecharts)"""
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Line, Bar, Grid
from pyecharts.commons.utils import JsCode

DATA_PATH = r"data/导出 U 本位合约成交明细 2026-08-10 11_16_02.098.csv"
OUT = r".\report.html"

df = pd.read_csv(DATA_PATH)
df["时间"] = pd.to_datetime(df["时间"])
for c in ["已实现盈亏", "净盈亏", "手续费"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

closes = df[df["方向"].str.contains("Close|Liquidation", case=False, na=False)].copy()
closes["月"] = closes["时间"].dt.to_period("M")

monthly = closes.groupby("月")["净盈亏"].sum()
cum = monthly.cumsum()

def add_header(page):
    from pyecharts.components import Table
    return page

# ============ 图1: 月度累计净值(面积图) ============
line = (
    Line(init_opts=opts.InitOpts(width="1200px", height="420px"))
    .add_xaxis([str(m) for m in monthly.index])
    .add_yaxis("累计净盈亏", [round(v, 2) for v in cum.values],
               is_smooth=True,
               symbol="circle", symbol_size=6,
               markpoint_opts=opts.MarkPointOpts(
                   data=[opts.MarkPointItem(type_="max", name="最高点"), opts.MarkPointItem(type_="min", name="最低点")]),
               markline_opts=opts.MarkLineOpts(data=[opts.MarkLineItem(y=0, name="盈亏平衡线")]))
    .set_global_opts(
        title_opts=opts.TitleOpts(title="月度累计净盈亏(USDT)"),
        yaxis_opts=opts.AxisOpts(name="累计盈亏 (USDT)", splitline_opts=opts.SplitLineOpts(is_show=True)),
        tooltip_opts=opts.TooltipOpts(trigger="axis", formatter=JsCode("params => params[0].axisValue + '<br/>累计盈亏: ' + params[0].value + ' USDT'"))
    )
)

# ============ 图2: 月度盈亏柱状图 ============
bar_month = (
    Bar(init_opts=opts.InitOpts(width="1200px", height="380px"))
    .add_xaxis([str(m) for m in monthly.index])
    .add_yaxis("月度盈亏",
               [round(v, 2) for v in monthly.values],
               itemstyle_opts=opts.ItemStyleOpts(
                   color=JsCode("params => params.value >= 0 ? '#2ca02c' : '#d62728'")))
    .set_global_opts(
        title_opts=opts.TitleOpts(title="月度盈亏(USDT)"),
        yaxis_opts=opts.AxisOpts(name="盈亏 (USDT)", splitline_opts=opts.SplitLineOpts(is_show=True)),
        tooltip_opts=opts.TooltipOpts(trigger="axis"))
)

# ============ 图3: 品种盈亏(横向条形) ============
by_symbol = closes.groupby("币种")["净盈亏"].sum().sort_values()
bar_sym = (
    Bar(init_opts=opts.InitOpts(width="1200px", height="420px"))
    .add_xaxis([str(s) for s in by_symbol.index])
    .add_yaxis("累计盈亏", [round(v, 2) for v in by_symbol.values],
               itemstyle_opts=opts.ItemStyleOpts(
                   color=JsCode("params => params.value >= 0 ? '#2ca02c' : '#d62728'")))
    .set_global_opts(
        title_opts=opts.TitleOpts(title="各品种累计盈亏(USDT)"),
        xaxis_opts=opts.AxisOpts(name="品种"),
        yaxis_opts=opts.AxisOpts(name="累计盈亏 (USDT)", splitline_opts=opts.SplitLineOpts(is_show=True)),
        tooltip_opts=opts.TooltipOpts(trigger="axis"))
    .reversal_axis()
)

# ============ 图4: 多空方向对比 ============
closes["方向类型"] = closes["方向"].apply(lambda x: "做多" if "long" in x.lower() else "做空")
dir_pnl = closes.groupby("方向类型")["净盈亏"].sum()
bar_dir = (
    Bar(init_opts=opts.InitOpts(width="1200px", height="320px"))
    .add_xaxis([str(d) for d in dir_pnl.index])
    .add_yaxis("累计盈亏", [round(v, 2) for v in dir_pnl.values],
               itemstyle_opts=opts.ItemStyleOpts(
                   color=JsCode("params => params.value >= 0 ? '#2ca02c' : '#d62728'")))
    .set_global_opts(
        title_opts=opts.TitleOpts(title="多空方向盈亏对比(USDT)"),
        yaxis_opts=opts.AxisOpts(name="累计盈亏 (USDT)", splitline_opts=opts.SplitLineOpts(is_show=True)),
        tooltip_opts=opts.TooltipOpts(trigger="axis"))
)

# ============ 图5: 盈亏分布直方图 ============
bins = pd.cut(closes["净盈亏"], bins=30).value_counts().sort_index()
bar_dist = (
    Bar(init_opts=opts.InitOpts(width="1200px", height="380px"))
    .add_xaxis([str(b) for b in bins.index])
    .add_yaxis("笔数", [int(v) for v in bins.values])
    .set_global_opts(
        title_opts=opts.TitleOpts(title="单笔盈亏分布"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45, interval=0, font_size=10)),
        yaxis_opts=opts.AxisOpts(name="笔数"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"))
)

# ============ 汇总指标卡 ============
total_pnl = closes["净盈亏"].sum()
total_fee = df["手续费"].sum()
win_rate = (closes["净盈亏"] > 0).mean() * 100
wins = closes[closes["净盈亏"] > 0]["净盈亏"]
losses = closes[closes["净盈亏"] < 0]["净盈亏"]
avg_win = wins.mean()
avg_loss = losses.mean()
pf = abs(wins.sum() / losses.sum()) if losses.sum() else float("inf")

html_head = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>交易绩效分析报告</title>
<style>
body {{ font-family: "Microsoft YaHei", sans-serif; background: #f7f8fa; margin: 0; padding: 20px; }}
.container {{ max-width: 1240px; margin: 0 auto; }}
h1 {{ text-align: center; color: #222; }}
.sub {{ text-align: center; color: #888; margin-bottom: 24px; }}
.cards {{ display: flex; flex-wrap: wrap; gap: 14px; justify-content: center; margin-bottom: 28px; }}
.card {{ background: #fff; border-radius: 10px; padding: 16px 22px; min-width: 150px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
.card .num {{ font-size: 22px; font-weight: bold; color: #222; }}
.card .lbl {{ font-size: 12px; color: #888; margin-top: 4px; }}
.red {{ color: #d62728 !important; }} .green {{ color: #2ca02c !important; }}
.chart {{ background: #fff; border-radius: 10px; padding: 12px 8px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
.conclusion {{ background: #fff; border-radius: 10px; padding: 18px 22px; box-shadow: 0 1px 4px rgba(0,0,0,.08); line-height: 1.9; font-size: 14px; }}
.conclusion h2 {{ margin-top: 0; }}
</style></head>
<body><div class="container">
<h1>交易绩效分析报告</h1>
<div class="sub">数据范围：2025.01 - 2026.08 &nbsp;|&nbsp; 平仓记录：{len(closes)} 笔 &nbsp;|&nbsp; 数据来源：Bitget U本位合约成交明细</div>
<div class="cards">
  <div class="card"><div class="num {'red' if total_pnl<0 else 'green'}">{total_pnl:+.2f}</div><div class="lbl">净盈亏 (USDT)</div></div>
  <div class="card"><div class="num">{win_rate:.1f}%</div><div class="lbl">胜率</div></div>
  <div class="card"><div class="num">{abs(avg_win/avg_loss):.2f}</div><div class="lbl">盈亏比</div></div>
  <div class="card"><div class="num">{pf:.2f}</div><div class="lbl">盈亏因子</div></div>
  <div class="card"><div class="num red">{total_fee:.2f}</div><div class="lbl">手续费 (USDT)</div></div>
  <div class="card"><div class="num">{len(closes)}</div><div class="lbl">平仓笔数</div></div>
</div>
"""

html_foot = f"""<div class="conclusion">
<h2>核心发现</h2>
<p><b>1. 盈亏比失衡是亏损主因</b>：胜率 {win_rate:.1f}%（{len(wins)}胜/{len(losses)}负），但平均盈利 {avg_win:+.3f} USDT vs 平均亏损 {avg_loss:+.3f} USDT，盈利单持有不足（赚小亏大）。</p>
<p><b>2. 交易成本过高</b>：累计手续费 {total_fee:.2f} USDT，占净亏损的 {abs(total_fee/total_pnl)*100:.0f}%，过度交易侵蚀利润。</p>
<p><b>3. 方向性差异显著</b>：做多累计 {dir_pnl.get('做多',0):+.1f} USDT vs 做空 {dir_pnl.get('做空',0):+.1f} USDT，做多为主要亏损来源。</p>
<p><b>4. 风控纪律有效</b>：前期爆仓 3 次后，连续 19 个月零爆仓，未出现单次大额亏损失控。</p>
</div>
</div></body></html>"""

parts = []
for chart in [line, bar_month, bar_sym, bar_dir, bar_dist]:
    parts.append(f'<div class="chart">{chart.render_embed()}</div>')

html = html_head + "".join(parts) + html_foot
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print("报告已生成:", OUT)
print("净盈亏: %.2f | 胜率: %.1f%% | 盈亏比: %.2f | 盈亏因子: %.2f | 手续费: %.2f" % (total_pnl, win_rate, abs(avg_win/avg_loss), pf, total_fee))
