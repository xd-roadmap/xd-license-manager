import plotly.graph_objects as go


def get_asset_gauge_chart(remaining_months: int, total_months: int = 34):
    """
    미니멀 스타일의 자산 풀 게이지 차트
    """
    used_months = total_months - remaining_months
    pct = remaining_months / total_months  # 0~1

    # 잔여량에 따른 색상 (그라데이션 느낌)
    if pct > 0.6:
        bar_color = "#3B82F6"      # 파랑 (충분)
    elif pct > 0.3:
        bar_color = "#F59E0B"      # 노랑 (주의)
    else:
        bar_color = "#EF4444"      # 빨강 (위험)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=remaining_months,
        delta={
            'reference': total_months,
            'valueformat': '.0f',
            'suffix': "개월 사용됨",
            'decreasing': {'color': "#94A3B8"},
            'increasing': {'color': "#94A3B8"},
        },
        number={
            'suffix': " 개월",
            'font': {'size': 52, 'color': "#1E293B", 'family': "Inter, Arial"},
        },
        title={
            'text': "잔여 자산",
            'font': {'size': 15, 'color': "#64748B", 'family': "Inter, Arial"},
        },
        gauge={
            'axis': {
                'range': [0, total_months],
                'tickwidth': 0,
                'tickcolor': "rgba(0,0,0,0)",
                'tickvals': [0, total_months * 0.3, total_months * 0.6, total_months],
                'ticktext': ['0', f'{int(total_months*0.3)}', f'{int(total_months*0.6)}', f'{total_months}'],
                'tickfont': {'size': 11, 'color': '#94A3B8'},
            },
            'bar': {'color': bar_color, 'thickness': 0.7},
            'bgcolor': "#F1F5F9",
            'borderwidth': 0,
            'steps': [
                {'range': [0, total_months * 0.3], 'color': '#FEE2E2'},
                {'range': [total_months * 0.3, total_months * 0.6], 'color': '#FEF3C7'},
                {'range': [total_months * 0.6, total_months], 'color': '#DBEAFE'},
            ],
            'threshold': {
                'line': {'color': bar_color, 'width': 3},
                'thickness': 0.85,
                'value': remaining_months,
            },
            'shape': "angular",
        },
    ))

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={'family': "Inter, Arial"},
        margin=dict(l=30, r=30, t=30, b=10),
        height=280,
    )

    return fig


def get_usage_bar_chart(remaining_months: int, total_months: int = 34):
    """
    사용/잔여를 보여주는 수평 프로그레스 바 형태 차트
    """
    used = total_months - remaining_months
    pct_remaining = remaining_months / total_months * 100
    pct_used = used / total_months * 100

    fig = go.Figure()

    # 잔여 (파랑)
    fig.add_trace(go.Bar(
        name="잔여",
        x=[remaining_months],
        y=[""],
        orientation='h',
        marker_color="#3B82F6",
        marker_line_width=0,
        text=f"잔여 {remaining_months}개월 ({pct_remaining:.0f}%)",
        textposition="inside",
        insidetextanchor="middle",
        textfont={'size': 13, 'color': 'white', 'family': 'Inter, Arial'},
        hovertemplate="잔여: %{x}개월<extra></extra>",
    ))

    # 사용됨 (연회색)
    fig.add_trace(go.Bar(
        name="사용됨",
        x=[used],
        y=[""],
        orientation='h',
        marker_color="#E2E8F0",
        marker_line_width=0,
        text=f"사용 {used}개월 ({pct_used:.0f}%)" if used > 0 else "",
        textposition="inside",
        insidetextanchor="middle",
        textfont={'size': 13, 'color': '#94A3B8', 'family': 'Inter, Arial'},
        hovertemplate="사용됨: %{x}개월<extra></extra>",
    ))

    fig.update_layout(
        barmode="stack",
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        height=60,
        xaxis=dict(visible=False, range=[0, total_months]),
        yaxis=dict(visible=False),
    )

    return fig
