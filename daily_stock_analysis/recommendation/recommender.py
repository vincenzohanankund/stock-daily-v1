# -*- coding: utf-8 -*-
"""
股票推荐模块（策略实现骨架）— 自动选出8只并生成 Markdown 报告。
- 与现有代码零耦合（新增文件）
- 自动发送默认关闭（通过环境变量控制）
"""
from typing import Tuple, List, Dict, Any, Callable
import pandas as pd
import numpy as np
import datetime

MIN_LISTING_DAYS = 750
MIN_TOTAL_MARKET_CAP = 50e8
MAX_TOTAL_MARKET_CAP = 500e8
MIN_FLOAT_MARKET_CAP = 50e8
MAX_FLOAT_MARKET_CAP = 200e8
MIN_PRICE = 1.0
MAX_PRICE = 30.0
MIN_TODAY_AMOUNT = 5e7

WEIGHT_FIN = 0.30
WEIGHT_TECH = 0.40
WEIGHT_FUNDS = 0.20
WEIGHT_HEAT = 0.10

def ma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).mean()

def pct_change(a, b) -> float:
    if b == 0:
        return np.nan
    return (a - b) / b

def apply_mandatory_filters(df_fin: pd.DataFrame, df_latest_daily: pd.DataFrame) -> pd.DataFrame:
    df = df_fin.copy()
    if 'code' in df_latest_daily.columns:
        df_latest_daily_indexed = df_latest_daily.set_index('code')
        df = df.set_index('code').join(df_latest_daily_indexed[['close', 'amount', 'turnover_rate']], how='left')
        df = df.reset_index()
        df.rename(columns={'close': 'close_price', 'amount': 'today_amount'}, inplace=True)
    if 'listing_days' in df.columns:
        cond_listing = df['listing_days'] >= MIN_LISTING_DAYS
    elif 'listing_date' in df.columns:
        today = pd.Timestamp.today().normalize()
        df['listing_days'] = (today - pd.to_datetime(df['listing_date'])).dt.days
        cond_listing = df['listing_days'] >= MIN_LISTING_DAYS
    else:
        cond_listing = True
    cond_not_st = ~df.get('is_st', False) & ~df.get('is_star_st', False)
    prefixes = df.get('market_prefix', df['code'].astype(str).str[:3])
    cond_exchange = prefixes.apply(lambda x: not (str(x).startswith('688') or str(x).startswith('300') or str(x).startswith('83') or str(x).startswith('87')))
    cond_mainboard = prefixes.apply(lambda x: any(str(x).startswith(p) for p in ['600','601','603','000','001']))
    cond_total_mv = (df.get('total_market_cap', np.nan) >= MIN_TOTAL_MARKET_CAP) & (df.get('total_market_cap', np.nan) <= MAX_TOTAL_MARKET_CAP)
    cond_float_mv = (df.get('float_market_cap', np.nan) >= MIN_FLOAT_MARKET_CAP) & (df.get('float_market_cap', np.nan) <= MAX_FLOAT_MARKET_CAP)
    cond_price = (df.get('close_price', np.nan) >= MIN_PRICE) & (df.get('close_price', np.nan) <= MAX_PRICE)
    cond_amount = df.get('today_amount', 0) > MIN_TODAY_AMOUNT

    mask = cond_listing & cond_not_st & cond_exchange & cond_mainboard & cond_total_mv & cond_float_mv & cond_price & cond_amount
    df_filtered = df[mask].copy()
    df_filtered['filter_reason'] = ''
    return df_filtered.reset_index(drop=True)

