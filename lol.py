import subprocess

# Paths to your audio files
audio_file_1 = "rta_best_final.m4a"
audio_file_2 = "rta_amen.ogg"

# Command to launch MPV with the first audio file
command_1 = ["mpv", audio_file_1]

# Command to launch MPV with the second audio file
command_2 = ["mpv", audio_file_2]

# Launch the first instance of MPV
subprocess.Popen(command_1)

# Launch the second instance of MPV
subprocess.Popen(command_2)

print("Launched two MPV instances playing different audio files.")
