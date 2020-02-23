import sys
import ntpath
from pathlib import Path
from functools import partial
from PyQt5.QtWidgets import (QWidget, QFrame, QGridLayout, QLabel, QLineEdit, QMessageBox,
                             QSpacerItem, QSizePolicy, QSlider, QSpinBox, QFrame,
                             QDoubleSpinBox, QFileDialog, QPushButton, QCheckBox, QComboBox, QVBoxLayout)
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp, Qt, QDir, QCoreApplication, pyqtSignal
from settings import get_setting, reset_defaults, LinkableSetting, set_setting
from visualizer import VisualizerWindow

SPACER = QSpacerItem(100, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)


def set_event_window(window):
    """
    To emulate keypresses, we need a window to send the keypress to.
    This main window is created in gui.pyw, so we need to set it here as well.
    """
    global WINDOW
    WINDOW = window


class LineEdit(QLineEdit):
    r"""
    A QLineEdit that overrides the keyPressEvent to allow the left and right
    keys to be sent to our window that controls shortcuts, instead of being used only by the LineEdit.
    """
    def __init__(self, parent):
        super().__init__(parent)
        # save current stylesheet for resetting highlighted style. Don't
        # want to reset to an empty string because our stylesheet may cascade
        # down to here in the future instead of being empty
        self.old_stylesheet = self.styleSheet()
        self.highlighted = False

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left or key == Qt.Key_Right:
            QCoreApplication.sendEvent(WINDOW, event)
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self.highlighted:
            self.setStyleSheet(self.old_stylesheet)
            self.highlighted = False

    def show_required(self):
        self.setStyleSheet(get_setting("required_style"))
        self.highlighted = True