def score_financials(row: pd.Series) -> float:
    score = 0.0
    weight_sum = 0.0
    def safe(v):
        try:
            return float(v)
        except:
            return np.nan
    weights = {'net_profit':0.15,'yoy':0.15,'deduct_yoy':0.15,'sales_margin':0.12,'gross_margin':0.12,'current_ratio':0.08,'pb':0.12,'ev_ebitda':0.11}
    net_profit = safe(row.get('net_profit', np.nan))
    score += weights['net_profit'] * (100 if net_profit>0 else 0); weight_sum += weights['net_profit']
    yoy = safe(row.get('net_profit_yoy_pct', np.nan))
    score += weights['yoy'] * (100 if yoy>10 else max(0, 100*(yoy/10) if not np.isnan(yoy) else 0)); weight_sum += weights['yoy']
    ded_yoy = safe(row.get('net_profit_after_deduct_yoy_pct', np.nan))
    score += weights['deduct_yoy'] * (100 if ded_yoy>=20 else max(0, 100*(ded_yoy/20) if not np.isnan(ded_yoy) else 0)); weight_sum += weights['deduct_yoy']
    sales_margin = safe(row.get('sales_net_margin_pct', np.nan))
    if not np.isnan(sales_margin):
        if sales_margin >= 15:
            score += weights['sales_margin'] * 100
        elif sales_margin >= 8:
            score += weights['sales_margin'] * 60
        else:
            score += weights['sales_margin'] * (100 * sales_margin/15 if sales_margin>0 else 0)
    weight_sum += weights['sales_margin']
    gross = safe(row.get('gross_margin_pct', np.nan))
    score += weights['gross_margin'] * (100 if gross>=35 else max(0, 100*(gross/35) if not np.isnan(gross) else 0)); weight_sum += weights['gross_margin']
    cr = safe(row.get('current_ratio', np.nan))
    score += weights['current_ratio'] * (100 if cr>=1.5 else max(0, 100*(cr/1.5) if not np.isnan(cr) else 0)); weight_sum += weights['current_ratio']
    pb = safe(row.get('pb', np.nan))
    if not np.isnan(pb) and pb>0:
        if pb < 1:
            pb_score = 100
        elif pb < 2:
            pb_score = 60 + 40*(2-pb)/1
        else:
            pb_score = 30
    else:
        pb_score = 50
    score += weights['pb'] * pb_score; weight_sum += weights['pb']
    ev = safe(row.get('ev_ebitda', np.nan))
    if not np.isnan(ev):
        ev_score = 100 if ev < 6 else max(0, 100*(10-ev)/4) if ev<10 else 0
    else:
        ev_score = 50
    score += weights['ev_ebitda'] * ev_score; weight_sum += weights['ev_ebitda']
    if weight_sum == 0:
        return 0.0
    return float(score / weight_sum)

def score_technical(code: str, df_hist: pd.DataFrame) -> Dict[str, Any]:
    info = {'code':code,'tech_score':0.0,'ma5':None,'ma10':None,'ma20':None,'ma30':None,'today_close':None,'today_open':None,'today_change_pct':None,'volume_vs_5':None,'volume_ratio':None,'turnover_rate':None,'amplitude_pct':None,'3m_pct':None,'crossed_ma30':False,'meeting_ma_arrange':False}
    try:
        s_close = df_hist['close'].astype(float)
    except Exception:
        return info
    if len(df_hist) < 30:
        return info
    ma5 = ma(s_close,5).iloc[-1]; ma10 = ma(s_close,10).iloc[-1]; ma20 = ma(s_close,20).iloc[-1]; ma30 = ma(s_close,30).iloc[-1]
    today = df_hist.iloc[-1]; prev = df_hist.iloc[-2]
    today_close = float(today['close']); today_open = float(today['open']); prev_close = float(prev['close'])
    today_change_pct = pct_change(today_close, prev_close) * 100
    amplitude = (float(today['high']) - float(today['low'])) / prev_close * 100 if prev_close!=0 else np.nan
    vol5 = df_hist['volume'].astype(float).rolling(5, min_periods=1).mean().iloc[-1]
    today_vol = float(today['volume']); volume_vs_5 = today_vol/vol5 if vol5>0 else np.nan
    volume_ratio = volume_vs_5
    turnover_rate = float(today.get('turnover_rate', np.nan))
    n63 = min(len(df_hist), 63); start_price = df_hist['close'].astype(float).iloc[-n63]
    pct_3m = pct_change(today_close, start_price)*100 if start_price!=0 else np.nan
    info.update({'ma5':ma5,'ma10':ma10,'ma20':ma20,'ma30':ma30,'today_close':today_close,'today_open':today_open,'today_change_pct':today_change_pct,'volume_vs_5':volume_vs_5,'volume_ratio':volume_ratio,'turnover_rate':turnover_rate,'amplitude_pct':amplitude,'3m_pct':pct_3m})
    score = 0.0; wsum = 0.0
    w_ma = 0.35
    ma_ok = (today_close > ma5 > ma10 > ma20)
    crossed30 = (prev['close'] < ma30) and (today_close > ma30)
    ma_score = 100 if ma_ok else (70 if crossed30 else 0)
    score += w_ma * ma_score; wsum += w_ma
    info['meeting_ma_arrange'] = ma_ok; info['crossed_ma30'] = bool(crossed30)
    w_vol = 0.25; vol_score = 0.0
    if not np.isnan(volume_vs_5) and volume_vs_5 > 1:
        vol_score += 60
    if 1 <= volume_ratio < 1.2:
        vol_score += 20
    if not np.isnan(turnover_rate):
        if 0.05 <= turnover_rate <= 0.10:
            vol_score += 20
        elif 0.08 <= turnover_rate <= 0.12:
            vol_score += 30
    score += w_vol * min(100, vol_score); wsum += w_vol
    w_mom = 0.25; mom_score = 0.0
    if 2 <= today_change_pct <= 5:
        mom_score += 40
    if (today_close / prev_close) > 1.05:
        mom_score += 30
    if (today['low'] / prev_close) > 0.95:
        mom_score += 10
    if today_close > today_open:
        mom_score += 10
    if 3 <= info['amplitude_pct'] <= 5:
        mom_score += 10
    if 0 < info['3m_pct'] < 50:
        mom_score += 10
    score += w_mom * min(100, mom_score); wsum += w_mom
    w_fund = 0.15; fund_score = 0.0
    if volume_vs_5 is not np.nan and volume_vs_5 > 1:
        fund_score += 40
    if not np.isnan(turnover_rate) and (turnover_rate > 0.05):
        fund_score += 40
    score += w_fund * min(100, fund_score); wsum += w_fund
    tech_score = float(score / wsum * 1.0) if wsum>0 else 0.0
    info['tech_score'] = tech_score
    return info

