#!/usr/bin/env python3
"""Create an independent 9:16 Story image/manifest from the day's prepared photo."""
import argparse, json
from pathlib import Path
from PIL import Image, ImageOps

p=argparse.ArgumentParser()
p.add_argument("--date", required=True)
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
feed_manifest=root/"posts"/f"{a.date}.json"
feed_image=root/"posts"/"images"/a.date/"post-01.jpg"
if not feed_manifest.is_file() or not feed_image.is_file():
    raise SystemExit("Feed source manifest/image missing. Run the Story workflow again after source preparation.")
data=json.loads(feed_manifest.read_text(encoding="utf-8"))
post=next((x for x in data.get("posts",[]) if x.get("image_url")),None)
if not post: raise SystemExit("No source post found.")
out=root/"stories"/"images"/a.date/"story-01.jpg"
out.parent.mkdir(parents=True,exist_ok=True)
with Image.open(feed_image) as im:
    im=ImageOps.exif_transpose(im).convert("RGB")
    im=ImageOps.fit(im,(1080,1920),method=Image.Resampling.LANCZOS,centering=(0.5,0.42))
    im.save(out,"JPEG",quality=92,optimize=True)
with Image.open(out) as check:
    if check.size!=(1080,1920): raise SystemExit("Story image must be 1080x1920.")
    check.verify()
manifest={
 "date":a.date,
 "stories":[{
   "id":f"{a.date}-story-01",
   "status":"queued",
   "topic":post.get("topic",""),
   "title":post.get("title",""),
   "image_url":f"https://raw.githubusercontent.com/trinadharaomamidi97-spec/mana-tech-autopilot/main/stories/images/{a.date}/story-01.jpg",
   "alt_text":post.get("alt_text",""),
 }]
}
path=root/"stories"/f"{a.date}.json"
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Prepared independent 9:16 Story asset: {out}")
