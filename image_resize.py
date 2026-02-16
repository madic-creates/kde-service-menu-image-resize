#!/usr/bin/python3
"""KDE Service Menu - Image Resize with ImageMagick."""

import os
import re
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QToolButton,
    QVBoxLayout,
)


class HelpButton(QToolButton):
    """A small '?' button that shows a help popup when clicked."""

    def __init__(self, title, help_text, parent=None):
        super().__init__(parent)
        self.setText("?")
        self.setFixedSize(24, 24)
        self._title = title
        self._help_text = help_text
        self.clicked.connect(self._show_help)

    def _show_help(self):
        QMessageBox.information(self, self._title, self._help_text)


class ResizeDialog(QDialog):
    """Dialog for image resize settings."""

    def __init__(self, file_count, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Resize")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        info = QLabel(f"Resize {file_count} image{'s' if file_count > 1 else ''}")
        info.setStyleSheet("font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(info)

        form = QFormLayout()

        # --- Resize resolution ---
        resize_row = QHBoxLayout()
        self.resize_input = QLineEdit("1920")
        self.resize_input.setPlaceholderText("e.g. 1920x1080, 1920x, x1080")
        resize_row.addWidget(self.resize_input)
        resize_row.addWidget(
            HelpButton(
                "Resize - Help",
                "Specify the target resolution for the image.\n\n"
                "Supported formats:\n"
                "  1920x1080 - Fit within width x height (aspect ratio preserved)\n"
                "  1920x or 1920 - Set width, auto-calculate height\n"
                "  x1080 - Set height, auto-calculate width\n\n"
                "Aspect ratio is ALWAYS preserved by default.\n"
                "When both dimensions are given, the image is scaled to fit\n"
                "within those bounds without distortion.\n\n"
                "To force an exact size (ignoring aspect ratio), append '!'\n"
                "  e.g. 1920x1080!",
            )
        )
        form.addRow("Resolution:", resize_row)

        # --- Lanczos filter checkbox ---
        filter_row = QHBoxLayout()
        self.lanczos_check = QCheckBox("Enable Lanczos Filter")
        self.lanczos_check.setChecked(True)
        filter_row.addWidget(self.lanczos_check)
        filter_row.addWidget(
            HelpButton(
                "Lanczos Filter - Help",
                "The Lanczos resampling filter is a high-quality interpolation\n"
                "algorithm used when resizing images.\n\n"
                "How it works:\n"
                "  Lanczos uses a windowed sinc function to interpolate pixel\n"
                "  values during resizing. It samples multiple neighboring\n"
                "  pixels to calculate each new pixel value.\n\n"
                "Benefits:\n"
                "  - Preserves sharp edges and fine details\n"
                "  - Reduces aliasing artifacts (jagged edges)\n"
                "  - Superior results for photographic images\n"
                "  - Widely considered the best general-purpose resize filter\n\n"
                "When to disable:\n"
                "  - If you need faster processing and quality is less important\n"
                "  - If you prefer ImageMagick's default filter selection",
            )
        )
        filter_row.addStretch()
        form.addRow("Filter:", filter_row)

        # --- Unsharp mask ---
        unsharp_row = QHBoxLayout()
        self.unsharp_check = QCheckBox()
        self.unsharp_check.setChecked(True)
        self.unsharp_check.toggled.connect(self._toggle_unsharp)
        unsharp_row.addWidget(self.unsharp_check)
        self.unsharp_input = QLineEdit("0x1")
        self.unsharp_input.setPlaceholderText("e.g. 0x1")
        unsharp_row.addWidget(self.unsharp_input)
        unsharp_row.addWidget(
            HelpButton(
                "Unsharp Mask - Help",
                "Unsharp masking is a sharpening technique that enhances\n"
                "edge contrast, making images appear sharper after resizing.\n\n"
                "Format: radiusxsigma\n"
                "  Radius - Size of the area for contrast comparison.\n"
                "           Use 0 for automatic selection (recommended).\n"
                "  Sigma  - Strength of the sharpening effect.\n"
                "           Higher values produce stronger sharpening.\n\n"
                "Common values:\n"
                "  0x0.5 - Very subtle sharpening\n"
                "  0x1   - Subtle sharpening (recommended)\n"
                "  0x2   - Moderate sharpening\n"
                "  0x3   - Strong sharpening\n\n"
                "Uncheck to skip unsharp masking entirely.",
            )
        )
        form.addRow("Unsharp:", unsharp_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _toggle_unsharp(self, checked):
        self.unsharp_input.setEnabled(checked)

    def _validate_and_accept(self):
        resize = self.resize_input.text().strip()
        if not resize:
            QMessageBox.warning(self, "Validation Error", "Resolution is required.")
            return

        if not re.match(r"^[0-9]+x?[0-9]*!?$|^x[0-9]+!?$", resize):
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Invalid resolution: {resize}\n\n"
                "Expected formats: 1920x1080, 1920x, x1080, or 1920",
            )
            return

        if self.unsharp_check.isChecked():
            unsharp = self.unsharp_input.text().strip()
            if not unsharp:
                QMessageBox.warning(
                    self, "Validation Error", "Unsharp value is required when enabled."
                )
                return
            if not re.match(r"^[0-9]+(\.[0-9]+)?x[0-9]+(\.[0-9]+)?$", unsharp):
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    f"Invalid unsharp value: {unsharp}\n\n"
                    "Expected format: radiusxsigma (e.g. 0x1)",
                )
                return

        self.accept()

    def get_settings(self):
        return {
            "resize": self.resize_input.text().strip(),
            "lanczos": self.lanczos_check.isChecked(),
            "unsharp": self.unsharp_input.text().strip()
            if self.unsharp_check.isChecked()
            else "",
        }


def build_command(input_file, output_file, settings):
    cmd = ["magick", input_file]
    if settings["lanczos"]:
        cmd.extend(["-filter", "Lanczos"])
    if settings["unsharp"]:
        cmd.extend(["-unsharp", settings["unsharp"]])
    cmd.extend(["-resize", settings["resize"]])
    cmd.append(output_file)
    return cmd


def get_output_path(input_file):
    path = Path(input_file)
    return str(path.parent / f"{path.stem}_resized{path.suffix}")


def notify(title, body, icon="transform-scale"):
    subprocess.run(["notify-send", "-a", "Image Resize", "-i", icon, title, body])


def main():
    files = sys.argv[1:]
    if not files:
        subprocess.run(["kdialog", "--error", "No files selected."])
        sys.exit(1)

    app = QApplication(sys.argv[:1])

    if subprocess.run(["which", "magick"], capture_output=True).returncode != 0:
        QMessageBox.critical(
            None, "Error", "ImageMagick is not installed.\nPlease install it first."
        )
        sys.exit(1)

    dialog = ResizeDialog(len(files))
    if dialog.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    settings = dialog.get_settings()

    progress = QProgressDialog("Resizing images...", "Cancel", 0, len(files))
    progress.setWindowTitle("Image Resize")
    progress.setMinimumDuration(0)

    errors = []
    success = []
    for i, input_file in enumerate(files):
        if progress.wasCanceled():
            break

        progress.setLabelText(f"Processing: {os.path.basename(input_file)}")
        progress.setValue(i)
        app.processEvents()

        output_file = get_output_path(input_file)
        cmd = build_command(input_file, output_file, settings)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            errors.append(f"{os.path.basename(input_file)}: {result.stderr.strip()}")
        else:
            success.append(os.path.basename(output_file))

    progress.setValue(len(files))

    if errors:
        notify("Image Resize Failed",
               "Errors:\n" + "\n".join(errors),
               "dialog-error")
    elif not progress.wasCanceled():
        notify(f"Resized {len(success)} image{'s' if len(success) > 1 else ''}",
               "\n".join(success))


if __name__ == "__main__":
    main()
