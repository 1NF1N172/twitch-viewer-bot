# ==========================================
# REQUIREMENTS AND INSTALLATION INSTRUCTIONS
# ==========================================
#
# 1. Install Python packages:
#    pip install colorama pystyle selenium requests
#
# 2. Install ChromeDriver:
#    - Download ChromeDriver from: https://chromedriver.chromium.org/downloads
#    - Make sure the version matches your Chrome browser version
#    - Place chromedriver.exe in the same folder as this script
#
# 3. AdBlock will be downloaded and installed automatically!
#
# ==========================================

import requests
import warnings
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from colorama import Fore
from pystyle import Center, Colors, Colorate
import os
import time
import zipfile
import shutil


warnings.filterwarnings("ignore", category=DeprecationWarning)

def download_ublock_origin():
    """Download uBlock Origin extension"""
    extension_dir = "ublock_extension"
    manifest_path = os.path.join(extension_dir, "manifest.json")
    
    # Check if valid extension already exists
    if os.path.exists(manifest_path):
        print(Fore.GREEN + "✓ uBlock Origin extension found!")
        return extension_dir
    
    # Clean up old folders
    for old_dir in ["ublock_extension", "adblock_extension", "ublock_origin"]:
        if os.path.exists(old_dir):
            try:
                shutil.rmtree(old_dir)
            except:
                pass
    
    print(Fore.YELLOW + "Downloading uBlock Origin extension...")
    
    # uBlock Origin CRX URL
    extension_url = "https://clients2.google.com/service/update2/crx?response=redirect&prodversion=120.0&acceptformat=crx2,crx3&x=id%3Dcjpalhdlnbpafiamejdnhcphjbkeiagm%26uc"
    
    try:
        response = requests.get(extension_url, timeout=30)
        crx_file = "ublock_temp.crx"
        
        with open(crx_file, 'wb') as f:
            f.write(response.content)
        
        print(Fore.GREEN + "✓ Downloaded successfully!")
        print(Fore.YELLOW + "Extracting extension...")
        
        # Read CRX file
        with open(crx_file, 'rb') as f:
            content = f.read()
        
        # Find ZIP header (CRX files are ZIP archives with a header)
        zip_start = content.find(b'PK\x03\x04')
        
        if zip_start != -1:
            # Extract ZIP content
            zip_file = "ublock_temp.zip"
            with open(zip_file, 'wb') as f:
                f.write(content[zip_start:])
            
            # Unzip
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extension_dir)
            
            # Cleanup temp files
            try:
                os.remove(crx_file)
                os.remove(zip_file)
            except:
                pass
            
            # Verify
            if os.path.exists(os.path.join(extension_dir, "manifest.json")):
                print(Fore.GREEN + "✓ Extension ready!")
                return extension_dir
            else:
                print(Fore.RED + "✗ Extension validation failed")
                return None
        else:
            print(Fore.RED + "✗ Could not extract extension")
            return None
            
    except Exception as e:
        print(Fore.RED + f"✗ Error: {e}")
        return None

def setup_chrome_with_adblock():
    """Setup Chrome with uBlock Origin properly loaded"""
    
    # Download extension
    extension_path = download_ublock_origin()
    
    chrome_options = webdriver.ChromeOptions()
    
    # Basic Chrome settings
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--mute-audio')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-sandbox')
    
    # Realistic user agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Ad blocking preferences
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "media_stream": 2,
        },
        "profile.managed_default_content_settings": {
            "popups": 2  # Block popups
        }
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Load the extension if available
    if extension_path and os.path.exists(extension_path):
        abs_path = os.path.abspath(extension_path)
        chrome_options.add_argument(f'--load-extension={abs_path}')
        chrome_options.add_argument('--disable-extensions-except=' + abs_path)
        print(Fore.GREEN + f"✓ uBlock Origin loaded: {abs_path}")
    else:
        print(Fore.YELLOW + "⚠ Running without extension - using built-in ad blocking")
    
    return chrome_options

