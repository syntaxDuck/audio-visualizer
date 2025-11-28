"""Show a text-mode spectrogram using live microphone data."""

import argparse
import math
import sys
import queue

import numpy as np
import sounddevice as sd

from matplotlib.animation import FuncAnimation
import matplotlib.cm as cm
import matplotlib.pyplot as plt

usage_line = " press <enter> to quit, +<enter> or -<enter> to change scaling "


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


q = queue.Queue()

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    "-l",
    "--list-devices",
    action="store_true",
    help="show list of audio devices and exit",
)
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser],
)

parser.add_argument(
    "-d",
    "--device",
    required=True,
    type=int_or_str,
    help="input device: (numeric ID or substring)",
)
parser.add_argument(
    "-s",
    "--samplerate",
    type=float,
    help="sampling rate of audio device (default is devices native samplerate)",
)
parser.add_argument(
    "-i",
    "--interval",
    type=float,
    default=75,
    help="interval in which graph is updated (in milliseconds, default: %(default)s ms)",
)
parser.add_argument(
    "-r",
    "--range",
    type=float,
    nargs=2,
    metavar=("LOW", "HIGH"),
    default=[0, 20000],
    help="frequency range (default: %(default)s Hz)",
)
parser.add_argument(
    "-g",
    "--gain",
    type=float,
    default=10,
    help="initial gain factor (default: %(default)s)",
)
parser.add_argument(
    "-b",
    "--bands",
    type=int,
    default=100,
    help="number of frequency bands represented (default: %(default)s)",
)
parser.add_argument(
    "--cmap",
    type=str,
    choices=plt.colormaps(),
    default="plasma",
    help="color gradient used for frequency bands (default: %(default)s)",
)
args = parser.parse_args(remaining)


def setup_graph(bands, low, interval, cmap_str):
    cmap = plt.get_cmap(cmap_str)

    plt.rcParams["toolbar"] = "none"
    fig, ax = plt.subplots()

    bars = ax.bar(range(len(plotdata)), plotdata, width=1.0)
    ax.axis((0, len(plotdata), 0, 1))
    ax.set_yticks([0])
    ax.yaxis.grid(True)
    ax.tick_params(
        bottom=False,
        top=False,
        labelbottom=False,
        right=False,
        left=False,
        labelleft=False,
    )
    fig.canvas.manager.toolmanager = None
    fig.tight_layout(pad=0)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    for xpos in range(10, bands, 10):
        ax.axvline(x=xpos, color="gray", linestyle="--", linewidth=0.5, alpha=0.5)

        label = int(low + xpos * delta_f)
        ax.text(
            xpos,
            1.02,
            str(label) + "hz",
            color="white",
            ha="center",
            va="top",
            fontsize=8,
        )

    ax.set_xlim(-0.5, bands - 0.5)
    ax.set_ylim(0, 1.1)

    def update_plot(frame):
        while True:
            try:
                plotdata = q.get_nowait()
            except queue.Empty:
                break

        normalized = (plotdata - np.min(plotdata)) / (
            np.max(plotdata) - np.min(plotdata) + 1e-6
        )
        for bar, h, n in zip(bars, plotdata, normalized):
            bar.set_height(h)
            bar.set_color(cmap(n))

        return bars

    ani = FuncAnimation(fig, update_plot, interval=interval, blit=False)

    return fig, ani


try:
    device_info = sd.query_devices(args.device, "input")
    samplerate = device_info["default_samplerate"]
    low, high = args.range
    delta_f = (high - low) / args.bands
    fftsize = math.ceil(samplerate / delta_f)
    low_bin = math.floor(low / delta_f)

    plotdata = np.zeros(args.bands)

    fig, ani = setup_graph(args.bands, low, args.interval, args.cmap)

    def audio_callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)

        if any(indata):
            magnitude = np.abs(np.fft.rfft(indata[:, 0], n=fftsize))
            magnitude *= args.gain / fftsize

            freq_range = magnitude[low_bin : low_bin + args.bands]
            q.put(freq_range)
        else:
            q.put(np.zeros(args.bands))

    stream = sd.InputStream(
        device=args.device,
        channels=1,
        samplerate=samplerate,
        callback=audio_callback,
    )

    with stream:
        plt.show()

except Exception as e:
    raise e
