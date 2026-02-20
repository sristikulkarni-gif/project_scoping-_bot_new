
try:
    print("Importing azure_blob...")
    from app.utils import azure_blob
    print("Importing scope_engine...")
    from app.utils import scope_engine
    print("Importing presenton router...")
    from app.routers import presenton
    print("✅ Imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
