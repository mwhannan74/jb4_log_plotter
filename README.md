# JB4 Log Plotter (Python)

A lightweight Python script for plotting **JB4 tuner CSV logs** with a fast, interactive Matplotlib UI. It is designed for logs that include JB4 metadata blocks before the actual data table.

This code was built using logs from a 2021 Kia Stinger (Kia & Hyundai Turbo). Assumption is that log files across different brands use same file format and parameters.

**You can find a prebuilt version for both Windows and Linux in the Releases section of the GitHub repo back (look on righthand side).**

![Example](images/jb4_log_plotter_example.png)

# JB4 Map Guide

https://www.jb4tech.com/forum/model-specific-engine-tuning-modification-discussion/kia-hyundai-turbo/20722-kia-hyundai-jb4

- **Map 0:** JB4 disabled
- **Map 1:** 4psi over stock peak tapering to 2.5psi at high RPM. Default performance map suitable for all 91+ octane fuels.
- **Map 2:** 5psi over stock tapering to 4psi at high RPM. Suggested for 93+ octane fuel.
- **Map 3:** 6psi stock tapering to 5psi at high RPM. Suggested for high quality fuel including unleaded race gas, ethanol mixtures up to 30%, or high quality octane booster like Torco or Boostane.
- **Map 4:** Up to 7psi over stock. For use with unleaded race fuel and/or E85 mixtures up to 30%.
- **Map 5:** Up to 7psi over stock but without top end taper. For unleaded race fuel use and bolt on modifications. May not be suitable for E85 mixtures due to high fuel pressure dropping. If using this map on E85 you should be experienced at reading your own logs and evaluating ignition advance and fuel pressure.
- **Map 6:** User adjustable map. Enter value of boost over stock by RPM on user adjustment page.
- **Map 7:** Progressive WMI (water/meth) map. Increases boost as a function of methanol flow & methanol boost additive. Holds boost low until WMI is flowing to avoid tip-in knock, and reduces boost as a function of WMI flow in the event of interruption like running out of fluid, leak, or component failure.
- **Map 8:** Valet map, runs around half as much boost as stock.

## JB4 Parameters

https://www.jb4tech.com/forum/model-specific-engine-tuning-modification-discussion/kia-hyundai-turbo/27792-jb4-logging-parameters

