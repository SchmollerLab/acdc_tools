import traceback
import sys
from typing import Union, Iterable

import pandas as pd
import numpy as np

import matplotlib
import matplotlib.colors
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

from . import widgets, _core, error_below, error_close

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

def _raise_non_unique_groups(grouping, dfs, groups_xx):
    groups_with_duplicates = {}
    for d, df in enumerate(dfs):
        if df.index.is_unique:
            continue
        group_xx = groups_xx[d]
        group_with_duplicates = df.columns[0].split(';;')[1].replace('-', ', ')
        duplicated_xx = group_xx[df.index.duplicated(keep='first')]
        groups_with_duplicates[group_with_duplicates] = duplicated_xx
    
    duplicates = []
    for group_values, duplicated_xx in groups_with_duplicates.items():
        xx_name = duplicated_xx.name
        xx_value = duplicated_xx.iloc[0]
        duplicates_str = (
            f'    * Duplicates of "{group_values}" --> {xx_name} = {xx_value}'
        )
        duplicates.append(duplicates_str)

    duplicates = '\n'.join(duplicates)

    traceback.print_exc()
    print(error_below)
    grouping_str = f'{grouping}'.strip('()').strip(',')
    print(f'The groups determined by "{grouping_str}" are not unique:\n')
    print(f'{duplicates}')
    print(error_close)
    exit()

def raise_missing_arg(argument_name):
    traceback.print_exc()
    print(error_below)
    print(f'The argument `{argument_name}` is required.')
    print(error_close)
    exit()

def _get_groups_data(
        df: pd.DataFrame, x: str, z: str, grouping: str, bin_size: int=None, 
        normalize_x: bool=False, zeroize_x: bool=False
    ):
    grouped = df.groupby(list(grouping))
    dfs = []
    groups_xx = []
    yticks_labels = []
    max_n_decimals = None
    min_norm_bin_size = None
    if normalize_x:
        min_dx = min([
            group_df[x].diff().abs().min() for _, group_df in grouped
        ])
        max_n_decimals = 0
        min_norm_bin_size = np.inf

    for name, group_df in grouped:
        groups_xx.append(group_df[x])
        if zeroize_x:
            group_xx = group_df[x]-group_df[x].min()
        else:
            group_xx = group_df[x]
        if len(grouping) == 1:
            name_str = str(name)
        else:
            name_str = '-'.join([str(n) for n in name])
        group_cols = {col:f'{col};;{name_str}' for col in group_df.columns}
        group_df = group_df.rename(columns=group_cols)
        if normalize_x: 
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
        else:
            group_df['x'] = group_xx
        col_name = f'{z};;{name_str}'
        dfs.append(group_df.set_index('x')[[col_name]])
        
        yticks_labels.append(f'{name}'.strip('()'))

    try:
        df_data = pd.concat(dfs, names=[x], axis=1).sort_index()
    except pd.errors.InvalidIndexError as err:
        _raise_non_unique_groups(grouping, dfs, groups_xx)

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

        df_data.index = pd.to_datetime(df_data.index.astype(int))
        rs = f'{bin_size}ns'
        df_data = df_data.resample(rs, label='right').mean()
        df_data.index = df_data.index.astype(np.int64)/order_of_magnitude

    data = df_data.fillna(0).values.T
    xx = df_data.index

    return data, xx, yticks_labels

def _check_df_data_args(**kwargs):
    for arg_name, arg_value in kwargs.items():
        if arg_value: 
            continue
        if arg_value is not None:
            continue
        raise_missing_arg(arg_name)

def _raise_group_label_depth_too_deep(group_label_depth, n_levels):
    traceback.print_exc()
    print(error_below)
    print(
        f'The `group_label_depth = {group_label_depth}` is too high, '
        f'there are only {n_levels} levels.'
    )
    print(error_close)
    exit()

def _get_heatmap_yticks(
        nrows, group_height, yticks_labels, group_label_depth
    ):
    yticks = np.arange(0,nrows*group_height, group_height) - 0.5
    # yticks = yticks + group_height/2 - 0.5

    if group_label_depth is not None:
        df_ticks = pd.DataFrame({
            'yticks': yticks,
            'yticks_labels': yticks_labels
        }).set_index('yticks').astype(str)
        df_ticks = df_ticks['yticks_labels'].str.split(',', expand=True)
        if group_label_depth > len(df_ticks.columns):
            n_levels = len(df_ticks.columns)
            _raise_group_label_depth_too_deep(group_label_depth, n_levels)
        df_ticks = df_ticks[list(range(group_label_depth))]
        df_ticks['yticks_labels'] = df_ticks.agg(','.join, axis=1)
        df_ticks = df_ticks.reset_index().set_index('yticks_labels')
        yticks_first = df_ticks[~df_ticks.index.duplicated(keep='first')]
        yticks_last = df_ticks[~df_ticks.index.duplicated(keep='last')]
        yticks_start = yticks_first['yticks']
        yticks_end = yticks_last['yticks']
        yticks_center = yticks_start + (yticks_end-yticks_start)/2
        yticks_center = yticks_center
    return yticks_start, yticks_end, yticks_center

