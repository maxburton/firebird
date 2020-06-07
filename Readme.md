# Setting up locally
## Windows
* Install Python3 <https://realpython.com/installing-python/>
	* Ensure the folder path to python.exe and pip.exe are in your PATH (See Helpful Tips)
* Install the Selenium module via pip by typing this command in your terminal:
	* `pip install selenium`
* Install GeckoDriver for FireFox <https://github.com/mozilla/geckodriver/releases> or download the version in the firebird directory
    * Make sure the URL to geckodriver.exe is in your PATH
* Install Firefox <https://www.mozilla.org/en-GB/firefox/new/>
* Download firebird.py and put it in the same directory as geckodriver.exe
* Run Firebird by typing this command in your terminal:  (Make sure to include the single quotes around the password!)
    * `python firebird.py insert_menu_url_here your_email 'firebird_gmail_password'`
### Helpful Tips
* How to add folder paths to Windows PATH System Variable <https://docs.alfresco.com/4.2/tasks/fot-addpath.html>
# Running on the server
* Log into the tools server with an SSH client (You'll need the server's public key)
* Navigate to the firebird folder:
    * `cd /var/tools/firebird`
* Run Firebird by typing this command: (Make sure to include the single quotes around the password!)
    * `/var/tools/firebird/xvfb-run-safe python3 /var/tools/firebird/firebird.py insert_menu_url_here your_email 'firebird_gmail_password'`
* Navigate to the firebird folder to see your results:
    * `cd /var/tools/firebird`
# Setting up the server
* Install Apache
* Install php
* Install Python3
* Install pip3
* Install Selenium
* Install Firefox
* Install xvfb
* Download geckodriver for linux
* Set up the xvfb-run-safe file
* Set up the firebird.py file
* Sudo touch and change permissions to 777 for the geckodriver.log file