import time
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup as soup
import json
import codecs
from pprint import pprint

base_url = "https://github.com"
issue_base_url = "https://github.com/arturbosch/detekt/issues/"
issuse_page_start = "https://github.com/arturbosch/detekt/issues"
commit_page_start = "https://github.com/arturbosch/detekt/commits/master"
fix_key_words = ["CLOSE", "CLOSES", "CLOSED", "FIX", "FIXES", "FIXED", "RESOLVE", "RESOLVES", "RESOLVED"]
feature_tags = ["feature", "improvement"]
bug_tags = ["bug"]


def main(commit_page_link):
    page_soup = get_page_soup_by_url(commit_page_link)

    commit_issue_dict = {}
    file_bug_issue = {}
    file_feature_issue = {}

    # Runtime check
    count = 0
    start_time = time.time()

    cells = page_soup.find_all("li", {"class": "commits-list-item"})
    while cells:
        count+=1
        print("Commit page index " + str(count) + ": " + str(time.time() - start_time) + "s")
        for html_li in cells:
            commit_cell = html_li.div
            commit_link = commit_cell.p.a["href"]
            files = get_files(commit_link)
            commit = parse_commit_title(commit_cell.p.a.text)
            # Situation when commit has at least one related issue
            issues = commit_cell.find_all("a", {"class": "issue-link"})
            for issue_a in issues:
                issue_link = issue_a["href"]
                if issue_a["data-hovercard-type"] == "issue":
                    issue_ids = get_issue_solved_by_issue(issue_link)
                else:
                    issue_ids = get_issues_solved_by_pull_request(issue_link)
                # Add to {issue: [commit]}
                for issue_id in issue_ids["all"]:
                    if issue_id not in commit_issue_dict:
                        commit_issue_dict[issue_id] = [commit]
                    elif commit not in commit_issue_dict[issue_id]:
                        commit_issue_dict[issue_id].append(commit)
                # Add to {file: [issue]}
                for issue_id in issue_ids["bug"]:
                    # Add file: issue
                    for file in files:
                        if file not in file_bug_issue:
                            file_bug_issue[file] = [issue_id]
                        elif issue_id not in file_bug_issue[file]:
                            file_bug_issue[file].append(issue_id)
                # Add to {file: [issue]}
                for issue_id in issue_ids["feature"]:
                    for file in files:
                        if file not in file_feature_issue:
                            file_feature_issue[file] = [issue_id]
                        elif issue_id not in file_feature_issue[file]:
                            file_feature_issue[file].append(issue_id)

        next_page_link = get_next_page_link(page_soup)
        print(next_page_link)
        page_soup = get_page_soup_by_url(next_page_link)
        if page_soup is None:
            cells = page_soup
        else:
            cells = page_soup.find_all("li", {"class": "commits-list-item"})
        # To be deleted
        # cells = None

    # Write dicts to the disk
    with open('commit_issue_dict.js', 'w') as file:
        file.write(json.dumps(commit_issue_dict))
    with open('file_bug_issue.js', 'w') as file:
        file.write(json.dumps(file_bug_issue))
    with open('file_feature_issue.js', 'w') as file:
        file.write(json.dumps(file_feature_issue))

    return {"commit_issue_dict":commit_issue_dict,
            "file_bug_issue": file_bug_issue,
            "file_feature_issue": file_feature_issue}


def parse_commit_title(s):
    """
    trim the " (" off the commit message

    :param s: unparsed commit message
    :return: commit message
    """
    return s.strip(" (")


def parse_issue_id_from_aria_label(s):
    """
    trim the "#" off the issue id

    :param s:
    :return: issue id
    """
    return s.split("#")[1].strip(".")


def get_files(url_link):
    """
    Get a list of files based on the link of a commit file link

    :param url_link:
    :return: file list
    """
    files = []
    page_soup = get_page_soup_by_url(base_url + url_link)
    file_divs = page_soup.find_all("div", {"class": "file-info"})
    for file_div in file_divs:
        files.append(file_div.a["title"])
    return files


def get_issue_solved_by_issue(url_link):
    """
    Get the issue identity by the issue link

    :param url_link: issue link
    :return: issue identity dict
    """
    issue_ids = {"all":[], "bug":[], "feature":[]}
    issue_id = url_link.split("/")[-1]
    issue_labels = get_issue_label(issue_base_url + issue_id)
    if issue_id not in issue_ids["all"]:
        issue_ids["all"].append(issue_id)
    for issue_label in issue_labels:
        if issue_label in feature_tags:
            if issue_ids not in issue_ids["feature"]:
                issue_ids["feature"].append(issue_id)
        if issue_label in bug_tags:
            if issue_ids not in issue_ids["bug"]:
                issue_ids["bug"].append(issue_id)
    return issue_ids

