import validators
import socket
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import os
import platform
import colorama
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

colorama.init(autoreset=True)
fg = [
    colorama.Fore.RED + colorama.Style.BRIGHT,     # red 0
    colorama.Fore.GREEN + colorama.Style.BRIGHT,   # green 1
    colorama.Fore.YELLOW + colorama.Style.BRIGHT,  # yellow 2
    colorama.Fore.BLUE + colorama.Style.BRIGHT,    # blue 3
    colorama.Fore.MAGENTA + colorama.Style.BRIGHT, # magenta 4
    colorama.Fore.CYAN + colorama.Style.BRIGHT,    # cyan 5
    colorama.Fore.WHITE + colorama.Style.BRIGHT    # white 6
]

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def clear():
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def banner():
    clear()
    print('''
  
                  _________-----_____
       _____------           __      ----_
___----             ___------              \\
   ----________        ----                 \\
               -----__    |             _____)
                    __-                /     \\
        _______-----    ___--          \    /)\\
  ------_______      ---____            \__/  /
               -----__    \ --    _          /\\
                      --__--__     \_____/   \_/\\
                              ----|   /          |
                                  |  |___________|
                                  |  | ((_(_)| )_)
                                  |  \\_((_(_)|/(_)
                                  \\             (
                                   \\_____________) Channel:@undergroundcy
    ''')


def get_website_ip(website):
    """Resolves website to an IP address."""
    try:
        hostname = urlparse(website).hostname
        return website, socket.gethostbyname(hostname)
    except (socket.gaierror, AttributeError):
        return website, None


def process_website(website, total_websites, idx):
    """Process a single website to extract IP."""
    _, ip = get_website_ip(website)
    if ip:
        logging.info(f"Converting {idx}/{total_websites}: {fg[1]}Website {website} is {ip}")
        return ip
    else:
        logging.info(f"Converting {idx}/{total_websites}: {fg[0]}Error: Couldn't resolve IP for {website}")
        return None


def read_ips_from_file(file_path):
    """Reads IPs from file."""
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logging.error(f"{fg[0]}Error: File {file_path} not found.")
        return []


def extract_domains_for_ip(ip):
    """Extracts domains hosted on a given IP."""
    base_url = "https://rapiddns.io/sameip/"
    extracted_domains = []
    page = 1

    while True:
        try:
            url = f"{base_url}{ip}?page={page}"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            for row in soup.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) > 1:
                    domain = cols[0].text.strip()
                    extracted_domains.append(domain)

            # Check for pagination
            pagination = soup.find('ul', class_='pagination')
            if pagination:
                all_pages = pagination.find_all('a', class_='page-link')
                last_page_number = int(all_pages[-2].get('href').split('=')[-1])
                if page >= last_page_number:
                    break
                page += 1
            else:
                break

        except requests.RequestException:
            logging.error(f"{fg[0]}Error: Could not fetch data from {url}")
            break

    return extracted_domains


def extract_domains_from_ips(file_path, output_file='extracted.txt', threads=5):
    """Extract domains for a list of IPs."""
    ips = read_ips_from_file(file_path)
    if not ips:
        return

    all_domains = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(extract_domains_for_ip, ip): ip for ip in ips}

        for future in as_completed(futures):
            ip = futures[future]
            try:
                domains = future.result()
                all_domains.extend(domains)
                logging.info(f"\nExtracted {len(domains)} domains for IP {ip}")
            except Exception as e:
                logging.error(f"Error extracting domains for IP {ip}: {str(e)}")

    # Write extracted domains to file
    with open(output_file, 'w') as f:
        for domain in all_domains:
            f.write(f"{domain}\n")

    logging.info(f"\nExtraction completed. Output written to {output_file}")


def resolve_websites_to_ips(website_list):
    """Resolves a list of websites to their IPs using multiple threads."""
    total_websites = len(website_list)
    ips = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_website, website, total_websites, idx + 1): website
                   for idx, website in enumerate(website_list)}

        for future in as_completed(futures):
            try:
                ip = future.result()
                if ip:
                    ips.append(ip)
            except Exception as e:
                logging.error(f"Error resolving IP for website {futures[future]}: {str(e)}")

    return ips


def main():
    banner()
    file_path = input("Enter your file path: ")

    try:
        website_list, ip_list = [], []
        with open(file_path) as file:
            for line in file:
                entry = line.strip()
                if entry:
                    if validators.url(entry):
                        website_list.append(entry)
                    elif validators.ipv4(entry) or validators.ipv6(entry):
                        ip_list.append(entry)
    except FileNotFoundError:
        logging.error(f"{fg[0]}Error: File {file_path} not found.")
        return

    logging.info(f"Number of websites: {len(website_list)}")
    logging.info(f"Number of IPs: {len(ip_list)}")

    # Convert websites to IPs
    if website_list:
        logging.info(f"Converting {len(website_list)} URLs to IPs")
        ips_from_websites = resolve_websites_to_ips(website_list)
        unique_ips = set(ips_from_websites + ip_list)

        # Write IPs to output file
        output_file = "output.txt"
        with open(output_file, 'w') as f:
            for ip in unique_ips:
                f.write(f"{ip}\n")

        logging.info(f"\nTotal IPs: {len(unique_ips)}")
        logging.info(f"Output written to {output_file}")

        # Extract domains for the collected IPs
        extract_domains_from_ips(output_file)


if __name__ == '__main__':
    main()
