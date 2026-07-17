# Harmonic Signal and Spectrum Visualizer

Интерактивное настольное приложение для построения гармонического сигнала,
осциллограммы и двустороннего амплитудного спектра.

Interactive desktop application for visualizing a harmonic signal, its
oscilloscope trace, and its two-sided amplitude spectrum.

---

## Русский язык

### Возможности

- Настройка амплитуды, частоты и фазы основной гармоники.
- Добавление, изменение и удаление высших гармоник.
- Обязательное подтверждение добавления и удаления гармоник.
- Непрерывная временная развёртка сигнала в режиме осциллографа.
- Двусторонний спектр с отрицательными и положительными частотами.
- Симметрично-логарифмическая шкала частоты.
- Логарифмическая шкала амплитуды в децибелах.
- Интерполяционная кривая до 10-й степени.
- Расчёт пикового и среднеквадратического значения сигнала.

### Системные требования

- Python 3.10 или новее.
- Модуль `tkinter`.

Сторонние библиотеки не требуются: приложение использует только стандартную
библиотеку Python.

Проверить наличие `tkinter` можно командой:

```powershell
python -m tkinter
```

Если появилось тестовое окно, модуль установлен правильно.

### Запуск

Перейдите в каталог приложения:

```powershell
cd "python/Develop_harmonic_signal"
python main.py
```

В Windows также можно использовать Python Launcher:

```powershell
py main.py
```

### Основная гармоника

Параметры основной гармоники регулируются слайдерами или числовыми полями:

| Параметр       | Диапазон    | Описание |
|                |             |
| Амплитуда `A₁` | `0.1…380`   | Максимальное отклонение основной синусоиды 
| Частота `f₀`   | `0.5…100 Гц`| Количество периодов в секунду 
| Фаза `φ₁`      | `−180…180°` | Начальный фазовый сдвиг 

Сигнал рассчитывается по формуле:

```text
x(t) = Σ Aₙ · sin(2π · n · f₀ · t + φₙ)
```

### Управление осциллограммой

Управление 

Перемещение временного окна по X и Y Зажать левую кнопку мыши и перемещать курсор 
Прокрутка по времени Колесо мыши 
Перемещение по вертикальной оси `Shift` + колесо мыши 
Возврат в исходное положение Двойной щелчок левой кнопкой 

При перемещении временного окна сигнал не сдвигается как готовое изображение,
а заново рассчитывается для нового диапазона времени. Поэтому осциллограмма
непрерывно достраивается без пустых участков.

### Высшие гармоники

Чтобы добавить гармонику:

1. Нажмите **«Добавить»**.
2. Введите номер гармоники `n`, амплитуду `Aₙ` и фазу `φₙ`.
3. Нажмите **«Продолжить»**.
4. Проверьте параметры и подтвердите добавление.

Ограничения:

- номер высшей гармоники: `n ≥ 2`;
- амплитуда: `0 < Aₙ ≤ 1000`;
- фаза: `−360° ≤ φₙ ≤ 360°`;
- гармоники с одинаковым номером не допускаются.

Для изменения выберите строку в таблице и нажмите **«Изменить»** либо дважды
щёлкните по строке. Для удаления выберите гармонику, нажмите **«Удалить»** и
подтвердите действие.

Частота высшей гармоники задаётся автоматически:

```text
fₙ = n · f₀
```

Например, при `f₀ = 50 Гц` гармоника `n = 11` располагается на частотах
`−550 Гц` и `+550 Гц`. Это частоты, а не значения фазы в градусах.

### Двусторонний спектр

Для вещественного синусоидального сигнала с амплитудой `Aₙ` отображаются две
спектральные линии:

```text
−n · f₀  →  Aₙ / 2
+n · f₀  →  Aₙ / 2
```

- Фиолетовые линии соответствуют отрицательным частотам.
- Голубые линии соответствуют положительным частотам.
- Горизонтальная ось использует симметрично-логарифмическое преобразование,
  поскольку обычный логарифм не определён для отрицательных значений и нуля.
- Вертикальная ось показывает относительный уровень в децибелах. Наибольшая
  спектральная линия имеет уровень `0 дБ`.

Уровень рассчитывается по формуле:

```text
Lₙ = 20 · log₁₀((Aₙ / 2) / Amax)
```

### Интерполяционная кривая

Вершины спектральных линий соединяются локальными полиномами Лагранжа степени
до 10. Для полинома 10-й степени требуется не менее 11 различных точек. Если
точек меньше, автоматически используется максимально возможная степень
`количество точек − 1`.

Например, четыре гармоники создают восемь точек двустороннего спектра, поэтому
для них максимальная степень интерполяции равна 7.

### Показатели сигнала

В нижней панели отображаются:

- формула текущего сигнала;
- пиковое значение;
- среднеквадратическое значение `RMS`;
- количество составляющих гармоник.

