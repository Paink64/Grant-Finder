from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import ActionResult, Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from pydantic import SecretStr
from browser_use.browser.context import BrowserContext

import os
from dotenv import load_dotenv
import asyncio

import time
from playwright.sync_api import sync_playwright

browser = Browser(
	config=BrowserConfig(
		chrome_instance_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
	),
)


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

controller = Controller()


def is_google_sheet(page) -> bool:
	return page.url.startswith('https://docs.google.com/spreadsheets/')


# TODO: refactor if not is_google_sheet(page): checks below to something like this:
# @controller.registry.action('Do something with a Google Sheet', page_filter=is_google_sheet)
# async def some_google_sheet_action(browser: BrowserContext):
# 	...


@controller.registry.action('Google Sheets: Open a specific Google Sheet')
async def open_google_sheet(browser: BrowserContext, google_sheet_url: str):
	page = await browser.get_current_page()
	if page.url != google_sheet_url:
		await page.goto(google_sheet_url)
		await page.wait_for_load_state()
	if not is_google_sheet(page):
		return ActionResult(error='Failed to open Google Sheet, are you sure you have permissions to access this sheet?')
	return ActionResult(extracted_content=f'Opened Google Sheet {google_sheet_url}', include_in_memory=False)


@controller.registry.action('Google Sheets: Get the contents of the entire sheet')
async def get_sheet_contents(browser: BrowserContext):
	page = await browser.get_current_page()
	if not is_google_sheet(page):
		return ActionResult(error='Current page is not a Google Sheet')

	# select all cells
	await page.keyboard.press('Enter')
	await page.keyboard.press('Escape')
	await page.keyboard.press('ControlOrMeta+A')
	await page.keyboard.press('ControlOrMeta+C')

	extracted_tsv = pyperclip.paste()
	return ActionResult(extracted_content=extracted_tsv, include_in_memory=True)


@controller.registry.action('Google Sheets: Select a specific cell or range of cells')
async def select_cell_or_range(browser: BrowserContext, cell_or_range: str):
	page = await browser.get_current_page()
	if not is_google_sheet(page):
		return ActionResult(error='Current page is not a Google Sheet')

	await page.keyboard.press('Enter')  # make sure we dont delete current cell contents if we were last editing
	await page.keyboard.press('Escape')  # to clear current focus (otherwise select range popup is additive)
	await asyncio.sleep(0.1)
	await page.keyboard.press('Home')  # move cursor to the top left of the sheet first
	await page.keyboard.press('ArrowUp')
	await asyncio.sleep(0.1)
	await page.keyboard.press('Control+G')  # open the goto range popup
	await asyncio.sleep(0.2)
	await page.keyboard.type(cell_or_range, delay=0.05)
	await asyncio.sleep(0.2)
	await page.keyboard.press('Enter')
	await asyncio.sleep(0.2)
	await page.keyboard.press('Escape')  # to make sure the popup still closes in the case where the jump failed
	return ActionResult(extracted_content=f'Selected cell {cell_or_range}', include_in_memory=False)


@controller.registry.action('Google Sheets: Get the contents of a specific cell or range of cells')
async def get_range_contents(browser: BrowserContext, cell_or_range: str):
	page = await browser.get_current_page()
	if not is_google_sheet(page):
		return ActionResult(error='Current page is not a Google Sheet')

	await select_cell_or_range(browser, cell_or_range)

	await page.keyboard.press('ControlOrMeta+C')
	await asyncio.sleep(0.1)
	extracted_tsv = pyperclip.paste()
	return ActionResult(extracted_content=extracted_tsv, include_in_memory=True)


@controller.registry.action('Google Sheets: Clear the currently selected cells')
async def clear_selected_range(browser: BrowserContext):
	page = await browser.get_current_page()
	if not is_google_sheet(page):
		return ActionResult(error='Current page is not a Google Sheet')

	await page.keyboard.press('Backspace')
	return ActionResult(extracted_content='Cleared selected range', include_in_memory=False)


@controller.registry.action('Google Sheets: Input text into the currently selected cell')
async def input_selected_cell_text(browser: BrowserContext, text: str):
	page = await browser.get_current_page()
	if not is_google_sheet(page):
		return ActionResult(error='Current page is not a Google Sheet')

	await page.keyboard.type(text, delay=0.1)
	await page.keyboard.press('Enter')  # make sure to commit the input so it doesnt get overwritten by the next action
	await page.keyboard.press('ArrowUp')
	return ActionResult(extracted_content=f'Inputted text {text}', include_in_memory=False)


@controller.registry.action('Google Sheets: Batch update a range of cells')
async def update_range_contents(browser: BrowserContext, range: str, new_contents_tsv: str):
	page = await browser.get_current_page()
	if not is_google_sheet(page):
		return ActionResult(error='Current page is not a Google Sheet')

	await select_cell_or_range(browser, range)

	# simulate paste event from clipboard with TSV content
	await page.evaluate(f"""
		const clipboardData = new DataTransfer();
		clipboardData.setData('text/plain', `{new_contents_tsv}`);
		document.activeElement.dispatchEvent(new ClipboardEvent('paste', {{clipboardData}}));
	""")

	return ActionResult(extracted_content=f'Updated cell {range} with {new_contents_tsv}', include_in_memory=False)



# Initialize the model
llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(os.getenv('GEMINI_API_KEY')))

sensitive_data = {'x_name': os.getenv("MYUSERNAME"), 'x_password': os.getenv("MYPASSWORD")}
organization = "California State University, San Bernardino"

initial_actions = [
	{'go_to_url': {'url': 'https://spin.infoedglobal.com'}},
	{'click_element': {'index': 7}},
    {'send_keys': {'keys': 'California State University, San Bernardino\n'}},
    {'click_element': {'index': 8}},
    {'click_element': {'index': 0}},
    {'send_keys': {'keys': sensitive_data['x_name']}},
    {'click_element': {'index': 1}},
    {'send_keys': {'keys': sensitive_data['x_password']}},
    {'send_keys': {'keys': '\n'}},
    {'wait': {'seconds' : 10}},
    {'click_element': {'index': 2}},
]

# Create agent with the model
async def main():
    agent = Agent(
        task="""In this database look for a grant that has to do with AI. Look through the grants and see which pay the most, Open https://docs.google.com/spreadsheets/
            Add on the first more rows 3column headers are present and all existing values in the sheet are formatted correctly.
				Columns:
					A: ID
					B: Link
					C: Funding
					D: Deadline
        
        
        
        """,
        llm=llm,
        initial_actions=initial_actions,
        sensitive_data=sensitive_data,
    )
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())