from io import BytesIO
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
import typing
import asyncio
from functools import partial
from random import random

matplotlib.use('Agg')  # must set before other imports to ensure correct backend

def save_fig(**kwargs) -> BytesIO:
    b = BytesIO()
    plt.savefig(b, format = kwargs.get("format") or "png", transparent = kwargs.get("transparent") or True)
    b.seek(0)
    return b

def pie(data: dict[str, int], *args, **kwargs) -> list[BytesIO]:
    """
    plot data to pie chart

    :param data: {labels: Size of slice}
    :param args: TODO: allow args use in chart
    :param kwargs: additional matplot configuration
    :return: Pie chart BytesIO
    """
    textprops = kwargs.get("textprops") or [{"color": "k", "size": "large", "weight": "heavy"}, {"color": "w", "size": "large", "weight": "heavy"}]
    plots = []
    for i in range(2):
        fig, ax = plt.subplots()
        ax.pie(
            x = list(data.values()),
            labels = list(data.keys()),
            autopct = kwargs.get("autopct") or "%1.0f%%",
            textprops = textprops[i],
            pctdistance = kwargs.get("pctdistance") or 0.85)
        plots.append(save_fig(**kwargs))
        plt.close()
    return plots

def bar(data: dict[str, int], *args, **kwargs) -> list[BytesIO]:
    """
    Plot data to bar chart

    :param data: {label: bar size}
    :param args:
    :param kwargs:
    :return: Bar chart BytesIO
    """
    plt_props = kwargs.get("plt_props") or [{"label_colour": "black", "bg_colour": "white"}, {"label_colour": "white", "bg_colour": "black"}]
    fig, ax = plt.subplots()  # type: plt.Figure, plt.Axes
    ax.bar(data.keys(), data.values(), color = [[random(), random(), random()] for _ in data])
    ax.yaxis.set_major_locator(MaxNLocator(integer = True))
    fig.autofmt_xdate()
    plots = []
    for i in range(2):
        ax.tick_params(colors = plt_props[i]["label_colour"])
        fig.set_facecolor(plt_props[i]["bg_colour"])
        plots.append(save_fig(**kwargs))
    plt.close()
    return plots

def line(data: dict[str, int], *args, **kwargs) -> list[BytesIO]:
    """
    Plot data to line chart

    :param data: {label: line size}
    :param args:
    :param kwargs:
    :return: Line chart BytesIO
    """
    plt_props = kwargs.get("plt_props") or [{"label_colour": "black", "bg_colour": "white"}, {"label_colour": "white", "bg_colour": "black"}]
    fig, ax = plt.subplots()  # type: plt.Figure, plt.Axes
    ax.plot(data.keys(), data.values(), color = [[random(), random(), random()] for _ in data])
    ax.yaxis.set_major_locator(MaxNLocator(integer = True))
    fig.autofmt_xdate()
    plots = []
    for i in range(2):
        ax.tick_params(colors = plt_props[i]["label_colour"])
        fig.set_facecolor(plt_props[i]["bg_colour"])
        plots.append(save_fig(**kwargs))
    plt.close()
    return plots

async def graph(graph_type: typing.Literal["pie", "bar"], loop: asyncio.AbstractEventLoop, data: dict[str, int], *args, **kwargs) -> list[BytesIO] | None:
    if not (graph_type or data):
        return
    return await loop.run_in_executor(None, partial(GRAPH_TYPES[graph_type], data, *args, **kwargs))

GRAPH_TYPES = {
    "pie": pie,
    "bar": bar,
    "line": line
}