def inject_aggressive_adblock(driver):
    """Inject targeted ad blocking JavaScript - won't break site functionality"""
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                // Remove webdriver flag
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // Block only known ad domains - very specific
                const blockedDomains = [
                    'doubleclick.net', 
                    'googlesyndication.com', 
                    'googleadservices.com',
                    'advertising.com',
                    'adserver.com',
                    'ads-twitter.com',
                    'analytics.google.com'
                ];
                
                // Intercept fetch for ad domains only
                const originalFetch = window.fetch;
                window.fetch = function(...args) {
                    const url = args[0].toString();
                    if (blockedDomains.some(d => url.includes(d))) {
                        return Promise.reject('blocked');
                    }
                    return originalFetch.apply(this, args);
                };
                
                // Hide ad elements with CSS - more specific selectors
                const style = document.createElement('style');
                style.textContent = `
                    iframe[src*="doubleclick"],
                    iframe[src*="googlesyndication"],
                    .adsbygoogle,
                    .advertisement,
                    .ad-banner,
                    div[id^="google_ads_"],
                    div[class*="GoogleActiveViewClass"] {
                        display: none !important;
                        visibility: hidden !important;
                    }
                `;
                
                // Wait for DOM and inject
                if (document.head) {
                    document.head.appendChild(style);
                } else {
                    document.addEventListener('DOMContentLoaded', () => {
                        document.head.appendChild(style);
                    });
                }
            '''
        })
    except:
        pass

def print_banner():
    """Print the banner"""
    os.system("cls")
    print(Colorate.Vertical(Colors.green_to_cyan, Center.XCenter("""
           
        ██╗███╗   ██╗███████╗
        ██║████╗  ██║██╔════╝
        ██║██╔██╗ ██║█████╗  
        ██║██║╚██╗██║██╔══╝  
        ██║██║ ╚████║██║     
        ╚═╝╚═╝  ╚═══╝╚═╝     
                                                             
Improvements can be made to the code. If you're getting an error, check the docs.
                             Github  1NF    """)))
    print("")
    print("")

def run_viewer_session(driver, proxy_url, twitch_username, proxy_count):
    """Run a viewer bot session"""
    successful_tabs = 0
    failed_tabs = 0

    for i in range(proxy_count):
        try:
            print(f"\n{Fore.CYAN}[Tab {i+1}/{proxy_count}] Opening new tab...")
            
            # Open new tab
            driver.execute_script("window.open('" + proxy_url + "')")
            driver.switch_to.window(driver.window_handles[-1])
            
            # Inject ad blocking in new tab
            inject_aggressive_adblock(driver)
            
            driver.get(proxy_url)
            
            print(f"{Fore.YELLOW}[Tab {i+1}/{proxy_count}] Loading page...")
            time.sleep(3)
            
            # Wait for page load
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(2)
            
            # Immediately close any consent popups
            try:
                driver.execute_script("""
                    // Remove all consent/cookie popups
                    document.querySelectorAll('[class*="consent"], [id*="consent"], [class*="cookie"], [id*="cookie"]').forEach(el => {
                        el.remove();
                    });
                    
                    // Click consent if exists
                    let consentBtn = document.querySelector('button[class*="consent"], button[id*="consent"]');
                    if (consentBtn) consentBtn.click();
                """)
            except:
                pass
            
            # Try clicking consent button
            try:
                consent_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Consent') or contains(text(), 'Accept')]"))
                )
                consent_button.click()
                time.sleep(1)
            except:
                pass
            
            print(f"{Fore.CYAN}[Tab {i+1}/{proxy_count}] Finding input field...")
            
            # Find input field
            text_box = None
            try:
                text_box = driver.find_element(By.ID, 'url')
                if text_box.get_attribute('type') != 'text':
                    text_box = None
            except:
                pass
            
            if text_box is None:
                try:
                    text_box = driver.find_element(By.CSS_SELECTOR, 'input[name="url"][type="text"]')
                except:
                    pass
            
            if text_box is None:
                print(f"{Fore.RED}[Tab {i+1}/{proxy_count}] ✗ Input field not found")
                failed_tabs += 1
                continue
            
            # Remove overlays
            try:
                driver.execute_script("""
                    document.querySelectorAll('[class*="modal"], [class*="popup"], [class*="overlay"]').forEach(el => {
                        el.style.display = 'none';
                    });
                """)
            except:
                pass
            
            # Interact with input
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", text_box)
            time.sleep(0.5)
            
            try:
                driver.execute_script("arguments[0].click();", text_box)
            except:
                pass
            
            time.sleep(0.5)
            
            print(f"{Fore.CYAN}[Tab {i+1}/{proxy_count}] Entering URL...")
            
            try:
                text_box.clear()
                time.sleep(0.3)
                text_box.send_keys(f'www.twitch.tv/{twitch_username}')
                time.sleep(0.5)
                
                try:
                    go_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Go')]")
                    go_button.click()
                except:
                    text_box.send_keys(Keys.RETURN)
                    
            except:
                driver.execute_script(f"arguments[0].value = 'www.twitch.tv/{twitch_username}';", text_box)
                time.sleep(0.3)
                try:
                    text_box.send_keys(Keys.RETURN)
                except:
                    pass
            
            successful_tabs += 1
            print(f"{Fore.GREEN}[Tab {i+1}/{proxy_count}] ✓ Viewer sent!")
            
            print(f"{Fore.YELLOW}[Tab {i+1}/{proxy_count}] Loading Twitch...")
            time.sleep(8)
            
            # Unmute and play video
            try:
                driver.execute_script("""
                    setTimeout(() => {
                        let video = document.querySelector('video');
                        if (video) {
                            video.muted = false;
                            video.play();
                        }
                    }, 3000);
                """)
            except:
                pass
            
            time.sleep(2)
            
        except Exception as e:
            print(f"{Fore.RED}[Tab {i+1}/{proxy_count}] ✗ Error: {str(e)[:100]}")
            failed_tabs += 1

    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.GREEN}SUCCESS: {successful_tabs} tabs | {Fore.RED}FAILED: {failed_tabs} tabs")
    print(f"{Fore.CYAN}{'='*50}\n")
    
    return successful_tabs, failed_tabs

def close_all_tabs(driver):
    """Close all tabs except the first one"""
    try:
        # Get all window handles
        all_windows = driver.window_handles
        
        # Close all windows except the first one
        for window in all_windows[1:]:
            driver.switch_to.window(window)
            driver.close()
        
        # Switch back to the first window
        driver.switch_to.window(all_windows[0])
        
        print(f"{Fore.GREEN}✓ All tabs closed successfully!")
    except Exception as e:
        print(f"{Fore.RED}✗ Error closing tabs: {e}")

def main():
    os.system(f"title 1NF - Twitch Viewer Bot")

    print_banner()
    
    # Setup Chrome options FIRST (but don't open browser yet)
    chrome_options = setup_chrome_with_adblock()
    print("")

    proxy_servers = {
        1: "https://www.blockaway.net",
        2: "https://www.croxyproxy.com",
        3: "https://www.croxyproxy.rocks",
        4: "https://www.croxy.network",
        5: "https://www.croxy.org",
        6: "https://www.youtubeunblocked.live",
        7: "https://www.croxyproxy.net",
    }

    # Get user input FIRST before opening browser
    print(Colors.green, "Proxy Server 1 Is Recommended")
    print(Colorate.Vertical(Colors.green_to_blue, "Please select a proxy server(1,2,3..):"))
    for i in range(1, 8):
        print(Colorate.Vertical(Colors.red_to_blue, f"Proxy Server {i}"))
    proxy_choice = int(input("> "))
    proxy_url = proxy_servers.get(proxy_choice)

    twitch_username = input(Colorate.Vertical(Colors.green_to_blue, "Enter your channel name (e.g 1NF): "))
    proxy_count = int(input(Colorate.Vertical(Colors.cyan_to_blue, "How many proxy sites do you want to open? (Viewer to send)")))
    
    print_banner()
    print(Colors.red, Center.XCenter("Starting viewer bot... Please wait"))
    print('')
    
    # NOW initialize Chrome with options
    print(Fore.YELLOW + "Initializing browser and ad blocker...")
    driver = webdriver.Chrome(options=chrome_options)
    
    # Inject ad blocking
    inject_aggressive_adblock(driver)
    
    # Maximize window
    driver.maximize_window()
    
    # Give extension time to initialize
    time.sleep(3)
    
    # Load the first page
    driver.get(proxy_url)
    
    print("Waiting for first page to load...")
    time.sleep(5)

    # Run the first session
    run_viewer_session(driver, proxy_url, twitch_username, proxy_count)
    
    # Main loop for additional sessions
    while True:
        # Ask what to do next
        print(f"\n{Fore.CYAN}{'='*50}")
        print(Fore.YELLOW + "What would you like to do?")
        print(Fore.GREEN + "1. Add more sessions")
        print(Fore.RED + "2. Exit and close all browser sessions")
        print(f"{Fore.CYAN}{'='*50}\n")
        
        choice = input(Fore.YELLOW + "Enter your choice (1 or 2): ").strip()
        
        if choice == "1":
            print(f"\n{Fore.YELLOW}Starting new session (keeping existing tabs)...")
            
            # Get new configuration
            print_banner()
            print(Colors.green, "Proxy Server 1 Is Recommended")
            print(Colorate.Vertical(Colors.green_to_blue, "Please select a proxy server(1,2,3..):"))
            for i in range(1, 8):
                print(Colorate.Vertical(Colors.red_to_blue, f"Proxy Server {i}"))
            proxy_choice = int(input("> "))
            proxy_url = proxy_servers.get(proxy_choice)

            twitch_username = input(Colorate.Vertical(Colors.green_to_blue, "Enter your channel name (e.g 1NF): "))
            proxy_count = int(input(Colorate.Vertical(Colors.cyan_to_blue, "How many proxy sites do you want to open? (Viewer to send)")))
            
            print_banner()
            print(Colors.red, Center.XCenter("Starting viewer bot... Please wait"))
            print('')
            
            # Run the new session
            run_viewer_session(driver, proxy_url, twitch_username, proxy_count)
        else:
            print(f"\n{Fore.GREEN}Closing all browser sessions and exiting...")
            driver.quit()
            break
    
    print(f"\n{Fore.GREEN}Thank you for using 1NF Twitch Viewer Bot!")
 #   input(Fore.YELLOW + "Press Enter to exit...")
    sleep(3)

if __name__ == '__main__':
    main()

# ==========================================
# Copyright 2025 1NF
# ==========================================