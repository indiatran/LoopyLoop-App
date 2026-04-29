import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


def get_ytdlp():
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        return None


class LoopyLoopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Loopy Loop")
        self.root.geometry("1180x650")
        self.root.minsize(1050, 600)
        self.root.resizable(True, True)

        self.video_files = []
        self.audio_path = tk.StringVar()
        self.audio_url = tk.StringVar()
        self.output_path = tk.StringVar()

        self.mode = tk.StringVar(value="hours")
        self.target_hours = tk.StringVar(value="1")
        self.loop_count = tk.StringVar(value="2")
        self.dark_mode = tk.BooleanVar(value=False)

        self.progress_value = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value="0.0%")
        self.status_text = tk.StringVar(value="Ready")
        self.elapsed_text = tk.StringVar(value="Elapsed: 00:00:00")
        self.remaining_text = tk.StringVar(value="Remaining: --:--:--")
        self.processed_text = tk.StringVar(value="Processed: 00:00:00 / 00:00:00")
        self.tool_text = tk.StringVar(value="Checking tools...")

        self.ffmpeg_path = self.find_ffmpeg()
        self.process = None
        self.processing = False
        self.cancel_requested = False
        self.start_time = None
        self.total_seconds = 0

        self.widgets = []
        self.build_ui()
        self.update_tool_text()
        self.apply_theme()

    def find_ffmpeg(self):
        found = shutil.which("ffmpeg")
        if found:
            return found

        if imageio_ffmpeg:
            try:
                return imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                pass

        return None

    def update_tool_text(self):
        ffmpeg_status = "FFmpeg: Ready" if self.ffmpeg_path else "FFmpeg: Missing"
        ytdlp_status = "yt-dlp: Ready" if get_ytdlp() else "yt-dlp: Missing"
        self.tool_text.set(f"{ffmpeg_status} | {ytdlp_status}")

    def add_widget(self, widget, kind):
        self.widgets.append((widget, kind))
        return widget

    def build_ui(self):
        self.main = self.add_widget(tk.Frame(self.root), "root")
        self.main.pack(fill="both", expand=True, padx=14, pady=10)

        self.add_widget(
            tk.Label(self.main, text="🎬 Loopy Loop 🎵", font=("Arial", 26, "bold")),
            "title"
        ).pack()

        self.add_widget(
            tk.Label(
                self.main,
                text="Add videos, use local audio or a YouTube audio URL, then create your looped MP4.",
                font=("Arial", 11)
            ),
            "normal_root"
        ).pack()

        self.add_widget(
            tk.Checkbutton(
                self.main,
                text="🌙 Dark Mode",
                variable=self.dark_mode,
                command=self.apply_theme,
                font=("Arial", 10, "bold")
            ),
            "check"
        ).pack(pady=4)

        self.add_widget(
            tk.Label(self.main, textvariable=self.tool_text, font=("Arial", 10, "bold")),
            "tool"
        ).pack(pady=(0, 8))

        self.content = self.add_widget(tk.Frame(self.main, bd=2, relief="groove"), "card")
        self.content.pack(fill="both", expand=True)

        left = self.add_widget(tk.Frame(self.content), "card")
        left.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        middle = self.add_widget(tk.Frame(self.content), "card")
        middle.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        right = self.add_widget(tk.Frame(self.content), "card")
        right.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        self.add_widget(
            tk.Label(left, text="Input Videos", font=("Arial", 12, "bold")),
            "section"
        ).pack()

        self.video_listbox = self.add_widget(
            tk.Listbox(left, height=14, font=("Arial", 9), justify="center"),
            "listbox"
        )
        self.video_listbox.pack(fill="both", expand=True, pady=6)

        video_buttons = self.add_widget(tk.Frame(left), "card")
        video_buttons.pack(fill="x")

        self.make_button(video_buttons, "Add Videos", "#00A6FF", self.add_videos).pack(
            side="left", expand=True, fill="x", padx=3
        )
        self.make_button(video_buttons, "Remove", "#FF4D6D", self.remove_selected_video).pack(
            side="left", expand=True, fill="x", padx=3
        )
        self.make_button(video_buttons, "Clear", "#9B5DE5", self.clear_videos).pack(
            side="left", expand=True, fill="x", padx=3
        )

        self.file_section(
            middle,
            "Optional Local Audio File",
            self.audio_path,
            self.browse_audio,
            "Browse Audio"
        )

        self.add_widget(
            tk.Label(middle, text="YouTube Audio URL", font=("Arial", 10, "bold")),
            "section"
        ).pack(anchor="w", pady=(10, 0))

        self.url_entry = self.add_widget(
            tk.Entry(middle, textvariable=self.audio_url, justify="center"),
            "entry"
        )
        self.url_entry.pack(fill="x", pady=(2, 2))

        self.add_widget(
            tk.Label(
                middle,
                text="Paste a YouTube URL to auto-convert audio to MP3.",
                font=("Arial", 8)
            ),
            "small"
        ).pack(anchor="w")

        self.file_section(
            middle,
            "Output Video",
            self.output_path,
            self.browse_output,
            "Save As"
        )

        settings = self.add_widget(
            tk.LabelFrame(
                right,
                text="Loop Settings",
                font=("Arial", 10, "bold"),
                padx=10,
                pady=10
            ),
            "labelframe"
        )
        settings.pack(fill="x")

        self.add_widget(
            tk.Radiobutton(settings, text="Target Hours", variable=self.mode, value="hours"),
            "radio"
        ).grid(row=0, column=0, sticky="w")

        self.add_widget(
            tk.Entry(settings, textvariable=self.target_hours, width=10, justify="center"),
            "entry"
        ).grid(row=0, column=1, padx=8)

        self.add_widget(
            tk.Label(settings, text="hours"),
            "normal_card"
        ).grid(row=0, column=2)

        self.add_widget(
            tk.Radiobutton(settings, text="Loop Count", variable=self.mode, value="loops"),
            "radio"
        ).grid(row=1, column=0, sticky="w", pady=5)

        self.add_widget(
            tk.Entry(settings, textvariable=self.loop_count, width=10, justify="center"),
            "entry"
        ).grid(row=1, column=1, padx=8)

        self.add_widget(
            tk.Label(settings, text="loops"),
            "normal_card"
        ).grid(row=1, column=2)

        progress = self.add_widget(
            tk.LabelFrame(
                right,
                text="Progress",
                font=("Arial", 10, "bold"),
                padx=10,
                pady=10
            ),
            "labelframe"
        )
        progress.pack(fill="x", pady=14)

        ttk.Progressbar(
            progress,
            variable=self.progress_value,
            maximum=100,
            mode="determinate"
        ).pack(fill="x")

        self.add_widget(
            tk.Label(progress, textvariable=self.progress_text, font=("Arial", 10, "bold")),
            "accent"
        ).pack(pady=(5, 0))

        self.add_widget(tk.Label(progress, textvariable=self.status_text), "status").pack()
        self.add_widget(tk.Label(progress, textvariable=self.elapsed_text), "normal_card").pack()
        self.add_widget(tk.Label(progress, textvariable=self.remaining_text), "normal_card").pack()
        self.add_widget(tk.Label(progress, textvariable=self.processed_text), "normal_card").pack()

        button_bar = self.add_widget(tk.Frame(self.main), "root")
        button_bar.pack(fill="x", pady=(10, 0))

        self.start_button = self.make_button(button_bar, "▶ START", "#7B2CBF", self.start_job)
        self.start_button.pack(side="left", expand=True, fill="x", padx=5)

        self.cancel_button = self.make_button(button_bar, "⛔ CANCEL", "#FF006E", self.cancel_job)
        self.cancel_button.pack(side="left", expand=True, fill="x", padx=5)
        self.cancel_button.config(state="disabled")

        self.folder_button = self.make_button(button_bar, "📂 FOLDER", "#06D6A0", self.open_output_folder)
        self.folder_button.pack(side="left", expand=True, fill="x", padx=5)

    def file_section(self, parent, title, variable, command, button_text):
        self.add_widget(
            tk.Label(parent, text=title, font=("Arial", 10, "bold")),
            "section"
        ).pack(anchor="w")

        row = self.add_widget(tk.Frame(parent), "card")
        row.pack(fill="x", pady=(2, 8))

        self.add_widget(
            tk.Entry(row, textvariable=variable, justify="center"),
            "entry"
        ).pack(side="left", fill="x", expand=True)

        self.make_button(row, button_text, "#00A6FF", command).pack(side="left", padx=(8, 0))

    def apply_theme(self):
        if self.dark_mode.get():
            theme = {
                "root": "#17172B",
                "card": "#24243E",
                "text": "#F8F7FF",
                "title": "#F15BB5",
                "section": "#00F5D4",
                "accent": "#FEE440",
                "tool": "#00BBF9",
                "entry": "#33334D",
                "status": "#FF4D6D"
            }
        else:
            theme = {
                "root": "#FFF3B0",
                "card": "#FFFFFF",
                "text": "#222222",
                "title": "#7B2CBF",
                "section": "#0077B6",
                "accent": "#9B5DE5",
                "tool": "#0081A7",
                "entry": "#FFFFFF",
                "status": "#FF006E"
            }

        self.root.configure(bg=theme["root"])

        for widget, kind in self.widgets:
            try:
                if kind == "root":
                    widget.configure(bg=theme["root"])
                elif kind == "card":
                    widget.configure(bg=theme["card"])
                elif kind == "title":
                    widget.configure(bg=theme["root"], fg=theme["title"])
                elif kind == "normal_root":
                    widget.configure(bg=theme["root"], fg=theme["text"])
                elif kind == "normal_card":
                    widget.configure(bg=theme["card"], fg=theme["text"])
                elif kind == "section":
                    widget.configure(bg=theme["card"], fg=theme["section"])
                elif kind == "accent":
                    widget.configure(bg=theme["card"], fg=theme["accent"])
                elif kind == "tool":
                    widget.configure(bg=theme["root"], fg=theme["tool"])
                elif kind == "small":
                    widget.configure(bg=theme["card"], fg=theme["text"])
                elif kind == "status":
                    widget.configure(bg=theme["card"], fg=theme["status"])
                elif kind == "entry":
                    widget.configure(
                        bg=theme["entry"],
                        fg=theme["text"],
                        insertbackground=theme["text"]
                    )
                elif kind == "listbox":
                    widget.configure(
                        bg=theme["entry"],
                        fg=theme["text"],
                        selectbackground=theme["title"]
                    )
                elif kind == "check":
                    widget.configure(
                        bg=theme["root"],
                        fg=theme["text"],
                        selectcolor=theme["entry"],
                        activebackground=theme["root"],
                        activeforeground=theme["text"]
                    )
                elif kind == "radio":
                    widget.configure(
                        bg=theme["card"],
                        fg=theme["text"],
                        selectcolor=theme["entry"],
                        activebackground=theme["card"],
                        activeforeground=theme["text"]
                    )
                elif kind == "labelframe":
                    widget.configure(bg=theme["card"], fg=theme["title"])
            except tk.TclError:
                pass

    def make_button(self, parent, text, color, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            height=2,
            activebackground=color,
            activeforeground="white"
        )

    def add_videos(self):
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[
                ("Video Files", "*.mp4 *.mov *.avi *.mkv *.wmv"),
                ("MP4 Files", "*.mp4"),
                ("All Files", "*.*")
            ]
        )

        for file in files:
            if file not in self.video_files:
                self.video_files.append(file)
                self.video_listbox.insert(tk.END, os.path.basename(file))

        if self.video_files and not self.output_path.get().strip():
            folder = os.path.dirname(self.video_files[0])
            self.output_path.set(os.path.join(folder, "loopy_loop_output.mp4"))

    def remove_selected_video(self):
        selected = self.video_listbox.curselection()
        if selected:
            index = selected[0]
            self.video_files.pop(index)
            self.video_listbox.delete(index)

    def clear_videos(self):
        self.video_files.clear()
        self.video_listbox.delete(0, tk.END)

    def browse_audio(self):
        file = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio/MP4 Files", "*.mp3 *.wav *.aac *.m4a *.ogg *.mp4"),
                ("MP3 Files", "*.mp3"),
                ("MP4 Files", "*.mp4"),
                ("All Files", "*.*")
            ]
        )

        if file:
            self.audio_path.set(file)

    def browse_output(self):
        file = filedialog.asksaveasfilename(
            title="Save Output Video",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )

        if file:
            self.output_path.set(file)

    def get_creation_flags(self):
        return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    def format_time(self, seconds):
        if seconds is None or seconds < 0:
            return "--:--:--"

        seconds = int(seconds)
        return f"{seconds // 3600:02}:{(seconds % 3600) // 60:02}:{seconds % 60:02}"

    def safe_ui(self, func):
        self.root.after(0, func)

    def get_duration(self, path):
        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg was not found. Run: python -m pip install imageio-ffmpeg")

        cmd = [self.ffmpeg_path, "-hide_banner", "-i", path]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=self.get_creation_flags()
        )

        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stdout)

        if not match:
            raise RuntimeError(f"Unable to read duration:\n{path}")

        return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))

    def validate_inputs(self):
        if not self.ffmpeg_path:
            raise ValueError(
                "FFmpeg was not found.\n\n"
                "Run this in VS Code terminal:\n"
                "python -m pip install imageio-ffmpeg"
            )

        if not self.video_files:
            raise ValueError("Please add at least one video.")

        output = self.output_path.get().strip()

        if not output:
            raise ValueError("Please choose an output file.")

        local_audio = self.audio_path.get().strip()
        url_audio = self.audio_url.get().strip()

        if local_audio and url_audio:
            raise ValueError("Use either a local audio file OR a YouTube URL, not both.")

        if local_audio and not os.path.exists(local_audio):
            raise ValueError("The selected local audio file does not exist.")

        if url_audio and get_ytdlp() is None:
            raise ValueError(
                "yt-dlp is not installed in this Python environment.\n\n"
                "Run this in your VS Code terminal:\n"
                "python -m pip install yt-dlp"
            )

        for video in self.video_files:
            if not os.path.exists(video):
                raise ValueError(f"This video does not exist:\n{video}")

            if os.path.abspath(video).lower() == os.path.abspath(output).lower():
                raise ValueError("Output file cannot be the same as an input video.")

        total_playlist = sum(self.get_duration(v) for v in self.video_files)

        if self.mode.get() == "hours":
            try:
                duration = float(self.target_hours.get().strip()) * 3600
            except ValueError:
                raise ValueError("Target hours must be a valid number.")
        else:
            try:
                duration = total_playlist * int(self.loop_count.get().strip())
            except ValueError:
                raise ValueError("Loop count must be a whole number.")

        if duration <= 0:
            raise ValueError("Duration must be greater than 0.")

        return output, local_audio, url_audio, duration

    def create_concat_file(self):
        temp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".txt",
            mode="w",
            encoding="utf-8"
        )

        for video in self.video_files:
            safe_path = video.replace("\\", "/").replace("'", "'\\''")
            temp.write(f"file '{safe_path}'\n")

        temp.close()
        return temp.name

    def download_youtube_audio(self, url, temp_dir):
        yt_dlp = get_ytdlp()

        if yt_dlp is None:
            raise RuntimeError("yt-dlp missing. Run: python -m pip install yt-dlp")

        self.safe_ui(lambda: self.status_text.set("Downloading YouTube audio..."))

        output_template = os.path.join(temp_dir, "youtube_audio.%(ext)s")

        options = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "ffmpeg_location": os.path.dirname(self.ffmpeg_path)
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

        mp3_path = os.path.join(temp_dir, "youtube_audio.mp3")

        if not os.path.exists(mp3_path):
            raise RuntimeError("YouTube audio could not be converted to MP3.")

        return mp3_path

    def set_progress(self, current):
        percent = max(0, min(100, (current / self.total_seconds) * 100))
        elapsed = time.time() - self.start_time if self.start_time else 0

        remaining = None

        if current > 0 and elapsed > 0:
            speed = current / elapsed
            if speed > 0:
                remaining = (self.total_seconds - current) / speed

        def update():
            self.progress_value.set(percent)
            self.progress_text.set(f"{percent:.1f}%")
            self.elapsed_text.set(f"Elapsed: {self.format_time(elapsed)}")
            self.remaining_text.set(f"Remaining: {self.format_time(remaining)}")
            self.processed_text.set(
                f"Processed: {self.format_time(current)} / {self.format_time(self.total_seconds)}"
            )

        self.safe_ui(update)

    def set_busy(self, busy):
        self.processing = busy

        def update():
            self.start_button.config(state="disabled" if busy else "normal")
            self.cancel_button.config(state="normal" if busy else "disabled")
            self.folder_button.config(state="disabled" if busy else "normal")

        self.safe_ui(update)

    def start_job(self):
        if self.processing:
            return

        try:
            output, local_audio, url_audio, duration = self.validate_inputs()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.total_seconds = duration
        self.cancel_requested = False
        self.progress_value.set(0)
        self.progress_text.set("0.0%")
        self.status_text.set("Starting...")
        self.elapsed_text.set("Elapsed: 00:00:00")
        self.remaining_text.set("Remaining: --:--:--")
        self.processed_text.set(f"Processed: 00:00:00 / {self.format_time(duration)}")

        threading.Thread(
            target=self.run_ffmpeg,
            args=(output, local_audio, url_audio),
            daemon=True
        ).start()

    def run_ffmpeg(self, output, local_audio, url_audio):
        self.set_busy(True)
        self.start_time = time.time()
        concat_file = None
        temp_dir = tempfile.mkdtemp(prefix="loopy_loop_")

        try:
            audio = local_audio

            if url_audio:
                audio = self.download_youtube_audio(url_audio, temp_dir)

            concat_file = self.create_concat_file()

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-nostats",
                "-stream_loop", "-1",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file
            ]

            if audio:
                cmd += [
                    "-stream_loop", "-1",
                    "-i", audio,
                    "-map", "0:v:0",
                    "-map", "1:a:0"
                ]
            else:
                cmd += [
                    "-map", "0:v:0",
                    "-map", "0:a:0?"
                ]

            cmd += [
                "-t", str(self.total_seconds),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-progress", "pipe:1",
                output
            ]

            self.safe_ui(lambda: self.status_text.set("Creating looped video..."))

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=self.get_creation_flags()
            )

            last_seconds = 0
            error_lines = []

            for line in self.process.stdout:
                if self.cancel_requested:
                    self.process.terminate()
                    break

                line = line.strip()

                if line.startswith("out_time_ms="):
                    try:
                        seconds = int(line.split("=", 1)[1]) / 1_000_000

                        if seconds >= last_seconds:
                            last_seconds = seconds
                            self.set_progress(seconds)
                    except ValueError:
                        pass

                elif line.startswith("out_time="):
                    seconds = self.time_to_seconds(line.split("=", 1)[1])

                    if seconds is not None and seconds >= last_seconds:
                        last_seconds = seconds
                        self.set_progress(seconds)

                elif line and not line.startswith(
                    ("frame=", "fps=", "stream_", "bitrate=", "total_size=", "speed=", "progress=")
                ):
                    error_lines.append(line)

            return_code = self.process.wait()
            self.process = None

            if self.cancel_requested:
                self.safe_ui(lambda: self.status_text.set("Cancelled"))
                self.safe_ui(lambda: messagebox.showinfo("Cancelled", "Processing was cancelled."))
                return

            if return_code != 0:
                raise RuntimeError("\n".join(error_lines[-12:]) or "FFmpeg failed.")

            self.set_progress(self.total_seconds)
            self.safe_ui(lambda: self.status_text.set("Completed"))
            self.safe_ui(lambda: messagebox.showinfo("Done", f"Finished!\nSaved to:\n{output}"))

        except Exception as e:
            self.safe_ui(lambda: self.status_text.set("Error"))
            self.safe_ui(lambda: messagebox.showerror("Error", str(e)))

        finally:
            if concat_file and os.path.exists(concat_file):
                try:
                    os.remove(concat_file)
                except Exception:
                    pass

            shutil.rmtree(temp_dir, ignore_errors=True)
            self.set_busy(False)

    def time_to_seconds(self, text):
        try:
            h, m, s = text.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            return None

    def cancel_job(self):
        self.cancel_requested = True
        self.status_text.set("Cancelling...")

        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass

    def open_output_folder(self):
        path = self.output_path.get().strip()

        if not path:
            messagebox.showerror("Error", "No output file selected yet.")
            return

        folder = os.path.dirname(path) or os.getcwd()

        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LoopyLoopApp(root)
    root.mainloop()