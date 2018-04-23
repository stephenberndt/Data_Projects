## Marketing Intelligence Content Management

<!-- TOC depthFrom:4 depthTo:5 withLinks:1 updateOnSave:1 orderedList:0 -->

- [Getting Started](#getting-started)
- [Clone the repo](#clone-the-repo)
- [File Structure](#file-structure)
	- [docs](#docs)
	- [template](#template)
	- [output](#output)
	- [upload_script](#uploadscript)
- [Running the script](#running-the-script)

<!-- /TOC -->

#### Getting Started
1. Read all of the steps first
1. Install Anaconda with pyton 2.7
1. Load the Conda env file tableaudev.yml
1. Ensure that module `psycopg2`, python's way of communicating with Postgres, is correctly configured - the setup process is different on Windows and OS X. The details for all platforms are listed [here](http://initd.org/psycopg/docs/install.html).
1. Some of the tableau-related python modules need to be manually installed. Ensure all those listed have been set up. These include:
	- tableausdk - [Tableau Help](https://onlinehelp.tableau.com/current/api/sdk/en-us/help.htm#SDK/tableau_sdk_installing.htm%3FTocPath%3D_____3)
	- tableaudocumentapi - [GitHub](https://github.com/tableau/document-api-python)
	- tableau_tools - [Tableau and Behold](https://tableauandbehold.com/tableau-rest-api-resources/)
1. (optional) If you wish to have the option to create graphviz files, an additional Ruby gem called `twb` will also need to be installed. [GitHub](https://github.com/ChrisGerrard/TWB)
1. Set tabcmd up on your computer. Instructions to do this on a Linux system are [here](https://tableauandbehold.com/2016/06/06/tabcmd-on-linux/)

#### Clone the repo
```
$ git clone https://github.com/Adapp/tune_BI
```

This creates a local copy of all of tune_BI git repository and runs `git init`. You will also want to add a remote for your local directory so that it is linked to the github repo. Follow the instructions [here](https://help.github.com/articles/adding-a-remote/) for setting up a remote. Once the remote is established, updates can be pulled down from the remote with the following:
```
$ git fetch remotename
# Fetches updates made to a remote repository
```
Once the repo is cloned, make a local copy of the code on your machine that is separate from the git repository. The reason for this is that running the script generates a number of files that are not a part of the repository.

Even more details on working with remotes [here](https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes).

#### File Structure
Below is the layout, by folder, of what makes up the module.

##### docs
A list of files under the folder `docs`

> ###### advertiser.config
> Make sure that you enter in credentials for Tableau Server, Tune DB, and Postgres. Also, set the list of files that you would like to upload. Those files that don't have '#' in front of their name will be included.

> ###### advertiser_batch.csv
> This is the file that will determine the site to which content is uploaded. All that needs to be done here is the actual name of the site and advertiser id be listed out separated by a comma (no space). Each advertiser should have it's own line

> Example:
```
BetaTest,7336
BetaTest2,3066
```
> ###### advertiser_list.csv
> This is a list of the current roster of advertisers for Marketing Intelligence

> ###### password_file.csv
> Currently a placeholder for more secure password management

##### template
> ###### 1693
This is the current template directory for the script. It's where the script will look for content to repoint. Functionality will be later added to simply allow for the folder of any advertiser to be placed there and content be generated off of it.

##### output
The output folder is actually generated the first time the script is run. The necessary files and folders will be created inside. If it already exists, files that are being updated will be overwritten with new versions of themselves.

###### Data Files
> ###### upload_times.csv
> After each file is repointed and uploaded, the sucess or failure of that action is logged here. There is a unique ID associated with the session that let's you track how particular batches faired during upload and where issues may have arisen. Rows generated for this file are uploaded when the argument `-r` or `--record` is added, and the data will be sent to the stack of the user's choosing. This file is cleared out after each new run of the script. The recorded history can be seen at `tunebi_metastats.upload_stats` on either Tetris C or D.

> ###### failed_files.csv
> If an action (repoint or upload) fails, then it will be logged here with the same fields that are contained in `upload_times.csv`. It's designed to be a quick look at what didn't go as planned for a particular session. Files appearing on this list are re-run at the end of the script to try one last time to get them uploaded.


> ###### Columns in the data files
> | Name | Type | Description |
> |------|------|-------------|
> | `date` | DATETIME | Date and time of the file was uploaded |
> | `adv_id` | VARCHAR(8) | Advertiser Tune ID |
> | `adv_name` | VARCHAR(20) | Advertiser name |
> | `full_file_name` | VARCHAR(75) | File name |
> | `version` |VARCHAR(8) | Version number vX.XX.X |
> | `short_file_name` |VARCHAR(75) | Name that is shown on the server |
> | `action` | VARCHAR(8) | repoint or upload |
> | `sec_to_complete` |DOUBLE(6) | Count in seconds to complete the action |
> | `status` | VARCHAR(8) | success or failure |

###### Content Folders
Two main folders will be generated when the script is run.

> ###### uploaded_content
> This will have a list of folders by advertiser ID that contains repointed and packaged versions of each workbook that was uploaded to the server by the script.
> ###### unpackaged_content
> This folder has a list of folders by advertiser ID similar to Uploaded_content, except that all of the content will be unpackaed for storage on Github.
>
> ###### graphviz_files
> These are files that get generated by the argument `-g` or `--graphviz` showing the workbook > dashboard > datasource relationship for each content workbook. The viewer for these files can be downloaded [here](http://www.graphviz.org/Download_macos.php).

##### upload_script
This is the heart of the application where the modules are separated by purpose
###### upload_content.py
Has a single function that kicks off the upload process. It's essentially 2 `for` loops that iterate first over the advertisers to upload and then the files for each advertier. The second loop calls the `Repoint()` class to process and upload the files.

###### config.py
While it's not directly involved in the actual process. This module is what dictates what and where files are being uploaded. It parses the `advertiser.config` file to get all of the session-specific settings. All of the variables can be brought into other modules by calling the class `Config()` and specifying what you want preceeded by `get_`. A quick example of displaying your tableau server username, password, and a list of the files that you've selected for upload:
```
settings = Config('advertiser.config', 'advertiser_batch.csv')
print settings.get_user
print settings.get_pw
print settings.get_templates
```
###### utils.py
This module was used as a place to put helper functions that are repeated in other areas. The module itself is commented in detail about what each function does.
###### publish.py
A module whose purpose is as the name implies, to publish content. The function `publish_content_to_server_restapi()` is set up to handle all types of tableau files. It uses Tableau's REST api to generate a HTTP request that uploads content to the server. The other function in this module is `publish_content_to_server_tabcmd`. It leverages Tableau's command line utility (tabcmd). It's important to note that setting up tabcmd on Unix can be tricky. Follow the instructions [here](https://tableauandbehold.com/2016/06/06/tabcmd-on-linux/).
###### repoint.py
This module is the backbone of the process that does a majority of the leg work involved in repointing and publishing the files. It's called with the `Repoint()` class and depending on how the user sets the `to_publish` parameter of the class will determine if it also calls `publish_content_to_tunebi()` from `publish.py`. This is initiated from the command line by adding `-rp PORT` or `--repoint-port PORT` after `python run.py`
###### gen_graphviz.rb
A ruby module that is called with the option `-g` or `--graphviz`. Upon selecting, `.dot` files are created for each for the content-centered workbooks with charts that follow a Dashboard -> Worksheet -> Data Source flow. Content-centered workbooks are considered `['LTV', 'Engagement', 'Re-Engagement', 'UserAcquisition', 'TrafficQuality', 'Retention', 'ExecutiveSummary']`
###### tabcmd.py
This module is a wrapper for tabcmd. Currently, this is the most efficient way to get content workbooks uploaded to the server.

#### Running the script
Simply type `python run.py` followed by your argument values, see [details](#uploadcontentpy)  on arg values at runtime, into your console after navigating to your project folder. There are 4 major options that you can configure to customize how the upload functions.

| Arg Value | Description |
|-----------|-------------|
| `-rp PORT`, `--repoint-port PORT` | Dictates the tetris stack that the repointed workbooks will look to and destination for upload stats. This is required for the upload to be successful.|
| `-u`, `--upload`| Indicates if user want content uploaded to the Tableau server |
| `-rs`, `--record-stats`| Indicates if the user wants logs saved to tunebi_metastats.upload_stats |
| `-g`, `--graphviz`| Generates graphviz files showing the workbook > dashboard > datasource relationship |
Example of changing upload options:
```
$ python run.py -rp 11107 -u -rs -g
```
Here, the user is saying they want to point the workbooks to the dev cluster, then upload and record the statistics on such, and also to generate graphviz files for each of the content workbooks. It's important to note that any of the 4 options can be run. If you upload without repointing the script will look for whatever matches the list in `advertiser.config`.
