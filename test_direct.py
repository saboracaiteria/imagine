import modal

cls = modal.Cls.from_name("grok007-engine", "GrokEngine")
f = cls().animate

with open('test_image_b64.txt', 'r') as file:
    img_b64 = file.read().strip()

print("Calling animate directly via Modal client...")
try:
    # This will show logs in the terminal
    result = f.remote(
        image_b64=img_b64,
        prompt="Woman walking towards the ocean, waves breaking on the sand, realistic fluid movement"
    )
    print("Success! Video length:", len(result))
except Exception as e:
    import traceback
    traceback.print_exc()
    raise e
