# run.py
import os
import sys
from app import create_app

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Create Flask app
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting AI Vision System...")
    print("📊 System Information:")
    print(f"   - Python Path: {sys.executable}")
    print(f"   - Working Directory: {os.getcwd()}")
    print(f"   - Project Root: {current_dir}")
    
    # Check if models directory exists
    models_dir = os.path.join(current_dir, "models")
    if os.path.exists(models_dir):
        print(f"   - Models Directory: ✅ Found")
        model_files = [f for f in os.listdir(models_dir) if f.endswith(('.pt', '.onnx', '.engine'))]
        print(f"   - Model Files: {model_files}")
    else:
        print(f"   - Models Directory: ❌ Not Found")
    
    # Start the Flask development server
    try:
        app.run(
            host='0.0.0.0',  # Allow external connections
            port=5000,
            debug=True,
            threaded=True    # Enable threading for better performance
        )
    except Exception as e:
        print(f"❌ Failed to start server: {str(e)}")
        sys.exit(1)