import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import imageio_ffmpeg


class VideoDuplicatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Duplicator App")
        self.root.geometry("640x580")
        self.root.minsize(580, 520)
        self.root.configure(bg="#FFF4E6")
        self.root.resizable(True, True)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.audio_path = tk.StringVar()
        self.duplicate_count = tk.StringVar(value="2")
        self.target_hours = tk.StringVar(value="10")
        self.mode = tk.StringVar(value="hours")
        self.status_text = tk.StringVar(value="Ready")
        self.progress_text = tk.StringVar(value="0%")

        self.is_processing = False
        self.last_output_file = ""

        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.ffprobe_exe = self.find_ffprobe()

        self.build_ui()
        self.root.bind("<Return>", self.enter_key_pressed)

    def find_ffprobe(self):
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            return ffprobe

        ffmpeg_dir = os.path.dirname(self.ffmpeg_exe)
        name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
        possible = os.path.join(ffmpeg_dir, name)
        if os.path.exists(possible):
            return possible

        return None

    def build_ui(self):
        title = tk.Label(
            self.root,
            text="🎬 Video Duplicator 🎨",
            font=("Arial", 20, "bold"),
            bg="#FFF4E6",
            fg="#FF6B6B"
        )
        title.pack(pady=(12, 6))

        subtitle = tk.Label(
            self.root,
            text="Select your video, add audio (opt.), choose duplication mode, then click ENTER",
            font=("Arial", 10),
            bg="#FFF4E6",
            fg="#6A4C93"
        )
        subtitle.pack(pady=(0, 10))

        main_frame = tk.Frame(self.root, bg="#FFFFFF", bd=3, relief="ridge")
        main_frame.pack(padx=14, pady=10, fill="both", expand=True)

        content = tk.Frame(main_frame, bg="#FFFFFF")
        content.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            content, text="Input Video:", font=("Arial", 11, "bold"),
            bg="#FFFFFF", fg="#1982C4"
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        tk.Entry(content, textvariable=self.input_path, font=("Arial", 10)).grid(
            row=1, column=0, sticky="ew", padx=(0, 10)
        )
        tk.Button(
            content, text="Browse Input", command=self.browse_input,
            font=("Arial", 10, "bold"), bg="#4D96FF", fg="white"
        ).grid(row=1, column=1, sticky="ew")

        tk.Label(
            content, text="Output Video:", font=("Arial", 11, "bold"),
            bg="#FFFFFF", fg="#1982C4"
        ).grid(row=2, column=0, sticky="w", pady=(14, 4))
        tk.Entry(content, textvariable=self.output_path, font=("Arial", 10)).grid(
            row=3, column=0, sticky="ew", padx=(0, 10)
        )
        tk.Button(
            content, text="Browse Output", command=self.browse_output,
            font=("Arial", 10, "bold"), bg="#6BCB77", fg="white"
        ).grid(row=3, column=1, sticky="ew")

        tk.Label(
            content, text="Optional Audio File:", font=("Arial", 11, "bold"),
            bg="#FFFFFF", fg="#1982C4"
        ).grid(row=4, column=0, sticky="w", pady=(14, 4))
        tk.Entry(content, textvariable=self.audio_path, font=("Arial", 10)).grid(
            row=5, column=0, sticky="ew", padx=(0, 10)
        )
        tk.Button(
            content, text="Browse Audio", command=self.browse_audio,
            font=("Arial", 10, "bold"), bg="#FF922B", fg="white"
        ).grid(row=5, column=1, sticky="ew")

        tk.Label(
            content, text="Choose Duplication Mode:", font=("Arial", 11, "bold"),
            bg="#FFFFFF", fg="#FF922B"
        ).grid(row=6, column=0, sticky="w", pady=(16, 6))

        tk.Radiobutton(
            content, text="Duplicate by number of times", variable=self.mode, value="count",
            font=("Arial", 10), bg="#FFFFFF", selectcolor="#FFD6A5"
        ).grid(row=7, column=0, sticky="w")

        tk.Radiobutton(
            content, text="Loop until target hours", variable=self.mode, value="hours",
            font=("Arial", 10), bg="#FFFFFF", selectcolor="#FFD6A5"
        ).grid(row=8, column=0, sticky="w")

        fields = tk.Frame(content, bg="#FFFFFF")
        fields.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(14, 8))

        tk.Label(
            fields, text="Duplicate Count:", font=("Arial", 10, "bold"),
            bg="#FFFFFF", fg="#9D4EDD"
        ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        tk.Entry(fields, textvariable=self.duplicate_count, width=14, font=("Arial", 10)).grid(
            row=0, column=1, sticky="w", pady=6
        )

        tk.Label(
            fields, text="Target Hours:", font=("Arial", 10, "bold"),
            bg="#FFFFFF", fg="#9D4EDD"
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        tk.Entry(fields, textvariable=self.target_hours, width=14, font=("Arial", 10)).grid(
            row=1, column=1, sticky="w", pady=6
        )

        self.status_label = tk.Label(
            content,
            textvariable=self.status_text,
            font=("Arial", 11, "bold"),
            bg="#FFFFFF",
            fg="#06D6A0"
        )
        self.status_label.grid(row=10, column=0, columnspan=2, pady=(12, 8))

        progress_frame = tk.Frame(content, bg="#FFFFFF")
        progress_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(4, 12))

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            length=400
        )
        self.progress_bar.pack(fill="x", expand=True, padx=4)

        self.progress_label = tk.Label(
            progress_frame,
            textvariable=self.progress_text,
            font=("Arial", 10, "bold"),
            bg="#FFFFFF",
            fg="#845EC2"
        )
        self.progress_label.pack(pady=(6, 0))

        buttons = tk.Frame(content, bg="#FFFFFF")
        buttons.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        self.start_button = tk.Button(
            buttons,
            text="▶ START / ENTER",
            font=("Arial", 12, "bold"),
            bg="#845EC2",
            fg="white",
            height=2,
            command=self.start_processing
        )
        self.start_button.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.folder_button = tk.Button(
            buttons,
            text="📂 Open Output Folder",
            font=("Arial", 12, "bold"),
            bg="#00C2A8",
            fg="white",
            height=2,
            command=self.open_output_folder
        )
        self.folder_button.pack(side="left", fill="x", expand=True, padx=(6, 0))

        content.grid_columnconfigure(0, weight=1)

    def browse_input(self):
        path = filedialog.askopenfilename(
            title="Select Input Video",
            filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")]
        )
        if path:
            self.input_path.set(path)
            base, _ = os.path.splitext(path)
            self.output_path.set(f"{base}_duplicated.mp4")

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save Output Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 Files", "*.mp4")]
        )
        if path:
            self.output_path.set(path)

    def browse_audio(self):
        path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[("Audio Files", "*.mp3 *.wav *.aac *.m4a")]
        )
        if path:
            self.audio_path.set(path)

    def enter_key_pressed(self, event):
        self.start_processing()

    def set_status(self, text):
        self.root.after(0, lambda: self.status_text.set(text))

    def set_progress(self, percent):
        percent = max(0, min(100, percent))

        def update():
            self.progress_bar.config(mode="determinate")
            self.progress_bar["value"] = percent
            self.progress_text.set(f"{percent:.1f}%")

        self.root.after(0, update)

    def reset_progress(self):
        def update():
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")
            self.progress_bar["value"] = 0
            self.progress_text.set("0%")

        self.root.after(0, update)

    def start_progress_animation(self):
        def update():
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start(10)
            self.progress_text.set("Starting...")

        self.root.after(0, update)

    def stop_progress_animation(self):
        def update():
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")

        self.root.after(0, update)

    def set_processing_state(self, busy):
        def update():
            self.is_processing = busy
            state = "disabled" if busy else "normal"
            self.start_button.config(state=state)
            self.folder_button.config(state=state)

        self.root.after(0, update)

    def show_error(self, message):
        self.root.after(0, lambda: messagebox.showerror("Error", message))

    def show_success(self, message):
        self.root.after(0, lambda: messagebox.showinfo("Success", message))

    def get_media_duration(self, input_file):
        if not self.ffprobe_exe:
            raise RuntimeError("ffprobe was not found. Count mode needs ffprobe installed.")

        cmd = [
            self.ffprobe_exe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 or not result.stdout.strip():
            raise RuntimeError("Could not read media duration for progress tracking.")

        return float(result.stdout.strip())

    def build_ffmpeg_command_hours(self, input_file, output_file, target_seconds, audio_file=None):
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-stats_period", "1",
            "-stream_loop", "-1",
            "-i", input_file
        ]

        if audio_file:
            cmd += [
                "-stream_loop", "-1",
                "-i", audio_file,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-t", str(target_seconds),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                output_file
            ]
        else:
            cmd += [
                "-t", str(target_seconds),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                output_file
            ]

        return cmd

    def build_ffmpeg_command_count(self, input_file, output_file, count, audio_file=None):
        loop_count = count - 1

        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-stats_period", "1",
            "-stream_loop", str(loop_count),
            "-i", input_file
        ]

        if audio_file:
            cmd += [
                "-stream_loop", str(loop_count),
                "-i", audio_file,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                output_file
            ]
        else:
            cmd += [
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                output_file
            ]

        return cmd

    def start_processing(self):
        if self.is_processing:
            return

        input_file = self.input_path.get().strip()
        output_file = self.output_path.get().strip()
        audio_file = self.audio_path.get().strip()
        selected_mode = self.mode.get().strip()

        if not input_file:
            messagebox.showerror("Error", "Please select an input video.")
            return

        if not os.path.exists(input_file):
            messagebox.showerror("Error", "The selected video file does not exist.")
            return

        if audio_file and not os.path.exists(audio_file):
            messagebox.showerror("Error", "The selected audio file does not exist.")
            return

        if not output_file:
            base, _ = os.path.splitext(input_file)
            output_file = f"{base}_duplicated.mp4"
            self.output_path.set(output_file)

        if os.path.abspath(input_file).lower() == os.path.abspath(output_file).lower():
            messagebox.showerror("Error", "Input and output cannot be the same file.")
            return

        try:
            if selected_mode == "count":
                count = int(self.duplicate_count.get())
                if count < 1:
                    raise ValueError("Duplicate count must be at least 1.")
                worker = threading.Thread(
                    target=self.run_ffmpeg_job_count,
                    args=(input_file, output_file, count, audio_file if audio_file else None),
                    daemon=True
                )
            else:
                hours = float(self.target_hours.get())
                if hours <= 0:
                    raise ValueError("Target hours must be greater than 0.")
                target_seconds = int(hours * 3600)
                worker = threading.Thread(
                    target=self.run_ffmpeg_job_hours,
                    args=(input_file, output_file, target_seconds, audio_file if audio_file else None),
                    daemon=True
                )

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        worker.start()

    def run_ffmpeg_job_hours(self, input_file, output_file, target_seconds, audio_file):
        self.set_processing_state(True)
        self.reset_progress()
        self.start_progress_animation()
        self.set_status("Starting FFmpeg...")

        try:
            cmd = self.build_ffmpeg_command_hours(
                input_file=input_file,
                output_file=output_file,
                target_seconds=target_seconds,
                audio_file=audio_file
            )

            cmd = cmd[:-1] + ["-progress", "pipe:1", "-nostats", cmd[-1]]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                bufsize=1
            )

            got_real_progress = False

            for line in process.stdout:
                line = line.strip()

                if line.startswith("out_time_ms="):
                    try:
                        out_time_ms = int(line.split("=")[1])
                        out_time_seconds = out_time_ms / 1_000_000
                        percent = (out_time_seconds / target_seconds) * 100

                        if not got_real_progress:
                            got_real_progress = True
                            self.stop_progress_animation()

                        self.set_progress(percent)
                        self.set_status(f"Processing video... {percent:.1f}%")
                    except Exception:
                        pass

                elif line.startswith("progress=end"):
                    self.stop_progress_animation()
                    self.set_progress(100)
                    self.set_status("Finalizing output...")

            stderr_output = process.stderr.read()
            return_code = process.wait()

            if return_code != 0:
                raise RuntimeError(stderr_output.strip() or "FFmpeg failed.")

            self.last_output_file = output_file
            self.stop_progress_animation()
            self.set_progress(100)
            self.set_status("Done! Video created successfully.")
            self.show_success(f"Video saved successfully:\n{output_file}")

        except Exception as e:
            self.stop_progress_animation()
            self.set_status("Error occurred.")
            self.show_error(str(e))

        finally:
            self.set_processing_state(False)

    def run_ffmpeg_job_count(self, input_file, output_file, count, audio_file):
        self.set_processing_state(True)
        self.reset_progress()
        self.start_progress_animation()
        self.set_status("Starting FFmpeg...")

        try:
            target_seconds = self.get_media_duration(input_file) * count

            cmd = self.build_ffmpeg_command_count(
                input_file=input_file,
                output_file=output_file,
                count=count,
                audio_file=audio_file
            )

            cmd = cmd[:-1] + ["-progress", "pipe:1", "-nostats", cmd[-1]]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                bufsize=1
            )

            got_real_progress = False

            for line in process.stdout:
                line = line.strip()

                if line.startswith("out_time_ms="):
                    try:
                        out_time_ms = int(line.split("=")[1])
                        out_time_seconds = out_time_ms / 1_000_000
                        percent = (out_time_seconds / target_seconds) * 100

                        if not got_real_progress:
                            got_real_progress = True
                            self.stop_progress_animation()

                        self.set_progress(percent)
                        self.set_status(f"Processing video... {percent:.1f}%")
                    except Exception:
                        pass

                elif line.startswith("progress=end"):
                    self.stop_progress_animation()
                    self.set_progress(100)
                    self.set_status("Finalizing output...")

            stderr_output = process.stderr.read()
            return_code = process.wait()

            if return_code != 0:
                raise RuntimeError(stderr_output.strip() or "FFmpeg failed.")

            self.last_output_file = output_file
            self.stop_progress_animation()
            self.set_progress(100)
            self.set_status("Done! Video created successfully.")
            self.show_success(f"Video saved successfully:\n{output_file}")

        except Exception as e:
            self.stop_progress_animation()
            self.set_status("Error occurred.")
            self.show_error(str(e))

        finally:
            self.set_processing_state(False)

    def open_output_folder(self):
        output_file = self.output_path.get().strip() or self.last_output_file

        if not output_file:
            messagebox.showerror("Error", "No output folder available yet.")
            return

        folder = os.path.dirname(output_file)
        if not os.path.exists(folder):
            messagebox.showerror("Error", "Output folder does not exist yet.")
            return

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
    app = VideoDuplicatorApp(root)
    root.mainloop()