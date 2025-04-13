from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.firefox.launch(headless=False)
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720}
    )
    page = context.new_page()

    try:
        print("Navigating to YouTube...")
        page.goto('https://www.youtube.com', timeout=60000, wait_until='domcontentloaded')
        print("✅ YouTube homepage loaded.")

        # Give it a moment to render the page properly
        page.wait_for_timeout(3000)

        print("Waiting for search input...")
        # Try a broader selector that is more reliable
        page.wait_for_selector('input[name="search_query"]', timeout=10000)

        print("Typing Ed Sheeran song name...")
        page.fill('input[name="search_query"]', 'Ed Sheeran Perfect')

        print("Pressing Enter to search...")
        page.keyboard.press('Enter')

        print("Waiting for search results...")
        page.wait_for_selector('ytd-video-renderer', timeout=15000)

        print("Clicking first video...")
        page.click('ytd-video-renderer')

        print("Waiting for video page to load...")
        page.wait_for_selector('span.view-count', timeout=15000)

        view_count = page.inner_text('span.view-count')
        print(f"🎥 View Count: {view_count}")

        page.screenshot(path='ed_sheeran_video_page.png')

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        try:
            page.screenshot(path='error_state.png')
        except:
            pass
    finally:
        browser.close()
        print("✅ Browser closed")

with sync_playwright() as playwright:
    run(playwright)
