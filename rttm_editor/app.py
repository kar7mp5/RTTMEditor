import os
import torchaudio
import sounddevice as sd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time


class RTTMEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("RTTM Editor")
        self.root.geometry("950x650")  # Increased height for input fields

        self.audio_path = None
        self.waveform = None
        self.sr = None
        self.playback_pos = 0
        self.is_playing = False
        self.total_duration = 0
        self.play_thread = None
        self.volume = 1.0
        self.rttm_path = None  

        self.create_widgets()

    def create_widgets(self):
        # Top control panel
        frame_top = tk.Frame(self.root)
        frame_top.pack(pady=5)

        # Audio selection and control buttons
        self.load_audio_btn = tk.Button(frame_top, text="Select Audio", command=self.load_audio)
        self.load_audio_btn.grid(row=0, column=0, padx=5)

        self.load_rttm_btn = tk.Button(frame_top, text="Load RTTM", command=self.load_rttm)
        self.load_rttm_btn.grid(row=0, column=1, padx=5)

        self.save_rttm_btn = tk.Button(frame_top, text="Save RTTM", command=self.save_rttm)
        self.save_rttm_btn.grid(row=0, column=2, padx=5)

        self.play_audio_btn = tk.Button(frame_top, text="Play", command=self.play_audio)
        self.play_audio_btn.grid(row=0, column=3, padx=5)

        self.stop_audio_btn = tk.Button(frame_top, text="Stop", command=self.stop_audio)
        self.stop_audio_btn.grid(row=0, column=4, padx=5)

        # Label to show the loaded audio file
        self.audio_label = tk.Label(frame_top, text="No audio loaded", fg="blue")
        self.audio_label.grid(row=0, column=5, padx=10)

        # Seek bar (progress bar for playback)
        frame_seek = tk.Frame(self.root)
        frame_seek.pack(pady=10)

        self.seek_bar = tk.Scale(frame_seek, from_=0, to=100, orient=tk.HORIZONTAL, length=600, showvalue=0)
        self.seek_bar.grid(row=0, column=0, padx=5)
        self.seek_bar.bind("<ButtonRelease-1>", self.seek_audio)

        # Label to show the current playback time
        self.time_label = tk.Label(frame_seek, text="00:00 / 00:00", fg="black")
        self.time_label.grid(row=0, column=1, padx=10)

        # Volume control slider
        frame_volume = tk.Frame(self.root)
        frame_volume.pack(pady=5)

        tk.Label(frame_volume, text="Volume:").grid(row=0, column=0, padx=5)
        self.volume_slider = tk.Scale(frame_volume, from_=0, to=100, orient=tk.HORIZONTAL, length=200, command=self.update_volume)
        self.volume_slider.set(100)
        self.volume_slider.grid(row=0, column=1, padx=5)

        # Table for RTTM entries
        self.tree = ttk.Treeview(self.root, columns=("Start Time", "End Time", "Speaker"), show="headings")
        self.tree.heading("Start Time", text="Start Time (s)")
        self.tree.heading("End Time", text="End Time (s)")
        self.tree.heading("Speaker", text="Speaker ID")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Bottom input panel for adding new entries
        frame_bottom = tk.Frame(self.root)
        frame_bottom.pack(pady=5)

        tk.Label(frame_bottom, text="Start Time:").grid(row=0, column=0, padx=5)
        self.start_time_input = tk.Entry(frame_bottom, width=8)
        self.start_time_input.grid(row=0, column=1, padx=5)

        tk.Label(frame_bottom, text="End Time:").grid(row=0, column=2, padx=5)
        self.end_time_input = tk.Entry(frame_bottom, width=8)
        self.end_time_input.grid(row=0, column=3, padx=5)

        tk.Label(frame_bottom, text="Speaker ID:").grid(row=0, column=4, padx=5)
        self.speaker_input = tk.Entry(frame_bottom, width=8)
        self.speaker_input.grid(row=0, column=5, padx=5)

        self.add_entry_btn = tk.Button(frame_bottom, text="Add Label", command=self.add_entry)
        self.add_entry_btn.grid(row=0, column=6, padx=5)

        self.delete_entry_btn = tk.Button(frame_bottom, text="Delete", command=self.delete_entry)
        self.delete_entry_btn.grid(row=0, column=7, padx=5)

        self.clear_all_btn = tk.Button(frame_bottom, text="Clear All", command=self.clear_entries)
        self.clear_all_btn.grid(row=0, column=8, padx=5)

    def update_volume(self, event=None):
        self.volume = self.volume_slider.get() / 100.0

    def play_audio(self):
        """ Play audio from the current position """
        if self.audio_path and self.waveform is not None:
            self.is_playing = True
            self.play_thread = threading.Thread(target=self._play, daemon=True)
            self.play_thread.start()

    def _play(self):
        """ Internal function to handle audio playback with synchronization """
        start_sample = int(self.playback_pos * self.sr)
        adjusted_waveform = self.waveform[start_sample:] * self.volume

        start_time = time.time() - self.playback_pos
        sd.play(adjusted_waveform, samplerate=self.sr)

        while self.is_playing and self.playback_pos < self.total_duration:
            elapsed_time = time.time() - start_time
            self.playback_pos = min(self.total_duration, elapsed_time)
            self.seek_bar.set(self.playback_pos)
            self.update_time_label(self.playback_pos)
            time.sleep(0.05)

        self.is_playing = False

    def stop_audio(self):
        self.is_playing = False
        sd.stop()

    def seek_audio(self, event):
        self.playback_pos = self.seek_bar.get()
        self.update_time_label(self.playback_pos)

        if self.is_playing:
            sd.stop()
            self.play_audio()

    def update_time_label(self, current_time):
        def format_time(seconds):
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            return f"{minutes:02}:{seconds:02}"

        self.time_label.config(text=f"{format_time(current_time)} / {format_time(self.total_duration)}")

    def load_audio(self):
        """ Loads an audio file and prepares it for playback. """
        file_path = filedialog.askopenfilename(title="Select Audio File", filetypes=[("Audio Files", "*.wav")])
        if file_path:
            self.audio_path = file_path
            self.audio_label.config(text=f"Loaded: {os.path.basename(file_path)}")

            # Load the audio file
            waveform, sr = torchaudio.load(self.audio_path)
            self.sr = 16000  # Set the desired sample rate
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=self.sr)
            self.waveform = resampler(waveform).mean(dim=0).numpy()  # Convert stereo to mono by averaging channels

            self.total_duration = len(self.waveform) / self.sr  # Calculate the total duration in seconds
            self.seek_bar.config(to=self.total_duration)  # Adjust the seek bar range

            self.update_time_label(0)  # Initialize the time label display

    def save_rttm(self):
        """ Saves the current table data to an RTTM file. """
        file_path = filedialog.asksaveasfilename(title="Save RTTM File", filetypes=[("RTTM Files", "*.rttm")], defaultextension=".rttm")
        if file_path:
            with open(file_path, "w") as file:
                for item in self.tree.get_children():
                    start_time, end_time, speaker = self.tree.item(item, "values")
                    duration = float(end_time) - float(start_time)  # Calculate the duration
                    file.write(f"SPEAKER unknown 1 {start_time} {duration:.2f} <NA> <NA> {speaker} <NA>\n")  # Write RTTM format

    def load_rttm(self):
        """ Loads an RTTM file and populates the table with its content. """
        file_path = filedialog.askopenfilename(title="Select RTTM File", filetypes=[("RTTM Files", "*.rttm")])
        if file_path:
            self.rttm_path = file_path
            self.tree.delete(*self.tree.get_children())  # Clear existing table data

            # Read the RTTM file and extract relevant information
            with open(self.rttm_path, "r") as file:
                for line in file:
                    parts = line.strip().split()
                    start_time = parts[3]  # Start time of the speech segment
                    duration = parts[4]  # Duration of the segment
                    speaker = parts[7]  # Speaker ID
                    self.tree.insert("", "end", values=(start_time, str(float(start_time) + float(duration)), speaker))  # Add entry to table

    def add_entry(self):
        """ Adds a new entry to the RTTM table. """
        start_time = self.start_time_input.get()
        end_time = self.end_time_input.get()
        speaker = self.speaker_input.get()
        if start_time and end_time and speaker:
            self.tree.insert("", "end", values=(start_time, end_time, speaker))  # Insert new row into the table

    def delete_entry(self):
        """ Deletes the selected table entry (or multiple entries). """
        selected_items = self.tree.selection()  # Get selected rows
        if selected_items:
            for item in selected_items:
                self.tree.delete(item)  # Delete multiple selected entries
        else:
            messagebox.showwarning("Selection Error", "Please select one or more entries to delete.")  # Warn if nothing is selected

    def clear_entries(self):
        """ Deletes all entries from the RTTM table. """
        confirm = messagebox.askyesno("Clear All", "Are you sure you want to delete all entries?")
        if confirm:
            self.tree.delete(*self.tree.get_children())  # Remove all table entries