import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

async def run_automation(row_number, email, reason, callback_url):
    print(f"\n--- [LOG] Starting Automation for Row {row_number} at {datetime.now()} ---")
    userName = "a_maher"
    password = "Marketing123!"
    status = "Failed"
    log_notes = ""

    async with async_playwright() as p:
        try:
            print("Step 1: Launching Chromium browser with sandbox disabled...")
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context()
            page = await context.new_page()

            print(f"Step 2: Navigating to login page for Redtail...")
            await page.goto("[https://smf.accounts.redtailtechnology.com/?Product=tailwag](https://smf.accounts.redtailtechnology.com/?Product=tailwag)")

            print(f"Step 3: Filling credentials for user: {userName}")
            await page.fill('input[name="session[username]"]', userName)
            await page.fill('input[name="session[password]"]', password)
            
            print("Step 4: Clicking Sign In...")
            await page.click('input[type="submit"]')

            print("Step 5: Waiting for redirect to CRM dashboard...")
            await page.wait_for_url("**/[crm.redtailtechnology.com/](https://crm.redtailtechnology.com/)**", timeout=60000)
            print("Login successful - CRM Dashboard reached.")

            print("Step 6: Navigating to Advanced Search (Tags) page...")
            await page.goto("[https://crm.redtailtechnology.com/contacts/tags/3/send_to_search](https://crm.redtailtechnology.com/contacts/tags/3/send_to_search)")

            print(f"Step 7: Configuring search filters for email: {email}")
            await page.get_by_label('Type').first.select_option('Email')
            await page.get_by_label('Field').first.select_option('Address')
            await page.get_by_label('Operand').first.select_option('Equal To')
            await page.locator('//input[@type="text" and @aria-label="Value"]').fill(email)
            
            print("Step 8: Clicking 'Run' to execute search...")
            await page.locator('//input[@type="submit" and @value="Run"]').click()
            
            print("Step 9: Verifying if contact exists in search results...")
            try:
                client_link = page.locator("td.Name").locator("a")
                await client_link.wait_for(timeout=15000)
                print("Contact found. Opening contact overview page...")
                await client_link.click()
            except Exception:
                print(f"CRITICAL: Contact with email {email} was not found.")
                raise Exception(f"Contact {email} not found in Redtail.")

            print("Step 10: Checking for existing 'All Email' tag...")
            email_tag = page.locator("td").filter(has_text="All Email")
            if await email_tag.count() > 0:
                print("'All Email' tag found. Attempting removal...")
                icon_row = email_tag.locator("xpath=./preceding-sibling::td[last()]")
                await icon_row.locator('button[type="button"]').click()
                await page.locator("div.open a").filter(has_text="Remove from Tag Group").click()
                await page.locator('input[type="submit"][value="Remove Member"]').click()
                print("Successfully removed 'All Email' tag.")
            else:
                print("'All Email' tag not present. Skipping removal.")

            print("Step 11: Adding 'Unsubscribed from Emails' tag...")
            current_url = page.url
            base_url = current_url.split("?")[0]
            if not base_url.endswith("/"): base_url += "/"
            query_path = base_url.replace("[https://crm.redtailtechnology.com/](https://crm.redtailtechnology.com/)","/") + "tag_groups/new"
            
            print(f"Opening Tag Group modal at: {query_path}")
            await page.locator(f'a[href="{query_path}"]').click()
            
            tag_input = page.locator('input#tag-group-list-filter')
            await tag_input.click()
            await tag_input.press_sequentially("Unsubscribed from Emails", delay=80)
            await page.wait_for_timeout(2000)

            unsub_item = page.locator("li.list-group-item").filter(has_text="Unsubscribed from Emails")
            if await unsub_item.count() > 0:
                checkbox = unsub_item.locator("input[type='checkbox']")
                if not await checkbox.is_checked():
                    print("Checking the 'Unsubscribed' checkbox...")
                    await unsub_item.click()
                await page.locator('input[type="submit"][value="Save"]').click()
                print("Unsubscribe tag saved.")
            else:
                print("WARNING: 'Unsubscribed from Emails' tag not found in system list.")

            print("Step 12: Navigating to Notes section to log unsub reason...")
            await page.goto(base_url + "notes")
            await page.get_by_role("link", name="Add Note").click()
            
            print(f"Filling note with reason: {reason}")
            frame_selector = 'iframe[title="Editor, modal-crm-rich-text-field"]'
            await page.wait_for_selector(frame_selector, timeout=15000)
            note_frame = page.frame_locator(frame_selector)
            await note_frame.locator('body').click()
            await note_frame.locator('body').fill(reason)
            
            print("Clicking 'Save Note'...")
            await page.locator('input[type="submit"][value="Save Note"]').click()
            
            status = "Success"
            log_notes = "Unsubscribe process completed successfully."
            print(f"--- [SUCCESS] Row {row_number} processed for {email} ---")

        except Exception as e:
            print(f"--- [ERROR] Automation failed for Row {row_number}: {e} ---")
            status = "Error"
            log_notes = str(e)
        finally:
            print("Closing browser session...")
            await browser.close()

    print(f"Step 13: Sending final result back to Zapier Catch Hook: {callback_url}")
    try:
        payload = {
            "status": status, 
            "notes": log_notes, 
            "row_number": row_number, 
            "email": email,
            "processed_at": datetime.now().isoformat()
        }
        resp = requests.post(callback_url, json=payload, timeout=15)
        print(f"Zapier Callback sent. Status Code: {resp.status_code}")
    except Exception as cb_err:
        print(f"FAILED to send callback to Zapier: {cb_err}")