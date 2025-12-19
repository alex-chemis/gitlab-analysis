from scripts.common.plot import barh_chart
import matplotlib.pyplot as plt
import numpy as np


def plot_trends(trends, out):
    trends = sorted(trends, key=lambda x: x["trend"], reverse=True)
    labels = [t["language"] for t in trends]
    values = [t["trend"] for t in trends]

    barh_chart(
        labels,
        values,
        out,
        title="Тренды популярности языков (наклон временного ряда)",
        xlabel="Рост / спад"
    )

def plot_timeseries_absolute(series, months, out, forecast=0):
    fig = plt.figure(figsize=(12, 8))

    last_month = months[-1]

    for lang, ys in series.items():
        plt.plot(months, ys, label=lang)

        if forecast > 0 and len(ys) >= 4:
            y_future = rolling_forecast(ys, forecast)
            future_months = [
                f"+{i+1}" for i in range(forecast)
            ]

            plt.plot(
                [months[-1]] + future_months,
                [ys[-1]] + list(y_future),
                linestyle="--",
                alpha=0.6
            )

    plt.xlabel("Месяц")
    plt.ylabel("Число проектов")
    plt.title("Популярность языков во времени (прогноз пунктиром)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def plot_timeseries_share(series, months, out, forecast=0):
    fig = plt.figure(figsize=(12, 8))

    data = np.array(list(series.values()))

    if forecast > 0:
        futures = []
        for ys in data:
            futures.append(rolling_forecast(ys, forecast))
        data = np.hstack([data, np.array(futures)])

    totals = data.sum(axis=0)
    shares = data / totals

    all_months = months + [f"+{i+1}" for i in range(forecast)]

    for i, lang in enumerate(series.keys()):
        plt.plot(all_months[:len(months)], shares[i][:len(months)], label=lang)
        if forecast > 0:
            plt.plot(
                all_months[len(months)-1:],
                shares[i][len(months)-1:],
                linestyle="--",
                alpha=0.6
            )

    plt.xlabel("Месяц")
    plt.ylabel("Доля проектов")
    plt.title("Доля языков во времени (прогноз пунктиром)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def linear_forecast(y, steps, window=6, damping=0.6):
    y = np.array(y[-window:])

    # локальные изменения
    deltas = np.diff(y)
    avg_delta = deltas.mean()

    forecast = []
    last = y[-1]
    delta = avg_delta

    for _ in range(steps):
        delta *= damping          # затухание импульса
        last = last + delta
        forecast.append(max(last, 0))

    return np.array(forecast)

def rolling_forecast(y, steps, window_size=8):
    forecast = []
    series = list(y)
    for i in range(steps):
        x_window = np.arange(len(series) - window_size, len(series))
        y_window = np.array(series[-window_size:])
        coef = np.polyfit(x_window, y_window, 1)
        y_next = np.polyval(coef, len(series))
        forecast.append(y_next)
        series.append(y_next)
    return np.array(forecast)


