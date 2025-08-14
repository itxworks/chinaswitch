import hashlib
import json
import os
import time
import schedule
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def is_docker():
    try:
        with open('/proc/self/cgroup', 'r') as procfile:
            for line in procfile:
                if 'docker' in line:
                    return True
    except FileNotFoundError:
        pass

    try:
        with open('/.dockerenv', 'r') as envfile:
            return True
    except FileNotFoundError:
        pass

    return False


def check_geckodriver_log():
    if is_docker():
        log_path = '/tmp/geckodriver.log'
        if os.path.exists(log_path):
            with open(log_path, 'r') as log_file:
                print(log_file.read())


def md5_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for form in soup.find_all('form'):
        form.decompose()
    return str(soup)


def find_valid_webdriver(webdriver_paths):
    for path in webdriver_paths:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("No valid WebDriver found.")


def extract_headers(table):
    headers = []
    header_rows = table.find_all('tr')[:2]  # Assuming the first two rows are headers

    for row_idx, header_row in enumerate(header_rows):
        for th in header_row.find_all('th'):
            header_text = th.get_text().strip()
            colspan = int(th.get('colspan', 1))

            if header_text in ['Speed/Duplex', 'Flow Control']:
                headers.append(header_text)  # Parent header
                headers.extend(['Speed/Actual', 'Flow_Control'] * (colspan // 2))  # Add 'Config' and 'Actual'
            elif header_text not in ['Config', 'Actual']:
                headers.extend([header_text] * colspan)
    final_headers = []
    seen = set()
    for header in headers:
        if header not in seen:
            final_headers.append(header)
            seen.add(header)

    print(f"Headers found: {final_headers}")  # Debugging line to check headers
    return final_headers


def extract_table_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    if not table:
        print("No table found in the HTML content.")
        return []

    headers = extract_headers(table)
    print(f"Headers found: {headers}")

    rows = []
    for tr in table.find_all('tr')[2:]:  # Skipping header rows
        cells = [td.get_text().strip() for td in tr.find_all('td')]
        print(f"Row cells: {cells}")

        # Adjust the header count to match cells
        expected_len = len(headers)
        if len(cells) == expected_len:
            row_data = {headers[i]: cells[i] for i in range(len(headers))}
            print(f"Row data: {row_data}")
            rows.append(row_data)
        else:
            print(f"Skipping row with insufficient columns: {cells}")

    return rows


def process_results(all_results):
    for result in all_results:
        login_url = result['login_url']
        content = result['content']

        # Extract table data from content
        table_data = extract_table_data(content)

        # Update result with extracted table data
        result['table_data'] = table_data

        # Print the processed result for debugging
        print(f"Processed result for {login_url}:")
        print(f"Table data: {table_data}")

    # Save the updated results to JSON
    if is_docker():
        with open('/app/results.json', 'w') as f:
            json.dump(all_results, f, indent=4)
        print("All results with table data saved to /app/results.json")
    else:
        with open('results.json', 'w') as f:
            json.dump(all_results, f, indent=4)
        print("All results with table data saved to results.json")


def parse_combined_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    sections = soup.find_all('h2')

    for section in sections:
        url = section.get_text().replace('Results for ', '').strip()
        next_sibling = section.find_next_sibling()

        # Extract the following HTML that belongs to this section
        section_html = ''
        while next_sibling and next_sibling.name != 'h2':
            section_html += str(next_sibling)
            next_sibling = next_sibling.find_next_sibling()

        table_data = extract_table_data(section_html)
        results.append({
            'login_url': url,
            'content': section_html,
            'table_data': table_data
        })

    return results


def create_driver(webdriver_path):
    options = Options()
    options.headless = True  # Run in headless mode

    service = Service(executable_path=webdriver_path)  # Ensure the correct path to the geckodriver

    # Create the WebDriver instance
    driver = webdriver.Firefox(service=service, options=options)
    return driver


# Add call to check the logs after quitting the driver in `check_switches` function
def check_switches():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        webdriver_paths = ["./geckodriver", "/usr/local/bin/geckodriver", "/usr/bin/geckodriver"]
        webdriver_path = find_valid_webdriver(webdriver_paths)
        print(f"Using WebDriver at {webdriver_path}")
        all_results = []
        for switch in config['switches']:
            login_url = switch['login_url']
            port_url = switch['port_url']
            username = switch['username']
            password = switch['password']
            driver = create_driver(webdriver_path)
            try:
                driver.get(login_url)
                print(f"Opened login page for {login_url}")
                username_field = driver.find_element(By.NAME, "username")
                password_field = driver.find_element(By.NAME, "password")
                response_value = md5_hash(username + password)
                driver.execute_script("document.querySelector('input[name=\"Response\"]').value = arguments[0];",
                                      response_value)
                username_field.send_keys(username)
                password_field.send_keys(password)
                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "div_lgi"))
                )
                login_button.click()
                print(f"Submitted login form for {login_url}")
                WebDriverWait(driver, 10).until(
                    EC.url_changes(login_url)
                )
                driver.get(port_url)
                print(f"Navigated to port URL for {port_url}")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                page_source = driver.page_source
                clean_page_source = clean_html(page_source)
                table_data = extract_table_data(page_source)
                result = {
                    "login_url": login_url,
                    "content": clean_page_source,
                    "table_data": table_data
                }
                all_results.append(result)
            except Exception as e:
                print(f"Error during switch check for {login_url}: {e}")
            finally:
                driver.quit()
                check_geckodriver_log()  # Call to print geckodriver log

        combined_html = f"<html><head><title>Results</title></head><body><h3>Report generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}</h3>"
        
        for result in all_results:
            #combined_html += f"<h2>Results for {result['login_url']}</h2>"
            combined_html += f'<h2>Results for <a href="{result["login_url"]}" target="_blank">{result["login_url"]}</a></h2>'
            combined_html += result['content']
        combined_html += "</body></html>"
        if is_docker():
            with open('/app/index.html', 'w') as f:
                f.write(combined_html)
            print("All results saved to /app/index.html")
            process_results(all_results)
        else:
            with open('index.html', 'w') as f:
                f.write(combined_html)
            print("All results saved to index.html")
            process_results(all_results)
    except Exception as e:
        print(f"Error in check_switches: {e}")



def run_initial_and_schedule():
    check_switches()
    with open('config.json', 'r') as f:
        config = json.load(f)
    interval_minutes = config.get('schedule', {}).get('interval_minutes', 10)
    schedule.every(interval_minutes).minutes.do(check_switches)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    if is_docker():
        print("Running inside Docker")
    else:
        print("Not running inside Docker")

    run_initial_and_schedule()
