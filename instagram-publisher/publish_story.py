#!/usr/bin/env python3
"""Publish queued Instagram Stories independently from Feed posts."""
import argparse, json, os, sys, time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
API_VERSION=os.getenv("META_API_VERSION","v27.0")
API_BASE=f"https://graph.facebook.com/{API_VERSION}"
PREFIX="https://raw.githubusercontent.com/trinadharaomamidi97-spec/mana-tech-autopilot/main/stories/images/"

def call(method,edge,params):
    url=f"{API_BASE}/{edge.lstrip('/')}"
    body=urlencode(params).encode()
    if method=="GET":
        url+="?"+body.decode()
        body=None
    req=Request(url,data=body,headers={"User-Agent":"ManaTechTeluguAutoPilot/1.0","Content-Type":"application/x-www-form-urlencoded"},method=method)
    try:
        with urlopen(req,timeout=45) as r: result=json.loads(r.read().decode())
    except HTTPError as e:
        try: result=json.loads(e.read().decode())
        except Exception: raise RuntimeError(f"Meta HTTP {e.code}") from None
    except URLError as e: raise RuntimeError(f"Meta network error: {e.reason}") from None
    if result.get("error"):
        er=result["error"]
        raise RuntimeError(f"Meta API error {er.get('code','?')}: {er.get('message','Unknown error')}")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--date",required=True)
    a=p.parse_args()
    ig=os.getenv("META_IG_USER_ID","").strip()
    token=os.getenv("META_ACCESS_TOKEN","").strip()
    if not ig or not token: raise RuntimeError("Missing META_IG_USER_ID or META_ACCESS_TOKEN GitHub Actions secret.")
    path=ROOT/"stories"/f"{a.date}.json"
    if not path.is_file(): raise RuntimeError(f"Story manifest not found: stories/{a.date}.json")
    manifest=json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("date")!=a.date: raise RuntimeError("Story manifest date mismatch.")
    for story in manifest.get("stories",[]):
        status=story.get("status")
        if status=="published":
            print(f"Skipping already-published Story {story['id']}.")
            continue
        if status!="queued": raise RuntimeError(f"Unsupported Story status: {status}")
        url=str(story.get("image_url",""))
        if not url.startswith(PREFIX+a.date+"/"): raise RuntimeError("Story image URL is outside the approved repository folder.")
        print(f"Creating Story container for {story['id']}...")
        container=call("POST",f"{ig}/media",{"image_url":url,"media_type":"STORIES","access_token":token})
        cid=str(container.get("id",""))
        if not cid: raise RuntimeError("Meta did not return a Story container ID.")
        for _ in range(30):
            state=call("GET",cid,{"fields":"status_code","access_token":token}).get("status_code","")
            print(f"Story container status: {state}")
            if state=="FINISHED": break
            if state in ("ERROR","EXPIRED"): raise RuntimeError(f"Story container status is {state}.")
            time.sleep(10)
        else: raise RuntimeError("Story container processing timed out.")
        result=call("POST",f"{ig}/media_publish",{"creation_id":cid,"access_token":token})
        mid=str(result.get("id",""))
        if not mid: raise RuntimeError("Meta did not return a published Story media ID.")
        story.update(status="published",instagram_media_id=mid,published_at=datetime.now(timezone.utc).isoformat())
        path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        import subprocess
        subprocess.run(["git","config","user.name","github-actions[bot]"],cwd=ROOT,check=True)
        subprocess.run(["git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],cwd=ROOT,check=True)
        subprocess.run(["git","add",str(path.relative_to(ROOT))],cwd=ROOT,check=True)
        subprocess.run(["git","commit","-m",f"Record Instagram Story publish: {story['id']}"],cwd=ROOT,check=True)
        subprocess.run(["git","push","origin","HEAD:main"],cwd=ROOT,check=True)
        print(f"Published Instagram Story {story['id']}; media ID {mid}")
if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"Story publishing stopped: {e}",file=sys.stderr)
        raise SystemExit(1)
