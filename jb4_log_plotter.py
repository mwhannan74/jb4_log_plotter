"""
JB4 log plotter (Kia Stinger GT)

What this script does:
1) Opens a simple file dialog so you can pick a JB4 CSV log file.
2) JB4 CSVs often contain metadata "blocks" before the actual data table.
   The real data header is the line that starts with "timestamp".
   We scan the file to find that line and tell pandas to treat it as the header.
3) Plots selected channels versus time using stacked subplots (sharex=True),
   so zoom/pan on one subplot applies to all subplots.
4) Adds a synchronized "cursor" (vertical line + markers) that follows your mouse
   across all plots and snaps to the nearest sample.

Virutal Environment
  python3 -m venv venv
Windows venv:
  .\.venv\Scripts\activate.bat
Linux venv
  source venv/bin/activate

Dependencies:
  pip install pandas matplotlib pyqt5
"""

from __future__ import annotations

from pathlib import Path

# IMPORTANT: Matplotlib "backend" must be selected before importing pyplot.
# "QtAgg" provides good interactive performance on Windows (zoom/pan toolbar, etc.).
import matplotlib
matplotlib.use("QtAgg")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------------------------------------------------------
# Plot configuration
# -----------------------------------------------------------------------------
# Each tuple: (Friendly name we want to plot, y-axis label, y-axis limits)
# Notes:
# - Your JB4 log may store Boost as either "Boost" or "ECU Boost".
# - Speed may show up as "Speed" or "GPS Speed".
#   We handle these differences in resolve_columns().
PLOTS = [
    ("RPM", "RPM", (0, 7000)),
    ("Boost", "Boost (psi)", (0, 25)),
    ("Pedal", "Pedal / Throttle (%)", (0, 110)),
    ("AFR", "AFR", (10, 22)),
    ("IAT", "IAT (°F)", (0, 160)),
    ("Speed", "Speed (mph)", (0, 120)),
]


# -----------------------------------------------------------------------------
# File picker
# -----------------------------------------------------------------------------
def pick_csv_file(initial_dir: Path) -> Path:
    """
    Open a basic OS file dialog so you can select the CSV log file.

    Why Tkinter?
    - It's part of the Python standard library.
    - It's "good enough" for a simple file selection window.

    Returns:
        Path to the selected file.

    Behavior:
        If user cancels, we exit the script cleanly by raising SystemExit.
    """
    import tkinter as tk
    from tkinter import filedialog

    # Create a hidden Tk root window. We do not want a full GUI app,
    # just a file picker dialog.
    root = tk.Tk()
    root.withdraw()

    # Make sure the dialog appears in front of other windows.
    root.attributes("-topmost", True)

    filename = filedialog.askopenfilename(
        title="Select JB4 CSV Log",
        initialdir=str(initial_dir),
        filetypes=[
            ("JB4 CSV files", "*.csv *.CSV"),  # accept both extensions
            ("All files", "*.*"),
        ],
    )


    # Destroy the hidden root window to avoid leaving a hanging Tk process.
    root.destroy()

    if not filename:
        # User hit cancel (empty string returned).
        raise SystemExit("No file selected. Exiting.")

    return Path(filename)


