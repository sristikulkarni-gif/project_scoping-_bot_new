
try:
    print("Attempting to import app.main...")
    from app import main
    print("✅ Successfully imported app.main")
except Exception as e:
    print(f"❌ Failed to import app.main: {e}")
    import traceback
    traceback.print_exc()
