import panel as pn
import logging
from panel.config import panel_extension
import dask_cudf

from .core_chart import BaseChart
from ...layouts import chart_view

css = """
.dataframe table{
  border: none;
}

.panel-df table{
    width: 100%;
    border-collapse: collapse;
    border: none;
}
.panel-df td{
    white-space: nowrap;
    overflow: auto;
    text-overflow: ellipsis;
}
"""

pn.config.raw_css += [css]


class ViewDataFrame:
    chart_type: str = "view_dataframe"
    _height: int = 0
    columns = None
    _width: int = 0
    chart = None
    source = None
    use_data_tiles = False
    _initialized = False

    def __init__(
        self, columns=None, width=400, height=400, force_computation=False
    ):
        self.columns = columns
        self._width = width
        self._height = height
        self.force_computation = force_computation

    @property
    def name(self):
        return self.chart_type

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value
        if self.chart is not None:
            self.update_dimensions(width=value)

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = value
        if self.chart is not None:
            self.update_dimensions(height=value)

    def initiate_chart(self, dashboard_cls):
        if isinstance(dashboard_cls._data, dask_cudf.core.DataFrame):
            if self.force_computation:
                self.generate_chart(dashboard_cls._data.compute())
            else:
                print(
                    "displaying only 1st partitions top 1000 rows for ",
                    "view_dataframe - dask_cudf to avoid partition based ",
                    "computation use force_computation=True for viewing ",
                    "top-level view of entire DataFrame. ",
                    "Warning - would slow the dashboard down significantly",
                )
                self.generate_chart(dashboard_cls._data.head(1000))
        else:
            self.generate_chart(dashboard_cls._data)

    def generate_chart(self, data):
        if self.columns is None:
            self.columns = list(data.columns)
        style = {
            "width": "100%",
            "height": "100%",
            "overflow-y": "auto",
            "font-size": "0.5vw",
            "overflow-x": "auto",
        }

        html_pane = pn.pane.HTML(data[self.columns], style=style)
        self.chart = pn.Column(html_pane, css_classes=["panel-df"])
        self.chart.sizing_mode = "scale_both"

    def _repr_mimebundle_(self, include=None, exclude=None):
        view = self.view()
        if self._initialized and panel_extension._loaded:
            return view._repr_mimebundle_(include, exclude)

        if self._initialized is False:
            logging.warning(
                "dashboard has not been initialized."
                "Please run cuxfilter.dashboard.Dashboard([...charts])"
                " to view this object in notebook"
            )

        if panel_extension._loaded is False:
            logging.warning(
                "notebooks assets not loaded."
                "Please run cuxfilter.load_notebooks_assets()"
                " to view this object in notebook"
            )
            if isinstance(view, pn.Column):
                return view.pprint()
        return None

    def view(self):
        return chart_view(self.chart, width=self.width)

    def reload_chart(self, data, patch_update: bool):
        if isinstance(data, dask_cudf.core.DataFrame):
            if self.force_computation:
                self.chart[0].object = data[self.columns].compute()
            else:
                self.chart[0].object = data[self.columns].head(1000)
        else:
            self.chart[0].object = data[self.columns]

    def update_dimensions(self, width=None, height=None):
        """
        Parameters
        ----------

        Ouput
        -----
        """
        if width is not None:
            self.chart.width = width
        if height is not None:
            self.chart.height = height

    def query_chart_by_range(
        self, active_chart: BaseChart, query_tuple, data, query=""
    ):
        """
        Description:

        -------------------------------------------
        Input:
            1. active_chart: chart object of active_chart
            2. query_tuple: (min_val, max_val) of the query [type: tuple]
            3. datatile: None in case of Gpu Geo Scatter charts
        -------------------------------------------

        Ouput:
        """
        min_val, max_val = query_tuple
        final_query = (
            str(min_val) + "<=" + active_chart.x + "<=" + str(max_val)
        )
        if len(query) > 0:
            final_query += " and " + query
        self.reload_chart(
            data.query(final_query), False,
        )

    def query_chart_by_indices(
        self, active_chart: BaseChart, old_indices, new_indices, data, query=""
    ):
        """
        Description:

        -------------------------------------------
        Input:
            1. active_chart: chart object of active_chart
            2. query_tuple: (min_val, max_val) of the query [type: tuple]
            3. datatile: None in case of Gpu Geo Scatter charts
        -------------------------------------------

        Ouput:
        """
        if "" in new_indices:
            new_indices.remove("")
        if len(new_indices) == 0:
            # case: all selected indices were reset
            # reset the chart
            self.reload_chart(data, False)
        elif len(new_indices) == 1:
            final_query = active_chart.x + "==" + str(float(new_indices[0]))
            if len(query) > 0:
                final_query += " and " + query
            # just a single index
            self.reload_chart(
                data.query(final_query), False,
            )
        else:
            new_indices_str = ",".join(map(str, new_indices))
            final_query = active_chart.x + " in (" + new_indices_str + ")"
            if len(query) > 0:
                final_query += " and " + query
            self.reload_chart(
                data.query(final_query), False,
            )
