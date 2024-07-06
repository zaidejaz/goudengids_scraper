import requests
from bs4 import BeautifulSoup
import logging
import csv
import undetected_chromedriver as webdriver
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base URLs
main_base_url = "https://www.goudengids.be/zoeken/tattoo/{}"
detail_base_url = "https://www.goudengids.be"

# Browser header
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# Function to get the HTML content of a page
def get_html(url):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    browser = webdriver.Chrome(options=chrome_options)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Will raise an HTTPError for bad responses
        return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        browser.get(url)
        soup = BeautifulSoup(browser.page_source, features="html.parser")
        return None

# Function to parse the main page HTML and extract the links
def extract_links(html):
    soup = BeautifulSoup(html, 'html.parser')
    result_list = soup.find('div', id='result-list')
    if not result_list:
        logging.warning("No result-list found on the page")
        return []

    result_items_ol = result_list.find('ol', class_='result-items')
    if not result_items_ol:
        logging.warning("No result-items found within the result-list")
        return []

    links = []
    for item in result_items_ol.find_all('li', class_='result-item'):
        link_tag = item.find('a', class_='absolute bottom-0 left-0 right-0 top-0 z-10')
        if link_tag:
            links.append(detail_base_url + link_tag['href'])
        else:
            logging.warning("No link found in one of the result-item entries")

    return links

# Function to parse the detail page HTML and extract the required data
def extract_details(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Extract the name
    name_tag = soup.find('h1', id='listing-title')
    name = name_tag.get_text(strip=True) if name_tag else ''

    # Extract the address
    address_tag = soup.find('span', id='handleLinkOpenMap')
    if address_tag:
        postal_code = address_tag.find('span', {'data-yext': 'postal-code'}).get_text(strip=True) if address_tag.find('span', {'data-yext': 'postal-code'}) else ''
        city_district = address_tag.find('span', {'data-yext': 'city-district'}).get_text(strip=True) if address_tag.find('span', {'data-yext': 'city-district'}) else ''
        city = address_tag.find('span', {'data-yext': 'city'}).get_text(strip=True) if address_tag.find('span', {'data-yext': 'city'}) else ''
        street = address_tag.find('span', {'data-yext': 'street'}).get_text(strip=True) if address_tag.find('span', {'data-yext': 'street'}) else ''
        address = f"{postal_code} {city_district} ({city}) {street}"
    else:
        address = ''

    # Extract the email
    email_tag = soup.find('a', attrs={'data-ta': 'EmailBtnClick'})
    email = email_tag['href'].replace('mailto:', '').split('?')[0] if email_tag else ''

    # Extract the phone number
    phone_tag = soup.find('a', id='phoneNumber')
    phone = phone_tag['data-phone-number'] if phone_tag else ''
    if phone == '':
        phone_tag = soup.find('li', id='phoneNumber')
        a_tag = phone_tag.find('a', attrs={'data-phone-number': True})
        phone_data = ''
        if a_tag:
            phone = a_tag["data-phone-number"]

        else:
            span_tag = phone_tag.find('span', attrs={'data-phone-number': True})
            if span_tag:
                phone_data = span_tag["data-phone-number"]
        if phone_data == 'multi':
            phone_numbers_ul = phone_tag.find('ul')
            if phone_numbers_ul:
                phone_numbers = phone_numbers_ul.find_all('li', class_='flex')
                for phone_number in phone_numbers:
                    phone = phone + phone_number.find('a').get_text(strip=True) + ', '
    # Extract the website
    website_tag = soup.find('li', {'data-toggle-contacts': 'link'})
    website = website_tag.find('a')['href'] if website_tag and website_tag.find('a') else ''

    # Extract categories
    categories_sections = soup.find_all('section', id='GO__categories')
    categories_section = None
    for section in categories_sections:
        h2 = section.find('h2')
        if h2:
            h2_text = h2.text.strip()
            if h2_text == 'Bedrijfsinformatie' or h2_text == 'Informations sur l’entreprise' or h2_text == 'Company information':
                categories_section = section
                break
    if categories_section is None:
            categories_section = soup.find('section', id='GO__categories')
    lists = categories_section.find_all('li', class_='block mb-2')
    company_number = ''
    date_of_creation = ''
    number_of_employee = ''
    status = ''
    for list in lists:
        tag = list.find('span')
        if tag:
            tag = tag.text.strip()
            if tag == "Numero d'entreprise:" or tag == "Ondernemingsnummer:" or tag == "Company number:":
                company_number = list.get_text(strip=True).split(':')[1]
            elif tag == "Date de creation:" or tag == "Oprichtingsdatum:" or tag == "Date of creation:":
                date_of_creation = list.get_text(strip=True).split(':')[1]
            elif tag == "Nombre d'employes:" or tag == "Aantal werknemers:" or tag == "Number of employees:":
                number_of_employee = list.get_text(strip=True).split(':')[1]
            elif tag == "Statut:" or tag == "Status:":
                status = list.get_text(strip=True).split(':')[1]
            else:
                pass
        else:
            pass

            
    return {
        'Name': name,
        'Address': address,
        'Email': email,
        'Phone': phone,
        'Website': website,
        'Company Number': company_number,
        'Date of Creation': date_of_creation,
        'Number of Employee': number_of_employee,
        'Status': status
    }

# Main function to iterate over pages and collect links
def main():
    csv_file = 'tattoo_shops.csv'
    csv_columns = ['Name', 'Address', 'Email', 'Phone', 'Website', 'Company Number', 'Date of Creation', 'Number of Employee', 'Status']
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()

            for page_num in range(1, 68):  # Pages from 1 to 68
                url = main_base_url.format(page_num)
                logging.info(f"Fetching page {page_num}")
                html = get_html(url)
                if html:
                    page_links = extract_links(html)
                    logging.info(f"Found {len(page_links)} links on page {page_num}")
                    for link in page_links:
                        logging.info(f"Fetching details for {link}")
                        detail_html = get_html(link)
                        if detail_html:
                            details = extract_details(detail_html)
                            print(details)
                            writer.writerow(details)
                        else:
                            logging.error(f"Failed to retrieve details for {link}")
                else:
                    logging.error(f"Failed to retrieve page {page_num}")

        logging.info(f"Data successfully saved to {csv_file}")
    except IOError as e:
        logging.error(f"I/O error({e.errno}): {e.strerror}")

if __name__ == "__main__":
    main()