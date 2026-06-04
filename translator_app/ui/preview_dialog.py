from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from translator_app.subtitle import SubtitleBlock, parse_srt


class PreviewDialog(QDialog):
    def __init__(self, video_path: Path, subtitle_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Subtitle Preview")
        self.resize(960, 640)
        self.blocks = self._load_subtitles(subtitle_path)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.video = QVideoWidget(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.audio.setVolume(0.8)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setMinimumHeight(72)
        self.subtitle_label.setStyleSheet(
            "QLabel { background: #111; color: white; padding: 12px; font-family: 'Malgun Gothic', 'Segoe UI', Arial; font-size: 18px; font-weight: 600; }"
        )

        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.open_video_button = QPushButton("Open Video")
        self.open_subtitle_button = QPushButton("Open Subtitle")
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)

        self.play_button.clicked.connect(self.player.play)
        self.pause_button.clicked.connect(self.player.pause)
        self.open_video_button.clicked.connect(self.choose_video)
        self.open_subtitle_button.clicked.connect(self.choose_subtitle)
        self.position_slider.sliderMoved.connect(self.player.setPosition)
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.position_slider.setMaximum)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.open_video_button)
        controls.addWidget(self.open_subtitle_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.video, 1)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.position_slider)
        layout.addLayout(controls)

        self.set_video(video_path)

    def set_video(self, video_path: Path) -> None:
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))

    def choose_video(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Open video",
            "",
            "Video files (*.mp4 *.webm *.mkv *.mov *.avi);;All files (*.*)",
        )
        if selected:
            self.set_video(Path(selected))

    def choose_subtitle(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Open subtitle",
            "",
            "Subtitle files (*.srt);;All files (*.*)",
        )
        if selected:
            self.blocks = self._load_subtitles(Path(selected))
            self.on_position_changed(self.player.position())

    def on_position_changed(self, position_ms: int) -> None:
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(position_ms)
        self.position_slider.blockSignals(False)
        self.subtitle_label.setText(self._subtitle_at(position_ms / 1000))

    def _subtitle_at(self, seconds: float) -> str:
        for block in self.blocks:
            if block.start <= seconds <= block.end:
                return block.text
        return ""

    @staticmethod
    def _load_subtitles(path: Path) -> list[SubtitleBlock]:
        if not path.exists():
            return []
        return parse_srt(path.read_text(encoding="utf-8"))
