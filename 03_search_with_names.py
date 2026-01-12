#!/usr/bin/env python3
"""
Search PubMed for collaborative publications between DCTV and DSF departments.
Uses BOTH affiliation patterns AND faculty names from department websites.

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

# Faculty names from department websites (current staff)
# Format: "Lastname Firstname" for PubMed author search
DCTV_FACULTY = [
    # Professori Ordinari
    "Angelini Annalisa", "Baldo Vincenzo", "Basso Cristina", "Calabrese Fiorella",
    "Corrado Domenico", "Cozzi Emanuele", "Gerosa Gino", "Grego Franco",
    "Gregori Dario", "Montisci Massimo", "Spagnolo Paolo", "Stramare Roberto",
    "Tarantini Giuseppe", "Tona Francesco", "Vida Vladimiro",
    # Professori Associati Confermati
    "Adimari Gianfranco", "Aprile Anna", "Favretto Donata", "Meloni Federica",
    # Professori Associati
    "Antonello Michele", "Baldi Ileana", "Baldovin Tatjana", "Baraldo Simonetta",
    "Bauce Barbara", "Bazzan Erica", "Bertoncello Chiara", "Biondini Davide",
    "Buja Alessandra", "Caenazzo Luciana", "Caforio Alida", "Canova Cristina",
    "Carrieri Mariella", "Castellani Chiara", "Catelan Dolores", "Cipriani Alberto",
    "Cocchio Silvia", "D'Onofrio Augusto", "Dell'Amore Andrea", "Frigo Anna Chiara",
    "Gianfredi Vincenza", "Iop Laura", "Mason Paola", "Migliore Federico",
    "Motta Raffaella", "Pavanello Sofia", "Perazzolo Marra Martina", "Piazza Michele",
    "Pilichou Kalliopi", "Rizzo Stefania", "Scapellato Maria Luisa", "Schiavon Marco",
    "Squizzato Francesco", "Tarzia Vincenzo", "Terranova Claudio", "Turato Graziella",
    "Vianello Andrea", "Viel Guido", "Zampieri Fabio", "Zorzi Alessandro",
    # Ricercatori
    "Menegolo Mirko", "Bernardinello Nicol", "Campisi Manuela", "Cecere Annagrazia",
    "Colacchio Elda Chiara", "De Gaspari Monica", "De Michieli Laura", "Faccioli Eleonora",
    "Franchetti Giorgia", "Giordani Andrea Silvio", "Graziano Francesca", "Liviero Filippo",
    "Longhini Jessica", "Martinato Matteo", "Ocagli Honoria", "Sabbatini Daniele",
    "Stoppa Giorgia", "Tine Mariaenrica", "Vadori Marta", "Vedovelli Luca",
    "Zanatta Alberto", "Giraudo Chiara", "Lorenzoni Giulia", "Pezzuto Federica", "Tozzo Pamela",
]

DSF_FACULTY = [
    # Professori Ordinari
    "Brini Marisa", "Caliceti Paolo", "Calo Girolamo", "Conconi Maria Teresa",
    "Gatto Barbara", "Morari Michele", "Moro Stefano", "Pasut Gianfranco",
    "Salmaso Stefano", "Sissi Claudia",
    # Professori Associati Confermati
    "Bertazzo Antonella", "Chilin Adriana", "Dalla Via Lisa", "De Filippis Vincenzo",
    "Dolmella Alessandro", "Filippini Raffaella", "Froldi Guglielmina", "Miolo Giorgia",
    # Professori Associati
    "Bolego Chiara", "Colucci Rocchina", "Comai Stefano", "Dall'Acqua Stefano",
    "De Martin Sara", "Di Liddo Rosa", "Franceschinis Erica", "Gandin Valentina",
    "Garofalo Mariangela", "Giron Maria Cecilia", "Malfanti Alessio", "Marzano Cristina",
    "Mastrotto Francesca", "Mattarei Andrea", "Montopoli Monica", "Morpurgo Margherita",
    "Piovan Anna", "Polverino De Laureto Patrizia", "Sosic Alice", "Spolaore Barbara",
    "Sturlese Mattia", "Zusso Morena",
    # Ricercatori
    "Quintieri Luigi", "Semenzato Alessandra", "Trevisi Lucia", "Acquasaliente Laura",
    "Franchin Cinzia", "Gabbia Daniela", "Bortolozzi Roberta", "Malfacini Davide",
    "Menilli Luca", "Rampado Riccardo", "Grigoletto Antonella", "Rigo Riccardo",
    "Runfola Massimiliano", "Salmaso Veronica",
]

# Affiliation patterns based on screening results
# DCTV: Dipartimento di Scienze Cardio-Toraco-Vascolari e Sanità Pubblica
DCTV_PATTERNS = [
    # With Public Health
    r"cardiac.*thoracic.*vascular.*sciences.*public.*health",
    r"cardiac.*thoracic.*vascular.*public.*health",
    r"cardio.*thoraco.*vascular.*public.*health",
    r"cardiovascular.*public.*health.*padov",
    r"cardiovascular.*public.*health.*padua",
    # Without Public Health (older naming)
    r"cardiac.*thoracic.*vascular.*sciences.*padov",
    r"cardiac.*thoracic.*vascular.*sciences.*padua",
    r"cardiac,?\s*thoracic,?\s*(and\s+)?vascular.*padov",
    r"cardiac,?\s*thoracic,?\s*(and\s+)?vascular.*padua",
    # Legal Medicine and Toxicology (part of DCTV)
    r"legal\s+medicine.*padov",
    r"legal\s+medicine.*padua",
    r"medicina\s+legale.*padov",
    # Italian variations
    r"cardio.*toraco.*vascolar.*sanit",
    r"scienze.*cardio.*toraco.*vascolar",
    # Abbreviation
    r"\bdctv\b",
]

DSF_PATTERNS = [
    r"pharmaceutical.*pharmacological.*sciences.*padov",
    r"pharmaceutical.*pharmacological.*sciences.*padua",
    r"pharmaceutical\s+(&|and)\s+pharmacological.*padov",
    r"pharmaceutical\s+(&|and)\s+pharmacological.*padua",
    r"scienze.*del.*farmaco.*padov",
    r"scienze.*del.*farmaco.*padua",
]

def search_pubmed(query, retmax=200):
    """Search PubMed and return PMIDs."""
    params = {
        'db': 'pubmed',
        'term': query,
        'retmax': retmax,
        'retmode': 'json',
    }
    url = BASE_URL + "esearch.fcgi?" + urllib.parse.urlencode(params)
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
            result = data.get('esearchresult', {})
            count = result.get('count', '0')
            pmids = result.get('idlist', [])
            return pmids, int(count)
    except Exception as e:
        print(f"  Error: {e}")
        return [], 0

def fetch_articles(pmids):
    """Fetch article details including affiliations."""
    if not pmids:
        return []
    
    articles = []
    # Fetch in batches of 50
    for i in range(0, len(pmids), 50):
        batch = pmids[i:i+50]
        params = {
            'db': 'pubmed',
            'id': ','.join(batch),
            'retmode': 'xml'
        }
        url = BASE_URL + "efetch.fcgi?" + urllib.parse.urlencode(params)
        
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                xml_data = response.read().decode()
                articles.extend(parse_xml(xml_data))
            time.sleep(0.4)
        except Exception as e:
            print(f"  Fetch error: {e}")
    
    return articles

def parse_xml(xml_data):
    """Parse PubMed XML and extract article info."""
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for article in root.findall('.//PubmedArticle'):
            pmid_elem = article.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else "Unknown"
            
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "No title"
            
            journal_elem = article.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ""
            
            year_elem = article.find('.//PubDate/Year')
            if year_elem is None:
                year_elem = article.find('.//PubDate/MedlineDate')
            year = year_elem.text[:4] if year_elem is not None and year_elem.text else ""
            
            affiliations = []
            for aff in article.findall('.//AffiliationInfo/Affiliation'):
                if aff.text:
                    affiliations.append(aff.text)
            for aff in article.findall('.//Affiliation'):
                if aff.text and aff.text not in affiliations:
                    affiliations.append(aff.text)
            
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
    except ET.ParseError:
        pass
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
                if aff not in matches:
                    matches.append(aff)
                break
    return matches

def check_author_in_list(authors, faculty_list):
    """Check if any author is in the faculty list. Strict matching with compound surname handling."""
    matches = []
    for author in authors:
        author_lower = author.lower().strip()
        
        for faculty in faculty_list:
            fac_lower = faculty.lower().strip()
            fac_parts = fac_lower.split()
            
            if len(fac_parts) < 2:
                continue
            
            # Handle compound surnames (e.g., "De Filippis Vincenzo", "Dalla Via Lisa")
            # Faculty format: "Lastname Firstname" or "Compound Lastname Firstname"
            fac_firstname = fac_parts[-1]  # Last word is firstname
            fac_lastname = ' '.join(fac_parts[:-1])  # Everything else is lastname
            
            # Author format from PubMed: "Lastname Firstname" 
            author_parts = author_lower.split()
            if len(author_parts) < 2:
                continue
            
            # Try to match compound surnames
            # Check if author starts with faculty lastname and ends with matching firstname
            author_firstname = author_parts[-1]
            author_lastname = ' '.join(author_parts[:-1])
            
            # Strict match: exact lastname AND firstname at least 5 chars match
            if (author_lastname == fac_lastname and 
                len(author_firstname) >= 5 and 
                len(fac_firstname) >= 5 and
                author_firstname[:5] == fac_firstname[:5]):
                matches.append(author)
                break
    return matches

def main():
    print("=" * 80)
    print("PUBMED COLLABORATION SEARCH: DCTV x DSF")
    print("University of Padova")
    print("=" * 80)
    print(f"Search date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nDCTV faculty loaded: {len(DCTV_FACULTY)}")
    print(f"DSF faculty loaded: {len(DSF_FACULTY)}")
    
    all_pmids = set()
    
    # STRATEGY 1: Search by affiliation patterns
    print("\n" + "=" * 60)
    print("PHASE 1: AFFILIATION-BASED SEARCH")
    print("=" * 60)
    
    affiliation_queries = [
        '("Pharmaceutical and Pharmacological Sciences"[Affiliation] OR "Scienze del Farmaco"[Affiliation]) AND (Padova[Affiliation] OR Padua[Affiliation]) AND ("Cardiac"[Affiliation] OR "Cardio"[Affiliation] OR "Public Health"[Affiliation] OR "DCTV"[Affiliation])',
        '("Cardiac Thoracic Vascular"[Affiliation] OR "Cardio-Toraco-Vascolar"[Affiliation]) AND (Padova[Affiliation] OR Padua[Affiliation]) AND ("Pharmaceutical"[Affiliation] OR "Pharmacological"[Affiliation] OR "Farmaco"[Affiliation])',
        # Legal Medicine cross with DSF
        '"Legal Medicine"[Affiliation] AND (Padova[Affiliation] OR Padua[Affiliation]) AND ("Pharmaceutical"[Affiliation] OR "Pharmacological"[Affiliation])',
    ]
    
    for q in affiliation_queries:
        print(f"\nQuery: {q[:80]}...")
        pmids, count = search_pubmed(q, retmax=300)
        print(f"  Found: {count} total, retrieved {len(pmids)}")
        all_pmids.update(pmids)
        time.sleep(0.5)
    
    # STRATEGY 2: Cross-search faculty names
    print("\n" + "=" * 60)
    print("PHASE 2: FACULTY NAME CROSS-SEARCH")
    print("=" * 60)
    
    # Select key faculty members for cross-search (to avoid too many queries)
    key_dctv = ["Basso Cristina", "Gerosa Gino", "Corrado Domenico", "Buja Alessandra", 
                "Baldo Vincenzo", "Calabrese Fiorella", "Caenazzo Luciana", "Favretto Donata",
                "Tona Francesco", "Iop Laura", "Giraudo Chiara", "Tozzo Pamela"]
    key_dsf = ["Caliceti Paolo", "Salmaso Stefano", "Moro Stefano", "De Filippis Vincenzo",
               "Conconi Maria Teresa", "Di Liddo Rosa", "Montopoli Monica", "Gabbia Daniela",
               "De Martin Sara", "Zusso Morena", "Miolo Giorgia", "Acquasaliente Laura"]
    
    print(f"\nCross-searching {len(key_dctv)} DCTV x {len(key_dsf)} DSF faculty...")
    
    # Search for DCTV faculty with DSF affiliation
    for dctv_name in key_dctv:
        parts = dctv_name.split()
        lastname = parts[0]
        firstname = parts[1] if len(parts) > 1 else ""
        
        query = f'{lastname} {firstname}[Author] AND (Padova[Affiliation] OR Padua[Affiliation]) AND ("Pharmaceutical"[Affiliation] OR "Pharmacological"[Affiliation] OR "Farmaco"[Affiliation])'
        pmids, count = search_pubmed(query, retmax=50)
        if pmids:
            print(f"  {dctv_name}: {len(pmids)} potential")
            all_pmids.update(pmids)
        time.sleep(0.3)
    
    # Search for DSF faculty with DCTV affiliation
    for dsf_name in key_dsf:
        parts = dsf_name.split()
        lastname = parts[0]
        firstname = parts[1] if len(parts) > 1 else ""
        
        query = f'{lastname} {firstname}[Author] AND (Padova[Affiliation] OR Padua[Affiliation]) AND ("Cardiac"[Affiliation] OR "Cardio"[Affiliation] OR "Public Health"[Affiliation] OR "Vascular"[Affiliation])'
        pmids, count = search_pubmed(query, retmax=50)
        if pmids:
            print(f"  {dsf_name}: {len(pmids)} potential")
            all_pmids.update(pmids)
        time.sleep(0.3)
    
    print(f"\n\nTotal unique PMIDs to analyze: {len(all_pmids)}")
    
    if not all_pmids:
        print("No articles found!")
        return
    
    # Fetch and analyze articles
    print("\n" + "=" * 60)
    print("PHASE 3: FETCHING AND ANALYZING ARTICLES")
    print("=" * 60)
    
    articles = fetch_articles(list(all_pmids))
    print(f"Fetched {len(articles)} articles")
    
    # Filter for true collaborations
    collaborations = []
    
    for article in articles:
        all_affs = ' '.join(article['affiliations']).lower()
        is_padova = 'padov' in all_affs or 'padua' in all_affs
        
        # Check affiliation patterns
        has_dctv_aff = check_affiliation_match(article['affiliations'], DCTV_PATTERNS)
        has_dsf_aff = check_affiliation_match(article['affiliations'], DSF_PATTERNS)
        
        # Check faculty names
        dctv_authors = check_author_in_list(article['authors'], DCTV_FACULTY)
        dsf_authors = check_author_in_list(article['authors'], DSF_FACULTY)
        
        # COLLABORATION RULE: 
        # Both affiliations must be present (DCTV AND DSF in Padova)
        # Faculty names are used only for additional info, not for filtering
        # This avoids false positives from name matching
        
        has_both_affiliations = has_dctv_aff and has_dsf_aff and is_padova
        
        if not has_both_affiliations:
            continue
        
        article['dctv_affiliations'] = get_matching_affiliations(article['affiliations'], DCTV_PATTERNS)
        article['dsf_affiliations'] = get_matching_affiliations(article['affiliations'], DSF_PATTERNS)
        article['dctv_authors'] = dctv_authors
        article['dsf_authors'] = dsf_authors
        collaborations.append(article)
    
    # Remove duplicates by PMID
    seen = set()
    unique_collabs = []
    for c in collaborations:
        if c['pmid'] not in seen:
            seen.add(c['pmid'])
            unique_collabs.append(c)
    collaborations = unique_collabs
    
    # Sort by year (most recent first)
    collaborations.sort(key=lambda x: x.get('year', '0000'), reverse=True)
    
    print(f"\n{'='*60}")
    print(f"FOUND {len(collaborations)} COLLABORATIVE PUBLICATIONS")
    print(f"{'='*60}")
    
    # Display results
    for i, article in enumerate(collaborations, 1):
        print(f"\n{'='*80}")
        print(f"[{i}] PMID: {article['pmid']}")
        print(f"Year: {article['year']}")
        print(f"Title: {article['title'][:100]}{'...' if len(article['title']) > 100 else ''}")
        print(f"Journal: {article['journal']}")
        print(f"Authors: {', '.join(article['authors'][:6])}{'...' if len(article['authors']) > 6 else ''}")
        
        if article['dctv_authors']:
            print(f"\n  DCTV Authors: {', '.join(article['dctv_authors'])}")
        if article['dctv_affiliations']:
            print(f"  DCTV Affiliation: {article['dctv_affiliations'][0][:100]}...")
        
        if article['dsf_authors']:
            print(f"\n  DSF Authors: {', '.join(article['dsf_authors'])}")
        if article['dsf_affiliations']:
            print(f"  DSF Affiliation: {article['dsf_affiliations'][0][:100]}...")
        
        print(f"\n  PubMed: https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save text report
    output_file = f"collaborations_dctv_dsf_{timestamp}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("COLLABORATIVE PUBLICATIONS: DCTV x DSF\n")
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
            f.write(f"\nDCTV Authors matched: {', '.join(article['dctv_authors']) if article['dctv_authors'] else 'None'}\n")
            f.write(f"DSF Authors matched: {', '.join(article['dsf_authors']) if article['dsf_authors'] else 'None'}\n")
            f.write(f"\nAll affiliations:\n")
            for aff in article['affiliations']:
                f.write(f"  - {aff}\n")
            f.write(f"\nPubMed: https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/\n")
            f.write("-" * 80 + "\n\n")
    
    # Save JSON
    json_file = f"collaborations_dctv_dsf_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(collaborations, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n{'='*80}")
    print(f"Results saved to: {output_file}")
    print(f"JSON data saved to: {json_file}")
    print(f"{'='*80}")
    
    # Summary of PMIDs for verification
    print("\n\nPMIDs for manual verification on PubMed:")
    pmid_list = [a['pmid'] for a in collaborations]
    print(", ".join(pmid_list))
    
    if pmid_list:
        print(f"\n\nDirect PubMed search link:")
        print(f"https://pubmed.ncbi.nlm.nih.gov/?term={'+OR+'.join(pmid_list[:20])}")

if __name__ == "__main__":
    main()
