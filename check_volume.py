import modal
import os

app = modal.App("check-volume")
volume = modal.Volume.from_name("grok007-models")

@app.function(volumes={"/models": volume})
def check():
    path = "/models/wan-2.1-i2v"
    if os.path.exists(path):
        print(f"Volume exists: {path}")
        files = os.listdir(path)
        print(f"Files: {files}")
        for f in files:
            fpath = os.path.join(path, f)
            if os.path.isfile(fpath):
                print(f"  - {f}: {os.path.getsize(fpath) / 1024**3:.2f} GB")
            elif os.path.isdir(fpath):
                 print(f"  - {f}/ (dir)")
    else:
        print(f"Volume NOT found at {path}")

if __name__ == "__main__":
    with app.run():
        check.remote()
