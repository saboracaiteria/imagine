import modal
import os

app = modal.App("test-wan-engine")

@app.function()
def test():
    cls = modal.Cls.from_name("grok007-engine", "GrokEngine")
    engine = cls()
    
    print("Calling GrokEngine.animate via Modal...")
    # Placeholder black image 1x1
    img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
    result = engine.animate.remote(
        image_b64=img_b64,
        prompt="Woman walking towards the ocean"
    )
    print(f"Success! Video length: {len(result)}")

if __name__ == "__main__":
    test.remote()
