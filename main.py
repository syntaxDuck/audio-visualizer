"""Show a live microphone frequency visualizer."""

import argparse
import math
import queue
import sys

import numpy as np
import sounddevice as sd

from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


q = queue.Queue()

test_mode_frame_count = 0


def generate_test_audio(frames, samplerate):
    """Generate synthetic sine wave audio that varies over time for testing."""
    global test_mode_frame_count
    t = np.arange(frames) / samplerate
    base_freq = 440 + 200 * np.sin(test_mode_frame_count * 0.05)
    freq_sweep = base_freq + 200 * np.sin(test_mode_frame_count * 0.02)
    wave = 0.3 * np.sin(2 * np.pi * freq_sweep * t)
    wave += 0.15 * np.sin(2 * np.pi * (freq_sweep * 2) * t)
    wave += 0.1 * np.sin(2 * np.pi * (freq_sweep * 3) * t)
    test_mode_frame_count += 1
    return wave.reshape(-1, 1)


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
    type=int_or_str,
    help="input device: numeric ID or substring (default: system default input)",
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
    default=30,
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
parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="output GIF filename (saves animation and exits)",
)
parser.add_argument(
    "--duration",
    type=float,
    default=10,
    help="recording duration in seconds for GIF output (default: %(default)s)",
)
parser.add_argument(
    "--test-mode",
    action="store_true",
    help="use synthetic sine wave audio instead of microphone for testing",
)
args = parser.parse_args(remaining)
low, high = args.range
if high <= low:
    parser.error("HIGH must be greater than LOW")


def resolve_input_device(device_arg):
    """Resolve explicit input device or fallback to the system default."""
    if device_arg is not None:
        return device_arg, sd.query_devices(device_arg, "input")

    default_input = sd.default.device[0]
    if default_input is None or default_input < 0:
        parser.error("No default input device found. Use -l to list available devices.")

    try:
        return default_input, sd.query_devices(default_input, "input")
    except Exception as exc:  # pragma: no cover - depends on host audio stack
        parser.error(
            f"Unable to use default input device ({default_input}): {exc}. "
            "Use -l to list available devices."
        )


def setup_graph(bands, low, interval, cmap_str, save_path=None, total_frames=None):
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
    if fig.canvas.manager:
        fig.canvas.manager.toolmanager = None
    fig.tight_layout(pad=0)
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    if bands <= 50:
        step = 10
    elif bands <= 100:
        step = 20
    elif bands <= 200:
        step = 50
    else:
        step = 100

    for xpos in range(step, bands, step):
        ax.axvline(x=xpos, color="gray", linestyle="--", linewidth=0.5, alpha=0.5)

        hz = int(low + xpos * delta_f)
        if hz >= 1000:
            label = f"{hz // 1000}k"
        else:
            label = str(hz)

        ax.text(
            xpos,
            1.02,
            label,
            color="white",
            ha="center",
            va="top",
            fontsize=7,
        )

    ax.set_xlim(-0.5, bands - 0.5)
    ax.set_ylim(0, 1.1)

    def update_plot(frame):
        try:
            latest = q.get_nowait()
        except queue.Empty:
            latest = plotdata

        normalized = (latest - np.min(latest)) / (
            np.max(latest) - np.min(latest) + 1e-6
        )
        for bar, h, n in zip(bars, latest, normalized):
            bar.set_height(h)
            bar.set_color(cmap(n))

        return bars

    ani = FuncAnimation(
        fig,
        update_plot,
        interval=interval,
        blit=False,
        cache_frame_data=False,
        frames=total_frames,
    )

    return fig, ani, save_path


try:
    input_device, device_info = resolve_input_device(args.device)
    samplerate = args.samplerate or device_info["default_samplerate"]
    delta_f = (high - low) / args.bands
    fftsize = math.ceil(samplerate / delta_f)
    low_bin = math.floor(low / delta_f)

    plotdata = np.zeros(args.bands)

    total_frames = None
    if args.output and args.test_mode:
        total_frames = int(args.duration * 1000 / args.interval)

    fig, ani, save_path = setup_graph(
        args.bands, low, args.interval, args.cmap, args.output, total_frames
    )

    if args.test_mode:
        print(f"Generating {args.duration}s test data ({total_frames} frames)...")
        for _ in range(total_frames):
            test_audio = generate_test_audio(
                int(samplerate * args.interval / 1000), samplerate
            )
            magnitude = np.abs(np.fft.rfft(test_audio[:, 0], n=fftsize))
            magnitude *= args.gain / fftsize
            freq_range = magnitude[low_bin : low_bin + args.bands]
            q.put(freq_range)

        import matplotlib

        matplotlib.use("Agg")
        print(f"Saving GIF to {save_path}...")
        ani.save(save_path, writer="pillow", fps=1000 / args.interval)
        print(f"GIF saved to {save_path}")
    else:

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
            device=input_device,
            channels=1,
            samplerate=samplerate,
            callback=audio_callback,
        )

        with stream:
            plt.show()

except Exception as e:
    raise e