### Возможные проблемы

**Команда `python` не найдена**

Установите Python и включите опцию добавления Python в `PATH` либо используйте
команду `py`.

**Ошибка `No module named tkinter`**

Установите компонент Tcl/Tk для вашей сборки Python. В официальном установщике
Python для Windows он называется **Tcl/Tk and IDLE**.

**Сообщения Pylance после внешнего изменения файла**

Сохраните файл и выполните в VS Code команду **Python: Restart Language
Server**.

---

## English version

### Features

- Fundamental amplitude, frequency, and phase controls.
- Add, edit, and remove higher harmonics.
- Mandatory confirmation before adding or removing a harmonic.
- Continuously reconstructed oscilloscope time window.
- Two-sided spectrum with negative and positive frequencies.
- Symmetric logarithmic frequency scale.
- Logarithmic magnitude scale in decibels.
- Interpolation curve up to degree 10.
- Peak and RMS signal measurements.

### Requirements

- Python 3.10 or newer.
- The `tkinter` module.

No third-party dependencies are required. The application uses only the Python
standard library.

Check that `tkinter` is available:

```powershell
python -m tkinter
```

If a test window opens, the module is installed correctly.

### Running the application

Open the application directory:

```powershell
cd "python/Develop_harmonic_signal"
python main.py
```

On Windows, Python Launcher can also be used:

```powershell
py main.py
```

### Fundamental harmonic

Use the sliders or numeric fields to adjust the fundamental component:

| Parameter      | Range       | Description |
|                |             |
| Amplitude `A₁` | `0.1…380`   | Maximum displacement of the fundamental sine wave 
| Frequency `f₀` | `0.5…100 Hz`| Number of periods per second 
| Phase `φ₁`     | `−180…180°` | Initial phase offset 

The signal is calculated as:

```text
x(t) = Σ Aₙ · sin(2π · n · f₀ · t + φₙ)
```

### Oscilloscope navigation

Action and Control

 Move the time window along X and Y Hold the left mouse button and drag
 Scroll through time Mouse wheel
 Move along the vertical axis `Shift` + mouse wheel
 Reset the view Double-click the left mouse button

Navigation changes the observed time range instead of translating a finished
image. The samples are recalculated continuously, so no empty gaps appear while
scrolling.

### Higher harmonics

To add a harmonic:

1. Click **Add**.
2. Enter the harmonic order `n`, amplitude `Aₙ`, and phase `φₙ`.
3. Click **Continue**.
4. Review the values and confirm the operation.

Constraints:

- higher-harmonic order: `n ≥ 2`;
- amplitude: `0 < Aₙ ≤ 1000`;
- phase: `−360° ≤ φₙ ≤ 360°`;
- duplicate harmonic orders are not allowed.

Select a table row and click **Edit**, or double-click the row, to modify a
harmonic. To remove it, select the harmonic, click **Remove**, and confirm the
operation.

The harmonic frequency is calculated automatically:

```text
fₙ = n · f₀
```

For example, when `f₀ = 50 Hz`, harmonic `n = 11` appears at `−550 Hz` and
`+550 Hz`. These values are frequencies, not phase angles in degrees.

### Two-sided spectrum

A real sine wave with amplitude `Aₙ` produces two displayed spectral lines:

```text
−n · f₀  →  Aₙ / 2
+n · f₀  →  Aₙ / 2
```

- Purple lines represent negative frequencies.
- Cyan lines represent positive frequencies.
- The horizontal axis uses a symmetric logarithmic transform because a regular
  logarithm is not defined for negative values or zero.
- The vertical axis shows the relative level in decibels. The strongest
  spectral line is normalized to `0 dB`.

The level is calculated as:

```text
Lₙ = 20 · log₁₀((Aₙ / 2) / Amax)
```

### Interpolation curve

The spectral peaks are connected using local Lagrange polynomials up to degree
10. A degree-10 polynomial requires at least 11 distinct points. When fewer
points are available, the application automatically uses the highest possible
degree, equal to `number of points − 1`.

For example, four harmonics produce eight two-sided spectral points, so their
maximum interpolation degree is 7.

### Signal information

The bottom status panel displays:

- the current signal equation;
- peak magnitude;
- RMS value;
- number of harmonic components.

### Troubleshooting

**The `python` command is not found**

Install Python and enable the option that adds it to `PATH`, or use the `py`
command on Windows.

**`No module named tkinter`**

Install the Tcl/Tk component for your Python distribution. In the official
Windows installer, this component is named **Tcl/Tk and IDLE**.

**Pylance diagnostics remain after an external file change**

Save the file and run **Python: Restart Language Server** in VS Code.

---

## Project files / Файлы проекта

```text
Develop_harmonic_signal/
├── main.py      # Application / Приложение
└── README.md    # User manual / Руководство пользователя
```

