import numpy as np, subprocess, os, math, asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = '/tmp/claude-0/-home-claude/75e13283-8b24-558c-93ac-5d18fcf984b9/scratchpad/clutch_src'
OUT = '/tmp/claude-0/-home-claude/75e13283-8b24-558c-93ac-5d18fcf984b9/scratchpad/clutch_ad'
W, H, FPS, DUR = 1080, 1920, 30, 15.0
N = int(FPS * DUR)
INK = (14, 14, 16); LIME = (197, 241, 107)

def load(n): return Image.open(f'{SRC}/{n}.jpg').convert('RGB')
img = {k: load(k) for k in ['01', '02', '03', '04', '08']}

# --- wordmark via playwright
def render_wordmark():
    from playwright.sync_api import sync_playwright
    svg = open('/home/claude/noirix-main/packages/design-system/assets/logos/noirix-wordmark-white.svg').read()
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 802, 'height': 200}, device_scale_factor=1)
        pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
        pg.screenshot(path=f'{OUT}/wordmark.png', omit_background=True); b.close()
render_wordmark()
wordmark = Image.open(f'{OUT}/wordmark.png').convert('RGBA')

F_LAT = '/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf'
F_LATB = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
F_THIN = '/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf'
F_AR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
F_ARB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(p, s): return ImageFont.truetype(p, s, layout_engine=ImageFont.Layout.RAQM)

def text_layer(lines):
    """lines: list of (text, fontpath, size, y, fill, rtl)"""
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    for t, fp, s, y, fill, rtl in lines:
        f = font(fp, s); kw = {'direction': 'rtl', 'language': 'ar'} if rtl else {}
        bb = d.textbbox((0, 0), t, font=f, **kw); x = (W - (bb[2] - bb[0])) // 2 - bb[0]
        ds.text((x, y + 3), t, font=f, fill=(0, 0, 0, 150), **kw)
        d.text((x, y), t, font=f, fill=fill, **kw)
    sh = sh.filter(ImageFilter.GaussianBlur(8))
    return Image.alpha_composite(sh, L)

def crop_window(im, cx, cy, h):
    h = min(h, im.height); w = h * W / H
    if w > im.width: w = im.width; h = w * H / W
    cx = min(max(cx, w / 2), im.width - w / 2); cy = min(max(cy, h / 2), im.height - h / 2)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return im.resize((W, H), Image.LANCZOS, box=box)

def ease(t): return 0.5 - 0.5 * math.cos(math.pi * max(0, min(1, t)))

