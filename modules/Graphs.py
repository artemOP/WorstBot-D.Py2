from io import BytesIO
import matplotlib
from matplotlib import pyplot as plt
import typing
import asyncio
from functools import partial

matplotlib.use('Agg')  # must set before other imports to ensure correct backend


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
        b = BytesIO()
        plt.savefig(b, format = kwargs.get("format") or "png", transparent = kwargs.get("transparent") or True)
        plt.close()
        b.seek(0)
        plots.append(b)
    return plots

def bar(data: dict[str, int], *args, **kwargs) -> list[BytesIO]:
    """
    Plot data to bar chart

    :param data: {label: bar size}
    :param args:
    :param kwargs:
    :return: Bar chart BytesIO
    """
    plots = []
    for _ in range(2):
        fig, ax = plt.subplots()  # type: plt.Figure, plt.Axes
        ax.bar(data.keys(), data.values())
        b = BytesIO()
        plt.savefig(b, format = kwargs.get("format") or "png", transparent = kwargs.get("transparent") or True)
        plt.close()
        b.seek(0)
        plots.append(b)
    return plots

async def graph(graph_type: typing.Literal["pie", "bar"], loop: asyncio.AbstractEventLoop, data: dict[str, int], *args, **kwargs) -> list[BytesIO] | None:
    if not (graph_type or data):
        return
    return await loop.run_in_executor(None, partial(GRAPH_TYPES[graph_type], data, *args, **kwargs))

GRAPH_TYPES = {
    "pie": pie,
    "bar": bar
}
