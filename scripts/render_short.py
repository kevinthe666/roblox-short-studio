import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes" / "episode_01.json"
OUT_DIR = ROOT / "output"
WIDTH, HEIGHT, FPS = 720, 1280, 24
SECONDS_PER_SCENE = 3.2

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

def make_frame(scene, index, total, series):
    img = Image.new("RGB", (WIDTH, HEIGHT))
    pix = img.load()
    mood = scene.get("mood", "quiet")
    top = (17,28,65) if mood == "quiet" else (50,17,65)
    bottom = (7,8,20)
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = tuple(int(top[k]*(1-t)+bottom[k]*t) for k in range(3))
        for x in range(WIDTH):
            pix[x,y] = color
    d = ImageDraw.Draw(img)
    d.text((36,34), "ROBLOX SHORTS STUDIO", font=font(20,True), fill=(139,208,255))
    d.text((36,74), series, font=font(24,True), fill=(255,255,255))
    d.polygon([(0,330),(720,330),(620,760),(100,760)], fill=(29,36,66))
    for x in (40,550):
        d.rectangle((x,300,x+120,620), fill=(43,52,83))
        d.rectangle((x+14,320,x+106,520), fill=(18,27,53))
    draw_character(d, 300, 420, (55,92,170), (25,26,36), mood == "shock", 1.15)
    if mood in ("mystery","shock","cliffhanger"):
        draw_character(d, 480, 455, (182,65,119), (70,36,26), True, 0.9)
    d.rounded_rectangle((28,845,692,1120), radius=24, fill=(3,5,16), outline=(87,176,255), width=3)
    fnt = font(38,True)
    lines = wrap_text(d, scene["caption"], fnt, 590)[:4]
    line_h = 52
    y = 845 + (275-len(lines)*line_h)//2
    for line in lines:
        tw = d.textbbox((0,0),line,font=fnt,stroke_width=1)[2]
        d.text(((WIDTH-tw)//2,y),line,font=fnt,fill="white",stroke_width=2,stroke_fill="black")
        y += line_h
    d.text((36,1190), f"PART 1  •  SCENE {index+1}/{total}", font=font(21,True), fill=(255,205,91))
    return img

def main():
    data = json.loads(EPISODE.read_text(encoding="utf-8"))
    frames_dir = OUT_DIR / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)
    frames_per_scene = int(FPS * SECONDS_PER_SCENE)
    frame_no = 0
    for i, scene in enumerate(data["scenes"]):
        base = make_frame(scene, i, len(data["scenes"]), data["series"])
        for j in range(frames_per_scene):
            scale = 1.0 + 0.018 * j / max(1, frames_per_scene-1)
            nw, nh = int(WIDTH*scale), int(HEIGHT*scale)
            zoom = base.resize((nw,nh), Image.Resampling.LANCZOS)
            left, top = (nw-WIDTH)//2, (nh-HEIGHT)//2
            zoom.crop((left,top,left+WIDTH,top+HEIGHT)).save(frames_dir/f"frame_{frame_no:05d}.jpg",quality=88)
            frame_no += 1
    mp4 = OUT_DIR / "episode_01.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg,"-y","-framerate",str(FPS),"-i",str(frames_dir/"frame_%05d.jpg"),
           "-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=44100",
           "-shortest","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","96k",
           "-movflags","+faststart",str(mp4)]
    subprocess.run(cmd, check=True)
    print(f"Rendered: {mp4}")
    print("Prototype note: visuals are geometric placeholders with silent audio; add original/licensed footage, narration and sound before publishing.")

if __name__ == "__main__":
    main()