def _get_heatmap_xticks():
    pass

def _check_x_dtype(df, x, force_x_to_int):
    if force_x_to_int:
        return

    if pd.api.types.is_integer_dtype(df[x]):
        return
    print(error_below)
    print(
        f'The `x` column must be of data type integer. '
        'Pass `force_x_to_int=True` if you want to force conversion to '
        'integers.'
    )
    print(error_close)
    exit()

def heatmap(
        data: Union[pd.DataFrame, np.ndarray], 
        x: str='',  
        z: str='',
        y_grouping: Union[str, list[str]]='',
        sort_groups: bool=True,
        normalize_x: bool=False,
        zeroize_x: bool=False,
        x_bin_size: int=None,
        force_x_to_int: bool=False,
        z_min: Union[int, float]=None,
        z_max: Union[int, float]=None,
        stretch_height_factor: float=None,
        stretch_width_factor: float=None,
        group_label_depth: int=None,
        colormap: Union[str, matplotlib.colors.Colormap]='viridis',
        missing_values_color=None,
        colorbar_pad: float= 0.07,
        colorbar_size: float=0.05,
        colorbar_label: str='',
        ax: plt.Axes=None,
        fig: plt.Figure=None,
        backend: str='matplotlib',
        block: bool=False
    ):
    
    if ax is None:
        fig, ax = plt.subplots()

    yticks_labels = None
    if isinstance(data, pd.DataFrame):
        _check_df_data_args(y_grouping=y_grouping, x=x, z=z)
        _check_x_dtype(data, x, force_x_to_int)
        if isinstance(y_grouping, str):
            y_cols = (y_grouping,)
        else:
            y_cols = y_grouping
        data = data[[*y_cols, x, z]]
        if sort_groups:
            data = data.sort_values(list(y_cols))
        data, xx, yticks_labels = _get_groups_data(
            data, x, z, grouping=y_cols, normalize_x=normalize_x,
            bin_size=x_bin_size, zeroize_x=zeroize_x
        )
    else:
        x = 'x' if not x else x
        y_grouping = 'groups' if not y_grouping else y_grouping
        z = 'x' if not z else z

    import pdb; pdb.set_trace()

    if z_min is None:
        z_min = np.nanmin(data)
    
    if z_max is None:
        z_max = np.nanmax(data)

    Y, X = data.shape
    group_height = round(X/Y)
    if stretch_height_factor is not None:
        group_height = round(group_height*stretch_height_factor)
    
    Y, X = data.shape
    x_unit_width = round(Y/X)
    if stretch_width_factor is not None:
        x_unit_width = round(stretch_width_factor)
    
    group_height = group_height if group_height>1 else 1
    x_unit_width = x_unit_width if x_unit_width>1 else 1

    yticks_start, yticks_end, yticks_center = _get_heatmap_yticks(
        len(data), group_height, yticks_labels, group_label_depth
    )
    yticks_labels = yticks_start.index.to_list()
    yticks = yticks_start.values

    if group_height > 1:
        data = np.repeat(data, [group_height]*len(data), axis=0)
    
    if x_unit_width > 1:
        ncols = data.shape[-1]
        data = np.repeat(data, [x_unit_width]*ncols, axis=1)
    
    
    if missing_values_color is not None:
        if isinstance(colormap, str):
            colormap = plt.get_cmap(colormap)

        bkgr_color = matplotlib.colors.to_rgba(missing_values_color)
        colors = colormap(np.linspace(0,1,256))
        colors[0] = bkgr_color
        colormap = matplotlib.colors.ListedColormap(colors)

    im = ax.imshow(data, cmap=colormap, vmin=z_min, vmax=z_max)
    ax.set_xlabel(x)
    ax.set_ylabel(y_grouping)
    ax.set_yticks(yticks, labels=yticks_labels)
    
    _size_perc = f'{int(colorbar_size*100)}%'
    _add_colorbar_axes(
        ax, im, size=_size_perc, pad=colorbar_pad, label=colorbar_label
    )
    
    if block:
        plt.show()
    else:
        return ax