import datetime
import re
import sys
import time
import urllib
import urllib2
import string
import argparse
import os
import codecs

from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader

documents = []
fara_url = 'https://efile.fara.gov/pls/apex/wwv_flow.accept'

def scrape():
    if __name__ == '__main__':
        parser = argparse.ArgumentParser(description="Scrape data from FARA portal")
        parser.add_argument('date_range', type=str, nargs='*',
                        help='A positional argument for dates. This is a range of dates. \
                        Date ranges should be given as start date then end \
                        date YYYY-MM-DD:YYYY-MM-DD. By default it will parse the last 25 days')
        parser.add_argument('-od', '--outdir', dest='outdir', action='store',
                        help='An output directory for the parsed content')

    args = parser.parse_args()
    if args.outdir:
        outdir = args.outdir
    else:
        this_filename = os.path.abspath(__file__)
        this_parent_dir = os.path.dirname(this_filename) 
        outdir = os.path.join(this_parent_dir, "output")
        if not os.path.exists(outdir):
            os.mkdir(outdir)

    if args.date_range:
        dates = args.date_range[0].split(':')
        start_date = datetime.datetime.strptime(dates[0], "%Y-%m-%d")
        end_date = datetime.datetime.strptime(dates[1], "%Y-%m-%d")
    else:
        start_date = datetime.date.today() - datetime.timedelta(days=25)
        end_date = datetime.date.today()

    url = 'https://efile.fara.gov/pls/apex/f?p=125:10:::NO::P10_DOCTYPE:ALL'
    search_html = urllib2.urlopen(url).read()
    search_page = BeautifulSoup(search_html)
    form = search_page.find("form", {"id":"wwvFlowForm"})

    data = []
    for input in form.findAll('input'):
        if input.has_attr('name'):
            if input['name'] not in ('p_t01', 'p_t02', 'p_t06', 'p_t07', 'p_request'):
                data.append((input['name'], input['value']))
    
    data += [('p_t01', 'ALL'),
             ('p_t02', 'ALL'),
             ('p_t06', start_date.strftime('%m/%d/%Y')),
             ('p_t07', end_date.strftime('%m/%d/%Y')),
             ('p_request', 'SEARCH'),
    ]
   
    url = 'https://efile.fara.gov/pls/apex/wwv_flow.accept'
    req = urllib2.Request(url, data=urllib.urlencode(data))
    
    page = urllib2.urlopen(req).read()
    page = BeautifulSoup(page)
    parse_and_save(page, outdir)
    next_url_realitive = page.find("a", {"class":"t14pagination"})

    while next_url_realitive != None:
        url_end = next_url_realitive['href']
        next_url = 'https://efile.fara.gov/pls/apex/' + url_end
        req = urllib2.Request(next_url)
        page = urllib2.urlopen(req).read()
        page = BeautifulSoup(page)
        parse_and_save(page, outdir)
        next_url_realitive = page.find("a", {"class":"t14pagination"})
        

def save_text(url, url_info, outdir):
    print "making file for %s" %(url)
    file_name = str(url[25:-4]) + ".txt"

    # set up paths
    metadata_path = os.path.join(outdir, "metadata")
    if not os.path.exists(metadata_path):
        os.mkdir(metadata_path)
    metadata_file_name = os.path.join(outdir, "metadata", file_name)

    document_path = os.path.join(outdir, "documents")
    if not os.path.exists(document_path):
        os.mkdir(document_path)
    doc_file_name = os.path.join(document_path, file_name)

    # create metadata 
    if not os.path.isfile(metadata_file_name):
        doc_file =  open(metadata_file_name, 'w')
        doc_file.write(str(url_info))
        doc_file.close()
   
    # download pdf and make text file
    if not os.path.isfile(doc_file_name):
        doc_file =  open(doc_file_name, 'w')
        print "download %s" % (doc_file_name)
        pdf = urllib2.urlopen(url)
        localFile = open("temp.pdf", 'w')
        localFile = localFile.write(pdf.read())
        tempDoc = file("temp.pdf", "rb")
        pdf_file = PdfFileReader(tempDoc)
        pages = pdf_file.getNumPages()
        text_file = codecs.open(doc_file_name, encoding='utf-8', mode='wb')

        #looping through the pages and putting the contents in to a text document
        count = 0
        while count < pages:
            pg = pdf_file.getPage(count)
            pgtxt = pg.extractText()
            count = count + 1
            text_file.write(pgtxt) 

        text_file.close()
        os.remove("temp.pdf")
    else:
        print "found %s " % (doc_file_name)


def parse_and_save(page, outdir):
    filings = page.find("table", {"class" : "t14Standard"})
    new_fara_docs = []

    for l in filings.find_all("tr"):
        url = l.find('a')['href']
    
        if url[:4] == "http":
            stamp_date = l.find('td',{"headers" : "STAMPED/RECEIVEDDATE"})
            stamp_date = stamp_date.text
            try:
                stamp_date_obj = datetime.datetime.strptime(stamp_date, "%m/%d/%Y")
            except:
                # just in case there is a problem with the form
                print "parsing date stamp date from url- %s" %(url)
                stamp_date = re.findall(r'\d{8}', url)
                stamp_date = stamp_date[0]
                stamp_date_obj = datetime.datetime.strptime(stamp_date, "%Y%m%d")
            date_string = stamp_date_obj.strftime('%Y-%m-%d')    

            reg_name = l.find('td',{"headers" : "REGISTRANTNAME"})
            reg_name = reg_name.text    
            reg_id = re.sub('-','', url[25:29])
            reg_id = re.sub('S','', reg_id)
            reg_id = re.sub('L','', reg_id)
            re.findall(r'href="(.*?)"', url)
            info = re.findall( r'-(.*?)-', url)

            if info[0] == 'Amendment':
                doc_type = 'Amendment'

            elif info[0] == 'Short':
                doc_type = 'Short Form'

            elif info[0] == 'Exhibit':
                if "AB" in url:
                    doc_type = 'Exhibit AB'  
                if "C" in url:
                    doc_type = 'Exhibit C'    
                if "D" in url:
                    doc_type = 'Exhibit D'

            elif info[0] == 'Conflict':
                doc_type = 'Conflict Provision'

            elif info[0] == 'Registration':
                doc_type = 'Registration'

            elif info[0] == 'Supplemental':
                doc_type = 'Supplemental' 

            else:
                message = "Can't identify form-- %s " % (url)
                doc_type = 'unknown'
                print message

            url_info= {'url':url,'reg_name':reg_name,  'reg_id':reg_id, 'doc_type':doc_type, 'stamp_date':date_string}
            documents.append(url_info)
            save_text(url, url_info, outdir)
        
scrape()





      