def card_scene(im, t, zoom0=1.0, zoom1=1.08, bg_tint=(28, 24, 22), size=860, cy=900, crop=None):
    src = im.crop(crop) if crop else im
    bg = src.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(60))
    bg = Image.blend(bg, Image.new('RGB', (W, H), bg_tint), 0.55)
    z = zoom0 + (zoom1 - zoom0) * ease(t)
    sw, shh = src.size; k = size / max(sw, shh)
    cw, ch = int(sw * k), int(shh * k)
    inner = src.resize((int(cw * z), int(ch * z)), Image.LANCZOS)
    inner = inner.crop(((inner.width - cw) // 2, (inner.height - ch) // 2, (inner.width - cw) // 2 + cw, (inner.height - ch) // 2 + ch))
    m = Image.new('L', (cw, ch), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, cw - 1, ch - 1), 36, fill=255)
    shadow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(shadow).rounded_rectangle(((W - cw) // 2, cy - ch // 2 + 24, (W + cw) // 2, cy + ch // 2 + 24), 36, fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(30))
    out = Image.alpha_composite(bg.convert('RGBA'), shadow)
    out.paste(inner, ((W - cw) // 2, cy - ch // 2), m)
    return out.convert('RGB')

# --- shots: (start, end, fn(t)->Image)
S = []
# A hook: extreme close on handle (02 black), push in
S.append((0.0, 2.0, lambda t: crop_window(img['02'], 690, 1170, 980 - 200 * ease(t))))
# B tilt down on white (08): from chain/scarf to bag
S.append((2.0, 4.5, lambda t: crop_window(img['08'], 600, 760 + 330 * ease(t), 1420)))
# C black on model, slow push
S.append((4.5, 6.5, lambda t: crop_window(img['02'], 700, 1060, 1720 - 260 * ease(t))))
# D brown in hand, card (crop out magazine on right)
S.append((6.5, 8.0, lambda t: card_scene(img['04'], t, 1.0, 1.10, (40, 28, 20), 900, 930, crop=(40, 60, 660, 780))))
# E colour trio quick cuts
S.append((8.0, 8.5, lambda t: card_scene(img['03'], t, 1.04, 1.0, (18, 18, 20), 900, 930, crop=(40, 60, 660, 780))))
S.append((8.5, 9.0, lambda t: card_scene(img['01'], t, 1.04, 1.0, (60, 56, 52), 900, 930, crop=(150, 150, 680, 640))))
S.append((9.0, 9.5, lambda t: card_scene(img['04'], t, 1.04, 1.0, (40, 28, 20), 900, 930, crop=(40, 60, 660, 780))))
# F hero card white bag
S.append((9.5, 12.5, lambda t: card_scene(img['08'], t, 1.0, 1.06, (22, 20, 20), 880, 860, crop=(250, 820, 1050, 1340))))
# G end card
def endcard(t):
    bg = Image.new('RGB', (W, H), INK)
    return bg
S.append((12.5, 15.0, endcard))

TXT = {
    0: text_layer([('A handle that turns heads', F_LATB, 66, 1330, (255, 255, 255, 255), False),
                   ('مقبض يلفت النظر', F_AR, 54, 1425, (255, 255, 255, 230), True)]),
    1: text_layer([('Day to night', F_LATB, 70, 1330, (255, 255, 255, 255), False),
                   ('من النهار إلى المساء', F_AR, 56, 1430, (255, 255, 255, 230), True)]),
    2: text_layer([('Statement metal. Simple shape.', F_LATB, 60, 1360, (255, 255, 255, 255), False)]),
    3: text_layer([('Brown', F_LATB, 76, 1450, (255, 255, 255, 255), False), ('بني', F_AR, 54, 1545, (255, 255, 255, 230), True)]),
    4: text_layer([('Black', F_LATB, 76, 1450, (255, 255, 255, 255), False), ('أسود', F_AR, 54, 1545, (255, 255, 255, 230), True)]),
    5: text_layer([('White', F_LATB, 76, 1450, (255, 255, 255, 255), False), ('أبيض', F_AR, 54, 1545, (255, 255, 255, 230), True)]),
    6: text_layer([('Brown', F_LATB, 76, 1450, (255, 255, 255, 255), False), ('بني', F_AR, 54, 1545, (255, 255, 255, 230), True)]),
    7: text_layer([('Chain Clutch', F_LATB, 70, 1230, (255, 255, 255, 255), False),
                   ('كلاتش بمقبض معدني وسلسلة', F_AR, 46, 1325, (255, 255, 255, 230), True),
                   ('AED 39', F_LATB, 92, 1420, LIME + (255,), False),
                   ('Prices shown in your local currency on the site', F_LAT, 30, 1560, (255, 255, 255, 200), False),
                   ('الأسعار حسب بلدك عند فتح الموقع', F_AR, 30, 1605, (255, 255, 255, 200), True)]),
}
# end card layer
def end_layer():
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    mono = Image.new('RGBA', (160, 160), (0, 0, 0, 0)); dm = ImageDraw.Draw(mono)
    dm.polygon([(18, 142), (18, 18), (43, 18), (126, 117), (142, 142), (111, 142), (44, 62), (44, 142)], fill=LIME)
    dm.polygon([(101, 18), (132, 18), (99, 58), (80, 35)], fill=LIME)
    mono = mono.resize((300, 300), Image.LANCZOS); L.alpha_composite(mono, ((W - 300) // 2, 560))
    wm = wordmark.resize((560, int(560 * wordmark.height / wordmark.width)), Image.LANCZOS)
    L.alpha_composite(wm, ((W - wm.width) // 2, 920))
    t = text_layer([('noirix.shop', F_LAT, 56, 1160, (255, 255, 255, 255), False),
                    ('Your world, your way', F_THIN, 40, 1250, (255, 255, 255, 210), False),
                    ('عالمك بطابعك', F_AR, 40, 1310, (255, 255, 255, 210), True)])
    return Image.alpha_composite(L, t)
TXT[8] = end_layer()

def grade(a, t):
    a = a.astype(np.float32) / 255.0
    a = a * np.array([1.035, 1.0, 0.955], np.float32)          # warm
    a = np.clip((a - 0.5) * 1.06 + 0.5, 0, 1)                  # contrast
    return a

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.2
vig = np.clip(vig, 0.55, 1)[..., None]
rng = np.random.default_rng(7)

def sweep(a, t, strength=0.22):
    # diagonal light band crossing the frame during t in [0,1]
    pos = -0.4 + 1.8 * t
    d = (xx / W + yy / H * 0.35) / 1.35 - pos
    band = np.exp(-(d / 0.06) ** 2)[..., None]
    return np.clip(a + band * strength, 0, 1)

_g = np.zeros((H, W, 4), np.uint8)
_ramp = np.clip((np.arange(H) - 1080) / 260.0, 0, 1) * np.clip((1780 - np.arange(H)) / 160.0, 0, 1)
_g[..., 3] = (_ramp * 150).astype(np.uint8)[:, None]
SCRIM = Image.fromarray(_g, 'RGBA')

def frame(i):
    tsec = i / FPS
    for k, (s, e, fn) in enumerate(S):
        if s <= tsec < e or (k == len(S) - 1 and tsec >= s):
            t = (tsec - s) / (e - s)
            im = fn(t).convert('RGBA')
            if k in (0, 1, 2):
                im = Image.alpha_composite(im, SCRIM)
            # text fade-in after 0.2s
            lay = TXT[k]
            fade = max(0, min(1, (tsec - s - 0.15) / 0.35)) if k not in (3,4,5,6) else max(0, min(1, (tsec - s) / 0.1))
            if k == 8: fade = max(0, min(1, (tsec - s) / 0.5))
            if fade > 0:
                lay2 = lay.copy(); al = lay2.getchannel('A').point(lambda v: int(v * fade)); lay2.putalpha(al)
                # slight rise
                off = int((1 - fade) * 24); base = Image.new('RGBA', (W, H), (0, 0, 0, 0)); base.alpha_composite(lay2, (0, off))
                im = Image.alpha_composite(im, base)
            a = grade(np.asarray(im.convert('RGB')), t)
            if k == 0: a = sweep(a, t, 0.20)
            if k == 7: a = sweep(a, min(1, t * 1.6), 0.14)
            if k != 8: a = a * vig
            # crossfade from black at very start, cut flash on quick cuts
            if k in (4, 5, 6) and t < 0.12: a = np.clip(a + (0.12 - t) * 2.0, 0, 1)
            a = a + rng.normal(0, 0.012, (H, W, 1)).astype(np.float32)  # grain
            return (np.clip(a, 0, 1) * 255).astype(np.uint8), k, t
    raise RuntimeError

# crossfades between consecutive long shots
XF = {1: 0.25, 2: 0.25, 3: 0.2, 7: 0.25, 8: 0.35}
def render():
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', f'{OUT}/video.mp4'], stdin=subprocess.PIPE)
    for i in range(N):
        a, k, t = frame(i)
        tsec = i / FPS
        if k in XF:
            s = S[k][0]; dx = XF[k]
            if tsec - s < dx:
                # blend with previous shot's last state
                pk = k - 1; ps, pe, pfn = S[pk]
                pim = pfn(1.0).convert('RGB'); pa = grade(np.asarray(pim), 1.0) * (vig if pk != 8 else 1)
                w = (tsec - s) / dx
                a = (a.astype(np.float32) / 255 * w + pa * (1 - w)); a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
        p.stdin.write(a.tobytes())
    p.stdin.close(); p.wait()

if __name__ == '__main__':
    render(); print('video done')
