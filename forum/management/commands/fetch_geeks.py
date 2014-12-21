from forum.models import OsqaCategory, User
from django.core.management.base import NoArgsCommand
from django.core.management.base import BaseCommand
from urllib2 import urlopen, HTTPError
import xml.etree.ElementTree as ET
import logging
logging.basicConfig(filename='error.log',level=logging.ERROR)
from bs4 import BeautifulSoup
import re
import time
from forum.actions import AskAction

categories = {
    #"Home": "http://www.geeksforgeeks.org",
    "Algorithms": "http://www.geeksforgeeks.org/fundamentals-of-algorithms/",
    "DS": "http://www.geeksforgeeks.org/data-structures/",
    #"GATE": "http://www.geeksforgeeks.org/gate-corner/",

    #"Q&A": "http://www.geeksforgeeks.org/forums/",
    "C": "http://www.geeksforgeeks.org/c/",
    "C++": "http://www.geeksforgeeks.org/c-plus-plus/",
    "Java": "http://www.geeksforgeeks.org/java/",
    #"Books": "http://www.geeksforgeeks.org/books/",
    #"Contribute": "http://www.geeksforgeeks.org/contribute/",
    #"Ask a Q": "http://www.geeksforgeeks.org/contribute/ask-a-question/",
    #"About": "http://www.geeksforgeeks.org/about/",
}

forumcategories= {
    #"Interview Corner": "http://www.geeksforgeeks.org/about/interview-corner/",
    "Array": "http://www.geeksforgeeks.org/category/c-arrays/",
    "Bit Magic": "http://www.geeksforgeeks.org/category/bit-magic/",
    "C/C++": "http://www.geeksforgeeks.org/category/c-puzzles/",
    #"Articles": "http://www.geeksforgeeks.org/category/articles/",
    #"GFacts": "http://www.geeksforgeeks.org/category/gfact/",
    "Linked List": "http://www.geeksforgeeks.org/category/linked-list/",
    #"MCQ": "http://www.geeksforgeeks.org/category/multiple-choice-question/",
    "Misc": "http://www.geeksforgeeks.org/category/c-programs/",
    "Output": "http://www.geeksforgeeks.org/category/program-output/",
    "String": "http://www.geeksforgeeks.org/category/c-strings/",
    "Tree": "http://www.geeksforgeeks.org/category/tree/",
    "Graph": "http://www.geeksforgeeks.org/category/graph/"
}

def get_or_create_categories(category):
    categories = OsqaCategory.objects.filter(name=category)
    if len(categories) > 0:
        return categories[0].pk
    else:
        user = User.objects.get(username='Geeks')
        category_obj = OsqaCategory()
        category_obj.name = category
        category_obj.order_no = len(OsqaCategory.objects.all())
        category_obj.created_by = user
        #import pdb; pdb.set_trace()
        category_obj.save()
        return category_obj.pk

def get_tags(tagstring):
    prop = ["of", "in", "to", "for", "with", "on", "at", "from", "by",
            "about", "as", "into", "like", "through", "after",
            "over", "between", "out", "against", "during", "without",
            "before", "under", "around", "among", "occurs", "a", "and", "the", "is", "that",
            "be", "vs", "function", "functions"]

    prop.extend([str(s) for s in range(0,100)])
    tags = [tag for tag in tagstring.split(" ") if tag not in prop]
    final_tags = [tag for tag in tags if len(tag) >5]
    return ",".join(final_tags)

def get_forumpage_links(key, url):
    #url = "http://www.geeksforgeeks.org/fundamentals-of-algorithms/"
    data_urls = []
#try:

    for page in range(1,1000):
        if page != 1:
            loop_url = url+"page/"+ str(page) +"/"
        else:
            loop_url = url
        try:
            html_data = urlopen(loop_url).read()
        except:
            print loop_url
            print "Maximum Pages in This category are ", page-1
            break
        web_page = BeautifulSoup(html_data)
        data_div = web_page.find("div", class_="post")
        if data_div:
            data_sections = data_div.find_all("h2", class_="post-title")

            for d in data_sections:
            #        for link in d.find_all("a"):
                    for link in d.find_all(href=re.compile("www.geeksforgeeks.org")):
                        data = {
                                 'name':strip(link.string),
                                 'link':link['href'],
                                  'tag':get_tags(strip(link.string)),
                                  'category':key
                                }
                        data_urls.append(data)
        #except Exception,e:
        #    print str(e)

        else:
            print "page don't have urls", url

    data_urls.reverse()
    return data_urls


def get_page_links(key, url):
    #url = "http://www.geeksforgeeks.org/fundamentals-of-algorithms/"
    data_urls = []
#try:
    html_data = urlopen(url).read()
    web_page = BeautifulSoup(html_data)
    data_div = web_page.find("div", class_="page-content")
    if data_div:
        data_sections = data_div.find_all("p")[:-4]


        for d in data_sections:
        #        for link in d.find_all("a"):
                for link in d.find_all(href=re.compile("www.geeksforgeeks.org")):
                    data = {
                             'name':strip(link.string),
                             'link':link['href'],
                              'tag':get_tags(strip(link.string)),
                              'category':key
                            }
                    data_urls.append(data)
    #except Exception,e:
    #    print str(e)

    else:
        print "page don't have urls", url

    data_urls.reverse()
    return data_urls

def strip(data):
    if data:
        return data.strip()
    else:
        ''

def get_doc_info(url):
    try:
        html_data = urlopen(url['link']).read()
        web_page = BeautifulSoup(html_data)
        data = ''
        data_div = web_page.find(class_="post-content")
        if data_div:
            for content in data_div.contents:
                if content and "adsbygoogle.js" in unicode(content):
                    break
                else:
                    data += unicode(content)

        data_info ={'name':url['name'],
                             'data':data,
                              'tag':url['tag'],
                              'category':url['category'],
                              'link':url['link']
                              }
    except HTTPError, e:
        print "link not loaded", url
        return {}
    else:
        return data_info

count = 0
def save_data_into_table(doc_info):
    if len(doc_info.keys()) > 0:
        user = User.objects.get(username='Geeks')
        category_id = get_or_create_categories(doc_info['category'])
        ip = '127.0.0.1'
        form_data = {
                        'category': str(category_id),
                        'wiki': False,
                        'upload_files': None,
                        'form_attachments': u'',
                        'tags':  doc_info['tag'],
                        'text':  doc_info['data'],
                        'title':  doc_info['name'],
                        'attachement_token': str(time.time() * 1000)
                    }
        #import pdb;pdb.set_trace()
        AskAction(user=user, ip=ip).save(data=form_data)
        global count
        count += 1
        print "Question Posted:",count


class Command(BaseCommand):
    """ How to Use:
        $ python manage.py fetch_geeks
    """
    def handle(self, *args, **options):
        for key in forumcategories.keys():
            #data_urls = get_page_links(key, categories[key])
            data_urls = get_forumpage_links(key, forumcategories[key])
            if len(data_urls):
                for url in data_urls:
                    doc_info = get_doc_info(url)
                    ## save doc Info into database
                    save_data_into_table(doc_info)

        for key in categories.keys():
            #data_urls = get_page_links(key, categories[key])
            data_urls = get_page_links(key, categories[key])
            if len(data_urls):
                for url in data_urls:
                    doc_info = get_doc_info(url)
                    ## save doc Info into database
                    save_data_into_table(doc_info)
