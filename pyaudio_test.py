import pyaudio
import numpy as np
import matplotlib.pyplot as plt

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100

p = pyaudio.PyAudio()

# WASAPI loopback device
device_index = None
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info.get('name').lower().find('loopback') != -1:
        device_index = i

if device_index is None:
    print("No loopback device found via name – trying WASAPI default.")
    device_index = p.get_default_output_device_info()['index']

print(device_index)

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK)

print("Recording...")
frames = []
for _ in range(100):
    data = stream.read(CHUNK)
    frames.append(np.frombuffer(data, dtype=np.int16))

stream.stop_stream()
stream.close()
p.terminate()

# Plot
data = np.hstack(frames)
plt.plot(data)
plt.show()