def get_issues_solved_by_pull_request(url_link):
    """
    Get a list of issue ids based on the link of a pull request

    :param url_link: issue (pull request thread) link
    :return: issue ids
    """
    issue_ids = {"all":[], "bug":[], "feature":[]}
    page_soup = get_page_soup_by_url(url_link)
    issue_spans = page_soup.find_all("span", {"class": "issue-keyword"})
    for issue_span in issue_spans:
        if issue_span.text.upper() in fix_key_words:
            issue_id = parse_issue_id_from_aria_label(issue_span["aria-label"])
            issue_labels = get_issue_label(issue_base_url + issue_id)
            if issue_id not in issue_ids["all"]:
                issue_ids["all"].append(issue_id)
            for issue_label in issue_labels:
                if issue_label in feature_tags:
                    if issue_ids not in issue_ids["feature"]:
                        issue_ids["feature"].append(issue_id)
                if issue_label in bug_tags:
                    if issue_ids not in issue_ids["bug"]:
                        issue_ids["bug"].append(issue_id)
    return issue_ids

def get_issue_label(issue_link):
    """
    Get issue labels of an issue given the issue link

    :param issue_link:
    :return: issue labels
    """
    page_soup = get_page_soup_by_url(issue_link)
    label_as = page_soup.find_all("a", {"class": "IssueLabel"})
    issue_labels = []
    for label_a in label_as:
        issue_labels.append(label_a["title"])
    return issue_labels

def get_next_page_link(page_soup):
    """
    Get the next page link of commits page given the page parsed in beautiful soup
    Return None if the link is not found

    :param page_soup:
    :return: page link
    """
    next_page_cells = page_soup.find_all("a", string="Older")
    if len(next_page_cells) > 0:
        return next_page_cells[0]['href']
    else:
        return None


def get_page_soup_by_url(url_link):
    """
    keep trying to get the page soup from the url until success
    (may get into infinity loop

    :param url_link:
    :return: page soup
    """
    page_soup = None
    if url_link is None:
        return page_soup
    try:
        page_html = get_page_html_by_url_onetime_call(url_link)
        page_soup = soup(page_html, "html.parser")
    except:
        time_sleep = 5
        while page_soup is None:
            try:
                page_html = get_page_html_by_url_onetime_call(url_link)
                page_soup = soup(page_html, "html.parser")
                time_sleep += 3
            except:
                pass
    return page_soup


def get_page_html_by_url_onetime_call(url_link):
    """
    Get the web page content of the link
    This call may throw exception

    :param url_link:
    :return: web page content of the link
    """
    req = Request(url_link)
    # req.add_header("User-Agent", "'Mozilla/5.0")
    # req.add_header("'Content-Type", "application/json")
    # req.add_header('method', 'GET')
    # req.add_header('Accept', 'application/json')
    uClient = urlopen(req)
    page_html = uClient.read()
    uClient.close()
    return page_html

# Obsolete
def grab_all_issue_ids(issue_page_link):
    """
    Get issue ids from the issue page given the issue page link

    :param issue_page_link:
    :return: issue links
    """
    req = Request(issue_page_link)
    uClient = urlopen(req)
    page_html = uClient.read()
    uClient.close()
    page_soup = soup(page_html, "html.parser")

    # Grab all ids from the curent page
    issue_containers = page_soup.find_all("a", {"data-hovercard-type": "issue"})
    issue_links = []
    for url_container in issue_containers:
        issue_links.append(url_container["href"])

    next_page = page_soup.find_all("a", {"class": "next_page"})
    if len(next_page) > 0:
        issue_links += grab_all_issue_ids(base_url + next_page[0]["href"])
    return issue_links

def parse_dic():



   d ={}
   # with open(‘commit_issue.json’,‘r’) as f:
   #     # json = json.loads(open(‘commit_issue.json’).read())
   #     data = json.load(f)
   data = json.load(codecs.open("commit_issue_dict.js", "r", "utf-8-sig"))
   # data = json.load(codecs.open(‘file_feature.json’, ‘r’, ‘utf-8-sig’))
   # data = json.load(codecs.open(‘commit_issue.json’, ‘r’, ‘utf-8-sig’))


   # pprint(data)
   # print(len(data.keys()))

   print(len(data.values()))


if __name__ == "__main__":
    # main(commit_page_start)
    parse_dic()