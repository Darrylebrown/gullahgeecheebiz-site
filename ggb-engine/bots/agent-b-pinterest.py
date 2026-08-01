#!/usr/bin/env python3
"""GGB Agent B-5 — Pinterest Executor. Pins to boards."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import PublishEngine, build_canonical_manifest_hash, REPO_ROOT
AGENT_NAME, AGENT_VERSION, PLATFORM = "agent-b-pinterest", "1.0.0", "pinterest"

class PinterestExecutor:
    def __init__(self, engine=None):
        self.engine = engine or PublishEngine()
        self.name, self.version = AGENT_NAME, AGENT_VERSION

    def verify_approval(self, mid):
        m = self.engine.db.load_manifest(mid)
        if not m: return {"verified": False, "error": "Manifest not found"}
        if m.get("approval",{}).get("status")!="approved": return {"verified": False, "error": "Not approved"}
        if build_canonical_manifest_hash(m)!=self.engine.db.get_approval_hash(mid): return {"verified": False, "error": "Approval expired"}
        return {"verified": True}

    def upload_pin(self, mid):
        a=self.verify_approval(mid)
        if not a["verified"]: return {"error": a["error"]}
        m=self.engine.db.load_manifest(mid)
        if not self.engine.adapter.check_auth().get("authenticated"): return {"error":"Pinterest auth failed"}
        did=m.get("draft_id","new-pin")
        pins_dir=REPO_ROOT/"publish"/"pins"
        ups=[]
        for f in sorted(pins_dir.glob("*")):
            if f.suffix in (".jpg",".png",".jpeg"):
                r=self.engine.adapter.upload_artifact(did,"pin",str(f))
                if r.get("success"): ups.append({"file":f.name})
        return {"status":"uploaded","platform":PLATFORM,"draft_id":did,"pins_uploaded":len(ups),"_mock":self.engine.adapter.is_mock()}

    def submit(self, mid, owner_approved=False):
        if not owner_approved: return {"error":"Owner approval required"}
        m=self.engine.db.load_manifest(mid)
        if not m: return {"error":"Manifest not found"}
        r=self.engine.adapter.submit(m.get("draft_id","new-pin"))
        return {"status":"submitted" if r.get("submitted") else "failed","platform":PLATFORM,"confirmation_id":r.get("confirmation_id",""),"_mock":self.engine.adapter.is_mock()}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(description=f"{AGENT_NAME} v{AGENT_VERSION}")
    p.add_argument("--json",action="store_true"); p.add_argument("manifest_id")
    s=p.add_subparsers(dest="command",required=True)
    s.add_parser("upload")
    sub=s.add_parser("submit"); sub.add_argument("--owner-approved",action="store_true")
    a=p.parse_args(); e=PinterestExecutor()
    if a.command=="upload": r=e.upload_pin(a.manifest_id)
    elif a.command=="submit": r=e.submit(a.manifest_id,a.owner_approved)
    if a.json: print(json.dumps(r,indent=2,default=str))
    else:
        for k,v in (r or {}).items(): print(f"{k}: {v}")
