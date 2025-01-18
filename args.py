import argparse

parser = argparse.ArgumentParser()
# New arguments for revise_homework.py
parser.add_argument('--api_key', type=str, help='API key for OpenAI')
parser.add_argument('--base_url', type=str, help='Base URL for API proxy', default='https://a1.aizex.me/v1')
parser.add_argument('--max_workers', type=int, default=4, help='Maximum number of workers for ThreadPoolExecutor')
parser.add_argument('--number_prepare', type=int, default=10, help='Number of students to prepare scores for')
parser.add_argument('--number_gen', type=int, default=5, help='Number of students to generate scores for')

# New arguments for prepare_data.py
parser.add_argument('--chrome_driver_path', type=str, help='Path to ChromeDriver executable')
parser.add_argument('--phonenumber', type=str, help='Phone number for login')
parser.add_argument('--password', type=str, help='Password for login')
parser.add_argument('--class_list', nargs='+', help='List of class names to process')
parser.add_argument('--course_urls', nargs='+', help='List of course URLs to process')

config = parser.parse_args()
