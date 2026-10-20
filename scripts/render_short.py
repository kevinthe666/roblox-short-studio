import json
import math
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes" / "episode_01.json"
OUT_DIR = ROOT / "output"
WIDTH, HEIGHT, FPS = 720, 1280, 24
SECONDS_PER_SCENE = 5

def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()

def wrap_text(draw, text, fnt, max_width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def draw_character(draw, x, y, shirt, hair, shocked=False, scale=1.0):
    w = int(104 * scale)
    draw.ellipse((x+10*scale, y+112*scale, x+w-10*scale, y+132*scale), fill=(20,24,42))
    draw.rectangle((x+12*scale, y+48*scale, x+w-12*scale, y+126*scale), fill=shirt)
    draw.rectangle((x+27*scale, y+8*scale, x+w-27*scale, y+61*scale), fill=(225,174,130))
    draw.rectangle((x+24*scale, y+4*scale, x+w-23*scale, y+24*scale), fill=hair)
    draw.rectangle((x+22*scale, y+17*scale, x+34*scale, y+35*scale), fill=hair)
    draw.rectangle((x+w-34*scale, y+17*scale, x+w-22*scale, y+35*scale), fill=hair)
    ey = y + 34*scale
    draw.ellipse((x+37*scale, ey, x+43*scale, ey+6*scale), fill=(25,25,35))
    draw.ellipse((x+61*scale, ey, x+67*scale, ey+6*scale), fill=(25,25,35))
    if shocked:
        draw.ellipse((x+47*scale, y+44*scale, x+57*scale, y+55*scale), outline=(70,35,35), width=2)
    else:
        draw.line((x+43*scale, y+49*scale, x+61*scale, y+49*scale), fill=(120,50,50), width=2)

def make_frame(scene, index, total, series, phase=0.0):
    img = Image.new("RGB", (WIDTH, HEIGHT))
    pix = img.load()
    mood = scene.get("mood", "quiet")
    palettes = {
        "quiet": ((17,28,65),(7,8,20)), "sad": ((29,31,65),(7,8,20)),
        "memory": ((45,42,73),(13,13,32)), "mystery": ((24,20,72),(7,5,24)),
        "shock": ((74,22,62),(12,5,22)), "cliffhanger": ((84,12,38),(8,3,17))
    }
    top, bottom = palettes.get(mood, palettes["quiet"])
    bottom = (7,8,20)
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = tuple(int(top[k]*(1-t)+bottom[k]*t) for k in range(3))
        for x in range(WIDTH):
            pix[x,y] = color
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((24,24,696,124), radius=20, fill=(5,8,22), outline=(76,132,205), width=2)
    d.text((42,39), "ROBLOX STORY", font=font(18,True), fill=(139,208,255))
    d.text((42,68), series, font=font(23,True), fill=(255,255,255))
    # School windows and floor perspective add depth to the scene.
    for wx in (38, 176, 464, 602):
        d.rounded_rectangle((wx, 190, wx+76, 440), radius=8, fill=(31,43,78))
        d.rectangle((wx+8, 202, wx+68, 428), fill=(48,67,105) if mood in ("quiet","sad") else (73,48,104))
        d.line((wx+38,205,wx+38,425), fill=(92,109,150), width=3)
    d.polygon([(0,680),(720,680),(720,1010),(0,1010)], fill=(22,28,51))
    for x in range(-250,1000,150):
        d.line((360,680,x,1010), fill=(39,47,76), width=2)
    for yy in (760,840,930):
        d.line((0,yy,720,yy-15), fill=(34,41,68), width=2)
    for x in (40,550):
        d.rectangle((x,300,x+120,620), fill=(43,52,83))
        d.rectangle((x+14,320,x+106,520), fill=(18,27,53))
    drift = int(15 * math.sin(phase * math.pi * 2 + index * 0.7))
    if mood in ("quiet","sad","memory"):
        draw_character(d, 280+drift, 440, (55,92,170), (25,26,36), False, 1.2)
        if mood == "memory":
            d.rounded_rectangle((465,620,610,740), radius=12, fill=(78,84,130), outline=(159,177,235), width=3)
            d.text((475,665), "EMPTY SEAT", font=font(17,True), fill=(222,228,255))
    elif mood == "mystery":
        draw_character(d, 205-drift, 440, (55,92,170), (25,26,36), False, 1.15)
        draw_character(d, 430+drift, 455, (182,65,119), (70,36,26), False, 1.0)
        d.rounded_rectangle((340,630,405,705), radius=6, fill=(240,230,192), outline=(255,255,255), width=2)
        d.line((352,650,392,650), fill=(90,76,66), width=2)
        d.line((352,665,386,665), fill=(90,76,66), width=2)
    else:
        draw_character(d, 190-drift, 440, (55,92,170), (25,26,36), True, 1.15)
        draw_character(d, 430+drift, 455, (182,65,119), (70,36,26), True, 1.0)
        d.ellipse((320,605,400,685), outline=(255,174,95), width=4)
    d.rounded_rectangle((28,845,692,1120), radius=24, fill=(3,5,16), outline=(87,176,255), width=3)
    fnt = font(38,True)
    lines = wrap_text(d, scene["caption"], fnt, 590)[:4]
    line_h = 52
    y = 845 + (275-len(lines)*line_h)//2
    for line in lines:
        tw = d.textbbox((0,0),line,font=fnt,stroke_width=1)[2]
        d.text(((WIDTH-tw)//2,y),line,font=fnt,fill="white",stroke_width=2,stroke_fill="black")
        y += line_h
    d.rounded_rectangle((28,1160,692,1215), radius=15, fill=(5,8,22))
    d.text((42,1175), f"PART 1  •  SCENE {index+1}/{total}", font=font(19,True), fill=(255,205,91))
    d.rounded_rectangle((42,1200,672,1207), radius=3, fill=(38,45,66))
    progress = int(630 * (index + 1) / total)
    d.rounded_rectangle((42,1200,42+progress,1207), radius=3, fill=(87,176,255))
    return img

def main():
    data = json.loads(EPISODE.read_text(encoding="utf-8"))
    frames_dir = OUT_DIR / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)
    seconds_per_scene = int(data.get("scene_seconds", SECONDS_PER_SCENE))
    frames_per_scene = int(FPS * seconds_per_scene)
    frame_no = 0
    for i, scene in enumerate(data["scenes"]):
        base = make_frame(scene, i, len(data["scenes"]), data["series"])
        for j in range(frames_per_scene):
            phase = j / max(1, frames_per_scene-1)
            scale = 1.0 + 0.025 * phase
            nw, nh = int(WIDTH*scale), int(HEIGHT*scale)
            zoom = base.resize((nw,nh), Image.Resampling.LANCZOS)
            left, top = (nw-WIDTH)//2, (nh-HEIGHT)//2
            zoom.crop((left,top,left+WIDTH,top+HEIGHT)).save(frames_dir/f"frame_{frame_no:05d}.jpg",quality=88)
            frame_no += 1
    mp4 = OUT_DIR / "episode_01.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    total_seconds = len(data["scenes"]) * seconds_per_scene
    # Generate a free spoken track when espeak-ng is installed on the runner.
    voice_path = OUT_DIR / "narration.wav"
    voice_ok = True
    with wave.open(str(voice_path), "wb") as combined:
        combined.setnchannels(1)
        combined.setsampwidth(2)
        combined.setframerate(22050)
        for i, scene in enumerate(data["scenes"]):
            part = OUT_DIR / f"voice_{i:02d}.wav"
            try:
                subprocess.run(["espeak-ng", "-s", "148", "-v", "en-us", "-w", str(part),
                                scene.get("narration", scene["caption"])], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with wave.open(str(part), "rb") as wf:
                    raw = wf.readframes(wf.getnframes())
                    rate, channels, width = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
                if (rate, channels, width) != (22050, 1, 2):
                    converted = OUT_DIR / f"voice_converted_{i:02d}.wav"
                    subprocess.run([ffmpeg, "-y", "-i", str(part), "-ac", "1", "-ar", "22050",
                                    "-sample_fmt", "s16", str(converted)], check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    with wave.open(str(converted), "rb") as wf:
                        raw = wf.readframes(wf.getnframes())
                max_bytes = 22050 * seconds_per_scene * 2
                raw = raw[:max_bytes]
                combined.writeframes(raw + b"\x00" * (max_bytes-len(raw)))
            except (FileNotFoundError, subprocess.CalledProcessError):
                voice_ok = False
                break
    if voice_ok:
        cmd = [ffmpeg, "-y", "-framerate", str(FPS), "-i", str(frames_dir/"frame_%05d.jpg"),
               "-i", str(voice_path), "-f", "lavfi", "-i",
               f"anoisesrc=color=pink:amplitude=0.018:sample_rate=22050:duration={total_seconds}",
               "-filter_complex", "[1:a]volume=1.8,highpass=f=100,lowpass=f=5000[voice];[2:a]volume=0.12,lowpass=f=650[amb];[voice][amb]amix=inputs=2:duration=longest:normalize=0[audio]",
               "-map", "0:v:0", "-map", "[audio]", "-t", str(total_seconds),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", str(mp4)]
    else:
        cmd = [ffmpeg, "-y", "-framerate", str(FPS), "-i", str(frames_dir/"frame_%05d.jpg"),
               "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={total_seconds}",
               "-t", str(total_seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-movflags", "+faststart", str(mp4)]
    subprocess.run(cmd, check=True)
    print(f"Rendered: {mp4}")
    print(f"Duration target: {total_seconds} seconds ({len(data['scenes'])} scenes x {seconds_per_scene}s).")
    print("Audio: generated English narration plus synthetic ambience." if voice_ok else "Audio: narration unavailable; install espeak-ng to enable it.")

if __name__ == "__main__":
    main()
