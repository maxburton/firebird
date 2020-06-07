"""
Program Name: Firebird
Description: Navigates JustEat menus emulating javascript clicks and scrolling to scrape all relevant data
Author: Max Burton
Version: 1.2.5
"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.support import expected_conditions as EC
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import shutil
import platform
import sys
import re
import json
import time
import math
import random
import traceback
import logging


# LOGGING Setup
log_format = '%(asctime)s [%(levelname)s]: %(message)s'
logging.basicConfig(filename='logs.txt', filemode='w', level=logging.INFO,
                    format=log_format, datefmt='%m/%d/%Y %I:%M:%S %p')
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter(log_format)

# add formatter to ch
ch.setFormatter(formatter)
logging.getLogger().addHandler(ch)


class Error(Exception):
    """Base class for other custom exceptions"""
    pass


class RestaurantNotOpenException(Error):
    """Raised when restaurant in not open and unavailable for preorder, hence unscrapable"""
    pass


class ElementNotClickableException(Error):
    """Raised after 10+ unsuccessful clicks"""
    pass


def encode_file(filename, message):
    # Open file in binary mode
    with open(filename, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email
    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {filename}",
    )

    # Add attachment to message and convert message to string
    message.attach(part)
    return message


def send_email():
    from_email = "ged.firebird@gmail.com"
    to_email = sys.argv[2]
    password = sys.argv[3]

    message = MIMEMultipart("alternative")
    message["Subject"] = "Scraping Results"
    message["From"] = from_email
    message["To"] = to_email

    text = """\
    Attached are the files generated from the scrape of %s

    Time Elapsed: %.2fs (%dhrs, %dmins, %dsecs)
    """ % (restaurant_name, time_elapsed, hours, minutes, seconds)
    html = """\
    <html>
      <body>
        <p>Attached are the files generated from the scrape of %s
        <br><br>
        Time Elapsed: %.2fs (%dhrs, %dmins, %dsecs)
        <br><br>
        </p>
      </body>
    </html>
    """ % (restaurant_name, time_elapsed, hours, minutes, seconds)

    message = encode_file(abs_file_path + "/menu.json", message)
    message = encode_file(abs_file_path + "/categories.csv", message)
    message = encode_file(abs_file_path + "/info.txt", message)
    message = encode_file(os.path.join(os.path.dirname(__file__), "logs.txt"), message)

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    # creates SMTP session
    s = smtplib.SMTP('smtp.gmail.com', 587)

    # start TLS for security
    s.starttls()

    # password = input("")

    # Authentication
    s.login(from_email, password)

    # sending the mail
    s.sendmail(from_email, to_email, message.as_string())

    # terminating the session
    s.quit()


def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata

    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = value.decode('utf-8')
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    value = re.sub('[-\s]+', '-', value)
    return value


# Strips the leading non-alphabetic characters from a composite name
def split_on_letter(s):
    match = re.compile("[^\W\d]").search(s)
    return [s[:match.start()], s[match.start():]]


def clean_up_url(url):
    new_url = url
    if 'http' not in url:
        new_url = 'https://' + url
    split_url = new_url.split('/')
    new_url = split_url[0] + '//' + split_url[2] + '/' + split_url[3]

    return new_url


def get_phone_number():
    allergy_button = driver.find_elements_by_class_name('allergenDefaultLink')[0]
    driver.execute_script("arguments[0].scrollIntoView(true);", allergy_button)  # Scroll to the allergy button
    allergy_button.click()
    allergy_popup = driver.find_elements_by_class_name('c-modal-overlay-container')[0]
    phone_number_string = allergy_popup.find_elements_by_tag_name("a")[0]
    phone_number = phone_number_string.get_attribute("innerText")
    allergy_close_button = driver.find_elements_by_class_name('advisoryDialogClose')[0]
    allergy_close_button.click()
    return phone_number


# When prompted to enter postcode, enter the restaurant's postcode (always valid)
def enter_postcode(postcode):
    postcode_prompt = driver.find_element_by_id('postcodePromptContainer')
    if postcode_prompt:
        postcode_field = driver.find_element_by_id('postcodeEntry')
        # Wait until postcode field is visible
        WebDriverWait(driver, 10).until(
            EC.visibility_of(postcode_field)
        )
        postcode_field.send_keys(postcode)  # Type in the postcode
        postcode_form_container = postcode_prompt.find_element_by_id('postcodeFormContainer')
        postcode_confirm_button = postcode_form_container.find_elements_by_tag_name('button.submit.o-btn.o-btn--primary')[0]
        postcode_confirm_button.click()


# Check the popup that appears when the first item is added, needs to be completed to advance
def check_popup(is_collection_disabled, postcode):
    """
    # Popup won't show up a second time if already completed
    popup_hidden = False
    try:
        driver.find_element_by_id('advisoryContainer').find_elements_by_class_name('show')
        popup_hidden = true
    except:
        logging.info("Popup is hidden")
    """
    # Check if restaurant is closed and hence unscrapable
    is_closed = False
    try:
        is_closed = driver.find_element_by_id('closedForTheDayPrompt')
    except:
        logging.info("Restaurant is open")
    if is_closed:
        back_button = driver.find_element_by_id('browsing')
        back_button.click()
        raise RestaurantNotOpenException

    is_currently_closed = False
    try:
        is_currently_closed = driver.find_element_by_id('currentlyNotOpenPrompt')
    except:
        logging.info("Restaurant is available to be scraped")
    # If the restaurant is open, click the view more button
    if not is_currently_closed:
        if not is_collection_disabled:
            logging.info("Restaurant is available for collection")
            collection_prompt = driver.find_elements_by_class_name('viewMoreButton')
            if collection_prompt:
                collection_prompt[0].click()
                enter_postcode()
        else:
            logging.info("Restaurant is only available for delivery (collection disabled)")
            enter_postcode(postcode)

    # If restaurant not open, click the preorder later button
    else:
        preorder_button_container = driver.find_elements_by_class_name('preOrderLaterButton')
        if preorder_button_container:
            preorder_button_container[0] = driver.find_elements_by_class_name('preOrderLaterButton')[0]
            preorder_button = preorder_button_container[0].find_elements_by_class_name('o-btn--secondary')[0]
            preorder_button.click()
            enter_postcode(postcode)


def get_is_composite():
    # Check if no change in composite headers (i.e. item is not composite)
    composite_headers = driver.find_elements_by_class_name('c-menupicker__options')
    composite_visible1 = driver.find_elements_by_tag_name("div.c-menupicker__dialog.hide.show")
    composite_visible2 = driver.find_elements_by_tag_name("div.c-menupicker__dialog.show")
    if not composite_visible1 and not composite_visible2:
        composite_headers = []

    if composite_headers:
        return True
    return False

def get_composites():
    # Get all composite item elements from popup
    composite_items = driver.find_elements_by_class_name('c-menupicker__option')
    composites = []
    composites_object = {}

    # Determine if composite option is Multi
    extra_items = driver.find_elements_by_class_name('c-menupicker__extra-add')
    if extra_items:
        composites_object["type"] = "Multi"
    else:
        composites_object["type"] = "Single"

    for i in range(len(composite_items)):
        price = 0.00
        price_element = composite_items[i].find_elements_by_class_name('c-menupicker__option-price')
        name_element = composite_items[i].find_elements_by_tag_name("div")[0]
        if price_element:  # If item has a price, fetch it
            price = price_element[0].get_attribute("innerText")
            price = price.split("£")
            price = price[1]  # Get only the numerical representation of the price, stripping away currency symbols
        name = name_element.get_attribute("innerText")
        name = split_on_letter(name)
        name = name[1]  # Get a clean representation of the item name
        composite = {"name": name, "price": price}
        composites.append(composite)

    # If composite option is Single
    if composite_items and not extra_items:
        WebDriverWait(driver, 10).until(
            EC.visibility_of(composite_items[0])
        )
        composite_items[0].click()  # Click the first composite item to advance to the next screen

    # If composite option is Multi
    elif extra_items:
        WebDriverWait(driver, 10).until(
            EC.visibility_of(extra_items[0])
        )
        extra_items[0].click()  # Add the first extra
        actions = driver.find_elements_by_tag_name("div#customisableProductSummary")[0]
        add_extras_button = actions.find_elements_by_class_name('submit')
        WebDriverWait(driver, 10).until(
            EC.visibility_of(add_extras_button[0])
        )
        add_extras_button[0].click()  # Click the add extras button

    composites_object["items"] = composites
    return composites_object


# Repeatedly get composite items on current popup screen until no screens are left
def get_composites_list():
    submit_button_disabled = True
    extra_items = True
    all_composites = []
    # If submit button is disabled or there's a Multi option, then not all composites have been scraped yet
    while submit_button_disabled or extra_items:
        composites = get_composites()
        if composites:
            all_composites.append(composites)
        submit_button_disabled = driver.find_elements_by_tag_name('input.submit.disabled')
        extra_items = driver.find_elements_by_class_name('c-menupicker__extra-add')
    close_button = driver.find_elements_by_class_name('c-menupicker__close')[0]
    close_button.click()
    return all_composites


for tries in range(3):
    success = False

    # Logging
    abs_file_path = "not_yet_set"
    restaurant_name = "not_yet_set"
    errors = "None"
    time_elapsed = 0
    hours = 0
    minutes = 0
    seconds = 0

    # URL of menu to be scraped
    url = ""
    if len(sys.argv) < 2:
        logging.fatal("You forgot to enter the URL! Paste the URL after firebird.py")
        exit(1)
    if len(sys.argv) < 3:
        logging.fatal("You forgot to enter your email! Paste your email after the URL")
        exit(1)
    if len(sys.argv) < 4:
        logging.fatal("You forgot to enter firebird's gmail password! Paste the password after your email")
        exit(1)
    url = sys.argv[1]
    if "just-eat" not in url:
        logging.warning("This does not look like a JustEat URL, have you entered it correctly?")
        logging.warning("An invalid URL will cause major errors!")
    url = clean_up_url(url)

    # create a new Firefox session
    options = Options()
    #options.add_argument("--headless")
    ff_profile = webdriver.FirefoxProfile()
    ff_profile.set_preference("browser.privatebrowsing.autostart", True)
    ff_profile.set_preference('browser.cache.disk.enable', False)
    ff_profile.set_preference('browser.cache.memory.enable', False)
    ff_profile.set_preference('browser.cache.offline.enable', False)
    ff_profile.set_preference('network.cookie.cookieBehavior', 2)
    this_os = platform.system()
    logging.info("OS: " + this_os)
    if this_os == "Linux":
        driver = webdriver.Firefox(options=options, executable_path="./geckodriver", firefox_profile=ff_profile)
    elif this_os == "Windows":
        driver = webdriver.Firefox(options=options, executable_path="./geckodriver.exe", firefox_profile=ff_profile)
    else:
        logging.fatal("Incompatible OS!")
        exit(1)

    try:
        start = time.time()  # measure time taken to parse menu
        driver.implicitly_wait(30)  # First wait 30 seconds to ensure page is loaded
        logging.info("Loading URL...")
        driver.get(url)
        logging.info("Loaded")

        # Scrape all useful info from the info screen
        driver.implicitly_wait(0)  # We don't need to wait while scraping this
        logging.info("Scraping restaurant info")
        street = driver.find_element_by_id('street').get_attribute('innerText')
        city = driver.find_element_by_id('city').get_attribute('innerText')
        postcode = driver.find_element_by_id('postcode').get_attribute('innerText')
        phone_number = get_phone_number()
        driver.implicitly_wait(5)  # Give the read more button time to load in
        try:
            read_more_button = driver.find_element_by_id('showMoreText')
            driver.implicitly_wait(0)
            # Scroll to the read more button
            driver.execute_script("arguments[0].scrollIntoView(true);", read_more_button)
            read_more_button.click()
        except:
            logging.debug("Read more button doesn't exist for this page")
        driver.implicitly_wait(0)
        restaurant_description = driver.find_element_by_id('restaurantDescriptionText').get_attribute('innerText')
        restaurant_description.replace('just-eat', 'goeatdirect')
        restaurant_description.replace('JUST EAT', 'GO EAT DIRECT')
        restaurant_description = restaurant_description

        opening_times = ""
        opening_times_element = driver.find_elements_by_class_name('restaurantOpeningHours')[0]
        opening_times_list = opening_times_element.find_elements_by_css_selector('td')
        for i in range(len(opening_times_list)):
            opening_times += '\n' + opening_times_list[i].get_attribute('innerText')

        delivery_areas = ""
        delivery_areas_element = driver.find_elements_by_class_name('restaurantDeliveryAreas')[0]
        delivery_areas_elements_list = delivery_areas_element.find_elements_by_css_selector('li')
        delivery_areas_list = []
        for i in range(len(delivery_areas_elements_list)):
            delivery_areas_list.append(delivery_areas_elements_list[i].get_attribute('innerText'))

        delivery_areas_prefixes = []
        postcode_suffix = "1NH"
        for i in range(len(delivery_areas_list)):
            current_delivery_area = delivery_areas_list[i]
            current_postcode = current_delivery_area.split(" ")[0] + postcode_suffix
            current_delivery_fee = "£0.00"

            driver.get(url + '/menu')
            while True:  # Repeatedly add the first item in case there is a minimum delivery
                first_button = driver.find_elements_by_class_name('addButton')[0]
                driver.execute_script("arguments[0].scrollIntoView(true);", first_button)
                first_button.click()
                check_popup(True, current_postcode)
                # Check if no change in composite headers (i.e. item is not composite)
                driver.execute_script("arguments[0].scrollIntoView(true);", first_button)
                WebDriverWait(driver, 10).until(
                    EC.visibility_of(first_button)
                )
                logging.info("B")
                first_button.click()
                is_composite = get_is_composite()
                # If a composite popup appears
                logging.info("A")
                if is_composite:
                    composites = get_composites_list()
                try:
                    driver.find_elements_by_class_name('minimumValueNotReachedMessage')
                except:
                    break
            try:
                delivery_fee_element = driver.find_elements_by_class_name('basketDeliveryFee')[0]
                current_delivery_fee = delivery_fee_element.find_elements_by_class_name('total')[0].get_attribute('innerText')
            except:
                logging.warning("Delivery fee does not exist")

            delivery_areas += '\n' + current_delivery_area + " " + current_delivery_fee

        # Now navigate to the menu
        driver.implicitly_wait(30)  # First wait 30 seconds to ensure page is loaded
        driver.get(url + '/menu')

        driver.implicitly_wait(5)  # Give leniency for popups and page refresh
        categories = driver.find_elements_by_class_name('category')
        collection = driver.find_elements_by_class_name('deliveryOptionButton')[1]  # The "Collection" button
        driver.execute_script("arguments[0].scrollIntoView(true);", collection)  # Scroll to the collection button
        menu_switcher = driver.find_element_by_id('menuSwitcher')
        is_collection_disabled = menu_switcher.find_elements_by_class_name('disabled')
        if not is_collection_disabled:
            collection.click()
        all_products = driver.find_elements_by_class_name('product')  # Find every product element
        postcode = "".join(str(postcode).split(" "))  # Delete space from postcode
        restaurant_name_element = driver.find_elements_by_class_name('name')[0]
        restaurant_name = restaurant_name_element.get_attribute("innerText")

        # Deletes annoying "product added" popup
        driver.execute_script("""
        var element = document.querySelector("#userNotification");
        if (element)
            element.parentNode.removeChild(element);
        """)

        driver.implicitly_wait(0)  # We can proceed immediately now

        script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
        restaurant_files_dirname = "Restaurant_Files"
        restaurant_files_path = os.path.join(script_dir, restaurant_files_dirname)
        try:
            os.mkdir(restaurant_files_path, 0o0777)
        except FileExistsError:
            logging.debug("Restaurant Files directory already exists")

        # slugify the restaurant name and postcode to abide by filesystem naming requirements
        safe_filename = restaurant_files_dirname + '/' + slugify(restaurant_name + '_' + postcode) + '_' + str(random.randint(1, 99999))

        # create directory for this restaurant's files
        abs_file_path = os.path.join(script_dir, safe_filename)
        try:
            # Create target Directory
            os.mkdir(abs_file_path, 0o0777)
            logging.info("Directory " + safe_filename + " created ")
        except FileExistsError:
            logging.info("Directory " + safe_filename + " already exists")

        logging.info("Writing restaurant info to file")
        with open(os.path.join(abs_file_path, 'info.txt'), mode='w', encoding='utf-8') as outfile:
            outfile.write("Restaurant Name: " + restaurant_name)
            logging.info("Restaurant: " + restaurant_name)
            outfile.write("\nPhone Number: " + phone_number)
            logging.info("Phone Number: " + phone_number)
            outfile.write("\nDescription: " + restaurant_description)
            logging.info("Description: " + restaurant_description)
            outfile.write("\nStreet: " + street)
            logging.info("Street: " + street)
            outfile.write("\nCity: " + city)
            logging.info("City: " + city)
            outfile.write("\nPostcode: " + postcode)
            logging.info("Postcode: " + postcode)
            outfile.write("\n\nOpening Times: " + opening_times)
            logging.info("Opening Times: " + opening_times)
            outfile.write("\n\nDelivery Areas: " + delivery_areas)
            logging.info("Delivery Areas: " + delivery_areas)

        logging.info("Creating categories csv file:")
        with open(os.path.join(abs_file_path, 'categories.csv'), mode='w', encoding='utf-8') as outfile:
            outfile.write("category,description\n")
            categories = driver.find_elements_by_class_name('category')
            for i in range(len(categories)):
                name = categories[i].find_elements_by_class_name('categoryName')[0].get_attribute("innerText")
                logging.info(name)
                desc = categories[i].find_elements_by_class_name('categoryDescription')
                if desc:
                    desc = desc[0].get_attribute("innerText")
                    desc = str(desc).replace('\n', ' -- ')
                    desc = str(desc).replace(',', ' ')
                    desc = str(desc).replace('£', '&#163;')
                    desc = bytes(desc, 'utf-8').decode('utf-8', 'ignore')
                else:
                    desc = ""
                out_line = str(name) + "," + str(desc) + "\n"
                outfile.write(out_line)

        menu = []  # Initialise menu array
        is_composite = False  # For timing purposes, we initialise this outside the loop

        # Click the first entry to deal with all the first run popups
        first_button = driver.find_elements_by_class_name('addButton')[0]
        driver.execute_script("arguments[0].scrollIntoView(true);", first_button)
        first_button.click()
        check_popup(is_collection_disabled, postcode)
        logging.info("Adding products to JSON:")

        # For every product
        for i in range(len(all_products)):
            product = {}
            sub_items = all_products[i].find_elements_by_class_name('addProductForm')  # Find all plus button elements
            product_sub_items = []

            # Get the product name
            name = all_products[i].find_elements_by_class_name('name')[0]
            name = name.get_attribute("innerText")
            product["name"] = name

            category_element = all_products[i].find_element_by_tag_name('form')
            category = category_element.get_attribute('data-category-name')

            # Some products have sub items, so we loop through all of those
            for j in range(len(sub_items)):
                synonyms = all_products[i].find_elements_by_class_name("synonymName")
                # For ease, products that don't have sub items are still stored as such,
                # with the product name as their sub item name
                synonym_name = name
                if synonyms:
                    synonym_name = synonyms[j].get_attribute("innerText")
                    synonym_name = name + " - " + synonym_name
                logging.info(synonym_name)

                # Get sub item price
                price = all_products[i].find_elements_by_class_name('price')[j]
                price = price.get_attribute("innerText")
                price = price.split("£")
                price = price[1]

                description = ""
                try:
                    product_information = all_products[i].find_elements_by_class_name('information')[j]
                    product_description = product_information.find_elements_by_class_name('description')[0]
                    description = product_description.get_attribute("innerText")
                except:
                    # product doesn't have description
                    pass

                product_sub_item = {"name": synonym_name, "category": category, "description": description,
                                    "price": price, "isComposite": False}

                # Click the plus button, to see if a popup appears
                plus_button = sub_items[j]
                # Wait until plus button is visible before clicking it
                driver.execute_script("arguments[0].scrollIntoView(true);", plus_button)
                if not (i == 0 and j == 0):
                    max_iters = 10
                    for iter in range(max_iters):
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", plus_button)
                            plus_button.click()
                            break
                        except WebDriverException:
                            logging.warning("Element is not clickable, retrying")
                        if iter >= max_iters - 1:
                            raise ElementNotClickableException
                        time.sleep(1)
                '''
                for iter in range(10):
                    driver.execute_script("arguments[0].scrollIntoView(true);", plus_button)
                    element = WebDriverWait(driver, 1).until(
                        EC.element_to_be_clickable(plus_button)
                    )
                    if element:
                        break
                '''

                # Check if no change in composite headers (i.e. item is not composite)
                is_composite = get_is_composite()

                # If a composite popup appears
                if is_composite:
                    product_sub_item["isComposite"] = True
                    composites = get_composites_list()
                    product_sub_item["composites"] = composites

                product_sub_items.append(product_sub_item)

            product["subItems"] = product_sub_items
            menu.append(product)

        # outputs menu array to json file
        json_array = {"restaurant": restaurant_name, "menu": menu}
        with open(os.path.join(abs_file_path, 'menu.json'), mode='w', encoding='utf-8') as outfile:
            json.dump(json_array, outfile)

        # measure how long the scraper took to execute
        end = time.time()
        time_elapsed = end - start
        hours = math.floor(time_elapsed / 3600)
        minutes = math.floor((time_elapsed % 3600) / 60)
        seconds = round(time_elapsed % 60)
        logging.info("Menu successfully parsed to JSON")
        logging.info("time elapsed: %.2fs (%dhrs, %dmins, %dsecs)" % (time_elapsed, hours, minutes, seconds))

        send_email()
        success = True

    except RestaurantNotOpenException:
        errors = "Restaurant closed and cannot be scraped, check website for when it is next open"
        try:
            next_open = driver.find_elements_by_class_name('estimateTimeLabel')[1].get_attribute("innerText")
            errors = "Restaurant closed and cannot be scraped, try again at " + next_open
        finally:
            logging.error(errors)
            break
    except ElementNotClickableException:
        errors = "An entry has been missed, for assurance of accuracy please re-run the script"
        logging.error(errors)
    except WebDriverException as wde:
        errors = """\
        WebDriverException:
        Check if the URL you have entered is correct
        And ensure you have FireFox installed on your system and that it is not currently updating or in use.
        Error Message:
        """ + str(wde)
        logging.error(errors)
    except NoSuchWindowException as nswe:
        errors = """\
        NoSuchWindowException:
        Did you close the FireFox window while the scraper was still running?
        Error Message:
        """ + str(nswe)
        logging.error(errors)
    except FileNotFoundError as ffe:
        errors = """\
        FileNotFoundError:
        This is most likely because the scraper is currently running on the same restaurant simultaneous to this!
        to prevent race conditions, please don't run the scraper for the same restaurant at the same time.
        Error Message:
        """ + str(ffe)
        logging.error(errors)
    except Exception as e:
        errors = """\
        Runtime Error:
        """ + str(traceback.print_exc())
        logging.error(errors)
    finally:
        # Delete file directory
        if os.path.exists(abs_file_path):
            shutil.rmtree(abs_file_path)
        # Ensure driver is closed
        driver.close()

    if success:
        logging.info("Program succeeded, exiting")
        exit(0)
    else:
        logging.warning("Something went wrong, trying again...")
logging.error("Retries exceeded, program exiting")
