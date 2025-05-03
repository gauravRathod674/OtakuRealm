import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Chatbot:
    def __init__(self, url="https://chatgpt.com/", timeout=90):
        self.url = url
        self.timeout = timeout
        self.driver = None
        self.wait = None

    def initialize_driver(self):
        print("[INFO] Initializing ChromeDriver...")
        chrome_options = uc.options.ChromeOptions()

        # Headless config (use --headless=new for Chrome 109+)
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Initialize the driver
        self.driver = uc.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

        # ⚠️ Fix for Chrome 117+ headless detection: override user agent via CDP
        custom_user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        )
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": custom_user_agent})
        print(f"[INFO] User-Agent overridden to: {custom_user_agent}")

        print("[INFO] ChromeDriver initialized successfully!")


    def open_website(self):
        print("[INFO] Opening ChatGPT website...")
        self.driver.get(self.url)

    def wait_for_element(self, by, identifier):
        print(f"[INFO] Waiting for element {identifier} to be visible...")
        element = self.wait.until(EC.visibility_of_element_located((by, identifier)))
        self.driver.execute_script("arguments[0].scrollIntoView();", element)
        print(f"[INFO] Element {identifier} is visible.")
        return element

    def send_message(self, message):
        input_box = self.wait_for_element(By.ID, "prompt-textarea")
        print("[INFO] Clicking to focus on the input box...")
        input_box.click()

        custom_message = (
            ". Check given question is anime related or not. "
            "If it is not, answer ONLY with the single word 'false'. Otherwise, answer the question normally."
        )
        final_message = f"Question=> '{message}'" + custom_message

        print(f"[INFO] Typing final message: '{final_message}'")
        input_box.send_keys(final_message)
        print("[INFO] Message typed in the contenteditable input.")

        print("[INFO] Waiting for the send button to be clickable...")
        send_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "(//button[@aria-label='Send prompt'])[1]"))
        )
        print("[INFO] Found send button. Clicking it to send the message...")
        send_button.click()
        print("[INFO] Message sent. Streaming assistant response...\n")

    def get_full_response(self, message):
        """
        Sends a message and waits for the full assistant response.
        Returns the full text after it's completely generated.
        """
        try:
            self.initialize_driver()
            self.open_website()
            self.send_message(message)

            assistant_xpath = "//div[@data-message-author-role='assistant']//div[contains(@class, 'markdown')]"
            printed_text = ""
            start_time = time.time()
            last_change_time = time.time()

            while time.time() - start_time < self.timeout:
                try:
                    element = self.driver.find_element(By.XPATH, assistant_xpath)
                    current_text = element.text
                except Exception:
                    current_text = printed_text

                if current_text != printed_text:
                    printed_text = current_text
                    last_change_time = time.time()
                else:
                    if time.time() - last_change_time >= 1:
                        break

                time.sleep(0.05)

            return printed_text.strip()

        except Exception as e:
            print(f"[ERROR] {str(e)}")
            return "Sorry, Seems like there is an error while generating your response...Please try prompting again."
        finally:
            if self.driver:
                self.driver.quit()
                print("[INFO] Browser closed.")
                uc.Chrome.__del__ = lambda self: None