class PasswordEdit(LineEdit):
    r"""
    A LineEdit that overrides focusInEvent and focusOutEven to show/hide the password on focus.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.setEchoMode(QLineEdit.Normal)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.setEchoMode(QLineEdit.Password)

class IDLineEdit(LineEdit):
    r"""
    A LineEdit that does not allow anything but digits to be entered.
    Specifically, anything not matched by regex ``\d*`` is not registered.
    """

    def __init__(self, parent):
        super().__init__(parent)
        # r prefix isn't necessary but pylint was annoying
        validator = QRegExpValidator(QRegExp(r"\d*"))
        self.setValidator(validator)


class SpinBox(QSpinBox):
    """
    A QSpinBox that overrides the keyPressEvent to allow the left and right
    keys to be sent to our window that controls shortcuts, instead of being used only by the SpinBox.
    """

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left or key == Qt.Key_Right:
            QCoreApplication.sendEvent(WINDOW, event)
        super().keyPressEvent(event)


class DoubleSpinBox(QDoubleSpinBox):
    """
    A QDoubleSpinBox that overrides the keyPressEvent to allow the left and right
    keys to be sent to our window that controls shortcuts, instead of being used only by the DoubleSpinBox.
    """

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Left or key == Qt.Key_Right:
            QCoreApplication.sendEvent(WINDOW, event)
        super().keyPressEvent(event)


class QHLine(QFrame):
    def __init__(self, shadow=QFrame.Plain):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(shadow)


class QVLine(QFrame):
    def __init__(self, shadow=QFrame.Plain):
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(shadow)


class Separator(QFrame):
    """
    Creates a horizontal line with text in the middle.
    Useful to vertically separate other widgets.
    """

    def __init__(self, title):
        super(Separator, self).__init__()

        label = QLabel(self)
        label.setText(title)
        label.setAlignment(Qt.AlignCenter)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(QHLine(), 0, 0, 1, 2)
        self.layout.addWidget(label, 0, 2, 1, 1)
        self.layout.addWidget(QHLine(), 0, 3, 1, 2)
        self.setLayout(self.layout)


class InputWidget(QFrame):
    """
    A container class of widgets that represents user input for an id. This class
    holds a Label and either a PasswordEdit, IDLineEdit, or LineEdit, depending
    on the constructor call. The former two inherit from LineEdit.
    """

    def __init__(self, title, tooltip, type_):
        super(InputWidget, self).__init__()

        label = QLabel(self)
        label.setText(title+":")
        label.setToolTip(tooltip)
        if type_ == "password":
            self.field = PasswordEdit(self)
        if type_ == "id":
            self.field = IDLineEdit(self)
        if type_ == "normal":
            self.field = LineEdit(self)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.field, 0, 2, 1, 3)
        self.setLayout(self.layout)

    def show_required(self):
        """
        Shows a red border around the LineEdit to indicate a field that must be
        filled in. This border is removed when the LineEdit receieves focus again.
        """
        self.field.show_required()


class IdWidgetCombined(QFrame):
    """
    A container class of widgets that represents user input for a map id and user id.
    If no map id is given the user id field will be disabled.

    This class holds 2 rows of a Label and IDLineEdit.
    """

    def __init__(self):
        super(IdWidgetCombined, self).__init__()

        self.map_id = InputWidget("Map Id", "Beatmap id, not the mapset id!", type_="id")
        self.map_id.field.textChanged.connect(self.update_user_enabled)

        self.user_id = InputWidget("User Id", "User id, as seen in the profile url", type_="id")

        self.update_user_enabled()

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.map_id, 0, 0, 1, 1)
        self.layout.addWidget(self.user_id, 1, 0, 1, 1)
        self.setLayout(self.layout)

    def update_user_enabled(self):
        """
        Enables the user id field if the map field has any text in it. Otherwise, disables the user id field.
        """
        self.user_id.setEnabled(self.map_id.field.text() != "")


class OptionWidget(LinkableSetting, QFrame):
    """
    A container class of widgets that represents an option with a boolean state.
    This class holds a Label and CheckBox.
    """

    def __init__(self, title, tooltip, setting, end=":"):
        """
        String setting: The name of the setting to link this OptionWidget to.
        """
        LinkableSetting.__init__(self, setting)
        QFrame.__init__(self)

        label = QLabel(self)
        label.setText(title + end)
        label.setToolTip(tooltip)
        self.box = QCheckBox(self)
        self.box.stateChanged.connect(self.on_setting_changed_from_gui)
        self.box.setChecked(self.setting_value)
        item = CenteredWidget(self.box)
        item.setFixedWidth(100)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addWidget(item, 0, 1, 1, 1, Qt.AlignRight)
        self.setLayout(self.layout)

    def on_setting_changed(self, new_value):
        self.box.setChecked(new_value)


class CenteredWidget(QWidget):
    """
    Turns a widget with a fixed size (for example a QCheckBox) into an flexible one which can be affected by the self.layout.
    """

    def __init__(self, widget):
        super().__init__()
        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setContentsMargins(0,0,0,0)
        self.setContentsMargins(0,0,0,0)
        self.layout.addWidget(widget)
        self.setLayout(self.layout)


class ButtonWidget(QFrame):
    """
    A container class of widgets that represents a clickable action with a label.
    This class holds a QLabel and QPushButton.
    """

    def __init__(self, label_title, button_title, tooltip, end=":"):
        super(ButtonWidget, self).__init__()

        label = QLabel(self)
        label.setText(label_title + end)
        label.setToolTip(tooltip)
        self.button = QPushButton(button_title)
        self.button.setFixedWidth(100)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.button, 0, 2, 1, 1)
        self.setLayout(self.layout)


class LoglevelWidget(QFrame):
    def __init__(self, tooltip):
        super(LoglevelWidget, self).__init__()

        level_label = QLabel(self)
        level_label.setText("Debug mode:")
        level_label.setToolTip(tooltip)

        output_label = QLabel(self)
        output_label.setText("Debug Output:")
        output_label.setToolTip(tooltip)

        level_combobox = QComboBox(self)
        level_combobox.setFixedWidth(100)
        level_combobox.addItem("CRITICAL", 50)
        level_combobox.addItem("ERROR", 40)
        level_combobox.addItem("WARNING", 30)
        level_combobox.addItem("INFO", 20)
        level_combobox.addItem("DEBUG", 10)
        level_combobox.addItem("TRACE", 5)
        level_combobox.setInsertPolicy(QComboBox.NoInsert)
        self.level_combobox = level_combobox

        save_option = OptionWidget("Save logs?", "", "log_save", end="")
        save_option.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.save_option = save_option

        output_combobox = QComboBox(self)
        output_combobox.setFixedWidth(100)
        output_combobox.addItem("NONE")
        output_combobox.addItem("TERMINAL")
        output_combobox.addItem("NEW WINDOW")
        output_combobox.addItem("BOTH")
        output_combobox.setInsertPolicy(QComboBox.NoInsert)
        output_combobox.setCurrentIndex(0) # NONE by default
        self.output_combobox = output_combobox
        self.save_folder = FolderChooser("Log Folder", get_setting("log_dir"))
        save_option.box.stateChanged.connect(self.save_folder.switch_enabled)
        self.save_folder.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.level_combobox.setCurrentIndex(get_setting("log_mode"))
        self.level_combobox.currentIndexChanged.connect(partial(set_setting, "log_mode"))

        self.save_option.box.setChecked(get_setting("log_save"))
        self.save_option.box.stateChanged.connect(partial(set_setting, "log_save"))

        self.output_combobox.setCurrentIndex(get_setting("log_output"))
        self.output_combobox.currentIndexChanged.connect(partial(set_setting, "log_output"))

        self.save_folder.switch_enabled(get_setting("log_save"))
        self.save_folder.path_signal.connect(partial(set_setting, "log_dir"))

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(level_label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.level_combobox, 0, 2, 1, 3, Qt.AlignRight)
        self.layout.addWidget(output_label, 1, 0, 1, 1)
        self.layout.addItem(SPACER, 1, 1, 1, 1)
        self.layout.addWidget(self.output_combobox, 1, 2, 1, 3, Qt.AlignRight)
        self.layout.addWidget(save_option, 2, 0, 1, 5)
        self.layout.addWidget(self.save_folder, 3, 0, 1, 5)

        self.setLayout(self.layout)


class CompareTopUsers(QFrame):
    """
    A container class of widgets that represents user input for how many users of a map to compare.
    This class holds a Label, Slider, and SpinBox.

    The SpinBox and Slider are linked internally by this class, so when one changes, so does the other.
    """

    def __init__(self, minimum):
        super().__init__()
        self.label = QLabel(self)
        self.label.setText("Compare Top Users:")
        self.label.setToolTip("Compare this many plays from the leaderboard")

        slider = QSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.ClickFocus)
        slider.setMinimum(minimum)
        slider.setMaximum(100)
        slider.setValue(50)
        slider.valueChanged.connect(self.update_spinbox)
        self.slider = slider

        spinbox = SpinBox(self)
        spinbox.setValue(50)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setRange(minimum, 100)
        spinbox.setSingleStep(1)
        spinbox.setFixedWidth(100)
        spinbox.valueChanged.connect(self.update_slider)
        self.spinbox = spinbox

        self.combined = WidgetCombiner(slider, spinbox)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.combined, 0, 2, 1, 3)
        self.setLayout(self.layout)

    # keep spinbox and slider in sync
    def update_spinbox(self, value):
        self.spinbox.setValue(value)

    def update_slider(self, value):
        self.slider.setValue(value)

    def update_user(self, mode):
        """
        This function is meant to be used to disable/enable the Slider and SpinBox externally.

        Args:
            Boolean mode: Declares if the widgets should be disabled or enabled
        """
        self.slider.setEnabled(mode)
        self.spinbox.setEnabled(mode)


class CompareTopPlays(QFrame):
    """
    A container class of widgets that represents user input for how many top plays of a user to compare.
    This class holds a Label, Slider, and SpinBox.

    The SpinBox and Slider are linked internally by this class, so when one changes, so does the other.
    """

    def __init__(self):
        super().__init__()
        label = QLabel(self)
        label.setText("Compare Top Plays:")
        label.setToolTip("Compare this many plays from the user")

        slider = QSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.ClickFocus)
        slider.setValue(20)
        slider.setMinimum(1)
        slider.setMaximum(100)
        slider.valueChanged.connect(self.update_spinbox)
        self.slider = slider

        spinbox = SpinBox(self)
        spinbox.setValue(20)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setRange(1, 100)
        spinbox.setSingleStep(1)
        spinbox.setFixedWidth(100)
        spinbox.valueChanged.connect(self.update_slider)
        self.spinbox = spinbox

        self.combined = WidgetCombiner(slider, spinbox)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.combined, 0, 2, 1, 3)

        self.setLayout(self.layout)

    # keep spinbox and slider in sync
    def update_spinbox(self, value):
        self.spinbox.setValue(value)

    def update_slider(self, value):
        self.slider.setValue(value)


class ResultW(QFrame):
    """
    Stores the result of a comparison that can be replayed at any time.
    Contains a QLabel, QPushButton (visualize) and QPushButton (copy to clipboard).
    """

    def __init__(self, text, result, replays):
        super().__init__()
        self.result = result
        self.replays = replays
        self.label = QLabel(self)
        self.label.setText(text)

        self.button = QPushButton(self)
        self.button.setText("Visualize")

        self.button_clipboard = QPushButton(self)
        self.button_clipboard.setText("Copy Template")

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.button, 0, 2, 1, 1)
        self.layout.addWidget(self.button_clipboard, 0, 3, 1, 1)

        self.setLayout(self.layout)

class RunWidget(QFrame):
    """
    A single run with QLabel displaying a state (either queued, finished,
    loading replays, comparing, or canceled), and a cancel QPushButton
    if not already finished or canceled.
    """

    def __init__(self, run):
        super().__init__()

        self.status = "Queued"
        self.label = QLabel(self)
        self.text = f"Run with {len(run.checks)} Checks"
        self.label.setText(self.text)

        self.status_label = QLabel(self)
        self.status_label.setText("<b>Status: " + self.status + "</b>")
        self.status_label.setTextFormat(Qt.RichText) # so we can bold it
        self.button = QPushButton(self)
        self.button.setText("Cancel")
        self.button.setFixedWidth(50)
        self.label.setFixedHeight(self.button.size().height()*0.75)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addWidget(self.status_label, 0, 1, 1, 1)
        # needs to be redefined because RunWidget is being called from a
        # different thread or something? get weird errors when not redefined
        SPACER = QSpacerItem(100, 0, QSizePolicy.Maximum, QSizePolicy.Minimum)
        self.layout.addItem(SPACER, 0, 2, 1, 1)
        self.layout.addWidget(self.button, 0, 3, 1, 1)
        self.setLayout(self.layout)

    def update_status(self, status):
        if status in ["Finished", "Invalid arguments"]:
            # not a qt function, pyqt's implementation of deleting a widget
            self.button.deleteLater()

        self.status = status
        self.status_label.setText("<b>Status: " + self.status + "</b>")

    def cancel(self):
        self.status = "Canceled"
        self.button.deleteLater()
        self.status_label.setText("<b>Status: " + self.status + "</b>")



class SliderBoxSetting(LinkableSetting, QFrame):
    """
    A container class of a QLabel, QSlider, and SpinBox, and links the slider
    and spinbox to a setting (ie the default values of the slider and spinbox
    will be the value of the setting, and changes made to the slider or
    spinbox will affect the setting).
    """

    def __init__(self, display, tooltip, setting, max_):
        LinkableSetting.__init__(self, setting)
        QFrame.__init__(self)

        label = QLabel(self)
        label.setText(display)
        label.setToolTip(tooltip)
        self.label = label

        slider = QSlider(Qt.Horizontal)
        slider.setFocusPolicy(Qt.ClickFocus)
        slider.setRange(0, max_)
        slider.setValue(self.setting_value)
        self.slider = slider

        spinbox = SpinBox(self)
        spinbox.setValue(self.setting_value)
        spinbox.setAlignment(Qt.AlignCenter)
        spinbox.setRange(0, max_)
        spinbox.setSingleStep(1)
        spinbox.setFixedWidth(100)
        self.spinbox = spinbox
        self.combined = WidgetCombiner(slider, spinbox)

        self.slider.valueChanged.connect(self.on_setting_changed_from_gui)
        self.spinbox.valueChanged.connect(self.on_setting_changed_from_gui)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.combined, 0, 2, 1, 3)

        self.setLayout(self.layout)

    def on_setting_changed(self, new_value):
        self.slider.setValue(new_value)
        self.spinbox.setValue(new_value)

class LineEditSetting(LinkableSetting, QFrame):
    """
    A container class of a QLabel and InputWidget that links the input widget
    to a setting (ie the default value of the widget will be the value of the
    setting, and changes made to the widget will affect the setting).
    """
    def __init__(self, display, tooltip, type_, setting):
        LinkableSetting.__init__(self, setting)
        QFrame.__init__(self)
        self.input_ = InputWidget(display, tooltip, type_=type_)
        self.input_.field.setText(self.setting_value)
        self.input_.field.textChanged.connect(self.on_setting_changed_from_gui)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.input_)
        self.setLayout(self.layout)

    def on_setting_changed(self, new_value):
        self.input_.field.setText(new_value)

class WidgetCombiner(QFrame):
    def __init__(self, widget1, widget2):
        super(WidgetCombiner, self).__init__()
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(widget1, 0, 0, 1, 1)
        self.layout.addWidget(widget2, 0, 1, 1, 1)
        self.setLayout(self.layout)


class FolderChooser(QFrame):
    path_signal = pyqtSignal(object) # an iterable if multiple_files is True, str otherwise

    def __init__(self, title, path=str(Path.home()), folder_mode=True, multiple_files=False, file_ending="osu! Beatmapfile (*.osu)", display_path=True):
        super(FolderChooser, self).__init__()
        self.highlighted = False
        self.changed = False # if the selection currently differs from the default path
        self.default_path = path
        self.path = path
        self.display_path = display_path
        self.folder_mode = folder_mode
        self.multiple_files = multiple_files
        self.file_ending = file_ending
        self.label = QLabel(self)
        self.label.setText(title+":")

        self.file_chooser_button = QPushButton(self)
        type_ = "Folder" if self.folder_mode else "Files" if self.multiple_files else "File"
        self.file_chooser_button.setText("Choose " + type_)
        # if we didn't have this line only clicking on the label would unhighlight,
        # since the button steals the mouse clicked event
        self.file_chooser_button.clicked.connect(self.reset_highlight)
        self.file_chooser_button.clicked.connect(self.set_dir)

        self.file_chooser_button.setFixedWidth(100)

        self.path_label = QLabel(self)
        if self.display_path:
            self.path_label.setText(path)
        self.combined = WidgetCombiner(self.path_label, self.file_chooser_button)
        self.old_stylesheet = self.combined.styleSheet() # for mousePressedEvent / show_required

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.combined, 0, 2, 1, 3)
        self.setLayout(self.layout)
        self.switch_enabled(True)

    def set_dir(self):
        parent_path_old = self.path if self.folder_mode else str(Path(self.path[0]).parent)
        if self.folder_mode:
            options = QFileDialog.Option()
            options |= QFileDialog.ShowDirsOnly
            options |= QFileDialog.HideNameFilterDetails
            update_path = QFileDialog.getExistingDirectory(caption="Select Folder", directory=parent_path_old, options=options)
        elif self.multiple_files:
            paths = QFileDialog.getOpenFileNames(caption="Select Files", directory=parent_path_old, filter=self.file_ending)
            # qt returns a list of ([path, path, ...], filter) when we use a filter
            update_path = paths[0]
        else:
            paths = QFileDialog.getOpenFileName(caption="Select File", directory=parent_path_old, filter=self.file_ending)
            update_path = paths[0]

        # dont update path if cancel is pressed
        if update_path != [] and update_path != "":
            self.update_dir(update_path)

    def update_dir(self, path):
        self.path = path if path != "" else self.path
        self.changed = True if self.path != self.default_path else False
        if self.display_path:
            if self.multiple_files:
                label = str(Path(self.path).parent)
            elif self.folder_mode:
                label = str(self.path)
            else:
                label = str(ntpath.basename(self.path))
            label = label[:50] + '...' if len(label) > 50 else label
            self.path_label.setText(label)
        self.path_signal.emit(self.path)

    def switch_enabled(self, state):
        self.label.setStyleSheet("color:grey" if not state else "")
        self.path_label.setStyleSheet("color:grey" if not state else "")
        self.file_chooser_button.setEnabled(state)

    def show_required(self):
        self.combined.setStyleSheet(get_setting("required_style"))
        self.highlighted = True

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.reset_highlight()

    # separate function so we can call this method outside of mousePressEvent
    def reset_highlight(self):
        if self.highlighted:
            self.combined.setStyleSheet(self.old_stylesheet)
            self.highlighted = False


class ResetSettings(QFrame):
    def __init__(self):
        super(ResetSettings, self).__init__()
        self.label = QLabel(self)
        self.label.setText("Reset settings:")

        self.button = QPushButton(self)
        self.button.setText("Reset")
        self.button.clicked.connect(self.reset_settings)
        self.button.setFixedWidth(100)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.label, 0, 0, 1, 1)
        self.layout.addItem(SPACER, 0, 1, 1, 1)
        self.layout.addWidget(self.button, 0, 2, 1, 1)
        self.setLayout(self.layout)

    def reset_settings(self):
        prompt = QMessageBox.question(self, "Reset settings",
                                      "Are you sure?\n"
                                      "This will reset all settings to their default value, "
                                      "and the application will quit.",
                                      buttons=QMessageBox.No | QMessageBox.Yes,
                                      defaultButton=QMessageBox.No)
        if prompt == QMessageBox.Yes:
            reset_defaults()
            QCoreApplication.quit()


class BeatmapTest(QFrame):
    def __init__(self):
        super(BeatmapTest, self).__init__()
        self.visualizer_window = None

        self.file_chooser = FolderChooser("Beatmap File", "", folder_mode=False)
        self.label = QLabel(self)
        self.label.setText("Test Beatmap:")

        self.button = QPushButton(self)
        self.button.setText("Visualize")
        self.button.clicked.connect(self.visualize)
        self.button.setFixedWidth(100)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.file_chooser, 0, 0, 1, 3)
        self.layout.addWidget(self.label, 1, 0, 1, 1)
        self.layout.addItem(SPACER, 1, 1, 1, 1)
        self.layout.addWidget(self.button, 1, 2, 1, 1)
        self.setLayout(self.layout)

    def visualize(self):
        self.visualizer_window = VisualizerWindow(beatmap_path=self.file_chooser.path)
        self.visualizer_window.show()


class EntryWidget(QFrame):
    pressed_signal = pyqtSignal(object)
    """
    Represents a single entry of some kind of data, consisting of a title, a button and the data which is stored at self.data.
    When the button is pressed, pressed_signal is emitted with the data for ease of use.
    """
    def __init__(self, title, action_name, data=None):
        super().__init__()
        self.data = data
        self.button = QPushButton(action_name)
        self.button.setFixedWidth(100)
        self.button.clicked.connect(self.button_pressed)
        self.layout = QGridLayout()
        self.layout.addWidget(QLabel(title), 0, 0, 1, 1)
        self.layout.addWidget(self.button, 0, 1, 1, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def button_pressed(self, _):
        self.pressed_signal.emit(self.data)
