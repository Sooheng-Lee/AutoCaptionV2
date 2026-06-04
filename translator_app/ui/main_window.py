from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from translator_app.config import AppConfig, load_config, save_config
from translator_app.events import JobOptions, JobResult
from translator_app.job import SubtitleJob
from translator_app.storage import safe_filename
from translator_app.ui.preview_dialog import PreviewDialog
from translator_app.ui.settings_dialog import SettingsDialog
from translator_app.youtube import YouTubeClient, validate_youtube_url


LANGUAGE_LABEL_TO_VALUE = {
    "한국어": "Korean",
    "영어": "English",
    "일본어": "Japanese",
    "중국어": "Chinese",
    "스페인어": "Spanish",
    "프랑스어": "French",
    "독일어": "German",
}
LANGUAGE_VALUE_TO_LABEL = {value: label for label, value in LANGUAGE_LABEL_TO_VALUE.items()}


class JobWorker(QThread):
    progress_changed = pyqtSignal(str, int, str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, options: JobOptions):
        super().__init__()
        self.options = options

    def run(self) -> None:
        try:
            job = SubtitleJob(self.options, self.progress_changed.emit)
            self.completed.emit(job.run())
        except Exception as exc:
            self.failed.emit(str(exc))


class VideoDownloadWorker(QThread):
    progress_changed = pyqtSignal(str, int, str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, url: str, output_dir: Path, quality: str):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.quality = quality

    def run(self) -> None:
        try:
            if not validate_youtube_url(self.url):
                raise RuntimeError("Invalid YouTube URL.")
            client = YouTubeClient(self.output_dir)
            self.progress_changed.emit("Metadata", 5, "Reading YouTube metadata.")
            metadata = client.fetch_metadata(self.url)
            self.progress_changed.emit("Download", 20, "Downloading video file.")
            media = client.download(self.url, metadata["title"], True, self.quality)
            self.completed.emit(
                JobResult(
                    output_dir=self.output_dir / safe_filename(metadata["title"]),
                    media_file=media,
                    metadata=metadata,
                )
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Subtitle Translator")
        self.config = load_config()
        self.worker: JobWorker | None = None
        self.download_worker: VideoDownloadWorker | None = None
        self.last_result: JobResult | None = None
        self.preview_dialog: PreviewDialog | None = None
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(14)

        header = QHBoxLayout()
        logo = QLabel("▶")
        logo.setObjectName("youtubeLogo")
        title = QLabel("YouTube Subtitle Translator")
        title.setObjectName("appTitle")
        self.settings_button = QPushButton("⚙")
        self.settings_button.setObjectName("iconButton")
        self.settings_button.clicked.connect(self.open_settings)
        header.addWidget(logo)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.settings_button)
        layout.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(16)
        layout.addLayout(content, 1)
        left = QVBoxLayout()
        left.setSpacing(12)
        right = QVBoxLayout()
        right.setSpacing(12)
        content.addLayout(left, 1)
        content.addLayout(right, 1)

        url_card, url_layout = self._card("YouTube 영상 URL 입력")
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("youtube.com/watch?v=...")
        self.analyze_button = QPushButton("분석")
        self.analyze_button.clicked.connect(self.analyze_url)
        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(self.analyze_button)
        url_layout.addLayout(url_row)
        video_box = QFrame()
        video_box.setObjectName("videoSummary")
        video_layout = QHBoxLayout(video_box)
        thumbnail = QLabel("▶")
        thumbnail.setObjectName("thumbnail")
        self.video_title_label = QLabel("영상을 분석하면 제목과 길이가 표시됩니다.")
        self.video_title_label.setObjectName("videoTitle")
        self.video_meta_label = QLabel("채널 / 길이")
        self.video_duration_label = QLabel("")
        info_col = QVBoxLayout()
        info_col.addWidget(self.video_title_label)
        info_col.addWidget(self.video_meta_label)
        info_col.addWidget(self.video_duration_label)
        info_col.addStretch()
        video_layout.addWidget(thumbnail)
        video_layout.addLayout(info_col, 1)
        url_layout.addWidget(video_box)
        left.addWidget(url_card)

        settings_card, settings_layout = self._card("자막 설정")
        controls_layout = QGridLayout()
        controls_layout.setHorizontalSpacing(14)
        controls_layout.setVerticalSpacing(8)
        self.language_combo = QComboBox()
        self.language_combo.addItems(list(LANGUAGE_LABEL_TO_VALUE))
        self.language_combo.setCurrentText(LANGUAGE_VALUE_TO_LABEL.get(self.config.target_language, "한국어"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["srt"])
        self.speech_combo = QComboBox()
        self.speech_combo.addItems(["faster-whisper-tiny", "faster-whisper-small"])
        self.speech_combo.setCurrentText(self.config.speech_model)
        self.gemma_input = QLineEdit(self.config.gemma_model)
        self.download_video = QCheckBox("영상 다운로드 포함")
        self.download_video.setChecked(True)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["best", "1080p", "720p"])
        self.output_input = QLineEdit(self.config.output_dir)
        self.output_browse = QPushButton("찾기")
        self.output_browse.clicked.connect(self.choose_output_dir)
        controls_layout.addWidget(QLabel("음성인식 모델"), 0, 0)
        controls_layout.addWidget(self.speech_combo, 0, 1, 1, 3)
        controls_layout.addWidget(QLabel("번역 대상 언어"), 1, 0)
        controls_layout.addWidget(self.language_combo, 1, 1)
        controls_layout.addWidget(QLabel("Gemma 모델"), 1, 2)
        controls_layout.addWidget(self.gemma_input, 1, 3)
        controls_layout.addWidget(QLabel("자막 형식"), 2, 0)
        controls_layout.addWidget(self.format_combo, 2, 1)
        controls_layout.addWidget(QLabel("영상 품질"), 2, 2)
        controls_layout.addWidget(self.quality_combo, 2, 3)
        controls_layout.addWidget(QLabel("저장 경로"), 3, 0)
        controls_layout.addWidget(self.output_input, 3, 1, 1, 2)
        controls_layout.addWidget(self.output_browse, 3, 3)
        settings_layout.addLayout(controls_layout)
        option_row = QHBoxLayout()
        option_row.addWidget(self.download_video)
        option_row.addStretch()
        settings_layout.addLayout(option_row)
        self.start_button = QPushButton("자막 생성 및 번역 시작")
        self.start_button.setObjectName("primaryButton")
        self.download_button = QPushButton("영상만 다운로드")
        self.preview_button = QPushButton("자막 프리뷰")
        self.open_output_button = QPushButton("저장 폴더 열기")
        self.start_button.clicked.connect(self.start_job)
        self.download_button.clicked.connect(self.download_video_only)
        self.preview_button.clicked.connect(self.open_preview)
        self.open_output_button.clicked.connect(self.open_output_folder)
        settings_layout.addWidget(self.start_button)
        actions = QHBoxLayout()
        actions.addWidget(self.download_button)
        actions.addWidget(self.preview_button)
        actions.addWidget(self.open_output_button)
        settings_layout.addLayout(actions)
        left.addWidget(settings_card, 1)

        model_card, model_layout = self._card("모델 설치 상태")
        model_grid = QGridLayout()
        self.model_status_whisper = self._status_badge("Whisper 준비 대기", "ok")
        self.model_status_gemma = self._status_badge("Gemma 준비 대기", "warn")
        model_grid.addWidget(QLabel("음성인식"), 0, 0)
        model_grid.addWidget(self.model_status_whisper, 0, 1)
        model_grid.addWidget(QLabel("번역 모델"), 1, 0)
        model_grid.addWidget(self.model_status_gemma, 1, 1)
        model_layout.addLayout(model_grid)
        right.addWidget(model_card)

        progress_card, progress_layout = self._card("작업 진행 현황")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusText")
        progress_layout.addWidget(self.progress)
        progress_layout.addWidget(self.status_label)
        self.step_labels = {
            "Metadata": QLabel("○ 영상 정보 조회 대기"),
            "Model": QLabel("○ 모델 확인 대기"),
            "Download": QLabel("○ 미디어 다운로드 대기"),
            "Transcription": QLabel("○ 음성인식 대기"),
            "Translation": QLabel("○ Gemma 번역 대기"),
            "Save": QLabel("○ 결과 저장 대기"),
        }
        for label in self.step_labels.values():
            label.setObjectName("stepLabel")
            progress_layout.addWidget(label)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        progress_layout.addWidget(self.log)
        right.addWidget(progress_card, 1)

        result_card, result_layout = self._card("결과 파일 목록")
        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(lambda item: self.open_path(Path(item.data(256))))
        result_layout.addWidget(self.results)
        right.addWidget(result_card)

        footer = QHBoxLayout()
        footer.addWidget(QLabel("v1.0 MVP"))
        footer.addStretch()
        self.accel_label = QLabel("GPU 가속: 사용 중" if self.config.use_gpu else "GPU 가속: 꺼짐")
        footer.addWidget(self.accel_label)
        layout.addLayout(footer)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                font-family: "Malgun Gothic", "Segoe UI", Arial;
                font-size: 14px;
                color: #0f1720;
                background: #eaf4fd;
            }
            QLabel#appTitle {
                font-size: 24px;
                font-weight: 800;
            }
            QLabel#youtubeLogo {
                background: #ff1f1f;
                color: white;
                border-radius: 7px;
                padding: 3px 8px;
                font-weight: 800;
            }
            QLabel#cardTitle {
                font-size: 20px;
                font-weight: 800;
                background: transparent;
            }
            QFrame#card {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid #b9ccdc;
                border-radius: 8px;
            }
            QFrame#videoSummary {
                background: rgba(255, 255, 255, 0.65);
                border: 1px solid #c6d6e4;
                border-radius: 8px;
            }
            QLabel#thumbnail {
                min-width: 168px;
                max-width: 168px;
                min-height: 96px;
                background: #c7d0d8;
                color: #6b7780;
                border-radius: 8px;
                font-size: 34px;
                qproperty-alignment: AlignCenter;
            }
            QLabel#videoTitle {
                font-size: 18px;
                font-weight: 800;
                background: transparent;
            }
            QLabel#statusBadgeOk {
                background: #d7f0df;
                color: #096b3a;
                border-radius: 8px;
                padding: 8px 10px;
                font-weight: 700;
            }
            QLabel#statusBadgeWarn {
                background: #fff0cd;
                color: #8a5300;
                border-radius: 8px;
                padding: 8px 10px;
                font-weight: 700;
            }
            QLabel#statusText, QLabel#stepLabel {
                background: transparent;
                font-size: 15px;
            }
            QPushButton {
                padding: 8px 12px;
                border: 1px solid #9fb8ce;
                border-radius: 7px;
                background: #dcecf8;
                font-weight: 700;
            }
            QPushButton#primaryButton {
                background: #4e8fbe;
                color: white;
                border-color: #4e8fbe;
                min-height: 34px;
            }
            QPushButton#iconButton {
                min-width: 34px;
                max-width: 34px;
                border-radius: 17px;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QListWidget {
                padding: 7px;
                border: 1px solid #9fb8ce;
                border-radius: 7px;
                background: rgba(255, 255, 255, 0.86);
            }
            QProgressBar {
                min-height: 18px;
                border: 0;
                border-radius: 9px;
                background: #c8dcec;
            }
            QProgressBar::chunk {
                border-radius: 9px;
                background: #4e8fbe;
            }
            """
        )

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label)
        return frame, layout

    def _status_badge(self, text: str, kind: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("statusBadgeOk" if kind == "ok" else "statusBadgeWarn")
        return label

    def _set_busy(self, busy: bool) -> None:
        self.start_button.setEnabled(not busy)
        self.download_button.setEnabled(not busy)

    def choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select output folder", self.output_input.text())
        if selected:
            self.output_input.setText(selected)

    def analyze_url(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Enter a YouTube URL first.")
            return
        try:
            self.append_log("Reading YouTube metadata.")
            metadata = YouTubeClient(Path(self.output_input.text())).fetch_metadata(url)
            self.video_title_label.setText(metadata.get("title") or "Unknown title")
            channel = metadata.get("channel") or "Unknown channel"
            duration = self._format_duration(int(metadata.get("duration") or 0))
            self.video_meta_label.setText(channel)
            self.video_duration_label.setText(duration)
            self.append_log("URL analysis completed.")
        except Exception as exc:
            self.append_log(f"[Error] {exc}")
            QMessageBox.warning(self, "Analysis failed", str(exc))

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.config = dialog.apply_to_config()
            save_config(self.config)
            self.output_input.setText(self.config.output_dir)
            self.gemma_input.setText(self.config.gemma_model)
            self.append_log("Settings saved.")

    def start_job(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Job running", "A subtitle job is already running.")
            return
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Enter a YouTube URL first.")
            return

        self.config.output_dir = self.output_input.text().strip()
        self.config.target_language = self._target_language()
        self.config.subtitle_format = self.format_combo.currentText()
        self.config.speech_model = self.speech_combo.currentText()
        self.config.gemma_model = self.gemma_input.text().strip() or "gemma4"
        save_config(self.config)
        if self.config.use_gpu:
            self.append_log("GPU mode is enabled. If CUDA DLLs are missing, transcription will retry on CPU.")
        else:
            self.append_log("CPU mode is enabled for transcription.")

        options = JobOptions(
            url=url,
            target_language=self.config.target_language,
            subtitle_format=self.config.subtitle_format,
            speech_model=self.config.speech_model,
            gemma_model=self.config.gemma_model,
            output_dir=Path(self.config.output_dir),
            model_dir=Path(self.config.model_dir),
            download_video=self.download_video.isChecked(),
            video_quality=self.quality_combo.currentText(),
            auto_download_models=self.config.auto_download_models,
            use_gpu=self.config.use_gpu,
            chunk_minutes=self.config.chunk_minutes,
            max_tokens=self.config.max_tokens,
            ollama_url=self.config.ollama_url,
        )

        self.results.clear()
        self.progress.setValue(0)
        self._set_busy(True)
        self.append_log("Starting subtitle job.")
        self.worker = JobWorker(options)
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def download_video_only(self) -> None:
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.information(self, "Download running", "A video download is already running.")
            return
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Enter a YouTube URL first.")
            return

        self.config.output_dir = self.output_input.text().strip()
        save_config(self.config)
        self.results.clear()
        self.progress.setValue(0)
        self._set_busy(True)
        self.append_log("Starting video download.")
        self.download_worker = VideoDownloadWorker(
            url,
            Path(self.config.output_dir),
            self.quality_combo.currentText(),
        )
        self.download_worker.progress_changed.connect(self.on_progress)
        self.download_worker.completed.connect(self.on_completed)
        self.download_worker.failed.connect(self.on_failed)
        self.download_worker.start()

    def on_progress(self, stage: str, value: int, message: str) -> None:
        self.status_label.setText(f"{stage}: {message}")
        self.progress.setValue(max(0, min(100, value)))
        if hasattr(self, "step_labels") and stage in self.step_labels:
            self.step_labels[stage].setText(f"● {self._stage_label(stage)} 진행 중")
        if stage == "Model":
            if "Whisper" in message or "faster-whisper" in message:
                self.model_status_whisper.setText("Whisper 준비 완료")
                self.model_status_whisper.setObjectName("statusBadgeOk")
            if "Gemma" in message or "Ollama" in message:
                self.model_status_gemma.setText("Gemma 확인 중")
                self.model_status_gemma.setObjectName("statusBadgeWarn")
            self._refresh_style(self.model_status_whisper)
            self._refresh_style(self.model_status_gemma)
        self.append_log(f"[{stage}] {message}")

    def on_completed(self, result: JobResult) -> None:
        self.last_result = result
        self._set_busy(False)
        self.status_label.setText("Completed")
        self.progress.setValue(100)
        for stage, label in getattr(self, "step_labels", {}).items():
            label.setText(f"● {self._stage_label(stage)} 완료")
        self.model_status_whisper.setText("Whisper 설치됨")
        self.model_status_gemma.setText("Gemma 준비됨")
        self.model_status_gemma.setObjectName("statusBadgeOk")
        self._refresh_style(self.model_status_whisper)
        self._refresh_style(self.model_status_gemma)
        if result.metadata:
            self.video_title_label.setText(result.metadata.get("title") or self.video_title_label.text())
            self.video_meta_label.setText(result.metadata.get("channel") or self.video_meta_label.text())
            self.video_duration_label.setText(self._format_duration(int(result.metadata.get("duration") or 0)))
        self.append_log("Job completed.")
        self._add_result("Source subtitle", result.source_subtitle)
        self._add_result("Translated subtitle", result.translated_subtitle)
        self._add_result("Media file", result.media_file)
        self._add_result("Output folder", result.output_dir)

    def on_failed(self, message: str) -> None:
        self._set_busy(False)
        self.status_label.setText("Failed")
        if "cublas64_12.dll" in message or "CUDA" in message:
            message = (
                f"{message}\n\n"
                "CUDA GPU libraries are not available. Open Settings and turn off "
                "`Use GPU when available`, then run the job again."
            )
        self.append_log(f"[Error] {message}")
        QMessageBox.critical(self, "Job failed", message)

    @staticmethod
    def _stage_label(stage: str) -> str:
        return {
            "Metadata": "영상 정보 조회",
            "Model": "모델 확인",
            "Download": "미디어 다운로드",
            "Transcription": "음성인식",
            "Translation": "Gemma 번역",
            "Save": "결과 저장",
        }.get(stage, stage)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds <= 0:
            return ""
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours}:{minutes:02}:{secs:02}"
        return f"{minutes}:{secs:02}"

    @staticmethod
    def _refresh_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def open_preview(self) -> None:
        video_path = self._find_preview_video()
        subtitle_path = self._find_preview_subtitle()
        if not video_path:
            QMessageBox.warning(
                self,
                "Video not found",
                "Download the video first or enable `Download video file` before creating subtitles.",
            )
            return
        if not subtitle_path:
            QMessageBox.warning(self, "Subtitle not found", "Create translated subtitles first.")
            return
        self.preview_dialog = PreviewDialog(video_path, subtitle_path, self)
        self.preview_dialog.show()

    def _find_preview_video(self) -> Path | None:
        if self.last_result and self.last_result.media_file and self._is_video_file(self.last_result.media_file):
            return self.last_result.media_file
        folder = self.last_result.output_dir if self.last_result else Path(self.output_input.text())
        if not folder.exists():
            return None
        for pattern in ("video.mp4", "video.webm", "video.mkv", "*.mp4", "*.webm", "*.mkv", "*.mov", "*.avi"):
            for match in sorted(folder.glob(pattern)):
                if self._is_video_file(match):
                    return match
        return None

    def _find_preview_subtitle(self) -> Path | None:
        if self.last_result and self.last_result.translated_subtitle and self.last_result.translated_subtitle.exists():
            return self.last_result.translated_subtitle
        folder = self.last_result.output_dir if self.last_result else Path(self.output_input.text())
        if not folder.exists():
            return None
        preferred = folder / f"{self._target_language().lower()}.srt"
        if preferred.exists():
            return preferred
        matches = sorted(folder.glob("*.srt"))
        return matches[0] if matches else None

    @staticmethod
    def _is_video_file(path: Path) -> bool:
        if path.stem.lower().startswith("audio"):
            return False
        return path.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".avi"}

    def _target_language(self) -> str:
        return LANGUAGE_LABEL_TO_VALUE.get(self.language_combo.currentText(), self.language_combo.currentText())

    def _add_result(self, label: str, path: Path | None) -> None:
        if not path:
            return
        item_text = f"{label}: {path}"
        self.results.addItem(item_text)
        item = self.results.item(self.results.count() - 1)
        item.setData(256, str(path))

    def append_log(self, message: str) -> None:
        self.log.appendPlainText(message)

    def open_output_folder(self) -> None:
        target = self.last_result.output_dir if self.last_result else Path(self.output_input.text())
        self.open_path(target)

    def open_path(self, path: Path) -> None:
        if not path.exists():
            QMessageBox.warning(self, "Path not found", str(path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
