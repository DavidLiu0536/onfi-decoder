"""Generate a 2-panel timeline visualization of decoded ONFI operations."""

import matplotlib.pyplot as plt
import matplotlib
import matplotlib.patches as mpatches
matplotlib.rcParams['font.sans-serif'] = ['Heiti TC', 'Arial Unicode MS', 'PingFang SC']
matplotlib.rcParams['axes.unicode_minus'] = False


COLOR_MAP = {
    'RESET':                '#7F8C8D',
    'READ_ID':              '#3498DB',
    'READ_PARAMETER_PAGE':  '#5DADE2',
    'READ_STATUS':          '#F39C12',
    'READ_STATUS_ENH':      '#F39C12',
    'READ_PAGE':            '#27AE60',
    'READ_PAGE_CONFIRM':    '#229954',
    'PROGRAM_PAGE':         '#E74C3C',
    'PROGRAM_CONFIRM':      '#C0392B',
    'BLOCK_ERASE':          '#8E44AD',
    'ERASE_CONFIRM':        '#7D3C98',
}


def _draw_panel(ax, events, t_start, t_end, title, label_cmds=True):
    """Render one timeline panel for the given time window."""
    cmds_in_panel = []
    for e in events:
        if not (t_start <= e.time_us <= t_end):
            continue
        if e.kind == 'CMD':
            color = COLOR_MAP.get(e.raw['name'], '#7F8C8D')
            ax.axvline(e.time_us, color=color, alpha=0.85, linewidth=1.5)
            cmds_in_panel.append((e.time_us, e.raw['name'], color))

    # busy regions
    busy_start = None
    for e in events:
        if e.kind == 'R/B':
            if 'BUSY' in e.raw['note']:
                busy_start = e.time_us
            elif 'READY' in e.raw['note'] and busy_start is not None:
                bs = max(busy_start, t_start); be = min(e.time_us, t_end)
                if be > bs:
                    ax.axvspan(bs, be, ymin=0.35, ymax=0.55, alpha=0.25, color='#E67E22')
                busy_start = None

    # data dots
    for e in events:
        if e.kind == 'DATA' and t_start <= e.time_us <= t_end:
            n = len(e.raw['bytes'])
            arrow = '↓' if e.raw['direction'] == 'read' else '↑'
            color = '#16A085' if e.raw['direction'] == 'read' else '#C0392B'
            ax.scatter([e.time_us], [0.20], s=70, color=color, marker='o', zorder=5)
            ax.annotate(f"{arrow}{n}B", xy=(e.time_us, 0.13), fontsize=8, ha='center', color=color)

    # CMD labels (smart vertical staggering to avoid overlap)
    if label_cmds and cmds_in_panel:
        levels = [0.95, 0.82, 0.69]
        last_x = -1e9; last_level = -1
        for t_us, name, color in cmds_in_panel:
            span = t_end - t_start
            if abs(t_us - last_x) < span * 0.04:
                last_level = (last_level + 1) % len(levels)
            else:
                last_level = 0
            y = levels[last_level]
            ax.annotate(name, xy=(t_us, y), fontsize=7, ha='center', va='top',
                        color=color, rotation=0)
            last_x = t_us

    ax.set_xlim(t_start, t_end)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xlabel('Time (μs)', fontsize=10)
    ax.set_title(title, fontsize=11, loc='left')
    ax.grid(True, alpha=0.3, axis='x')


def plot_timeline(decoder, output_path='timeline.png'):
    """Render two panels: top = zoomed busy region, bottom = full overview."""
    events = decoder.events
    if not events:
        print("No events to plot."); return

    total = events[-1].time_us
    # find busy regions; pick the first dense command cluster
    cmd_times = [e.time_us for e in events if e.kind == 'CMD']
    if cmd_times:
        zoom_end = cmd_times[-1] + (total - cmd_times[-1]) * 0.05
        zoom_end = min(zoom_end, total)
    else:
        zoom_end = total

    # Find a smart zoom: include the largest CMD cluster + first few hundred us
    cluster_end = max([t for t in cmd_times if t < total * 0.9] or [zoom_end])
    smart_zoom = min(cluster_end + 50, total * 0.9)

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(14, 7),
                                          gridspec_kw={'height_ratios': [3, 2], 'hspace': 0.45})

    _draw_panel(ax_top, events, 0, smart_zoom,
                f'Zoomed view (0 — {smart_zoom:.0f} μs): early command sequence')
    _draw_panel(ax_bot, events, 0, total,
                f'Full capture overview (0 — {total:.0f} μs)', label_cmds=False)

    # global legend
    seen = {}
    for e in events:
        if e.kind == 'CMD':
            seen[e.raw['name']] = COLOR_MAP.get(e.raw['name'], '#7F8C8D')
    legend = [mpatches.Patch(color=c, label=n) for n, c in list(seen.items())[:8]]
    legend += [
        mpatches.Patch(color='#E67E22', alpha=0.3, label='BUSY (R/B# low)'),
        mpatches.Patch(color='#16A085', label='Data Read'),
        mpatches.Patch(color='#C0392B', label='Data Write'),
    ]
    fig.legend(handles=legend, loc='upper right', fontsize=8, ncol=2,
               bbox_to_anchor=(0.99, 0.99))

    stats = decoder.stats()
    fig.suptitle(f'ONFI Bus Decoded Timeline  —  {stats["commands_total"]} commands · '
                 f'{stats["data_bytes_total"]} data bytes · {stats["duration_us"]:.1f} μs',
                 fontsize=13, fontweight='bold', y=0.995)

    plt.savefig(output_path, dpi=130, bbox_inches='tight')
    print(f"Timeline saved: {output_path}")