# -----------------------------------------------------------------------------
# CSV parsing: skip metadata blocks and start at the header row "timestamp,..."
# -----------------------------------------------------------------------------
def find_header_line(csv_path: Path, header_startswith: str = "timestamp") -> int:
    """
    JB4 logs often start with metadata lines, then the "real" CSV header appears.

    We scan the file (line-by-line) until we find a line whose beginning is:
        "timestamp"

    Returns:
        0-based line index of the header row. This index can be passed to pandas
        read_csv(..., header=<index>).

    Example:
        If the file's header row is the 5th line in the file, return 4.
    """
    with csv_path.open("r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            # lstrip() removes leading whitespace; helpful if file has odd formatting.
            if line.lstrip().startswith(header_startswith):
                return i

    raise ValueError(f'Could not find a header line starting with "{header_startswith}" in {csv_path}')


def read_jb4_csv(csv_path: Path) -> pd.DataFrame:
    """
    Read a JB4 CSV file into a DataFrame, ignoring metadata lines before the header.

    Steps:
    1) Find the header line index (row that begins with "timestamp").
    2) Read the CSV with pandas, using that row as the header.
    3) Clean column names (strip whitespace and normalize spacing).
    4) Convert timestamp to numeric and drop rows that don't parse.

    Returns:
        pandas DataFrame where df["timestamp"] is numeric seconds (float).
    """
    header_line = find_header_line(csv_path, header_startswith="timestamp")

    # pandas will treat the specified line as the header row.
    df = pd.read_csv(csv_path, header=header_line)

    # Some logs have trailing/leading spaces in column names or multiple spaces.
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    # Require timestamp column
    if "timestamp" not in df.columns:
        raise ValueError(f'Expected a "timestamp" column, found: {list(df.columns)}')

    # Convert timestamp to numeric; invalid parsing becomes NaN
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")

    # Drop any rows without a valid timestamp
    df = df.dropna(subset=["timestamp"]).reset_index(drop=True)

    return df


def resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """
    Different JB4 logs can have slightly different column names.

    This function maps the "friendly" names used in PLOTS to the actual column
    names present in the file.

    Example:
        If file has "ECU Boost" but not "Boost", we map friendly "Boost" -> "ECU Boost".
    """
    available = set(df.columns)

    # Start with columns we expect to exist as-is
    mapping: dict[str, str] = {
        "RPM": "RPM",
        "Pedal": "Pedal",
        "Throttle": "Throttle",
        "AFR": "AFR",
        "IAT": "IAT",
    }

    # Boost can be either "Boost" or "ECU Boost"
    if "Boost" in available:
        mapping["Boost"] = "Boost"
    elif "ECU Boost" in available:
        mapping["Boost"] = "ECU Boost"
    else:
        raise ValueError('Could not find "Boost" or "ECU Boost" column.')

    # Speed can be either "Speed" or "GPS Speed"
    if "Speed" in available:
        mapping["Speed"] = "Speed"
    elif "GPS Speed" in available:
        mapping["Speed"] = "GPS Speed"
    else:
        raise ValueError('Could not find "Speed" or "GPS Speed" column.')

    # Validate everything we mapped exists
    missing = [friendly for friendly, col in mapping.items() if col not in available]
    if missing:
        raise ValueError(f"Missing required columns: {missing}\nAvailable: {sorted(available)}")

    return mapping


# -----------------------------------------------------------------------------
# Cursor helpers
# -----------------------------------------------------------------------------
def nearest_index(x: float, x_arr: np.ndarray) -> int:
    """
    Return the index of the nearest sample in x_arr to the value x.

    We use np.searchsorted(), which is efficient if x_arr is sorted ascending.
    timestamp should be sorted in your log.

    Example:
      x_arr = [0.0, 1.5, 2.5, 3.5]
      x = 2.7  -> nearest is 2.5 (index 2)
    """
    i = int(np.searchsorted(x_arr, x))

    # Clamp to valid bounds
    if i <= 0:
        return 0
    if i >= len(x_arr):
        return len(x_arr) - 1

    # Pick whichever of i-1 and i is closer
    return i if (x_arr[i] - x) < (x - x_arr[i - 1]) else (i - 1)


# -----------------------------------------------------------------------------
# Main plotting routine
# -----------------------------------------------------------------------------
def main() -> None:
    # Use the script's directory as the starting folder for the dialog.
    script_dir = Path(__file__).resolve().parent

    # Pop up file picker so you don't have to hardcode filenames.
    csv_path = pick_csv_file(script_dir)

    # Read log (auto-skipping metadata) and resolve column-name differences.
    df = read_jb4_csv(csv_path)
    colmap = resolve_columns(df)

    # Convert timestamp to numpy array (faster operations in cursor callback)
    t = df["timestamp"].to_numpy(dtype=float)
    if len(t) == 0:
        raise ValueError("No data rows found after parsing CSV.")

    # Create stacked subplots sharing the same x-axis.
    # sharex=True is what "locks" x-zoom/pan together across all subplots.
    n = len(PLOTS)
    fig, axes = plt.subplots(nrows=n, ncols=1, sharex=True, figsize=(12, 2.0 * n))
    fig.suptitle(f"JB4 Log: {csv_path.name}", y=0.995)

    # If there's only one subplot, matplotlib returns a single Axes, not a list.
    if n == 1:
        axes = [axes]

    # We'll store each plotted y-series so the cursor can quickly grab y[idx].
    y_series: list[np.ndarray] = []

    # Store extra series for the Boost subplot (Boost2 and Target)
    boost_ax_index: int | None = None
    boost_extra_series: list[tuple[str, np.ndarray]] = []

    pedal_ax_index: int | None = None
    pedal_extra_series: list[tuple[str, np.ndarray]] = []

    # Plot each channel in its own subplot with its own y-limits.
    for ax_i, (ax, (friendly_name, y_label, y_lim)) in enumerate(zip(axes, PLOTS)):
        col = colmap.get(friendly_name, friendly_name)

        # Convert data to numeric. Non-numeric becomes NaN.
        y = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        y_series.append(y)

        # Special case: Boost plot gets two additional lines (Boost2 and Target)
        if friendly_name == "Boost":
            boost_ax_index = ax_i

            # Plot Boost, Boost2, Target with distinct line colors
            ax.plot(t, y, label="Boost", color="C0")

            y_boost2 = pd.to_numeric(df["Boost2"], errors="coerce").to_numpy(dtype=float)
            ax.plot(t, y_boost2, label="Boost2", color="C1")
            boost_extra_series.append(("Boost2", y_boost2))

            y_target = pd.to_numeric(df["Target"], errors="coerce").to_numpy(dtype=float)
            ax.plot(t, y_target, label="Target", color="C2")
            boost_extra_series.append(("Target", y_target))

        elif friendly_name == "Pedal":
            pedal_ax_index = ax_i

            ax.plot(t, y, label="Pedal", color="C0")

            y_throttle = pd.to_numeric(df["Throttle"], errors="coerce").to_numpy(dtype=float)
            ax.plot(t, y_throttle, label="Throttle", color="C1")
            pedal_extra_series.append(("Throttle", y_throttle))

        else:
            ax.plot(t, y, label=friendly_name)

        ax.set_ylabel(y_label)
        ax.set_ylim(*y_lim)
        ax.grid(True, linewidth=0.5, alpha=0.5)
        ax.legend(loc="upper right")

    axes[-1].set_xlabel("Time (s)")

    # -------------------------------------------------------------------------
    # Add interactive cursor: vertical line across all plots + point markers.
    # -------------------------------------------------------------------------
    # One vertical line per axis so the cursor appears in every subplot.
    # Initially invisible until mouse moves inside plots.
    vlines = [ax.axvline(t[0], linewidth=1.0, alpha=0.7, visible=False) for ax in axes]

    # One marker per subplot (a small dot) at the nearest data sample.
    markers = [
        ax.plot([], [], marker="o", markersize=4, linestyle="None", visible=False)[0]
        for ax in axes
    ]

    # NEW: A value label per subplot that will show the Y-value at the marker.
    # We draw these as text objects and update them on mouse movement.
    #
    # Note: We keep these in "data coordinates" so the label naturally moves with the dot.
    # We also use a small bounding box so the text remains readable over the plot lines.
    value_labels = [
        ax.text(
            0.0,
            0.0,
            "",
            visible=False,
            fontsize=9,
            ha="left",
            va="center",
            bbox=dict(boxstyle="round,pad=0.2", alpha=0.7),
        )
        for ax in axes
    ]

    # Extra markers + labels for the Boost subplot (Boost2 and Target)
    boost_extra_markers: list[plt.Line2D] = []
    boost_extra_labels: list[plt.Annotation] = []
    if boost_ax_index is not None and boost_extra_series:
        boost_ax = axes[boost_ax_index]

        boost_extra_markers = [
            boost_ax.plot([], [], marker="o", markersize=4, linestyle="None", visible=False)[0]
            for _name, _y in boost_extra_series
        ]

        # Use annotate() so label placement can be specified in screen-pixel offsets.
        # This prevents overlap when Boost/Boost2/Target values are close together.
        boost_extra_labels = [
            boost_ax.annotate(
                text="",
                xy=(0.0, 0.0),          # will be updated on mouse move
                xytext=(10, 0),         # (dx, dy) in offset points; dy will be updated per series
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", alpha=0.7),
                visible=False,
            )
            for _name, _y in boost_extra_series
        ]

    pedal_extra_markers: list[plt.Line2D] = []
    pedal_extra_labels: list[plt.Annotation] = []
    if pedal_ax_index is not None and pedal_extra_series:
        pedal_ax = axes[pedal_ax_index]

        pedal_extra_markers = [
            pedal_ax.plot([], [], marker="o", markersize=4, linestyle="None", visible=False)[0]
            for _name, _y in pedal_extra_series
        ]

        pedal_extra_labels = [
            pedal_ax.annotate(
                text="",
                xy=(0.0, 0.0),
                xytext=(10, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", alpha=0.7),
                visible=False,
            )
            for _name, _y in pedal_extra_series
        ]


    # A small info readout in the bottom-left of the figure.
    # You can expand this later to show all channel values at the cursor.
    info_text = fig.text(0.01, 0.01, "", ha="left", va="bottom")

    def on_move(event) -> None:
        """
        Mouse-move callback.
        event.xdata is the x-value in data coordinates (timestamp seconds) for the axis under the mouse.
        """
        # If mouse isn't over an axes, do nothing.
        if event.inaxes is None or event.xdata is None:
            return

        x = float(event.xdata)

        # If cursor moves outside the data time range, hide cursor artifacts.
        if x < t[0] or x > t[-1]:
            for vl in vlines:
                vl.set_visible(False)
            for mk in markers:
                mk.set_visible(False)
            for lbl in value_labels:
                lbl.set_visible(False)
            for mk in boost_extra_markers:
                mk.set_visible(False)
            for lbl in boost_extra_labels:
                lbl.set_visible(False)
            for mk in pedal_extra_markers:
                mk.set_visible(False)
            for lbl in pedal_extra_labels:
                lbl.set_visible(False)
            info_text.set_text("")
            fig.canvas.draw_idle()
            return

        # Snap cursor to nearest real timestamp sample
        idx = nearest_index(x, t)
        x_snap = t[idx]

        # A small horizontal offset so the value label does not sit directly on the vertical line.
        # We scale this by the current x-axis span so it behaves reasonably at different zoom levels.
        x0, x1 = axes[0].get_xlim()
        x_offset = 0.01 * (x1 - x0)

        # Move the vertical line in every subplot
        for vl in vlines:
            vl.set_xdata([x_snap, x_snap])
            vl.set_visible(True)

        # Move each marker to the (time, value) point for that subplot,
        # and update the corresponding text label to display the Y-value.
        for (mk, y, lbl, (friendly_name, _y_label, _y_lim)) in zip(markers, y_series, value_labels, PLOTS):
            y_val = y[idx]

            mk.set_data([x_snap], [y_val])
            mk.set_visible(True)

            # Update label text and location (slightly to the right of the cursor line)
            # Use compact formatting:
            # - Integers (like RPM) will display without decimals if they are close to ints
            # - Otherwise, display with 2 decimals
            if np.isfinite(y_val) and abs(y_val - round(y_val)) < 1e-9:
                text = f"{friendly_name}: {int(round(y_val))}"
            else:
                text = f"{friendly_name}: {y_val:.2f}"

            lbl.set_text(text)
            lbl.set_position((x_snap + x_offset, y_val))
            lbl.set_visible(True)

        # Update Boost subplot extra markers/labels (Boost2 and Target)
        if boost_ax_index is not None and boost_extra_series:
            # Stack labels vertically (in screen space) so they remain readable even when
            # the underlying y-values are very close.
            #
            # Offsets are in "points" (1/72 inch). Tune these if you want more/less spacing.
            y_offsets_pts = [14, 0, -14]

            for j, ((name, y_arr), mk, lbl) in enumerate(
                zip(boost_extra_series, boost_extra_markers, boost_extra_labels),
                start=0,
            ):
                y_val = y_arr[idx]

                mk.set_data([x_snap], [y_val])
                mk.set_visible(True)

                if np.isfinite(y_val) and abs(y_val - round(y_val)) < 1e-9:
                    text = f"{name}: {int(round(y_val))}"
                else:
                    text = f"{name}: {y_val:.2f}"

                lbl.set_text(text)
                lbl.xy = (x_snap, y_val)
                dy = y_offsets_pts[j] if j < len(y_offsets_pts) else (14 - 14 * j)
                lbl.set_position((10, dy))  # (dx, dy) in offset points
                lbl.set_visible(True)

        if pedal_ax_index is not None and pedal_extra_series:
            y_offsets_pts = [14]

            for j, ((name, y_arr), mk, lbl) in enumerate(
                zip(pedal_extra_series, pedal_extra_markers, pedal_extra_labels),
                start=0,
            ):
                y_val = y_arr[idx]

                mk.set_data([x_snap], [y_val])
                mk.set_visible(True)

                if np.isfinite(y_val) and abs(y_val - round(y_val)) < 1e-9:
                    text = f"{name}: {int(round(y_val))}"
                else:
                    text = f"{name}: {y_val:.2f}"

                lbl.set_text(text)
                lbl.xy = (x_snap, y_val)
                dy = y_offsets_pts[j] if j < len(y_offsets_pts) else (14 - 14 * j)
                lbl.set_position((10, dy))  # (dx, dy) in offset points
                lbl.set_visible(True)


        info_text.set_text(f"t = {x_snap:.2f} s   (index {idx})")
        fig.canvas.draw_idle()  # request a redraw without blocking

    def on_leave(_event) -> None:
        """
        When mouse leaves the figure window, hide cursor artifacts.
        """
        for vl in vlines:
            vl.set_visible(False)
        for mk in markers:
            mk.set_visible(False)
        for lbl in value_labels:
            lbl.set_visible(False)
        for mk in boost_extra_markers:
            mk.set_visible(False)
        for lbl in boost_extra_labels:
            lbl.set_visible(False)
        for mk in pedal_extra_markers:
            mk.set_visible(False)
        for lbl in pedal_extra_labels:
            lbl.set_visible(False)
        info_text.set_text("")
        fig.canvas.draw_idle()

    # Connect callbacks to matplotlib's event system
    fig.canvas.mpl_connect("motion_notify_event", on_move)
    fig.canvas.mpl_connect("figure_leave_event", on_leave)

    # Layout and show
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
