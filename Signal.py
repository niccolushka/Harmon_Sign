"""Interactive harmonic signal and spectrum visualizer.

The application intentionally uses only Python's standard library.  Run it with
``python main.py`` on a Python installation that includes tkinter.
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Iterable, Literal


TextAnchor = Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]


@dataclass(frozen=True)
class Harmonic:
    """One sinusoidal component of a periodic signal."""

    order: int
    amplitude: float
    phase_deg: float


def signal_value(
    time_s: float, fundamental_frequency: float, harmonics: Iterable[Harmonic]
) -> float:
    """Return the sum of all harmonic components at *time_s*."""

    return sum(
        harmonic.amplitude
        * math.sin(
            2.0 * math.pi * harmonic.order * fundamental_frequency * time_s
            + math.radians(harmonic.phase_deg)
        )
        for harmonic in harmonics
    )


def signal_samples(
    fundamental_frequency: float,
    harmonics: Iterable[Harmonic],
    period_count: float = 3.0,
    sample_count: int = 1000,
) -> list[tuple[float, float]]:
    """Build evenly spaced samples covering several fundamental periods."""

    if fundamental_frequency <= 0:
        raise ValueError("Частота должна быть больше нуля")
    if sample_count < 2:
        raise ValueError("Требуется как минимум две точки")

    components = tuple(harmonics)
    duration = period_count / fundamental_frequency
    return [
        (
            duration * index / (sample_count - 1),
            signal_value(
                duration * index / (sample_count - 1),
                fundamental_frequency,
                components,
            ),
        )
        for index in range(sample_count)
    ]


def polynomial_interpolation_curve(
    points: Iterable[tuple[float, float]],
    degree: int = 10,
    samples_per_segment: int = 20,
) -> list[tuple[float, float]]:
    """Interpolate adjacent points with local polynomials up to *degree*."""

    ordered_points = sorted(points)
    if len(ordered_points) < 2:
        return ordered_points
    if degree < 1:
        raise ValueError("Степень полинома должна быть не меньше единицы")
    if samples_per_segment < 1:
        raise ValueError("На сегмент требуется как минимум один отсчёт")

    node_count = min(degree + 1, len(ordered_points))
    result: list[tuple[float, float]] = []

    for segment in range(len(ordered_points) - 1):
        # An eleven-point moving window produces a tenth-degree polynomial and
        # always contains both ends of the segment currently being drawn.  With
        # fewer points, the highest mathematically possible degree is used.
        window_start = max(
            0,
            min(
                segment - (node_count - 2) // 2,
                len(ordered_points) - node_count,
            ),
        )
        nodes = ordered_points[window_start : window_start + node_count]
        x_start = ordered_points[segment][0]
        x_end = ordered_points[segment + 1][0]

        first_sample = 0 if segment == 0 else 1
        for sample in range(first_sample, samples_per_segment + 1):
            x = x_start + (x_end - x_start) * sample / samples_per_segment
            y = 0.0

            # Lagrange form: the local polynomial passes through every node.
            for node_index, (node_x, node_y) in enumerate(nodes):
                basis = 1.0
                for other_index, (other_x, _other_y) in enumerate(nodes):
                    if node_index != other_index:
                        basis *= (x - other_x) / (node_x - other_x)
                y += node_y * basis
            result.append((x, y))

    return result


class Chart(tk.Canvas):
    """A lightweight canvas chart with axes, grid and labels."""

    BACKGROUND = "#0b1220"
    GRID = "#233047"
    AXIS = "#8da2c0"
    TEXT = "#cbd5e1"
    ACCENT = "#38bdf8"
    SECONDARY = "#a78bfa"

    def __init__(self, master: tk.Misc, interactive: bool = False) -> None:
        super().__init__(
            master,
            background=self.BACKGROUND,
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._drag_origin: tuple[int, int] | None = None
        self.bind("<Configure>", lambda _event: self.event_generate("<<ChartResize>>"))
        if interactive:
            self.bind("<ButtonPress-1>", self._start_pan)
            self.bind("<B1-Motion>", self._drag_pan)
            self.bind("<ButtonRelease-1>", self._finish_pan)
            self.bind("<Double-Button-1>", self._reset_pan)
            self.bind("<MouseWheel>", self._scroll_pan)

    def _start_pan(self, event: tk.Event[tk.Misc]) -> None:
        self._drag_origin = (event.x, event.y)
        self.configure(cursor="fleur")

    def _drag_pan(self, event: tk.Event[tk.Misc]) -> None:
        if self._drag_origin is None:
            return
        previous_x, previous_y = self._drag_origin
        delta_x = event.x - previous_x
        delta_y = event.y - previous_y
        self._pan_x += delta_x
        self._pan_y += delta_y
        self._drag_origin = (event.x, event.y)
        self.event_generate("<<ChartPan>>")

    def _finish_pan(self, _event: tk.Event[tk.Misc]) -> None:
        self._drag_origin = None
        self.configure(cursor="")

    def _reset_pan(self, _event: tk.Event[tk.Misc]) -> None:
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._drag_origin = None
        self.configure(cursor="")
        self.event_generate("<<ChartPan>>")

    def _scroll_pan(self, event: tk.Event[tk.Misc]) -> None:
        steps = event.delta / 120.0
        try:
            modifier_state = int(event.state)
        except (TypeError, ValueError):
            modifier_state = 0
        if modifier_state & 0x0001:  # Shift + wheel moves the vertical window.
            self._pan_y += steps * 24.0
        else:
            self._pan_x += steps * 48.0
        self.event_generate("<<ChartPan>>")

    def _mask_outside_plot(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        width: float,
        height: float,
    ) -> None:
        """Hide data outside the plotting rectangle and restore the overlay."""

        masks = (
            (0, 0, width, top),
            (0, bottom, width, height),
            (0, top, left, bottom),
            (right, top, width, bottom),
        )
        for coordinates in masks:
            self.create_rectangle(
                *coordinates,
                fill=self.BACKGROUND,
                outline="",
                tags=("mask",),
            )
        self.tag_raise("overlay")

    @staticmethod
    def _nice_number(value: float) -> str:
        absolute = abs(value)
        if absolute >= 1000 or (0 < absolute < 0.01):
            return f"{value:.1e}"
        if absolute >= 10:
            return f"{value:.1f}"
        return f"{value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _boxes_overlap(
        first: tuple[int, int, int, int],
        second: tuple[int, int, int, int],
        padding: int = 3,
    ) -> bool:
        return not (
            first[2] + padding < second[0]
            or first[0] - padding > second[2]
            or first[3] + padding < second[1]
            or first[1] - padding > second[3]
        )

    def _draw_peak_labels(
        self,
        labels: list[tuple[float, float, str]],
        bounds: tuple[float, float, float, float],
    ) -> None:
        """Place compact labels near peaks while avoiding label collisions."""

        left, top, right, bottom = bounds
        occupied: list[tuple[int, int, int, int]] = []

        # Highest peaks get the best positions first.
        for x, y, text in sorted(labels, key=lambda label: label[1]):
            below: list[tuple[float, float, TextAnchor]] = [
                (x, y + 8, "n"),
                (x - 7, y + 8, "ne"),
                (x + 7, y + 8, "nw"),
                (x, y + 38, "n"),
            ]
            above: list[tuple[float, float, TextAnchor]] = [
                (x, y - 8, "s"),
                (x - 7, y - 8, "se"),
                (x + 7, y - 8, "sw"),
                (x, y - 38, "s"),
            ]
            candidates = below + above if y - top < 40 else above + below

            for label_x, label_y, anchor in candidates:
                text_item = self.create_text(
                    label_x,
                    label_y,
                    text=text,
                    fill=self.TEXT,
                    anchor=anchor,
                    justify="center",
                    font=("Segoe UI", 8),
                )
                box = self.bbox(text_item)
                is_inside = box is not None and (
                    box[0] >= left + 2
                    and box[1] >= top + 2
                    and box[2] <= right - 2
                    and box[3] <= bottom - 2
                )
                is_free = box is not None and all(
                    not self._boxes_overlap(box, used_box)
                    for used_box in occupied
                )
                if is_inside and is_free and box is not None:
                    background = self.create_rectangle(
                        box[0] - 2,
                        box[1] - 1,
                        box[2] + 2,
                        box[3] + 1,
                        fill=self.BACKGROUND,
                        outline="",
                        tags=("movable",),
                    )
                    self.itemconfigure(text_item, tags=("movable",))
                    self.tag_lower(background, text_item)
                    occupied.append(box)
                    break
                self.delete(text_item)

    def draw_signal(
        self,
        fundamental_frequency: float,
        harmonics: list[Harmonic],
        period_count: float = 3.0,
        sample_count: int = 1000,
    ) -> None:
        """Draw a continuously reconstructed oscilloscope time window."""

        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        left, right, top, bottom = 66, 34, 24, 58
        plot_width = width - left - right
        plot_height = height - top - bottom

        if (
            not harmonics
            or fundamental_frequency <= 0
            or plot_width < 80
            or plot_height < 60
        ):
            return

        axis_bottom = top + plot_height
        duration = period_count / fundamental_frequency
        time_start = -self._pan_x / plot_width * duration
        samples = [
            (
                time_start + duration * index / (sample_count - 1),
                signal_value(
                    time_start + duration * index / (sample_count - 1),
                    fundamental_frequency,
                    harmonics,
                ),
            )
            for index in range(sample_count)
        ]
        peak = max(max(abs(value) for _, value in samples), 0.1) * 1.12

        def x_coord(time_s: float) -> float:
            return left + ((time_s - time_start) / duration) * plot_width

        def y_coord(value: float) -> float:
            return (
                top
                + (peak - value) / (2.0 * peak) * plot_height
                + self._pan_y
            )

        for index in range(7):
            x = left + plot_width * index / 6
            self.create_line(x, top, x, axis_bottom, fill=self.GRID)
            label = self._nice_number(
                (time_start + duration * index / 6) * 1000
            )
            self.create_text(
                x,
                axis_bottom + 17,
                text=label,
                fill=self.TEXT,
                font=("Segoe UI", 9),
            )

        for index in range(5):
            grid_y = top + plot_height * index / 4
            value = peak - (grid_y - top - self._pan_y) / plot_height * 2.0 * peak
            y = top + plot_height * index / 4
            self.create_line(left, y, left + plot_width, y, fill=self.GRID)
            self.create_text(
                left - 9,
                y,
                text=self._nice_number(value),
                fill=self.TEXT,
                anchor="e",
                font=("Segoe UI", 9),
            )

        zero_y = y_coord(0.0)
        if top <= zero_y <= axis_bottom:
            self.create_line(
                left,
                zero_y,
                left + plot_width,
                zero_y,
                fill=self.AXIS,
                width=2,
            )
        self.create_line(left, top, left, axis_bottom, fill=self.AXIS, width=2)
        self.create_text(
            left + plot_width / 2,
            height - 12,
            text="Время, мс",
            fill=self.TEXT,
            font=("Segoe UI", 9),
        )
        self.create_text(
            7,
            top - 10,
            text="x(t)",
            fill=self.TEXT,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )
        self.create_text(
            width - right,
            top - 10,
            text="ЛКМ — X/Y · колесо — X · Shift+колесо — Y · 2×ЛКМ — сброс",
            fill=self.AXIS,
            anchor="e",
            font=("Segoe UI", 8),
        )

        # Everything drawn so far belongs to the fixed coordinate overlay.
        self.addtag_withtag("overlay", "all")

        points: list[float] = []
        for time_s, value in samples:
            points.extend((x_coord(time_s), y_coord(value)))
        self.create_line(
            *points,
            fill=self.ACCENT,
            width=2,
            smooth=False,
            tags=("data",),
        )
        self._mask_outside_plot(
            left,
            top,
            left + plot_width,
            axis_bottom,
            width,
            height,
        )

    def draw_spectrum(
        self, fundamental_frequency: float, harmonics: list[Harmonic]
    ) -> None:
        """Draw a two-sided spectrum with symlog frequency and dB magnitude."""

        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        left, right, top, bottom = 66, 34, 24, 58
        plot_width = width - left - right
        plot_height = height - top - bottom

        if not harmonics or plot_width < 80 or plot_height < 60:
            return

        axis_bottom = top + plot_height
        max_order = max(component.order for component in harmonics)
        max_frequency = fundamental_frequency * max_order

        # A real sine with amplitude A has two complex spectral lines: A/2 at
        # the negative frequency and A/2 at the positive frequency.
        magnitudes = {
            component.order: max(abs(component.amplitude) / 2.0, 1e-300)
            for component in harmonics
        }
        max_magnitude = max(magnitudes.values())
        relative_db = {
            order: 20.0 * math.log10(magnitude / max_magnitude)
            for order, magnitude in magnitudes.items()
        }
        minimum_db = min(relative_db.values())
        floor_db = min(-60.0, 20.0 * math.floor(minimum_db / 20.0))
        top_db = 3.0

        # A normal logarithm cannot display zero and negative frequencies.
        # This signed log1p transform is linear around zero and logarithmic
        # away from it, while keeping the graph symmetric about f=0.
        linear_threshold = max(fundamental_frequency, 1e-12)
        max_log_frequency = (
            math.log10(1.0 + max_frequency / linear_threshold) * 1.08
        )
        center_x = left + plot_width / 2.0
        half_width = plot_width / 2.0

        def x_coord(frequency: float) -> float:
            if frequency == 0:
                return center_x
            direction = 1.0 if frequency > 0 else -1.0
            log_frequency = math.log10(
                1.0 + abs(frequency) / linear_threshold
            )
            return (
                center_x
                + direction * log_frequency / max_log_frequency * half_width
            )

        def y_coord(decibels: float) -> float:
            visible_db = max(decibels, floor_db)
            return top + (top_db - visible_db) / (top_db - floor_db) * plot_height

        for index in range(5):
            decibels = floor_db * index / 4.0
            y = y_coord(decibels)
            self.create_line(left, y, left + plot_width, y, fill=self.GRID)
            self.create_text(
                left - 9,
                y,
                text=f"{decibels:g}",
                fill=self.TEXT,
                anchor="e",
                font=("Segoe UI", 9),
            )

        for component in harmonics:
            frequency = component.order * fundamental_frequency
            for signed_frequency in (-frequency, frequency):
                x = x_coord(signed_frequency)
                self.create_line(x, top, x, axis_bottom, fill=self.GRID)

        self.create_line(
            center_x, top, center_x, axis_bottom, fill=self.AXIS, width=2
        )
        self.create_line(
            left,
            axis_bottom,
            left + plot_width,
            axis_bottom,
            fill=self.AXIS,
            width=2,
        )
        self.create_text(
            center_x,
            axis_bottom + 17,
            text="0",
            fill=self.TEXT,
            font=("Segoe UI", 8),
        )

        spectrum_points = [
            (
                x_coord(signed_frequency),
                relative_db[component.order],
            )
            for component in harmonics
            for signed_frequency in (
                -component.order * fundamental_frequency,
                component.order * fundamental_frequency,
            )
        ]
        interpolation_degree = min(10, len(spectrum_points) - 1)
        curve = polynomial_interpolation_curve(
            spectrum_points, degree=interpolation_degree
        )
        if len(curve) >= 2:
            curve_coordinates: list[float] = []
            for x, decibels in curve:
                visible_db = min(top_db, max(floor_db, decibels))
                curve_coordinates.extend((x, y_coord(visible_db)))
            self.create_line(
                *curve_coordinates,
                fill="#f59e0b",
                width=2,
                smooth=False,
                tags=("movable",),
            )

        peak_labels: list[tuple[float, float, str]] = []
        for component in harmonics:
            frequency = component.order * fundamental_frequency
            magnitude = magnitudes[component.order]
            decibels = relative_db[component.order]
            y = y_coord(decibels)
            db_label = (
                "≤" + f"{floor_db:g}"
                if decibels < floor_db
                else f"{decibels:.1f}"
            )

            for signed_frequency in (-frequency, frequency):
                x = x_coord(signed_frequency)
                color = self.SECONDARY if signed_frequency < 0 else self.ACCENT
                self.create_line(
                    x,
                    axis_bottom,
                    x,
                    y,
                    fill=color,
                    width=5,
                    tags=("movable",),
                )
                self.create_oval(
                    x - 4,
                    y - 4,
                    x + 4,
                    y + 4,
                    fill=color,
                    outline="",
                    tags=("movable",),
                )
                peak_labels.append(
                    (x, y, f"{self._nice_number(magnitude)}\n{db_label} дБ")
                )
                self.create_text(
                    x,
                    axis_bottom + 17,
                    text=self._nice_number(signed_frequency),
                    fill=self.TEXT,
                    font=("Segoe UI", 8),
                    tags=("movable",),
                )

        self._draw_peak_labels(
            peak_labels,
            (left, top, left + plot_width, axis_bottom),
        )

        self.create_text(
            left + plot_width / 2,
            height - 12,
            text="Частота, Гц (симметрично-логарифмическая шкала)",
            fill=self.TEXT,
            font=("Segoe UI", 9),
        )
        self.create_text(
            7,
            top - 10,
            text="|A|, дБ",
            fill=self.TEXT,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )
class HarmonicDialog(tk.Toplevel):
    """Modal editor used before adding or changing a higher harmonic."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        initial: Harmonic | None = None,
        allow_order_edit: bool = True,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(background="#f1f5f9")
        self.transient(parent)
        self.result: Harmonic | None = None
        self.order_var = tk.StringVar(value=str(initial.order if initial else 2))
        self.amplitude_var = tk.StringVar(
            value=f"{initial.amplitude:g}" if initial else "0.5"
        )
        self.phase_var = tk.StringVar(
            value=f"{initial.phase_deg:g}" if initial else "0"
        )

        body = ttk.Frame(self, style="Card.TFrame", padding=18)
        body.grid(sticky="nsew")
        fields = (
            ("Номер гармоники n", self.order_var),
            ("Амплитуда Aₙ", self.amplitude_var),
            ("Фаза φₙ, °", self.phase_var),
        )
        self.entries: list[ttk.Entry] = []
        for row, (label, variable) in enumerate(fields):
            ttk.Label(body, text=label, style="Control.TLabel").grid(
                row=row, column=0, sticky="w", pady=6
            )
            entry = ttk.Entry(
                body, textvariable=variable, width=18, style="Value.TEntry"
            )
            entry.grid(row=row, column=1, padx=(14, 0), pady=5)
            self.entries.append(entry)
        if not allow_order_edit:
            self.entries[0].state(["disabled"])

        buttons = ttk.Frame(body, style="CardBody.TFrame")
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(
            buttons, text="Отмена", style="Secondary.TButton", command=self.destroy
        ).pack(side="right")
        ttk.Button(
            buttons,
            text="Продолжить",
            style="Primary.TButton",
            command=self._accept,
        ).pack(
            side="right", padx=(0, 8)
        )

        self.bind("<Return>", lambda _event: self._accept())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()
        self.entries[0 if allow_order_edit else 1].focus_set()
        self.update_idletasks()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")

    def _accept(self) -> None:
        try:
            order = int(self.order_var.get().strip())
            amplitude = float(self.amplitude_var.get().strip().replace(",", "."))
            phase = float(self.phase_var.get().strip().replace(",", "."))
            if order < 2:
                raise ValueError("Номер высшей гармоники должен быть не меньше 2.")
            if not 0 < amplitude <= 1000:
                raise ValueError("Амплитуда должна быть в диапазоне (0; 1000].")
            if not -360 <= phase <= 360:
                raise ValueError("Фаза должна быть в диапазоне от −360° до 360°.")
        except ValueError as error:
            messagebox.showerror("Некорректные параметры", str(error), parent=self)
            return

        self.result = Harmonic(order, amplitude, phase)
        self.destroy()


class HarmonicSignalApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Гармонический сигнал и его спектр")
        self.geometry("1180x760")
        self.minsize(960, 660)
        self.configure(background="#f1f5f9")

        self.amplitude_var = tk.DoubleVar(value=1.0)
        self.frequency_var = tk.DoubleVar(value=5.0)
        self.phase_var = tk.DoubleVar(value=0.0)
        self.stats_var = tk.StringVar()
        self.formula_var = tk.StringVar()
        self.extra_harmonics: dict[int, Harmonic] = {}
        self._redraw_scheduled = False

        self._configure_style()
        self._build_layout()
        for variable in (self.amplitude_var, self.frequency_var, self.phase_var):
            variable.trace_add("write", self._schedule_redraw)
        self.after_idle(self.redraw)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#f1f5f9")
        style.configure(
            "Card.TFrame",
            background="#ffffff",
            borderwidth=1,
            relief="solid",
            lightcolor="#dbe3ee",
            darkcolor="#dbe3ee",
        )
        style.configure("CardBody.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f1f5f9", foreground="#172033")
        style.configure("Card.TLabel", background="#ffffff", foreground="#172033")
        style.configure(
            "Hint.TLabel",
            background="#ffffff",
            foreground="#64748b",
            font=("Segoe UI", 8),
        )
        style.configure(
            "Range.TLabel",
            background="#ffffff",
            foreground="#94a3b8",
            font=("Segoe UI", 8),
        )
        style.configure(
            "Title.TLabel",
            background="#f1f5f9",
            foreground="#0f172a",
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#f1f5f9",
            foreground="#64748b",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background="#ffffff",
            foreground="#0f172a",
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Control.TLabel",
            background="#ffffff",
            foreground="#334155",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Value.TSpinbox",
            fieldbackground="#ffffff",
            foreground="#0f172a",
            bordercolor="#cbd5e1",
            lightcolor="#cbd5e1",
            darkcolor="#cbd5e1",
            arrowcolor="#2563eb",
            padding=4,
        )
        style.configure(
            "Value.TEntry",
            fieldbackground="#ffffff",
            foreground="#0f172a",
            bordercolor="#cbd5e1",
            lightcolor="#cbd5e1",
            darkcolor="#cbd5e1",
            padding=6,
        )
        style.map(
            "Value.TEntry",
            bordercolor=[("focus", "#2563eb")],
            lightcolor=[("focus", "#2563eb")],
            darkcolor=[("focus", "#2563eb")],
        )
        style.map(
            "Value.TSpinbox",
            bordercolor=[("focus", "#2563eb")],
            lightcolor=[("focus", "#2563eb")],
            darkcolor=[("focus", "#2563eb")],
        )
        style.configure(
            "Modern.Horizontal.TScale",
            background="#ffffff",
            troughcolor="#dbeafe",
            bordercolor="#dbeafe",
            lightcolor="#2563eb",
            darkcolor="#2563eb",
            sliderrelief="flat",
        )
        style.map(
            "Modern.Horizontal.TScale",
            background=[("active", "#1d4ed8"), ("!active", "#2563eb")],
        )
        style.configure(
            "Primary.TButton",
            background="#2563eb",
            foreground="#ffffff",
            borderwidth=0,
            padding=(11, 7),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("pressed", "#1e40af"), ("active", "#1d4ed8")],
            foreground=[("disabled", "#e2e8f0"), ("!disabled", "#ffffff")],
        )
        style.configure(
            "Secondary.TButton",
            background="#e2e8f0",
            foreground="#334155",
            borderwidth=0,
            padding=(11, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "Secondary.TButton",
            background=[("pressed", "#cbd5e1"), ("active", "#d8e0ea")],
        )
        style.configure(
            "Danger.TButton",
            background="#fee2e2",
            foreground="#b91c1c",
            borderwidth=0,
            padding=(11, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "Danger.TButton",
            background=[("pressed", "#fecaca"), ("active", "#fecaca")],
        )
        style.configure(
            "Harmonics.Treeview",
            background="#f8fafc",
            fieldbackground="#f8fafc",
            foreground="#334155",
            bordercolor="#dbe3ee",
            rowheight=30,
            font=("Segoe UI", 9),
        )
        style.map(
            "Harmonics.Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#1e3a8a")],
        )
        style.configure(
            "Harmonics.Treeview.Heading",
            background="#eef2f7",
            foreground="#334155",
            relief="flat",
            padding=(5, 7),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Harmonics.Treeview.Heading",
            background=[("active", "#e2e8f0")],
        )
        style.configure(
            "Status.TFrame",
            background="#ffffff",
            borderwidth=1,
            relief="solid",
            lightcolor="#dbe3ee",
            darkcolor="#dbe3ee",
        )
        style.configure(
            "Status.TLabel",
            background="#ffffff",
            foreground="#475569",
            font=("Segoe UI", 9),
        )

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0, minsize=340)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ttk.Label(header, text="Гармонический сигнал", style="Title.TLabel").pack(
            side="left"
        )
        ttk.Label(
            header,
            text="временная форма и дискретный амплитудный спектр",
            style="Subtitle.TLabel",
        ).pack(side="left", padx=(14, 0), pady=(7, 0))

        controls = ttk.Frame(root, style="Card.TFrame", padding=18)
        controls.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        controls.columnconfigure(0, weight=1)
        controls.rowconfigure(5, weight=1)

        ttk.Label(
            controls, text="Основная гармоника", style="Section.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self._add_parameter_control(
            controls, 1, "Амплитуда A₁", self.amplitude_var, 0.1, 380.0, 0.1, 1
        )
        self._add_parameter_control(
            controls, 2, "Частота f₀, Гц", self.frequency_var, 0.5, 100.0, 0.5, 1
        )
        self._add_parameter_control(
            controls, 3, "Фаза φ₁, °", self.phase_var, -180.0, 180.0, 1.0, 0
        )

        ttk.Separator(controls).grid(row=4, column=0, sticky="ew", pady=14)
        harmonic_box = ttk.Frame(controls, style="CardBody.TFrame")
        harmonic_box.grid(row=5, column=0, sticky="nsew")
        harmonic_box.columnconfigure(0, weight=1)
        harmonic_box.rowconfigure(1, weight=1)
        ttk.Label(
            harmonic_box, text="Высшие гармоники", style="Section.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        columns = ("order", "amplitude", "phase")
        self.harmonic_table = ttk.Treeview(
            harmonic_box,
            columns=columns,
            show="headings",
            height=5,
            selectmode="browse",
            style="Harmonics.Treeview",
        )
        self.harmonic_table.heading("order", text="n")
        self.harmonic_table.heading("amplitude", text="Aₙ")
        self.harmonic_table.heading("phase", text="φₙ")
        self.harmonic_table.column("order", width=40, anchor="center", stretch=False)
        self.harmonic_table.column("amplitude", width=80, anchor="center")
        self.harmonic_table.column("phase", width=80, anchor="center")
        self.harmonic_table.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            harmonic_box, orient="vertical", command=self.harmonic_table.yview
        )
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.harmonic_table.configure(yscrollcommand=scrollbar.set)
        self.harmonic_table.bind("<Double-1>", lambda _event: self.edit_harmonic())

        buttons = ttk.Frame(harmonic_box, style="CardBody.TFrame")
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for column in range(3):
            buttons.columnconfigure(column, weight=1)
        ttk.Button(
            buttons,
            text="＋ Добавить",
            style="Primary.TButton",
            command=self.add_harmonic,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(
            buttons,
            text="Изменить",
            style="Secondary.TButton",
            command=self.edit_harmonic,
        ).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(
            buttons,
            text="Удалить",
            style="Danger.TButton",
            command=self.remove_harmonic,
        ).grid(row=0, column=2, sticky="ew", padx=(4, 0))
        ttk.Label(
            harmonic_box,
            text="Добавление и удаление — только после подтверждения.",
            style="Hint.TLabel",
            wraplength=295,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        charts = ttk.Frame(root)
        charts.grid(row=1, column=1, sticky="nsew")
        charts.columnconfigure(0, weight=1)
        charts.rowconfigure(0, weight=1)
        charts.rowconfigure(1, weight=1)

        signal_card = ttk.Frame(charts, style="Card.TFrame", padding=12)
        signal_card.grid(row=0, column=0, sticky="nsew", pady=(0, 7))
        signal_card.columnconfigure(0, weight=1)
        signal_card.rowconfigure(1, weight=1)
        ttk.Label(signal_card, text="Сигнал x(t)", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 7)
        )
        self.signal_chart = Chart(signal_card, interactive=True)
        self.signal_chart.grid(row=1, column=0, sticky="nsew")

        spectrum_card = ttk.Frame(charts, style="Card.TFrame", padding=12)
        spectrum_card.grid(row=1, column=0, sticky="nsew", pady=(7, 0))
        spectrum_card.columnconfigure(0, weight=1)
        spectrum_card.rowconfigure(1, weight=1)
        ttk.Label(
            spectrum_card,
            text="Двусторонний спектр |A(f)| · интерполяция до 10-го порядка",
            style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 7))
        self.spectrum_chart = Chart(spectrum_card)
        self.spectrum_chart.grid(row=1, column=0, sticky="nsew")

        footer = ttk.Frame(root, style="Status.TFrame", padding=(12, 8))
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(
            footer,
            textvariable=self.formula_var,
            style="Status.TLabel",
            font=("Consolas", 10),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            footer,
            textvariable=self.stats_var,
            style="Status.TLabel",
        ).grid(row=0, column=1, sticky="e", padx=(16, 0))

        self.signal_chart.bind("<<ChartResize>>", self._schedule_redraw)
        self.signal_chart.bind("<<ChartPan>>", self._schedule_redraw)
        self.spectrum_chart.bind("<<ChartResize>>", self._schedule_redraw)

    def _add_parameter_control(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.DoubleVar,
        minimum: float,
        maximum: float,
        increment: float,
        digits: int,
    ) -> None:
        group = ttk.Frame(parent, style="CardBody.TFrame")
        group.grid(row=row, column=0, sticky="ew", pady=7)
        group.columnconfigure(0, weight=1)
        ttk.Label(group, text=label, style="Control.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        spinbox = ttk.Spinbox(
            group,
            from_=minimum,
            to=maximum,
            increment=increment,
            textvariable=variable,
            width=9,
            justify="right",
            format=f"%.{digits}f",
            style="Value.TSpinbox",
        )
        spinbox.grid(row=0, column=1, sticky="e")
        scale = ttk.Scale(
            group,
            from_=minimum,
            to=maximum,
            variable=variable,
            orient="horizontal",
            style="Modern.Horizontal.TScale",
            command=lambda value: variable.set(round(float(value), digits)),
        )
        scale.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 0))
        ttk.Label(
            group, text=f"{minimum:g}", style="Range.TLabel"
        ).grid(row=2, column=0, sticky="w")
        ttk.Label(
            group, text=f"{maximum:g}", style="Range.TLabel"
        ).grid(row=2, column=1, sticky="e")

    def all_harmonics(self) -> list[Harmonic]:
        fundamental = Harmonic(1, self.amplitude_var.get(), self.phase_var.get())
        return [fundamental, *sorted(self.extra_harmonics.values(), key=lambda item: item.order)]

    def _schedule_redraw(self, *_args: object) -> None:
        if not self._redraw_scheduled:
            self._redraw_scheduled = True
            self.after_idle(self.redraw)

    def redraw(self) -> None:
        self._redraw_scheduled = False
        try:
            frequency = float(self.frequency_var.get())
            harmonics = self.all_harmonics()
            if frequency <= 0:
                return
        except (tk.TclError, ValueError):
            return

        samples = signal_samples(frequency, harmonics)
        self.signal_chart.draw_signal(frequency, harmonics)
        self.spectrum_chart.draw_spectrum(frequency, harmonics)

        values = [value for _, value in samples]
        rms = math.sqrt(sum(value * value for value in values) / len(values))
        peak = max(abs(value) for value in values)
        self.stats_var.set(f"Пик: {peak:.3g}   RMS: {rms:.3g}   Гармоник: {len(harmonics)}")
        terms = [
            f"{component.amplitude:g}·sin(2π·{component.order}·f₀·t"
            f" {component.phase_deg:+g}°)"
            for component in harmonics
        ]
        formula = "x(t) = " + " + ".join(terms)
        self.formula_var.set(formula if len(formula) < 115 else formula[:112] + "…")

    def add_harmonic(self) -> None:
        dialog = HarmonicDialog(self, "Новая высшая гармоника")
        self.wait_window(dialog)
        harmonic = dialog.result
        if harmonic is None:
            return
        if harmonic.order in self.extra_harmonics:
            messagebox.showwarning(
                "Гармоника уже существует",
                f"Гармоника n={harmonic.order} уже добавлена. Выберите её и нажмите «Изменить».",
                parent=self,
            )
            return

        frequency = harmonic.order * self.frequency_var.get()
        confirmed = messagebox.askyesno(
            "Подтвердите добавление",
            f"Добавить гармонику n={harmonic.order}?\n\n"
            f"Частота: {frequency:g} Гц ({harmonic.order}·f₀)\n"
            f"Амплитуда: {harmonic.amplitude:g}\n"
            f"Фаза: {harmonic.phase_deg:g}°",
            icon="question",
            parent=self,
        )
        if not confirmed:
            return

        self.extra_harmonics[harmonic.order] = harmonic
        self._refresh_harmonic_table(select_order=harmonic.order)
        self._schedule_redraw()

    def selected_harmonic(self) -> Harmonic | None:
        selection = self.harmonic_table.selection()
        if not selection:
            return None
        return self.extra_harmonics.get(int(selection[0]))

    def edit_harmonic(self) -> None:
        current = self.selected_harmonic()
        if current is None:
            messagebox.showinfo(
                "Гармоника не выбрана",
                "Выберите высшую гармонику в таблице.",
                parent=self,
            )
            return
        dialog = HarmonicDialog(
            self, f"Изменение гармоники n={current.order}", current, allow_order_edit=False
        )
        self.wait_window(dialog)
        if dialog.result is None:
            return
        self.extra_harmonics[current.order] = dialog.result
        self._refresh_harmonic_table(select_order=current.order)
        self._schedule_redraw()

    def remove_harmonic(self) -> None:
        harmonic = self.selected_harmonic()
        if harmonic is None:
            messagebox.showinfo(
                "Гармоника не выбрана",
                "Выберите высшую гармонику в таблице.",
                parent=self,
            )
            return
        confirmed = messagebox.askyesno(
            "Подтвердите удаление",
            f"Удалить гармонику n={harmonic.order} из сигнала?\n\n"
            f"Амплитуда: {harmonic.amplitude:g}\n"
            f"Фаза: {harmonic.phase_deg:g}°",
            icon="warning",
            parent=self,
        )
        if not confirmed:
            return

        del self.extra_harmonics[harmonic.order]
        self._refresh_harmonic_table()
        self._schedule_redraw()

    def _refresh_harmonic_table(self, select_order: int | None = None) -> None:
        for item_id in self.harmonic_table.get_children():
            self.harmonic_table.delete(item_id)
        for harmonic in sorted(self.extra_harmonics.values(), key=lambda item: item.order):
            item_id = str(harmonic.order)
            self.harmonic_table.insert(
                "",
                "end",
                iid=item_id,
                values=(harmonic.order, f"{harmonic.amplitude:g}", f"{harmonic.phase_deg:g}°"),
            )
        if select_order is not None and self.harmonic_table.exists(str(select_order)):
            self.harmonic_table.selection_set(str(select_order))
            self.harmonic_table.focus(str(select_order))


def main() -> None:
    app = HarmonicSignalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
