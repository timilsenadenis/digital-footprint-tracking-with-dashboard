"""
charts.py — Server-side Plotly chart generators (optional)
Use these if you want to render charts as static images or JSON on the server.
The dashboard.html uses client-side Plotly instead, but these helpers
are useful for exporting reports or generating chart data via the API.
"""

import json


def _base_layout(title="", **kwargs):
    layout = {
        "margin":        {"t": 40, "r": 20, "b": 50, "l": 60},
        "paper_bgcolor": "white",
        "plot_bgcolor":  "#fafafa",
        "font":          {"family": "Arial, sans-serif", "size": 12},
        "showlegend":    False,
    }
    if title:
        layout["title"] = {"text": title, "font": {"size": 16}}
    layout.update(kwargs)
    return layout


def daily_activity_chart(rows):
    """Bar + line chart showing daily visits and time online."""
    days         = [str(r["day"]) for r in rows]
    visits       = [r.get("total_visits", 0) for r in rows]
    minutes      = [round((r.get("total_time_sec") or 0) / 60) for r in rows]

    return {
        "data": [
            {
                "type": "bar", "name": "Visits",
                "x": days, "y": visits,
                "marker": {"color": "#4f46e5", "opacity": 0.85},
            },
            {
                "type": "scatter", "name": "Minutes online",
                "x": days, "y": minutes,
                "mode": "lines+markers", "yaxis": "y2",
                "line": {"color": "#10b981", "width": 2},
                "marker": {"size": 5, "color": "#10b981"},
            },
        ],
        "layout": _base_layout(
            title="Daily Activity",
            yaxis={"title": "Visits", "gridcolor": "#e5e7eb"},
            yaxis2={"title": "Minutes", "overlaying": "y",
                    "side": "right", "gridcolor": "#e5e7eb"},
            showlegend=True,
            bargap=0.3,
        ),
    }


def category_pie_chart(rows):
    """Donut chart showing visit distribution by category."""
    return {
        "data": [{
            "type": "pie",
            "labels": [r.get("name", "Other") for r in rows],
            "values": [r.get("visits", 0) for r in rows],
            "marker": {"colors": [r.get("color_hex", "#888") for r in rows]},
            "hole": 0.42,
            "textinfo": "label+percent",
        }],
        "layout": _base_layout(title="Category Breakdown"),
    }


def top_domains_chart(rows, limit=10):
    """Horizontal bar chart of top visited domains."""
    top     = rows[:limit]
    domains = [r.get("domain", "") for r in reversed(top)]
    visits  = [r.get("visits", 0) for r in reversed(top)]

    return {
        "data": [{
            "type": "bar", "orientation": "h",
            "y": domains, "x": visits,
            "marker": {"color": "#4f46e5", "opacity": 0.8},
        }],
        "layout": _base_layout(
            title="Top Domains",
            margin={"t": 40, "r": 20, "b": 40, "l": 140},
            xaxis={"gridcolor": "#e5e7eb"},
        ),
    }


def heatmap_chart(rows):
    """Activity heatmap: day of week × hour of day."""
    DAYS  = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    HOURS = [f"{h}:00" for h in range(24)]
    z     = [[0] * 24 for _ in range(7)]

    for r in rows:
        d = int(r.get("day_of_week", 0))
        h = int(r.get("hour_of_day", 0))
        if 0 <= d < 7 and 0 <= h < 24:
            z[d][h] = r.get("visit_count", 0)

    return {
        "data": [{
            "type": "heatmap",
            "z": z, "x": HOURS, "y": DAYS,
            "colorscale": [[0, "#eef2ff"], [0.5, "#6366f1"], [1, "#312e81"]],
            "showscale": True,
        }],
        "layout": _base_layout(
            title="Activity Heatmap",
            margin={"t": 40, "r": 80, "b": 60, "l": 50},
            xaxis={"tickangle": -45},
        ),
    }


def keyword_frequency_chart(rows, limit=20):
    """Horizontal bar showing most searched keywords."""
    top      = rows[:limit]
    keywords = [r.get("keyword", "") for r in reversed(top)]
    freqs    = [r.get("frequency", 0) for r in reversed(top)]

    return {
        "data": [{
            "type": "bar", "orientation": "h",
            "y": keywords, "x": freqs,
            "marker": {"color": "#10b981", "opacity": 0.85},
        }],
        "layout": _base_layout(
            title="Top Search Keywords",
            margin={"t": 40, "r": 20, "b": 40, "l": 110},
            xaxis={"gridcolor": "#e5e7eb"},
        ),
    }


def social_platform_chart(rows):
    """Grouped bar chart for social platform actions."""
    platforms = [r.get("platform", "") for r in rows]

    return {
        "data": [
            {
                "type": "bar", "name": "Posts",
                "x": platforms, "y": [r.get("posts", 0) for r in rows],
                "marker": {"color": "#4f46e5"},
            },
            {
                "type": "bar", "name": "Likes",
                "x": platforms, "y": [r.get("likes", 0) for r in rows],
                "marker": {"color": "#10b981"},
            },
            {
                "type": "bar", "name": "Scrolls",
                "x": platforms, "y": [r.get("scrolls", 0) for r in rows],
                "marker": {"color": "#f59e0b"},
            },
        ],
        "layout": _base_layout(
            title="Social Media Actions",
            barmode="group",
            showlegend=True,
            yaxis={"gridcolor": "#e5e7eb"},
        ),
    }


def app_usage_chart(rows, limit=10):
    """Horizontal bar of top app usage by minutes."""
    top      = rows[:limit]
    apps     = [r.get("app_name", "") for r in reversed(top)]
    minutes  = [round((r.get("total_sec") or 0) / 60) for r in reversed(top)]

    return {
        "data": [{
            "type": "bar", "orientation": "h",
            "y": apps, "x": minutes,
            "marker": {"color": "#8b5cf6", "opacity": 0.85},
        }],
        "layout": _base_layout(
            title="App Usage (minutes)",
            margin={"t": 40, "r": 20, "b": 40, "l": 130},
            xaxis={"title": "Minutes", "gridcolor": "#e5e7eb"},
        ),
    }