def score_funds_and_heat(row_fin: pd.Series) -> Tuple[float, float]:
    large_net = row_fin.get('large_order_net_inflow', np.nan)
    tradable = row_fin.get('tradable_shares', np.nan)
    funds_score = 50.0
    try:
        if not np.isnan(large_net):
            funds_score = min(100, (large_net / 1e7) * 2)
    except:
        funds_score = 50.0
    vol_turnover_ratio = row_fin.get('today_amount', 0) / tradable if tradable and tradable>0 else 0
    if vol_turnover_ratio > 0.0015:
        funds_score = max(funds_score, 80)
    heat = 0.0
    if row_fin.get('recent_high_30d', False):
        heat += 40
    cons_up = row_fin.get('consecutive_up_days', 0) or 0
    if 2 <= cons_up <=5:
        heat += 30
    forum_rank = row_fin.get('forum_rank', np.nan)
    if not np.isnan(forum_rank) and forum_rank <= 2000:
        heat += 30
    if row_fin.get('institution_ratings_count', 0) >= 3:
        heat += 20
    heat_score = min(100, heat)
    return float(funds_score), float(heat_score)

def compute_overall_scores(df_candidates: pd.DataFrame, hist_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    recs = []
    for _, row in df_candidates.iterrows():
        code = row['code']
        fin_score = score_financials(row)
        df_hist = hist_map.get(code)
        tech_info = score_technical(code, df_hist) if df_hist is not None else {'tech_score':0}
        funds_score, heat_score = score_funds_and_heat(row)
        total = fin_score*WEIGHT_FIN + tech_info['tech_score']*WEIGHT_TECH + funds_score*WEIGHT_FUNDS + heat_score*WEIGHT_HEAT
        rec = row.to_dict()
        rec.update({'fin_score':fin_score,'tech_score':tech_info['tech_score'],'funds_score':funds_score,'heat_score':heat_score,'total_score':total,'tech_meta':tech_info})
        recs.append(rec)
    dfr = pd.DataFrame(recs)
    dfr = dfr.sort_values('total_score', ascending=False).reset_index(drop=True)
    return dfr

def pick_final_8(df_scored: pd.DataFrame, industry_col: str='industry') -> pd.DataFrame:
    selected = []; industry_count = {}
    def mv_bucket(v):
        if v < 100e8: return 'small'
        elif v < 300e8: return 'mid'
        else: return 'large'
    df_pool = df_scored.copy().sort_values('total_score', ascending=False).reset_index(drop=True)
    high = df_pool[df_pool['total_score']>=80]
    pool = pd.concat([high, df_pool[~df_pool.index.isin(high.index)]]).drop_duplicates('code')
    for _, row in pool.iterrows():
        if len(selected) >= 8: break
        ind = row.get(industry_col, '未知')
        if industry_count.get(ind,0) >= 3: continue
        selected.append(row); industry_count[ind] = industry_count.get(ind,0)+1
    if len(selected) < 8:
        remaining = df_pool[~df_pool['code'].isin([r['code'] for r in selected])].head(8-len(selected))
        for _, r in remaining.iterrows():
            selected.append(r)
    df_selected = pd.DataFrame(selected).reset_index(drop=True)
    return df_selected

def format_recommendation_md(df_final: pd.DataFrame, date_str: str, market_env: str) -> str:
    lines = []
    lines.append(f"📈 A股趋势策略精选组合（8只）\n")
    lines.append(f"生成时间：{date_str}")
    lines.append(f"市场环境：{market_env}\n")
    df = df_final.sort_values('total_score', ascending=False).reset_index(drop=True)
    groups = {'首选': df.head(2), '重点': df.iloc[2:5], '关注': df.iloc[5:8]}
    idx = 1
    for label, group in groups.items():
        lines.append(f"{idx}. { '🥇 首选标的（2只）' if idx==1 else ('🥈 重点标的（3只）' if idx==2 else '🥉 关注标的（3只）')} and for r in group.iterrows():
            code = row['code']; name = row.get('name','')
            lines.append(f"【{code} {name}】")
            reasons = []
            if row.get('fin_score',0) >= 80: reasons.append("财务质量较好（盈利/成长/估值匹配）")
            techs = row.get('tech_meta',{})
            if techs.get('meeting_ma_arrange'): reasons.append("均线多头且量能配合")
            if techs.get('crossed_ma30'): reasons.append("今日上穿30日均线，短期突破")
            if row.get('funds_score',0) >= 70: reasons.append("当日资金显著流入/换手活跃")
            reasons = reasons[:3] if reasons else ["符合筛选与评分标准"]
            lines.append("推荐理由：")
            for r in reasons: lines.append(f"- {r}")
            t = row.get('tech_meta',{})
            tech_feat = f"收盘/MA5/MA10/MA20: {t.get('today_close')}/{t.get('ma5')}/{t.get('ma10')}/{t.get('ma20')}; 当日涨幅: {t.get('today_change_pct') if t.get('today_change_pct') is not None else 0:.2f}%"
            lines.append(f"技术特征：{tech_feat}")
            price = row.get('close_price', row.get('today_close', np.nan))
            try:
                tgt_low = round(float(price) * 0.95, 2); tgt_high = round(float(price) * 1.15, 2)
            except:
                tgt_low, tgt_high = 'N/A','N/A'
            lines.append(f"目标区间：{tgt_low} - {tgt_high} 元")
            rp = ["市场系统性风险"]
            if row.get('pb', np.nan) > 1.8: rp.append("估值回撤风险")
            lines.append("风险提示：" + "；".join(rp))
            lines.append("")
        idx += 1
    avg_mv = df_final['total_market_cap'].mean() if 'total_market_cap' in df_final.columns else np.nan
    lines.append("🎯 组合特征分析：")
    lines.append(f"- 平均市值：{round(avg_mv/1e8,2) if not np.isnan(avg_mv) else 'N/A'} 亿元")
    if 'industry' in df_final.columns:
        dist = df_final['industry'].value_counts(normalize=True).to_dict()
        dist_str = ", ".join([f"{k}({int(v*100)}%)" for k,v in dist.items()])
        lines.append(f"- 行业分布：{dist_str}")
    if 'pb' in df_final.columns:
        lines.append(f"- 平均估值：PB {round(df_final['pb'].mean(),2)}")
    break_count = df_final['tech_meta'].apply(lambda x: x.get('crossed_ma30', False)).sum()
    lines.append(f"- 技术状态：{int(break_count)} 只上穿30日均线")
    lines.append("\n⚠️ 风险提示：")
    lines.append("1. 大盘系统性风险")
    lines.append("2. 行业政策变化风险")
    lines.append("3. 个股基本面变化风险")
    lines.append("4. 流动性风险")
    return "\n".join(lines)

def generate_recommendations(df_daily_all: pd.DataFrame, df_fin: pd.DataFrame, date_str: str = None, data_hist_map: Dict[str, pd.DataFrame] = None, market_env: str = "待填") -> Tuple[pd.DataFrame, str]:
    if date_str is None:
        date_str = datetime.date.today().isoformat()
    if 'date' in df_daily_all.columns:
        latest_date = df_daily_all['date'].max()
        df_latest = df_daily_all[df_daily_all['date']==latest_date][['code','close','amount','turnover_rate']]
    else:
        df_latest = df_daily_all[['code','close','amount','turnover_rate']]
    df_candidates = apply_mandatory_filters(df_fin, df_latest)
    if data_hist_map is None:
        data_hist_map = {}
        for code, g in df_daily_all.groupby('code'):
            g_sorted = g.sort_values('date')
            data_hist_map[code] = g_sorted[['date','open','high','low','close','volume','amount','turnover_rate']].reset_index(drop=True)
    df_scored = compute_overall_scores(df_candidates, data_hist_map)
    df_top = df_scored.head(50)
    df_precise = df_top[(df_top['total_score']>=80) | (df_top.index < 20)]
    df_final_candidates = pick_final_8(df_precise)
    md = format_recommendation_md(df_final_candidates, date_str, market_env)
    return df_final_candidates, md

def send_recommendation_after_daily(send_func: Callable[[str,str], None], df_daily_all: pd.DataFrame, df_fin: pd.DataFrame, date_str: str = None, data_hist_map: Dict[str, pd.DataFrame] = None, market_env: str = "待填", title: str = "今日 A股 趋势策略精选组合（8只）") -> None:
    df_final, md = generate_recommendations(df_daily_all, df_fin, date_str=date_str, data_hist_map=data_hist_map, market_env=market_env)
    try:
        send_func(title, md)
    except Exception as e:
        print(f"[recommender] send failed: {e}")
