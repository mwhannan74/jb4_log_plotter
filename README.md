# JB4 Log Plotter (Python)

A lightweight Python script for plotting **JB4 tuner CSV logs** with a fast, interactive Matplotlib UI. It is designed for logs that include JB4 metadata blocks before the actual data table.

## Features

- **File picker dialog**: choose a JB4 CSV log without editing code.
- **Metadata-aware CSV parsing**: automatically skips JB4 metadata blocks and begins reading at the first line that starts with `timestamp`.
- **Stacked plots with locked x-axis**: each channel has its own y-axis scale and limits; all plots share the same time axis (`sharex=True`) so zoom/pan stays synchronized.
- **Interactive cursor**:
  - vertical line follows the mouse across all subplots
  - markers snap to the nearest timestamp sample on each channel
  - time readout in the figure

## Example Plots (Default Channels)

The script plots the following channels vs. time (seconds), each with fixed y-limits:

- RPM (0–6500)
- Boost (0–20 psi) *(falls back to `ECU Boost` if needed)*
- Pedal (0–100 %)
- Throttle (0–100 %)
- AFR (0–20)
- IAT (0–120 °F)
- Speed (0–100 mph) *(falls back to `GPS Speed` if needed)*

You can modify these in the `PLOTS` list in the script.

---

## Requirements

- Python 3.10+ recommended (3.8+ often works)
- Packages:
  - `pandas`
  - `matplotlib`
  - `pyqt5` (for the `QtAgg` backend used for interactive zoom/pan)

Install dependencies:

```bash
pip install pandas matplotlib pyqt5
````

> Note: On some systems you may prefer `PySide6` instead of `PyQt5`, but the script currently targets `pyqt5` for simplicity.

---

## Quick Start

1. Clone or download this repo.

2. Install dependencies (see above).

3. Run the script:

```bash
python jb4_log_plotter.py
```

4. A file dialog opens—select your JB4 `.csv` log.

---

## Controls (Interactive Plot)

The Matplotlib toolbar provides standard controls:

* **Pan** (hand icon): click and drag to pan the view
* **Zoom** (magnifier icon): drag a box to zoom into a region
* **Home**: reset view
* **Back/Forward**: navigate view history

Because the plots share the x-axis, zoom/pan changes apply to all subplots.

### Cursor Behavior

* Move the mouse over any subplot:

  * a vertical line appears at the nearest timestamp
  * markers appear on each subplot at that timestamp
  * time readout appears in the lower-left corner
* Move the mouse outside the data range or leave the figure window:

  * the cursor and markers hide automatically

---

## How It Works (High Level)

### 1) Finding the header line

JB4 logs often include metadata blocks before the real table. The script scans the file line-by-line until it finds a line starting with:

```
timestamp,...
```

That line index is passed to pandas:

```python
pd.read_csv(csv_path, header=header_line)
```

### 2) Column name normalization

Column headers are stripped and normalized to avoid issues with spacing:

* leading/trailing spaces removed
* multiple spaces collapsed

### 3) Column name compatibility

Some logs may not contain `Boost` but do contain `ECU Boost`. Similarly, `Speed` may appear as `GPS Speed`. The script resolves these variations automatically.

---

## Customization

### Add/remove channels

Edit the `PLOTS` list in the script:

```python
PLOTS = [
    ("RPM", "RPM", (0, 6500)),
    ("Boost", "Boost (psi)", (0, 20)),
    ...
]
```

Each entry is:

```
(friendly_name, y_axis_label, (ymin, ymax))
```

### Adjust y-axis limits

Change the `(ymin, ymax)` tuple for any plot.

### Change the initial folder in the file dialog

The dialog currently starts in the same folder as the script:

```python
script_dir = Path(__file__).resolve().parent
csv_path = pick_csv_file(script_dir)
```

You can point it somewhere else if preferred.

---

## Troubleshooting

### The file dialog opens but nothing plots

* Confirm you selected a valid JB4 CSV log.
* If the script raises an error about not finding a `timestamp` header line, your file may be formatted differently. Open the CSV in a text editor and confirm the header row starts with `timestamp`.

### Backend / GUI issues

The script forces:

```python
matplotlib.use("QtAgg")
```

If you do not want Qt or have issues installing `pyqt5`, you can:

* remove/comment out the backend line and let Matplotlib choose a default, or
* replace it with:

```python
matplotlib.use("TkAgg")
```

(Then you may need a Tk-enabled Python install.)

### Missing columns

If your log uses different column naming, you may need to update `resolve_columns()`.

---

## Project Structure (Minimal)

This project is intentionally lightweight:

* `jb4_log_plotter.py` — main script
* `README.md` — this file

Recommended additions for a public repo:

* `requirements.txt`
* `LICENSE` (MIT is common)

Example `requirements.txt`:

```text
pandas
matplotlib
pyqt5
```

---

## Disclaimer

This script is provided as a utility for viewing and analyzing JB4 logs. Validate any conclusions with appropriate tuning knowledge and safe testing practices.