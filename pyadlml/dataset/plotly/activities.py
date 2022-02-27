import functools

import plotly.figure_factory as ff
from .util import _style_colorbar, STRFTIME_DATE
import plotly.express as px
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects
import plotly.graph_objects as go
from plotly.colors import n_colors
from plotly.subplots import make_subplots

from pyadlml.dataset import START_TIME, ACTIVITY, TIME, END_TIME
from pyadlml.dataset.stats.activities import activities_duration_dist, \
    activities_count, activity_duration, activities_dist, \
    activities_transitions
from pyadlml.dataset.util import get_sorted_index, check_scale, check_order, activity_order_by


def density(df_act: pd.DataFrame = None, df_density: pd.DataFrame = None,
            dt=None, n=1000, height=350, order='alphabetical', show_meanline=True) -> plotly.graph_objects.Figure:
    """
    https://plotly.com/python/violin/

    for one day plot the activity distribution over the day
    - sample uniform from each interval   
    """

    title = 'Density'

    if df_act is None:
        df = df_density
    else:
        df = activities_dist(df_act.copy(), n=n, dt=dt)

    acts = np.flip(activity_order_by(df, rule=order))

    colors = n_colors('rgb(5, 200, 200)', 'rgb(200, 10, 10)', len(acts), colortype='rgb')
    fig = go.Figure()

    for activity, color in zip(acts, colors):
        data_line = df[df[ACTIVITY] == activity][TIME]
        data_line = pd.to_datetime(data_line)
        fig.add_trace(go.Violin(x=data_line, line_color=color, name=activity,
                                hoverinfo='skip'))

    # Set custom x-axis labels
    fig.update_xaxes(tickformat="%H:%M", nticks=24, tickangle=-45,
                     title_text='Time', range=[
                        data_line.iloc[0].floor('D'),
                        data_line.iloc[0].ceil('D')
                     ])
    fig.update_traces(orientation='h', side='positive', width=1, points=False)
    fig.update_layout(xaxis_showgrid=True, xaxis_zeroline=False, showlegend=False,
                      height=height, margin=dict(l=0, r=0, b=0, t=30, pad=0))
    _set_compact_title(fig, title=title)
    if show_meanline:
        fig.update_traces(meanline_visible=True)

    return fig

@check_scale
def _scale_xaxis(fig, scale, values) -> None:
    if scale == 'log':
        r_min = np.floor(np.log10(values.min()))
        r_max = np.ceil(np.log10(values.max()))
        fig.update_xaxes(type="log", range=[r_min, r_max])  # log range: 10^r_min=1, 10^r_max=100000

@check_scale
def violin_duration(df_act, x_scale='linear', no_title=False, height=350) -> plotly.graph_objects.Figure:
    df = activities_duration_dist(df_act)
    # Add column for hover display of datapoints later
    df[START_TIME] = df_act[START_TIME].dt.strftime('%c')
    df[END_TIME] = df_act[END_TIME].dt.strftime('%c')

    fig = px.violin(df, y='activity', x='minutes', box=False, orientation='h', points='outliers',
                    hover_data=[START_TIME, END_TIME, 'minutes'])

    if not no_title:
        fig.update_layout(title='Activity distribution')
    _scale_xaxis(fig, x_scale, df['minutes'])
    fig.update_yaxes(title=None, visible=False, showticklabels=False)
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=0, pad=0), height=height)
    return fig

def _set_compact_title(fig: plotly.graph_objects.Figure, title: str) -> None:
    fig.update_layout(title=dict(
        text=title,
        yanchor='top',
        xanchor='left',
        pad={'t': 2, 'l': -20}
    ))

