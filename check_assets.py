import os

# Folder where your images are stored
assets_dir = "assets"

# List the files your app EXPECTS (copy these from your error message)
expected_files = [
    "stairs-bedroom-downstairs.jpg",
    "upstairs-bedroom.jpg",
    "three-bed-room.jpg",
    "four-bed.jpg"
]

# Get the actual files inside /assets
actual_files = os.listdir(assets_dir)

print("\n--- Checking Assets ---")
print("Expected:", expected_files)
print("Found in folder:", actual_files)

# Check which ones are missing
missing = [f for f in expected_files if f not in actual_files]

if missing:
    print("\n❌ Missing files:")
    for f in missing:
        print("-", f)
else:
    print("\n✅ All expected files are present!")
