"""Contact sheet of out/stills → out/sheet.png (labelled with time and bar.beat)."""
import glob, sys
from PIL import Image, ImageDraw
files = sorted(glob.glob('out/stills/*.png'))
cols = int(sys.argv[1]) if len(sys.argv) > 1 else 4
th = 360
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * th, rows * th), 'white')
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    t = float(f.split('/t')[-1][:-4])
    im = Image.open(f).convert('RGB').resize((th, th), Image.LANCZOS)
    x, y = (i % cols) * th, (i // cols) * th
    sheet.paste(im, (x, y))
    b = int(t // 0.5)
    d.text((x + 8, y + 6), f'{t:.2f}s  {b // 4 + 1}.{b % 4 + 1}', fill=(0, 0, 0))
sheet.save('out/sheet.png')
print('out/sheet.png', sheet.size)
