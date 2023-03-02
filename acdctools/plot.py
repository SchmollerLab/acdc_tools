import sys
from typing import Union, Iterable

import pandas as pd
import numpy as np

import matplotlib
import matplotlib.colors
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

from . import widgets, _core

def matplotlib_cmap_to_lut(
        cmap: Union[Iterable, matplotlib.colors.Colormap, str], 
        n_colors: int=256
    ):
    if isinstance(cmap, str):
        cmap = plt.get_cmap(cmap)
    
    rgbs = [cmap(i) for i in np.linspace(0,1,n_colors)]
    lut = np.zeros((256, 4), dtype=np.uint8)
    for i, rgb in enumerate(rgbs):
        lut[i] = [int(c*255) for c in rgb]
    return lut


def imshow(
        *images: np.ndarray, 
        points_coords: np.ndarray=None, 
        hide_axes: bool=True, 
        lut: Union[Iterable, matplotlib.colors.Colormap, str]=None, 
        autoLevels: bool=True,
        autoLevelsOnScroll: bool=False,
        block: bool=True,
    ):
    if lut is None:
        lut = matplotlib_cmap_to_lut('viridis')

    if isinstance(lut, str):
        lut = matplotlib_cmap_to_lut(lut)

    if isinstance(lut, np.ndarray):
        luts = [lut]*len(images)
    else:
        luts = lut
    
    if luts is not None:
        for l in range(len(luts)):
            if not isinstance(luts[l], str):
                continue
            
            luts[l] = matplotlib_cmap_to_lut(luts[l])
    
    app = widgets.setupApp()
    win = widgets.ImShow()
    if app is not None:
        win.app = app
    win.setupMainLayout()
    win.setupStatusBar()
    win.setupGraphicLayout(*images, hide_axes=hide_axes)
    win.showImages(
        *images, luts=luts, autoLevels=autoLevels, 
        autoLevelsOnScroll=autoLevelsOnScroll
    )
    if points_coords is not None:
        win.drawPoints(points_coords)
    win.run(block=block)
    return win

def _add_colorbar_axes(
        ax: plt.Axes, im: matplotlib.image.AxesImage, size='5%', pad=0.07,
        label=''
    ):
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    cbar = plt.colorbar(im, cax=cax)
    if label:
        cbar.set_label(label)

def _get_groups_data(
        df: pd.DataFrame, x: str, z: str, grouping: str, bin_size: int=None, 
        normalize_x: bool=True
    ):
    grouped = df.groupby(grouping)
    dfs = []
    max_n_decimals = None
    min_norm_bin_size = None
    if normalize_x:
        min_dx = min([
            group_df[x].diff().abs().min() for _, group_df in grouped
        ])
        max_n_decimals = 0
        min_norm_bin_size = np.inf
        for name, group_df in grouped:
            group_xx = group_df[x]-group_df[x].min()
            group_cols = {col:f'{col}_{name}' for col in group_df.columns}
            group_df = group_df.rename(columns=group_cols)
            max_xx = group_xx.max()
            norm_dx = min_dx/max_xx
            min_dx_rounded = _core.round_to_significant(norm_dx, 2)
            n_decimals = len(str(min_dx_rounded).split('.')[1])
            if n_decimals > max_n_decimals:
                max_n_decimals = n_decimals
            norm_xx = (group_xx/max_xx).round(n_decimals)
            norm_xx_perc = norm_xx*100
            if bin_size is not None:
                norm_bin_size = (bin_size/max_xx).round(n_decimals)*100
                if norm_bin_size < min_norm_bin_size:
                    min_norm_bin_size = norm_bin_size
            group_df['x'] = norm_xx_perc
            dfs.append(group_df.set_index('x')[[f'{z}_{name}']])
    else:
        for name, group_df in grouped:
            group_cols = {col:f'{col}_{name}' for col in group_df.columns}
            group_df = group_df.rename(columns=group_cols)
            dfs.append(group_df.set_index(x)[[f'{z}_{name}']])
            
    df_data = pd.concat(dfs, names=[x], axis=1).sort_index()

    if min_norm_bin_size is not None:
        bin_size = min_norm_bin_size

    if bin_size is not None:
        order_of_magnitude = 1
        if max_n_decimals is not None:
            # Remove 2 because we work with percentage
            n_decimals = max_n_decimals - 2
            order_of_magnitude = 10**n_decimals
            df_data = df_data.reset_index()
            df_data['x_int'] = (df_data['x']*order_of_magnitude).astype(int)
            df_data = df_data.set_index('x_int').drop(columns='x')
            bin_size = int(bin_size*order_of_magnitude)

        df_data.index = pd.to_datetime(df_data.index)
        rs = f'{bin_size}ns'
        df_data = df_data.resample(rs, label='right').mean()
        df_data.index = df_data.index.astype(np.int64)/order_of_magnitude

    data = df_data.fillna(0).values.T
    xx = df_data.index

    return data, xx

def heatmap(
        data: Union[pd.DataFrame, np.ndarray], 
        x: str='',  
        z: str='',
        y_grouping: Union[str, tuple[str]]='',
        normalize_x: bool=True,
        x_bin_size: int=None,
        z_min: Union[int, float]=None,
        z_max: Union[int, float]=None,
        group_height: int=1,
        colorbar_pad: float= 0.07,
        colorbar_size: float=0.05,
        colorbar_label: str='',
        ax: plt.Axes=None,
        fig: plt.Figure=None,
        backend: str='matplotlib',
        block: bool=False
    ):
    x = 'x' if not x else x
    y_grouping = 'groups' if not y_grouping else y_grouping
    z = 'x' if not z else z
    
    if ax is None:
        fig, ax = plt.subplots()

    if isinstance(data, pd.DataFrame):
        if isinstance(y_grouping, str):
            y_cols = (y_grouping,)
        else:
            y_cols = y_grouping
        data = data[[*y_cols, x, z]]
        data, xx = _get_groups_data(
            data, x, z, grouping=y_grouping, normalize_x=normalize_x,
            bin_size=x_bin_size
        )
    
    if z_min is None:
        z_min = np.nanmin(data)
    
    if z_max is None:
        z_max = np.nanmax(data)
    
    if group_height > 1:
        data = np.repeat(data, [group_height]*len(data), axis=0)

    im = ax.imshow(data, vmin=z_min, vmax=z_max)
    ax.set_xlabel(x)
    ax.set_ylabel(y_grouping)
    # ax.set_yticks(np.arange(0,len(data)*group_height, group_height))
    
    _size_perc = f'{int(colorbar_size*100)}%'
    _add_colorbar_axes(
        ax, im, size=_size_perc, pad=colorbar_pad, label=colorbar_label
    )
    
    if block:
        plt.show()
    else:
        return ax