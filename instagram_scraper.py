import instaloader
import time
from openpyxl import Workbook
import random
import requests
from instaloader.exceptions import ProfileNotExistsException, LoginRequiredException, TooManyRequestsException

class InstagramScraper:
    def __init__(self, username, password):
        self.L = instaloader.Instaloader()
        self.username = username
        self.password = password
        self.proxies = self.get_proxies_from_proxyscrape()
        self.current_proxy = None
        self.followers_data = []

    def get_proxies_from_proxyscrape(self):
        try:
            response = requests.get('https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all')
            if response.status_code == 200:
                proxy_list = response.text.strip().split('\r\n')
                return [f"http://{proxy}" for proxy in proxy_list]
            else:
                print("Failed to fetch proxies from ProxyScrape")
                return []
        except Exception as e:
            print(f"Error fetching proxies: {str(e)}")
            return []

    def login(self):
        try:
            if self.proxies:
                self.rotate_proxy()
            self.L.login(self.username, self.password)
            print("Login successful")
            return True
        except TooManyRequestsException as e:
            print(f"Rate limited during login: {str(e)}")
            self.handle_rate_limit(e)
            return False
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False
    def rotate_proxy(self):
        if self.proxies:
            self.current_proxy = random.choice(self.proxies)
            self.L.context._session.proxies = {'http': self.current_proxy, 'https': self.current_proxy}
            print(f"Using proxy: {self.current_proxy}")

    def scrape_followers(self, target_username, max_followers=None):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.rotate_proxy()  # Rotate proxy before fetching profile
                profile = instaloader.Profile.from_username(self.L.context, target_username)
                
                if profile.is_private:
                    print(f"The account {target_username} is private. Unable to scrape followers.")
                    return []

                followers = profile.get_followers()
                
                print(f"Scraping followers of {target_username}")
                count = 0
                
                for follower in followers:
                    if max_followers is not None and count >= max_followers:
                        break
                    
                    follower_data = self.process_follower(follower)
                    if follower_data:
                        self.followers_data.append(follower_data)
                    count += 1
                    
                    if count % 100 == 0:
                        print(f"Processed {count} followers")
                    
                    time.sleep(0.1)  # Small delay to avoid overwhelming the API
                
                print(f"Total followers processed: {len(self.followers_data)}")
                return self.followers_data

            except ProfileNotExistsException:
                print(f"The profile {target_username} does not exist.")
                return []
            except LoginRequiredException:
                print("Login is required to view this profile. Ensure you're logged in and the account is public.")
                return []
            except TooManyRequestsException as e:
                print(f"Rate limited while scraping followers (attempt {attempt + 1}/{max_retries})")
                self.handle_rate_limit(e)
                if attempt < max_retries - 1:
                    print("Retrying...")
                else:
                    print("Max retries reached. Unable to scrape followers.")
                    return []
            except Exception as e:
                print(f"Error scraping followers (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    time.sleep(5)  
                else:
                    print("Max retries reached. Unable to scrape followers.")
                    return []

        return []  # If all retries fail

    def process_follower(self, follower):
        try:
            follower_data = {
                "username": follower.username,
                "bio": follower.biography,
                "followers_count": follower.followers
            }
            self.rotate_proxy()
            return follower_data
        except TooManyRequestsException as e:
            print(f"Rate limited while processing follower {follower.username}")
            self.handle_rate_limit(e)
            return None

    def save_to_excel(self, data, filename):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Followers Data"

            # Add headers
            headers = ["Username", "Bio", "Followers Count"]
            ws.append(headers)

            # Add data in batches
            batch_size = 5000
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                for follower in batch:
                    ws.append([follower['username'], follower['bio'], follower['followers_count']])
                print(f"Wrote {i + len(batch)} rows to Excel")

            # Adjust column widths
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column[:1000]:  # Sample only the first 1000 rows
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = min((max_length + 2), 100)  # Cap width at 100
                ws.column_dimensions[column_letter].width = adjusted_width

            wb.save(filename)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving to Excel: {str(e)}")

    def run(self):
        if self.login():
            target_username = input("Enter the username whose followers you want to scrape: ")
            scrape_all = input("Do you want to scrape all followers? (y/n): ").lower() == 'y'
            
            if scrape_all:
                max_followers = None
            else:
                max_followers = int(input("Enter the maximum number of followers to scrape: "))
            
            followers_data = self.scrape_followers(target_username, max_followers)
            if followers_data:
                filename = f"{target_username}_followers_data.xlsx"
                self.save_to_excel(followers_data, filename)
            else:
                print("No follower data collected")
        else:
            print("Login failed, unable to proceed")

    def test_proxy_scraping(self):
        proxies = self.get_proxies_from_proxyscrape()
        print(f"Number of proxies fetched: {len(proxies)}")
        print("First 5 proxies:")
        for proxy in proxies[:5]:
            print(proxy)

if __name__ == "__main__":
    scraper = InstagramScraper("username", "password")
    scraper.run()
