from io import BytesIO
import matplotlib
from matplotlib import pyplot as plt
from typing import Literal
import asyncio
from functools import partial

matplotlib.use('Agg')  # must set before other imports to ensure correct backend


def pie(data: dict[str, int], *args, **kwargs) -> BytesIO:
    """
    plot data to pie chart

    :param data: {labels: Size of slice}
    :param args: TODO: allow args use in chart
    :param kwargs: additional matplot configuration
    :return: Pie chart BytesIO
    """
    fig, ax = plt.subplots()
    ax.pie(
        x = list(data.values()),
        labels = list(data.keys()), autopct = kwargs.get("autopct") or "%1.0f%%",
        textprops = kwargs.get("textprops") or {"color": "w", "size": "large", "weight": "heavy"},
        pctdistance = kwargs.get("pctdistance") or 0.85)
    b = BytesIO()
    plt.savefig(b, format = kwargs.get("format") or "png", transparent = kwargs.get("transparent") or True)
    plt.close()
    b.seek(0)
    return b

async def graph(graph_type: Literal["pie"], data: dict[str, int], *args, **kwargs) -> BytesIO | None:
    if not (graph_type or data):
        return
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(GRAPH_TYPES[graph_type], data, *args, **kwargs))

GRAPH_TYPES = {
    "pie": pie
}