@check_scale
def boxplot_duration(df_act, scale='linear', height=350, order='alphabetical') -> plotly.graph_objects.Figure:
    """ Plot a boxplot of activity durations (mean) max min
    """
    title = 'Duration'

    df = activities_duration_dist(df_act)
    act_order = activity_order_by(df, rule=order)

    # Add column for hover display of datapoints later
    df[START_TIME] = df_act[START_TIME]
    df[END_TIME] = df_act[END_TIME]
    df['total_time'] = df['total_time'].apply(str)

    fig = px.box(df, y="activity", x='minutes', orientation='h',
                 category_orders={'activity': act_order},
                 notched=False, points='all',
                 hover_data=[START_TIME, END_TIME, 'minutes', 'total_time'])

    _set_compact_title(fig, title)
    _scale_xaxis(fig, scale, df['minutes'])

    fig.update_yaxes(title=None, visible=False, showticklabels=False)
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=30, pad=0), height=height)
    hover_template = 'Minutes=%{x}=%{customdata[2]}<br>Activity=%{y}<br>'\
                     + 'Start_time=%{customdata[0]|' + STRFTIME_DATE + '}<br>'\
                     + 'End_time=%{customdata[1]|' + STRFTIME_DATE + '}<extra></extra>'
    fig.data[0].hovertemplate = hover_template
    return fig



@check_scale
def bar_cum(df_act, scale='linear', height=350, order='alphabetical', no_title=False) -> plotly.graph_objects.Figure:
    """ Plots the cumulated activities durations in a histogram for each activity
    """

    title = 'Duration'
    x_label = 'minutes' if scale == 'linear' else 'log minutes'
    df = activity_duration(df_act.copy())
    df = df.loc[get_sorted_index(df, order), :]

    # Create hoverstrings to represent the timedelta
    format_td = lambda x: ':'.join(str(x).split(':')[:-1]) \
                         +':' + str(x).split(':')[-1][:5]
    df['td'] = pd.to_timedelta(df['minutes'], unit='m')\
                 .apply(format_td)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['minutes'],
                         customdata=df['td'],
                         hovertemplate="%{y} with %{customdata}<extra></extra>",
                         y=df[ACTIVITY],
                         orientation='h',
                         name='duration'))

    _set_compact_title(fig, title)
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=30, pad=0), height=height)
    if isinstance(order, list) or isinstance(order, np.ndarray):
        fig.update_yaxes(title=None, categoryorder='array', categoryarray=np.flip(order))
    else:
        fig.update_yaxes(title=None)
    fig.update_xaxes(title=x_label)
    if scale == 'log':
        fig.update_xaxes(type='log')
    return fig

@check_scale
def bar_count(df_act, scale='linear', height=350, no_title=False, order='count') -> plotly.graph_objects.Figure:
    """ Plots the activities durations against each other
    """
    title ='Counts'
    col_label = 'occurrence'
    xlabel = 'log count' if scale == 'log' else 'count'

    df = activities_count(df_act.copy())
    act_order = activity_order_by(df_act, rule=order)


    fig = px.bar(df, y='activity',
                 category_orders={'activity': act_order},
                 x='occurrence',
                 orientation='h')

    _set_compact_title(fig, title)

    fig.update_layout(margin=dict(l=0, r=0, b=0, t=30, pad=0), height=height)
    fig.update_yaxes(title=None)
    fig.update_xaxes(title=xlabel)
    if scale == 'log':
        fig.update_xaxes(type='log')
    return fig

@check_scale
def heatmap_transitions(df_act, scale='linear', height=350, order='alphabetical') -> plotly.graph_objects.Figure:
    """
    """
    title = 'Transitions'
    cbarlabel = 'count' if scale == 'linear' else 'log count'

    # get the list of cross tabulations per t_window
    df = activities_transitions(df_act)
    act_lst = list(df.columns)


    act_order = activity_order_by(df_act, rule=order)
    df = df[act_order]          # change order of rows
    df = df.reindex(act_order)  # change order of columns
    z = df.values if scale == 'linear' else np.log(df.values)

    fig = go.Figure(data=go.Heatmap(
        z=z.T,
        x=act_order,
        y=act_order,
        hovertemplate='"%{x}" then "%{y}" %{z} times<extra></extra>',
        colorscale='Viridis',
        hoverongaps=False))

    if scale == 'log':
        fig.data[0].hovertemplate = '"%{x}" then "%{y}" %{customdata} times<extra></extra>'
        cd = np.array([df.values.T])
        fig['data'][0]['customdata'] = np.moveaxis(cd, 0, -1)

    _set_compact_title(fig, title)

    fig.update_xaxes(tickangle=45)
    fig.update_yaxes(visible=False, showticklabels=False)
    fig.update_layout(margin=dict(l=0, r=0, b=0, t=30, pad=0), height=height)
    _style_colorbar(fig, cbarlabel)
    return fig
