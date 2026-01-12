#!/usr/bin/env python3
"""
Step 1: Screen PubMed for affiliation variations of DCTV and DSF departments.
This script searches for various ways the departments might be written.
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time
import re
from collections import defaultdict

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def search_pubmed(query, retmax=100):
    """Search PubMed and return PMIDs."""
    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': retmax,
        'retmode': 'json'
    }
    url = BASE_URL + "esearch.fcgi?" + urllib.parse.urlencode(params)
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            import json
            data = json.loads(response.read().decode())
            return data.get('esearchresult', {}).get('idlist', [])
    except Exception as e:
        print(f"Error searching: {e}")
        return []

def fetch_abstracts_with_affiliations(pmids):
    """Fetch article details including affiliations."""
    if not pmids:
        return []
    
    params = {
        'db': 'pubmed',
        'id': ','.join(pmids),
        'retmode': 'xml'
    }
    url = BASE_URL + "efetch.fcgi?" + urllib.parse.urlencode(params)
    
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read().decode()
    except Exception as e:
        print(f"Error fetching: {e}")
        return ""

def extract_affiliations(xml_data):
    """Extract affiliations from PubMed XML."""
    affiliations = []
    try:
        root = ET.fromstring(xml_data)
        for article in root.findall('.//PubmedArticle'):
            pmid = article.find('.//PMID')
            pmid_text = pmid.text if pmid is not None else "Unknown"
            
            # Get affiliations from various places
            for aff in article.findall('.//Affiliation'):
                if aff.text:
                    affiliations.append((pmid_text, aff.text))
            
            for aff in article.findall('.//AffiliationInfo/Affiliation'):
                if aff.text:
                    affiliations.append((pmid_text, aff.text))
    except Exception as e:
        print(f"Error parsing XML: {e}")
    
    return affiliations

def main():
    print("=" * 80)
    print("SCREENING PUBMED FOR DEPARTMENT AFFILIATION VARIATIONS")
    print("University of Padova - DCTV and DSF Departments")
    print("=" * 80)
    
    # Search queries to find variations of the two departments
    # DCTV: Dipartimento di Scienze Cardio-Toraco-Vascolari e Sanità Pubblica
    # DSF: Dipartimento di Scienze del Farmaco
    
    dctv_queries = [
        '"Cardio-Toraco-Vascolar"[Affiliation] AND Padova[Affiliation]',
        '"Cardiac Thoracic Vascular"[Affiliation] AND Padova[Affiliation]',
        '"Sanità Pubblica"[Affiliation] AND Padova[Affiliation]',
        '"Public Health"[Affiliation] AND Padova[Affiliation] AND (Cardiac OR Cardio OR Vascular)',
        '"DCTV"[Affiliation] AND Padova[Affiliation]',
        '"Cardiothoracic"[Affiliation] AND Padova[Affiliation]',
    ]
    
    dsf_queries = [
        '"Scienze del Farmaco"[Affiliation] AND Padova[Affiliation]',
        '"Pharmaceutical Sciences"[Affiliation] AND Padova[Affiliation]',
        '"Pharmacological Sciences"[Affiliation] AND Padova[Affiliation]',
        '"Pharmaceutical and Pharmacological"[Affiliation] AND Padova[Affiliation]',
        '"DSF"[Affiliation] AND Padova[Affiliation] AND (Pharma OR Drug)',
        '"Department of Pharmaceutical"[Affiliation] AND (Padova OR Padua)[Affiliation]',
    ]
    
    print("\n" + "=" * 80)
    print("PART 1: DCTV DEPARTMENT VARIATIONS")
    print("(Dipartimento di Scienze Cardio-Toraco-Vascolari e Sanità Pubblica)")
    print("=" * 80)
    
    dctv_affiliations = defaultdict(list)
    
    for query in dctv_queries:
        print(f"\nSearching: {query}")
        pmids = search_pubmed(query, retmax=50)
        print(f"  Found {len(pmids)} results")
        
        if pmids:
            time.sleep(0.5)  # Be nice to NCBI
            xml_data = fetch_abstracts_with_affiliations(pmids)
            affs = extract_affiliations(xml_data)
            
            for pmid, aff in affs:
                # Filter for Padova-related affiliations
                if 'padov' in aff.lower() or 'padua' in aff.lower():
                    dctv_affiliations[aff].append(pmid)
        
        time.sleep(0.5)
    
    print("\n" + "-" * 40)
    print("UNIQUE DCTV-RELATED AFFILIATIONS FOUND:")
    print("-" * 40)
    
    for i, (aff, pmids) in enumerate(sorted(dctv_affiliations.items(), key=lambda x: -len(x[1]))[:30], 1):
        print(f"\n{i}. [{len(pmids)} articles] Example PMID: {pmids[0]}")
        print(f"   {aff[:200]}{'...' if len(aff) > 200 else ''}")
    
    print("\n" + "=" * 80)
    print("PART 2: DSF DEPARTMENT VARIATIONS")
    print("(Dipartimento di Scienze del Farmaco)")
    print("=" * 80)
    
    dsf_affiliations = defaultdict(list)
    
    for query in dsf_queries:
        print(f"\nSearching: {query}")
        pmids = search_pubmed(query, retmax=50)
        print(f"  Found {len(pmids)} results")
        
        if pmids:
            time.sleep(0.5)
            xml_data = fetch_abstracts_with_affiliations(pmids)
            affs = extract_affiliations(xml_data)
            
            for pmid, aff in affs:
                if 'padov' in aff.lower() or 'padua' in aff.lower():
                    dsf_affiliations[aff].append(pmid)
        
        time.sleep(0.5)
    
    print("\n" + "-" * 40)
    print("UNIQUE DSF-RELATED AFFILIATIONS FOUND:")
    print("-" * 40)
    
    for i, (aff, pmids) in enumerate(sorted(dsf_affiliations.items(), key=lambda x: -len(x[1]))[:30], 1):
        print(f"\n{i}. [{len(pmids)} articles] Example PMID: {pmids[0]}")
        print(f"   {aff[:200]}{'...' if len(aff) > 200 else ''}")
    
    # Save results to file
    with open('affiliation_screening_results.txt', 'w') as f:
        f.write("PUBMED AFFILIATION SCREENING RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("DCTV DEPARTMENT VARIATIONS:\n")
        f.write("-" * 40 + "\n")
        for aff, pmids in sorted(dctv_affiliations.items(), key=lambda x: -len(x[1])):
            f.write(f"\n[{len(pmids)} articles] PMIDs: {', '.join(pmids[:5])}{'...' if len(pmids) > 5 else ''}\n")
            f.write(f"{aff}\n")
        
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("DSF DEPARTMENT VARIATIONS:\n")
        f.write("-" * 40 + "\n")
        for aff, pmids in sorted(dsf_affiliations.items(), key=lambda x: -len(x[1])):
            f.write(f"\n[{len(pmids)} articles] PMIDs: {', '.join(pmids[:5])}{'...' if len(pmids) > 5 else ''}\n")
            f.write(f"{aff}\n")
    
    print("\n" + "=" * 80)
    print("Results saved to: affiliation_screening_results.txt")
    print("=" * 80)

if __name__ == "__main__":
    main()
