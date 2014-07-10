# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>
import os, sys, inspect
sys.path.insert(0, os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],".."))))
from util import path_tools, path_to_docid
import pandas as pd, numpy as np, csv
import re, time,sys, itertools
from collections import Counter
reload(sys)
sys.setdefaultencoding('utf-8')


def docname_normalizer09(doc_name):
    """
    Input: takes in a document name from 2009 OMB File
    Ouput: returns a normalized list of relevant attributes
    
    """ 
    house = 'house'
    senate = 'senate'
    bill = 'bill'
    report = 'report' 
    congress = 111
    if re.findall('\d+',doc_name):
        poc = doc_name[0:doc_name.index(re.findall('\d+',doc_name)[0])]
        
        if 'Div. ' in poc or 'Div.' in poc:
            if 'Defense' in doc_name or 'Homeland Security' in doc_name or 'Military Construction' in doc_name:
                path = [110, bill ,house,'hr2638']
            else:
                congress = 111
                path = [congress, bill, house, ('hr1105', doc_name)]
            
            return path
        
        elif 'Report' in poc: 
            congress = re.findall('\d+', doc_name)[0]
            rep = re.findall('\d+', doc_name)[1]
            if 'H. Report' in poc: 
                path = [congress,report,house, rep]
            else: 
                path = [congress,report, senate, rep]
            
            return path    
                    
        elif 'S. ' in poc and 'Report' not in poc: 
            bi = 's'+str(re.findall('\d+', doc_name)[0])
            path = [congress,bill, senate, bi]
            return path 
        
def docname_normalizer10(doc_name):
    """
    Input: takes in a document name from 2010 OMB File
    Ouput: returns a normalized list of relevant attributes
    """ 
    house = 'house'
    senate = 'senate'
    bill = 'bill'
    report = 'report' 
    congress = 111
    if re.findall('\d+',doc_name):
        poc = doc_name[0:doc_name.index(re.findall('\d+',doc_name)[0])]
        if 'Div. ' in poc or 'Div.' in poc:
            path = [congress,bill,house,'hr3288']
            return path 
        
        elif 'H.R.' in poc:
            bill = re.findall('\d+', doc_name)[0]
            bill_name = 'hr'+str(bill)
            path = [congress, bill, house, bill_name]
            return path
        
        elif 'S. ' in poc: 
            bill = re.findall('\d+', doc_name)[0]
            bill_name = 's'+str(bill)
            path = [congress,bill, senate, bill_name]
            return path 

        elif 'Report' in poc: 
            rep = re.findall('\d+', doc_name)[1]
            if 'Senate' in poc: 
                path = [congress,report, senate, rep]
            else: 
                path = [congress,report, house, rep]
            
            return path
            
        elif 'Joint Explanatory Statement ' in poc:
            rep = re.findall('\d+', doc_name)[1]
            
            if 'xxx' not in doc_name:
                rep = re.findall('\d+', doc_name)[1]
                path = [congress, report, house, rep]
                return path 
                
        
def csv_extractor(earmarks,year=2010):
    """
    Input: 2010 or 2009 earmark csvs, year
    Output: a list of lists where each element contains 
            relevant info associated with the earmark_id       
    """
    
    document_columns = ['hc_f_cttn_reference_name','hf_f_cttn_reference_name','sc_f_cttn_reference_name','sf_f_cttn_reference_name', 'c_f_cttn_reference_name']
    
    meta_data = {'hc_f_cttn_reference_name':['hc_f_cttn_location','hc_f_cttn_excerpt'],
             'hf_f_cttn_reference_name':['hf_f_cttn_location','hf_f_cttn_excerpt'],
             'sc_f_cttn_reference_name': ['sc_f_cttn_location','sc_f_cttn_excerpt'],
             'sf_f_cttn_reference_name': ['sf_f_cttn_location','sf_f_cttn_excerpt'],
             'c_f_cttn_reference_name' : ['c_f_cttn_location','c_f_cttn_excerpt']
                 }
    
    columns = []
    earmarks_lis = []
    unis = []
    if year == 2010:
        normalizer = docname_normalizer10
    else:
        normalizer = docname_normalizer09
    
    csvFile = csv.reader(earmarks)
    for rows in csvFile:
        if not columns: 
            columns = rows
            doc_index = [columns.index(i) for i in document_columns]
            metaData_index = {}
            for ind, item in enumerate(doc_index):
                metaData_index[item] = [columns.index(j) for j in meta_data[document_columns[ind]]]

            earmarkid_index = columns.index('earmark_id')
        else:
            for name in doc_index:
                doc_name = rows[name]
                earmark_id = rows[earmarkid_index]
                unis_info = (earmark_id, doc_name)
                if doc_name and not unis_info in unis:
                    page = rows[metaData_index[name][0]]
                    excerpt = rows[metaData_index[name][1]]
                    docS_name = normalizer(doc_name)
                    if docS_name:
                        db_info = (earmark_id, docS_name, page, excerpt)
                        earmarks_lis.append(db_info)
                        unis.append(unis_info)
        
    return earmarks_lis
        

# <codecell>

#with open("2009_app.csv", "rU") as f_obj:
 #   elis1 = csv_extractor(f_obj,2009)


