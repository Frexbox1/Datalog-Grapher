import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import random
import re

from matplotlib.offsetbox import (
    AnnotationBbox, DrawingArea, HPacker, VPacker, TextArea
)
from matplotlib.patches import Circle
from matplotlib.ticker import ScalarFormatter


mpl.rcParams['font.size'] = 8
mpl.rcParams['font.family'] = 'DejaVu Sans Mono'


class DynamicPlot:
    def __init__(self, csv_file, columns_to_display, skip_header_rows=1, data_fontsize=8, log_scale=False):
        self.csv_file = csv_file
        self.columns_to_display = columns_to_display
        self.skip_header_rows = skip_header_rows
        self.data_fontsize = data_fontsize
        self.log_scale = log_scale

        self.load_data()
        self.color_map = self.assign_random_colors()
        self.max_label_length = self.compute_max_label_length()  # Compute max label length for spacing
        self.setup_plot()
        self.plot_data()
        self.create_annotation_box()
        self.connect_events()

    def compute_max_label_length(self):
        cleaned_labels = [re.sub(r'\(.*?\)', '', label).strip() for label in self.columns_to_display]
        cleaned_labels = [f"{label} = " for label in cleaned_labels]
        max_length = max(len(label) for label in cleaned_labels)
        return max_length

    def load_data(self):
        try:
            self.df = pd.read_csv(self.csv_file, skiprows=self.skip_header_rows)
        except FileNotFoundError:
            raise FileNotFoundError(f"The file {self.csv_file} does not exist.")
        except pd.errors.EmptyDataError:
            raise ValueError("The CSV file is empty.")
        except Exception as e:
            raise ValueError(f"An error occurred while reading the CSV file: {e}")


        if "Time(s)" not in self.df.columns:
            raise ValueError("The CSV file must contain a 'Time(s)' column.")


        missing_cols = [col for col in self.columns_to_display if col not in self.df.columns]
        if missing_cols:
            raise ValueError(f"The following columns are missing in the CSV file: {', '.join(missing_cols)}")

        for col in self.columns_to_display:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

        self.df["Time(s)"] = pd.to_numeric(self.df["Time(s)"], errors='coerce')

        required_cols = self.columns_to_display + ["Time(s)"]
        self.df.dropna(subset=required_cols, inplace=True)

    def assign_random_colors(self):
        color_map = {}
        for col in self.columns_to_display:

            color = "#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
            color_map[col] = color

        return color_map

    def setup_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(15, 6))
        self.ax.set_title("2025-01-10_18.47.52_log")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)
        self.fig.subplots_adjust(right=0.75)

    def apply_yaxis_formatter(self):
        formatter = ScalarFormatter()
        formatter.set_scientific(False)
        formatter.set_useOffset(False)
        self.ax.yaxis.set_major_formatter(formatter)
        self.ax.ticklabel_format(style='plain', axis='y')

    def plot_data(self):

        self.uses_symlog = False  # Flag to track if symlog is used

        # Check for negative values in any of the columns
        if self.log_scale and self.df[self.columns_to_display].lt(0).any().any():
            # If negative values are present and log_scale is True, use symlog
            self.uses_symlog = True
            self.linthresh = 10  # Define a threshold for linear scaling near zero
            self.ax.set_yscale('symlog', linthresh=self.linthresh)
        elif self.log_scale:
            # If no negative values, use standard log scale
            self.ax.set_yscale('log')
        else:
            # Use linear scale
            self.ax.set_yscale('linear')

        # Apply the y-axis formatter
        self.apply_yaxis_formatter()

        for col in self.columns_to_display:
            self.ax.plot(self.df["Time(s)"], self.df[col], color=self.color_map[col], label=col, linewidth=2)

        # Set y-axis limits based on data
        if self.uses_symlog:
            y_min = self.df[self.columns_to_display].min().min()
            y_max = self.df[self.columns_to_display].max().max()
            # To ensure symlog handles negative and positive extremes
            self.ax.set_ylim(y_min * 1.1 if y_min < 0 else y_min * 0.9,
                             y_max * 1.1)
        else:
            y_min = self.df[self.columns_to_display].min().min() * 0.9
            y_max = self.df[self.columns_to_display].max().max() * 1.1
            self.ax.set_ylim(y_min, y_max)

        # Set x-axis limits based on Time(s) data
        x_min = self.df["Time(s)"].min()
        x_max = self.df["Time(s)"].max()
        self.ax.set_xlim(x_min, x_max)  # Explicitly set the x-axis limits
        self.ax.grid(linestyle='none')


    def format_value(self, value, width=1, decimals=2):
        # Create format string based on desired decimals
        format_str = f"{{value:10.{decimals}f}}"
        txt = f"{format_str.format(value=value)}"
        # Now pad to fixed width:
        return txt.ljust(width)

    def make_row(self, label, color):
        # 1) Create the circle patch
        patch_area = DrawingArea(20, 20)
        circle = Circle((10, 10), 5, facecolor=color, edgecolor="none")
        patch_area.add_artist(circle)

        # 2) Create the label TextArea with padding
        # Clean the label to remove units or special characters
        clean_label = re.sub(r'\(.*?\)', '', label).strip()  # Removes anything in parentheses
        clean_label = f"{clean_label} = "  # Add equal sign
        clean_label = clean_label.ljust(self.max_label_length)  # Pad to fixed width

        label_text = TextArea(clean_label, textprops={
            "ha": "left",
            # "va": "center",  # Commented out to fix alignment issue
            "family": "DejaVu Sans Mono",
            "fontsize": self.data_fontsize
        })

        # 3) Create the value TextArea (initially empty)
        value_text = TextArea("", textprops={
            "ha": "right",
            # "va": "center",  # Commented out to fix alignment issue
            "family": "DejaVu Sans Mono",
            "fontsize": self.data_fontsize
        })

        # 4) Combine label and value into a single TextArea
        combined_text = HPacker(
            children=[label_text, value_text],
            pad=0,
            sep=5,
            align="center",  # Ensures horizontal alignment
            mode="fixed"     # Ensures the value does not expand
        )

        # 5) Combine circle and combined_text in a single HPacker
        row_box = HPacker(
            children=[patch_area, combined_text],
            pad=0,
            sep=5,
            align="center",  # Ensures alignment similar to functional code
            mode="fixed"     # Ensures the circle remains fixed and doesn't shift
        )

        return row_box, value_text

    def create_annotation_box(self):
        # Create rows and store value_text objects for dynamic updates
        self.rows = []
        self.value_texts = []
        for label, color in zip(self.columns_to_display, self.color_map.values()):
            row_box, value_text = self.make_row(label, color)
            self.rows.append(row_box)
            self.value_texts.append(value_text)

        # Stack all rows vertically with fixed mode
        vbox = VPacker(
            children=self.rows,
            pad=0,
            sep=0,
            align="baseline",
            mode="fixed"  # Ensures all rows have the same total width and do not expand
        )

        # Put them in an AnnotationBbox placed outside the main axes
        self.box_ab = AnnotationBbox(
            vbox,
            xy=(1.02, 0.5),            # Position: slightly outside the axes to the right, vertically centered
            xycoords=self.ax.transAxes,     
            box_alignment=(0, 0.5),    # Align the left edge of the box to x=1.02
            frameon=True,
            pad=0.5                     # Padding as per functional code
        )
        self.ax.add_artist(self.box_ab)

    def on_mouse_move(self, event):
        if event.inaxes != self.ax:
            self.box_ab.set_visible(False)
            self.vertical_line.set_visible(False)
            self.fig.canvas.draw_idle()
            return

        mouse_x = event.xdata
        if mouse_x is None:
            self.box_ab.set_visible(False)
            self.vertical_line.set_visible(False)
            self.fig.canvas.draw_idle()
            return

        # Find the nearest row in the data
        idx_closest = (self.df["Time(s)"] - mouse_x).abs().idxmin()
        row = self.df.loc[idx_closest]

        # Update the vertical line position
        x_val = row["Time(s)"]
        self.vertical_line.set_xdata([x_val, x_val])
        self.vertical_line.set_visible(True)

        # Update each value in the annotation box
        for value_text, col in zip(self.value_texts, self.columns_to_display):
            value = row[col]
            formatted_value = self.format_value(value, width=1, decimals=2)  # Removed label
            value_text.set_text(formatted_value)

        # Make sure the annotation box is visible
        self.box_ab.set_visible(True)
        self.fig.canvas.draw_idle()

    def connect_events(self):
        self.vertical_line = self.ax.axvline(x=0, color='gray', alpha=0.6)
        self.vertical_line.set_visible(False)
        self.fig.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)

    def run(self):
        """
        Displays the plot.
        """
        plt.show()


if __name__ == "__main__":
    # Define the columns you want to display
    columns_to_display = [
        "Pedal(wped_w)(% PED)",
        "Eng spd(nmot_w)(1/min)",
        "Temp charge air(tans)(Grad C)",
        "Ign #1(zwcalcar)(Grad KW)",
        "Ign #2(zwcalcar_2)(Grad KW)",
        "Ign #3(zwcalcar_3)(Grad KW)",
        "Ign #4(zwcalcar_4)(Grad KW)",
        "Ign #5(zwcalcar_5)(Grad KW)",
        "Ign act(zwist)(Grad KW)",
        "Lambda STFT(frm_w)(-)",
        "HPF act unfilt(prroh_w)(MPa)",
        "HPF tgt(prsoll_w)(MPa)",
        "Pres pre throt(pvdg1_w)(hPa)",
        "Pres tgt before throt(pvds_w)(hPa)",
        "Pres tgt max(pvdxs_w)(hPa)",
    ]


    plot_instance = DynamicPlot(
        csv_file="2025-01-10_18.47.52_log.csv",
        columns_to_display=columns_to_display,
        skip_header_rows=1,
        data_fontsize=10,
        log_scale=True
    )
    plot_instance.run()
