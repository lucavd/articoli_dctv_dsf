#!/usr/bin/env python3
"""
Step 2: Search PubMed for collaborative publications between DCTV and DSF departments.
This script searches for articles where BOTH departments are present in affiliations.

DCTV = Dipartimento di Scienze Cardio-Toraco-Vascolari e Sanità Pubblica
DSF = Dipartimento di Scienze del Farmaco (Pharmaceutical and Pharmacological Sciences)
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time
import json
import re
from datetime import datetime

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# Affiliation patterns based on screening results
DCTV_PATTERNS = [
    # English variations
    "cardiac.*thoracic.*vascular.*public.*health",
    "cardio.*thoraco.*vascular.*public.*health",
    "cardiothoracic.*vascular.*public.*health",
    # Italian variations  
    "cardio.*toraco.*vascolar.*sanit",
    "scienze.*cardio.*toraco.*vascolar",
    # Abbreviation
    "dctv",
]

DSF_PATTERNS = [
    # English variations
    "pharmaceutical.*pharmacological.*sciences",
    "pharmaceutical.*sciences.*padov",
    "pharmacological.*sciences.*padov",
    # Italian variations
    "scienze.*del.*farmaco",
    # Note: DSF alone is too generic
]

def search_pubmed(query, retmax=500):
    """Search PubMed and return PMIDs."""
    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': retmax,
        'retmode': 'json',
        'usehistory': 'y'
    }
    url = BASE_URL + "esearch.fcgi?" + urllib.parse.urlencode(params)
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
            result = data.get('esearchresult', {})
            count = result.get('count', '0')
            pmids = result.get('idlist', [])
            print(f"  Total count: {count}, Retrieved: {len(pmids)}")
            return pmids
    except Exception as e:
        print(f"Error searching: {e}")
        return []

def fetch_articles(pmids):
    """Fetch article details including affiliations."""
    if not pmids:
        return ""
    
    # Fetch in batches of 100
    all_xml = ""
    for i in range(0, len(pmids), 100):
        batch = pmids[i:i+100]
        params = {
            'db': 'pubmed',
            'id': ','.join(batch),
            'retmode': 'xml'
        }
        url = BASE_URL + "efetch.fcgi?" + urllib.parse.urlencode(params)
        
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                all_xml += response.read().decode()
            time.sleep(0.4)
        except Exception as e:
            print(f"Error fetching batch: {e}")
    
    return all_xml

def parse_articles(xml_data):
    """Parse PubMed XML and extract article info with affiliations."""
    articles = []
    
    # Handle multiple XML documents concatenated
    xml_chunks = xml_data.split('<?xml version="1.0"')
    
    for chunk in xml_chunks:
        if not chunk.strip():
            continue
        if not chunk.startswith('<?xml'):
            chunk = '<?xml version="1.0"' + chunk
        
        try:
            root = ET.fromstring(chunk)
            
            for article in root.findall('.//PubmedArticle'):
                pmid_elem = article.find('.//PMID')
                pmid = pmid_elem.text if pmid_elem is not None else "Unknown"
                
                # Get title
                title_elem = article.find('.//ArticleTitle')
                title = title_elem.text if title_elem is not None else "No title"
                
                # Get journal
                journal_elem = article.find('.//Journal/Title')
                journal = journal_elem.text if journal_elem is not None else ""
                
                # Get year
                year_elem = article.find('.//PubDate/Year')
                if year_elem is None:
                    year_elem = article.find('.//PubDate/MedlineDate')
                year = year_elem.text[:4] if year_elem is not None and year_elem.text else ""
                
                # Get all affiliations
                affiliations = []
                for aff in article.findall('.//AffiliationInfo/Affiliation'):
                    if aff.text:
                        affiliations.append(aff.text)
                
                # Also check old-style affiliations
                for aff in article.findall('.//Affiliation'):
                    if aff.text and aff.text not in affiliations:
                        affiliations.append(aff.text)
                
                # Get authors
                authors = []
                for author in article.findall('.//Author'):
                    lastname = author.find('LastName')
                    forename = author.find('ForeName')
                    if lastname is not None:
                        name = lastname.text
                        if forename is not None:
                            name += " " + forename.text
                        authors.append(name)
                
                articles.append({
                    'pmid': pmid,
                    'title': title,
                    'journal': journal,
                    'year': year,
                    'authors': authors,
                    'affiliations': affiliations
                })
        except ET.ParseError as e:
            continue
    
    return articles

def check_affiliation_match(affiliations, patterns):
    """Check if any affiliation matches any pattern."""
    all_affs = ' '.join(affiliations).lower()
    for pattern in patterns:
        if re.search(pattern, all_affs, re.IGNORECASE):
            return True
    return False

def get_matching_affiliations(affiliations, patterns):
    """Get the specific affiliations that match the patterns."""
    matches = []
    for aff in affiliations:
        for pattern in patterns:
            if re.search(pattern, aff, re.IGNORECASE):
                matches.append(aff)
                break
    return matches

def main():
    print("=" * 80)
    print("PUBMED COLLABORATION SEARCH")
    print("DCTV x DSF - University of Padova")
    print("=" * 80)
    print(f"\nSearch date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Strategy: Search for Padova + indicators of both departments
    # Then filter locally for articles with BOTH departments
    
    search_queries = [
        # Combined searches that might catch collaborations
        '("Pharmaceutical and Pharmacological Sciences"[Affiliation] OR "Scienze del Farmaco"[Affiliation]) AND (Padova[Affiliation] OR Padua[Affiliation]) AND ("Cardiac"[Affiliation] OR "Cardio"[Affiliation] OR "Public Health"[Affiliation])',
        
        '("Cardiac Thoracic Vascular"[Affiliation] OR "Cardio-Toraco-Vascolar"[Affiliation] OR "DCTV"[Affiliation]) AND (Padova[Affiliation] OR Padua[Affiliation]) AND ("Pharmaceutical"[Affiliation] OR "Pharmacological"[Affiliation] OR "Farmaco"[Affiliation])',
        
        # Broader search with University of Padova
        '"University of Padova"[Affiliation] AND "Pharmaceutical"[Affiliation] AND ("Cardiac"[Affiliation] OR "Public Health"[Affiliation])',
        
        '"University of Padua"[Affiliation] AND "Pharmaceutical"[Affiliation] AND ("Cardiac"[Affiliation] OR "Public Health"[Affiliation])',
        
        # Search with department names
        '"Department of Pharmaceutical and Pharmacological Sciences"[Affiliation] AND Padova[Affiliation]',
        
        '"Department of Cardiac, Thoracic, Vascular Sciences and Public Health"[Affiliation]',
        
        '"Department of Cardiac Thoracic Vascular Sciences and Public Health"[Affiliation]',
    ]
    
    all_pmids = set()
    
    print("\n" + "-" * 40)
    print("SEARCHING PUBMED...")
    print("-" * 40)
    
    for query in search_queries:
        print(f"\nQuery: {query[:70]}...")
        pmids = search_pubmed(query, retmax=500)
        all_pmids.update(pmids)
        time.sleep(0.5)
    
    print(f"\n\nTotal unique PMIDs collected: {len(all_pmids)}")
    
    if not all_pmids:
        print("No articles found!")
        return
    
    print("\n" + "-" * 40)
    print("FETCHING ARTICLE DETAILS...")
    print("-" * 40)
    
    xml_data = fetch_articles(list(all_pmids))
    articles = parse_articles(xml_data)
    
    print(f"Parsed {len(articles)} articles")
    
    # Filter for articles with BOTH departments
    print("\n" + "-" * 40)
    print("FILTERING FOR COLLABORATIONS...")
    print("-" * 40)
    
    collaborations = []
    
    for article in articles:
        has_dctv = check_affiliation_match(article['affiliations'], DCTV_PATTERNS)
        has_dsf = check_affiliation_match(article['affiliations'], DSF_PATTERNS)
        
        if has_dctv and has_dsf:
            # Also check it's actually Padova
            all_affs = ' '.join(article['affiliations']).lower()
            if 'padov' in all_affs or 'padua' in all_affs:
                article['dctv_affiliations'] = get_matching_affiliations(article['affiliations'], DCTV_PATTERNS)
                article['dsf_affiliations'] = get_matching_affiliations(article['affiliations'], DSF_PATTERNS)
                collaborations.append(article)
    
    print(f"\nFound {len(collaborations)} collaborative articles!")
    
    # Sort by year (most recent first)
    collaborations.sort(key=lambda x: x.get('year', '0000'), reverse=True)
    
    # Display results
    print("\n" + "=" * 80)
    print("COLLABORATIVE PUBLICATIONS (DCTV + DSF)")
    print("=" * 80)
    
    for i, article in enumerate(collaborations, 1):
        print(f"\n{'='*80}")
        print(f"[{i}] PMID: {article['pmid']}")
        print(f"Year: {article['year']}")
        print(f"Title: {article['title']}")
        print(f"Journal: {article['journal']}")
        print(f"Authors: {', '.join(article['authors'][:5])}{'...' if len(article['authors']) > 5 else ''}")
        print(f"\nDCTV Affiliation(s):")
        for aff in article['dctv_affiliations'][:2]:
            print(f"  - {aff[:150]}{'...' if len(aff) > 150 else ''}")
        print(f"\nDSF Affiliation(s):")
        for aff in article['dsf_affiliations'][:2]:
            print(f"  - {aff[:150]}{'...' if len(aff) > 150 else ''}")
        print(f"\nPubMed link: https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/")
    
    # Save results to file
    output_file = f"collaborations_dctv_dsf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("COLLABORATIVE PUBLICATIONS BETWEEN DCTV AND DSF\n")
        f.write("University of Padova\n")
        f.write(f"Search date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total collaborations found: {len(collaborations)}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, article in enumerate(collaborations, 1):
            f.write(f"[{i}] PMID: {article['pmid']}\n")
            f.write(f"Year: {article['year']}\n")
            f.write(f"Title: {article['title']}\n")
            f.write(f"Journal: {article['journal']}\n")
            f.write(f"Authors: {', '.join(article['authors'])}\n")
            f.write(f"\nAll affiliations:\n")
            for aff in article['affiliations']:
                f.write(f"  - {aff}\n")
            f.write(f"\nDCTV matches:\n")
            for aff in article['dctv_affiliations']:
                f.write(f"  * {aff}\n")
            f.write(f"\nDSF matches:\n")
            for aff in article['dsf_affiliations']:
                f.write(f"  * {aff}\n")
            f.write(f"\nPubMed: https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/\n")
            f.write("-" * 80 + "\n\n")
    
    # Also save as JSON for further processing
    json_file = f"collaborations_dctv_dsf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(collaborations, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n{'='*80}")
    print(f"Results saved to: {output_file}")
    print(f"JSON data saved to: {json_file}")
    print(f"{'='*80}")
    
    # Print PMIDs for easy verification
    print("\n\nPMIDs for manual verification on PubMed:")
    print(", ".join([a['pmid'] for a in collaborations]))

if __name__ == "__main__":
    main()
