from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from translator_app.config import AppConfig


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.config = config

        self.output_dir = QLineEdit(config.output_dir)
        self.model_dir = QLineEdit(config.model_dir)
        self.ollama_url = QLineEdit(config.ollama_url)
        self.auto_download = QCheckBox("Enable automatic model download")
        self.auto_download.setChecked(config.auto_download_models)
        self.confirm_download = QCheckBox("Ask before model download")
        self.confirm_download.setChecked(config.confirm_model_download)
        self.use_gpu = QCheckBox("Use GPU when available")
        self.use_gpu.setChecked(config.use_gpu)
        self.keep_temp = QCheckBox("Keep temporary files")
        self.keep_temp.setChecked(config.keep_temp_files)

        self.chunk_minutes = QSpinBox()
        self.chunk_minutes.setRange(1, 60)
        self.chunk_minutes.setValue(config.chunk_minutes)
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(1000, 200000)
        self.max_tokens.setSingleStep(1000)
        self.max_tokens.setValue(config.max_tokens)

        form = QFormLayout()
        form.addRow("Output folder", self._path_row(self.output_dir))
        form.addRow("Model folder", self._path_row(self.model_dir))
        form.addRow("Ollama URL", self.ollama_url)
        form.addRow("Chunk minutes", self.chunk_minutes)
        form.addRow("Max tokens", self.max_tokens)
        form.addRow("", self.auto_download)
        form.addRow("", self.confirm_download)
        form.addRow("", self.use_gpu)
        form.addRow("", self.keep_temp)

        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Application settings"))
        layout.addLayout(form)
        layout.addLayout(buttons)

    def _path_row(self, edit: QLineEdit):
        row = QHBoxLayout()
        browse = QPushButton("Browse")
        browse.clicked.connect(lambda: self._browse(edit))
        row.addWidget(edit)
        row.addWidget(browse)
        return row

    def _browse(self, edit: QLineEdit) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select folder", edit.text())
        if selected:
            edit.setText(selected)

    def apply_to_config(self) -> AppConfig:
        self.config.output_dir = self.output_dir.text().strip()
        self.config.model_dir = self.model_dir.text().strip()
        self.config.ollama_url = self.ollama_url.text().strip()
        self.config.auto_download_models = self.auto_download.isChecked()
        self.config.confirm_model_download = self.confirm_download.isChecked()
        self.config.use_gpu = self.use_gpu.isChecked()
        self.config.keep_temp_files = self.keep_temp.isChecked()
        self.config.chunk_minutes = self.chunk_minutes.value()
        self.config.max_tokens = self.max_tokens.value()
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.model_dir).mkdir(parents=True, exist_ok=True)
        return self.config

