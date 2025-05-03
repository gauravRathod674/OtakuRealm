import google.generativeai as genai
import time

# Set up the API key
API_KEY = "AIzaSyBi0O2XvJRpWngtjvv2JswmGfnhESCy_20"
genai.configure(api_key=API_KEY)

# Select an available model
MODEL_NAME = "gemini-1.5-pro-latest"

# Function to generate a streaming-like response
def chat_with_gemini_stream(prompt):
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        # Get the full response first
        response = model.generate_content(prompt)
        if not response.text:
            print("\nError: No response received.")
            return

        print("\nGemini's Response:", end=" ", flush=True)
        
        # Simulate real-time word-by-word output
        for word in response.text.split():
            print(word, end=" ", flush=True)
            time.sleep(0.05)  # Adjust speed to feel natural
        
        print()  # New line at the end
    except Exception as e:
        print(f"\nError: {str(e)}")

# Main execution
if __name__ == "__main__":
    user_input = input("Enter your prompt: ")
    chat_with_gemini_stream(user_input)