- **Boost:** Pressure in front of the throttle body in PSI. Normal range from the factory is 12-14psi depending on barometric pressure, intake temperatures, engine speed, time under boost, and other factors. Boost will increase under JB4 maps and expect to see a normal range of 16-20psi depending on the map selected. Note when reading boost short term “spikes”, especially against a closed throttle body, are not relevant. Look for sustained boost during longer pulls for a more accurate reading of what your boost pressure is. If boost exceeds the boost safety setting on the user adjustment page the JB4 will disable. Remember with this platform boost targeting is LOAD based which means at lower elevation, colder temperatures, you'll have a LOWER boost target than higher elevation, warmer temperatures. The factory logic attempts to adjust it's boost target to keep engine performance similar across a wide range of operating conditions.
- **Boost2:** Pressure behind the throttle body in the intake manifold. This is generally a “better” indication of how much boost the engine is actually under. Normally Boost2 will mirror Boost unless the throttle blade is closing enough to limit manifold boost.
- **Target:** This is how much boost over factory the JB4 is requesting. It will vary by JB4 map, running conditions, engine speed, throttle position, and a host of other internal tuning factors. Generally map2 runs around 6psi over factory peak tapering down to 4psi over factory at higher engine speed.
- **ECU_PSI:** This is how much boost the ECU is observing and will generally mirror factory boost levels. At high enough boost levels Boost – Target = ECU_PSI.
- **DME_BT:** This would represent how much boost the ECU is requesting at an given moment but is not enabled on the Kia platform yet. Instead we use an internal algorithm to estimate what the factory boost target should be.
- **Pedal:** How far down the gas pedal is being pushed 0-100%
- **Thrtl:** The position of the throttle body 0-100%. This value is run by the ECU and it’s important to realize that the throttle body itself is substantially over sized, meaning that there needs to be significant throttle movement before you’ll see any deviation between Boost and Boost2. The ECU generally uses throttle to regulate ECU_PSI to DME_BT, closing throttle when ECU_PSI exceeds DME_BT, which can happen for a variety of reasons. Most commonly a dynamic target change due to traction control or some other on ECU driven on demand target change. On cars with fully modified exhaust systems you might see boost creep over target in higher gears and when that happens you’ll see throttle close proportionally to maintain Boost2 on target.
- **WGDC:** How much wastegate dutycycle offset is being applied by the JB4 if equipped with EWG connectors. If not equipped with EWG connnectors this parameter has no meaning. A value of 50 is no offset applied. Values over 50 mean WGDC is being added and values lower than 50 mean WGDC is being subtracted.
- **Ign1-6:** Timing advance in the specific cylinder. Generally all cylinders will agree but as you start to approach a limit of Boost for a given fuel quality/octane level then you’ll start to see 3.5 degree timing drops in specific cylinders. The lower the grade fuel the more frequently you’ll see drops. If you see drops in the same cylinder repeating several times in a single gear then it’s usually an indicator that you’d be better off with a lower Target for the given fuel. Note that timing in all cylinders regularly drops negative during shifts and under some other driving conditions so do not confused mapped changes affecting all cylinders with cylinder specific timing drops when evaluating logs. Also note cyl1 is sampled via OBDII while cyl2-6 are sampled via RAM read so there will be some timing differences between the readings due to the different protocols. Cyl 2-6 are not available for all vehicle models. Note with firmware v20+ values 2-6 reflect timing drops rather than raw timing advance per cylinder. Set FUA = 1 to revert back to raw timing if needed. In the new format this shows how many degrees were removed from that specific cylinder. Also note it's normal to see timing drops. If you're trying to tune for zero drops then you'll end up leaving a lot of power on the table.
- **Ign Avg:** This is not enabled for the Kia platform yet.
- **AFR:** Air/fuel ratio bank1. Factory air/fuel ratio runs stoich 14.7:1 during lean spool mode and quickly drops down to 10:1 under sustained full throttle. The JB4 using FuelEn will lean out the AFR dynamically to a target of around 11.9:1. If AFR goes leaner than 14:1 at higher RPM the JB4 will disable.
- **AFR2:** Same as above but for bank2. Note 4 cylinder vehicles will have only one bank and AFR2/Trim2 will always show as 0.
- **Trim:** Fuel trims in bank1. The JB4 has scaled fuel trims for quicker viewing, 25 in JB4 logs = 0%, 50 = +34%, and 0 = -34%. Generally fuel trims will jump up in to the 40s under peak torque and drop down towards 25 at higher RPM.
- **Trim2:** Fuel trims in bank2. These will mirror Trim generally and if there is a deviation may indicate a fuel wire is loose or installed improperly. The JB4 will disable if Trim and Trim2 have more than a 15pt variation.
- **FuelEn:** This represents the bank1 dynamic o2 sensor offset required to maintain a 11.9:1 AFR at full throttle. It’s managed by the JB4 internally using its dynamic double fuel control PID.
- **CalcTQ:** This represents the bank2 equivalent of FuelEn.
- **Gear:** Currently selected gear.
- **MPH:** The road speed in miles per hour.
- **FP_H:** The fuel pressure in mbar of the high pressure pump. Generally will sit above 10. If FP_H dips this indicates you’re using more fuel than the high pressure system can maintain, generally comes up on those running heavy E85 mixtures at higher boost levels. If FP_H drops below 7 the JB4 will disable.
- **FP_L:** Not currently enabled for Kia via CANbus, some customers have this linked up to Fuel-IT low pressure analog sensors they’ve added on. If you have not added on a separate low fuel pressure sensor ignore this parameter.
- **E85:** The ethanol mixture. Generally only accurate if also equipped with a Fuel-IT flex fuel sensor. There is a BETA version of a virtual flex fuel logic in the latest firmware but it’s not fully accurate and only there for data collection.
- **Meth:** If equipped with a WMI kit this represents your meth flow 0-100%.
- **WaterF:** Engine water temperature
- **OilF:** Not yet supported on the Stinger
- **ransTemp:** Transmission oil temperature
- **FF:** The feed forward component of the optional EWG PID control system. Adjusted via the FF and duty bias user adjustment settings, the PID output is added in to arrive at final WGDC.
- **WGDC:** Stands for waste gate duty cycle, but it's technically the JB4 WGDC offset as wastegate control is shared between the JB4 and the ECU with EWG connectors equipped. Values above 50 are closing the WG more, values below 50 opening WG more, and exactly 50 is a complete pass through with no changes.
- **Clock:** This is used for internal communication diagnostics and generally represents how many samples per second of CANbus data are being returned from the ECU. Not relevant to most users unless diagnosing a CANbus communications issue. 

## Code Features

- **File picker dialog**: choose a JB4 CSV log without editing code.
- **Metadata-aware CSV parsing**: automatically skips JB4 metadata blocks and begins reading at the first line that starts with `timestamp`.
- **Stacked plots with locked x-axis**: each channel has its own y-axis scale and limits; all plots share the same time axis (`sharex=True`) so zoom/pan stays synchronized.
- **Interactive cursor**:
  - vertical line follows the mouse across all subplots
  - markers snap to the nearest timestamp sample on each channel
  - time readout in the figure

## Code Example Plots (Default Channels)

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

## Building an Installer
From your activated venv that you were building and testing your code, run the following commands. 
Then go into the dist folder and zip up that folder. You distribute the zip file.

pip install pyinstaller

### Windows
pyinstaller --noconfirm --clean --name JB4LogPlotter-win --windowed jb4_log_plotter.py
### Linux
pyinstaller --noconfirm --clean --name JB4LogPlotter-linux --windowed jb4_log_plotter.py

---

## Disclaimer

This script is provided as a utility for viewing and analyzing JB4 logs. Validate any conclusions with appropriate tuning knowledge and safe testing practices.